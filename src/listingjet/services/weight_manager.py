import logging
from typing import Literal

try:
    import xgboost as xgb
    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False

GLOBAL_BASELINE_WEIGHT = 1.0  # updated after Juke eval set reaches 200 examples
WEIGHT_MIN = 0.1
WEIGHT_MAX = 2.0
BLEND_LISTING_THRESHOLD = 10  # listings (not events) before full tenant weights
COLD_START_THRESHOLD = 3  # listings below which a weight can be safely reset
MIN_TRAIN_SAMPLES = 50  # minimum labeled events before XGBoost training runs

logger = logging.getLogger(__name__)

# Outcome boost blending: how much weight outcome data gets vs base score
# Ramps from 0→OUTCOME_MAX_INFLUENCE as closed listings grow past MIN_OUTCOMES
OUTCOME_MIN_SAMPLES = 3
OUTCOME_MAX_INFLUENCE = 0.15  # max 15% adjustment from outcome data

_POSITIVE_OUTCOMES = frozenset({"approval", "swap_to"})
_NEGATIVE_OUTCOMES = frozenset({"rejection", "swap_from"})

# Module-level model cache — shared across all WeightManager instances.
# Reset to None when retrain produces a new model or in tests.
_xgb_model: "xgb.Booster | None" = None


class WeightManager:
    """
    Single source of truth for Learning Agent weight operations.
    Scoring backend is swappable: rule-based now, XGBoost in Phase 2.
    See TODOS.md TODO-4 for XGBoost upgrade plan.
    """

    def blend(
        self,
        tenant_id: str,
        room_label: str,
        labeled_listing_count: int,
        tenant_weight: float,
        global_weight: float = GLOBAL_BASELINE_WEIGHT,
    ) -> float:
        """Blend global baseline with tenant-specific weight based on labeled listing count."""
        ratio = min(labeled_listing_count / BLEND_LISTING_THRESHOLD, 1.0)
        return ratio * tenant_weight + (1 - ratio) * global_weight

    def apply_update(
        self,
        current_weight: float,
        action: Literal["approval", "rejection", "swap_to", "swap_from"],
    ) -> float:
        """Apply delta + regression-to-mean pull + hard clamp."""
        deltas = {"approval": 0.05, "rejection": -0.05, "swap_to": 0.03, "swap_from": -0.03}
        delta = deltas[action]
        # Regression-to-mean: 0.01 pull toward 1.0 on every update
        pull = 0.01 if current_weight > 1.0 else -0.01
        new_weight = current_weight + delta - pull
        clamped = max(WEIGHT_MIN, min(WEIGHT_MAX, new_weight))
        if clamped == WEIGHT_MIN or clamped == WEIGHT_MAX:
            logger.warning(
                "weight_clamped action=%s current=%.3f new=%.3f boundary=%.1f",
                action, current_weight, new_weight, clamped,
            )
        return clamped

    def apply_decay(self, weight: float, days_since_update: int) -> float:
        """Regress stale weights toward 1.0 after 90 days of inactivity."""
        if days_since_update < 90:
            return weight
        decay = min(0.1 * ((days_since_update - 90) / 30), 0.5)  # max 50% decay
        return weight * (1 - decay) + 1.0 * decay

    def apply_outcome_boost(
        self,
        base_score: float,
        outcome_boost: float,
        sample_count: int,
    ) -> float:
        """Apply outcome-based boost from PhotoOutcomeCorrelation data.

        The influence ramps up as sample_count grows, capped at
        OUTCOME_MAX_INFLUENCE.  A boost of 1.1 with full influence
        raises the score by ~1.5%.
        """
        if sample_count < OUTCOME_MIN_SAMPLES or outcome_boost == 1.0:
            return base_score

        # Ramp influence: 3 samples → 33%, 10+ → 100% of max influence
        ramp = min((sample_count - OUTCOME_MIN_SAMPLES + 1) / 7.0, 1.0)
        influence = ramp * OUTCOME_MAX_INFLUENCE

        # Apply boost as a blend: score * (1 + influence * (boost - 1))
        adjusted = base_score * (1.0 + influence * (outcome_boost - 1.0))
        return min(1.0, max(0.0, adjusted))

    @staticmethod
    def _to_feature_vector(features: dict) -> list[float]:
        return [
            features.get("quality_score", 50) / 100.0,
            features.get("commercial_score", 50) / 100.0,
            1.0 if features.get("hero_candidate", False) else 0.0,
            features.get("room_weight", 1.0),
        ]

    @staticmethod
    def _rule_based_score(features: dict) -> float:
        quality = features.get("quality_score", 50) / 100.0
        commercial = features.get("commercial_score", 50) / 100.0
        hero_bonus = 1.0 if features.get("hero_candidate", False) else 0.0
        room_weight = features.get("room_weight", 1.0)
        composite = (quality * 0.5) + (commercial * 0.3) + (hero_bonus * 0.2)
        return min(1.0, max(0.0, composite * room_weight))

    def _xgb_score(self, features: dict) -> float:
        fv = self._to_feature_vector(features)
        dmat = xgb.DMatrix([fv])
        return float(_xgb_model.predict(dmat)[0])

    def score(self, features: dict) -> float:
        """
        Composite scoring for photo selection.
        Dispatches to XGBoost when a trained model is cached, otherwise uses
        the rule-based formula (quality*0.5 + commercial*0.3 + hero_bonus*0.2) * room_weight.
        Optionally adjusted by outcome_boost from Phase 5 correlations.
        Clamped to [0.0, 1.0].
        """
        if _xgb_model is not None and _XGB_AVAILABLE:
            base = self._xgb_score(features)
        else:
            base = self._rule_based_score(features)

        # Phase 5: outcome boost from real sale performance data
        outcome_boost = features.get("outcome_boost", 1.0)
        outcome_samples = features.get("outcome_samples", 0)
        if outcome_boost != 1.0 and outcome_samples >= OUTCOME_MIN_SAMPLES:
            base = self.apply_outcome_boost(base, outcome_boost, outcome_samples)

        return base

    @staticmethod
    def train_model(events: list[dict]) -> bool:
        """Train XGBoost binary classifier on labeled ScoringEvents.

        *events* is a list of dicts with keys ``features`` (dict) and
        ``outcome`` (str).  Returns True if a new model was cached.
        """
        global _xgb_model

        if not _XGB_AVAILABLE:
            logger.warning("xgboost not installed — skipping model training")
            return False

        labeled = [
            e for e in events
            if e.get("outcome") in _POSITIVE_OUTCOMES | _NEGATIVE_OUTCOMES
        ]

        if len(labeled) < MIN_TRAIN_SAMPLES:
            logger.info(
                "xgb_train_skipped reason=insufficient_samples count=%d required=%d",
                len(labeled), MIN_TRAIN_SAMPLES,
            )
            return False

        X = [WeightManager._to_feature_vector(e.get("features", {})) for e in labeled]
        y = [1.0 if e["outcome"] in _POSITIVE_OUTCOMES else 0.0 for e in labeled]

        dtrain = xgb.DMatrix(X, label=y)
        params = {
            "max_depth": 4,
            "eta": 0.1,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "verbosity": 0,
        }
        _xgb_model = xgb.train(params, dtrain, num_boost_round=50)
        logger.info("xgb_model_trained samples=%d", len(labeled))
        return True

    # ------------------------------------------------------------------
    # Monitoring & cold-start protection
    # ------------------------------------------------------------------

    @staticmethod
    def check_health(weights: list[dict]) -> dict:
        """Return health statistics for a set of tenant learning weights.

        *weights* is a list of dicts with keys ``room_label``, ``weight``,
        and ``labeled_listing_count``.

        Returns a summary dict useful for admin dashboards and alerts.
        """
        if not weights:
            return {
                "total_rooms": 0,
                "min_weight": None,
                "max_weight": None,
                "at_floor": 0,
                "at_ceiling": 0,
                "cold_start_rooms": 0,
                "cold_start_labels": [],
            }

        ws = [w["weight"] for w in weights]
        cold = [
            w["room_label"]
            for w in weights
            if w["labeled_listing_count"] < COLD_START_THRESHOLD
        ]
        return {
            "total_rooms": len(weights),
            "min_weight": min(ws),
            "max_weight": max(ws),
            "at_floor": sum(1 for v in ws if v <= WEIGHT_MIN),
            "at_ceiling": sum(1 for v in ws if v >= WEIGHT_MAX),
            "cold_start_rooms": len(cold),
            "cold_start_labels": cold,
        }

    @staticmethod
    def should_reset_cold_start(labeled_listing_count: int) -> bool:
        """Return True if a weight has too few observations to be reliable."""
        return labeled_listing_count < COLD_START_THRESHOLD
