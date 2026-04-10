"""
Comparables service — source of truth for CMA comparable-sales lookup.

Tries Repliers first (when configured + feature-flagged on), falls back to
synthetic data otherwise. The return shape matches what CMAReportAgent
expects so the downstream LLM prompt and HTML template are unchanged.

Returned dict shape per comparable::

    {
        "address": "123 Oak Ave, Austin",
        "beds": 3,
        "baths": 2.0,
        "sqft": 1800,
        "price": 425000,
        "price_per_sqft": 236.11,
        # Optional when sourced from Repliers:
        "sold_date": "2024-11-04",
        "mls_number": "C1234567",
    }
"""
from __future__ import annotations

import logging
import random

from listingjet.config import settings
from listingjet.providers.repliers import RepliersClient, normalize_listing

logger = logging.getLogger(__name__)

# How many comparables we want to return from a single lookup.
TARGET_COMP_COUNT = 6

# Search window around the subject property — keeps comps relevant.
SQFT_WINDOW_PCT = 0.20    # ±20% of subject sqft
BED_WINDOW = 1            # ±1 bedroom


class ComparablesService:
    """Fetches comparable sales, Repliers-first with synthetic fallback."""

    def __init__(self, repliers_client: RepliersClient | None = None):
        self._repliers = repliers_client or RepliersClient()

    async def fetch(self, subject: dict) -> list[dict]:
        """Return comparables for the subject property.

        Args:
            subject: dict with keys address, beds, baths, sqft, year_built,
                     property_type, price (all optional but more = better).

        Returns:
            A list of comparable dicts. Never raises — on any failure we fall
            back to synthetic data so the CMA report always has something to
            render.
        """
        if settings.repliers_cma_enabled and self._repliers.configured:
            try:
                comps = await self._fetch_from_repliers(subject)
                if comps:
                    logger.info(
                        "comparables.repliers_hit count=%d subject_city=%s",
                        len(comps), _extract_city(subject),
                    )
                    return comps
                logger.info(
                    "comparables.repliers_empty subject_city=%s — falling back",
                    _extract_city(subject),
                )
            except Exception:
                logger.exception("comparables.repliers_error — falling back to synthetic")

        return self._synthetic_comparables(subject)

    # ------------------------------------------------------------------
    # Repliers path
    # ------------------------------------------------------------------

    async def _fetch_from_repliers(self, subject: dict) -> list[dict]:
        filters = _build_filters(subject)
        if filters is None:
            # Not enough info to form a meaningful query — skip Repliers.
            return []

        raw_listings = await self._repliers.search_listings(filters)

        comps: list[dict] = []
        for raw in raw_listings:
            normalized = normalize_listing(raw)
            if normalized is not None:
                comps.append(normalized)
            if len(comps) >= TARGET_COMP_COUNT:
                break
        return comps

    # ------------------------------------------------------------------
    # Synthetic fallback (moved out of CMAReportAgent so it has one home)
    # ------------------------------------------------------------------

    @staticmethod
    def _synthetic_comparables(subject: dict) -> list[dict]:
        """Deterministic-ish synthetic comps based on the subject's attributes.

        Copied from the old CMAReportAgent._generate_comparables() — kept as
        a fallback so the CMA report always renders even when Repliers is off.
        """
        base_sqft = subject.get("sqft") or 1800
        base_price = subject.get("price") or 400_000
        base_beds = subject.get("beds") or 3
        base_baths = subject.get("baths") or 2
        base_ppsf = base_price / base_sqft if base_sqft > 0 else 220

        streets = [
            "Oak Ave", "Maple Dr", "Pine St", "Cedar Ln", "Elm Blvd",
            "Birch Ct", "Willow Way", "Ash Rd",
        ]
        city = _extract_city(subject) or "Austin"

        comps = []
        for i in range(TARGET_COMP_COUNT):
            sqft_delta = random.randint(-200, 200)
            sqft = max(800, base_sqft + sqft_delta)
            ppsf = round(base_ppsf + random.uniform(-30, 30), 2)
            price = round(sqft * ppsf / 1000) * 1000

            comps.append({
                "address": f"{random.randint(100, 999)} {streets[i]}, {city}",
                "beds": base_beds + random.choice([-1, 0, 0, 1]),
                "baths": base_baths + random.choice([-0.5, 0, 0, 0.5]),
                "sqft": sqft,
                "price": price,
                "price_per_sqft": ppsf,
            })

        return comps


# ----------------------------------------------------------------------
# Pure helpers (module-level so they're easy to unit-test)
# ----------------------------------------------------------------------

def _extract_city(subject: dict) -> str:
    """Pull a city out of the subject dict; handles both address-string and dict forms."""
    address = subject.get("address")
    if isinstance(address, str) and "," in address:
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 2:
            return parts[1]
    if isinstance(address, dict):
        return address.get("city", "") or ""
    return ""


def _extract_state(subject: dict) -> str:
    address = subject.get("address")
    if isinstance(address, str):
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 3:
            # "street, city, state [zip]" — grab just the state token
            return parts[2].split()[0] if parts[2] else ""
    if isinstance(address, dict):
        return address.get("state", "") or ""
    return ""


def _build_filters(subject: dict) -> dict | None:
    """Build Repliers /listings query params from a subject dict.

    Returns None if there's not enough info to form a meaningful query.
    """
    city = _extract_city(subject)
    state = _extract_state(subject)
    if not city:
        return None

    filters: dict = {
        "status": "Sld",
        "city": city,
        "pageSize": TARGET_COMP_COUNT * 2,  # over-fetch — some will fail normalization
    }
    if state:
        filters["state"] = state

    sqft = subject.get("sqft")
    if sqft:
        try:
            sqft_int = int(sqft)
            filters["minSqft"] = int(sqft_int * (1 - SQFT_WINDOW_PCT))
            filters["maxSqft"] = int(sqft_int * (1 + SQFT_WINDOW_PCT))
        except (ValueError, TypeError):
            pass

    beds = subject.get("beds")
    if beds:
        try:
            beds_int = int(beds)
            filters["minBedrooms"] = max(1, beds_int - BED_WINDOW)
            filters["maxBedrooms"] = beds_int + BED_WINDOW
        except (ValueError, TypeError):
            pass

    prop_type = subject.get("property_type")
    if prop_type:
        filters["propertyType"] = prop_type

    return filters
