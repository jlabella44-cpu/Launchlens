import logging
from typing import Literal

GLOBAL_BASELINE_WEIGHT = 1.0  # updated after Juke eval set reaches 200 examples
WEIGHT_MIN = 0.1
WEIGHT_MAX = 2.0
BLEND_LISTING_THRESHOLD = 10  # listings (not events) before full tenant weights
COLD_START_THRESHOLD = 3  # listings below which a weight can be safely reset

logger = logging.getLogger(__name__)


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

    def score(self, features: dict) -> float:
        """
        Composite scoring for photo selection.
        Formula: (quality*0.5 + commercial*0.3 + hero_bonus*0.2) * room_weight
        Clamped to [0.0, 1.0].
        Phase 2: XGBoost model (see TODOS.md TODO-4).
        """
        quality = features.get("quality_score", 50) / 100.0
        commercial = features.get("commercial_score", 50) / 100.0
        hero_bonus = 1.0 if features.get("hero_candidate", False) else 0.0
        room_weight = features.get("room_weight", 1.0)

        composite = (quality * 0.5) + (commercial * 0.3) + (hero_bonus * 0.2)
        return min(1.0, max(0.0, composite * room_weight))

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
