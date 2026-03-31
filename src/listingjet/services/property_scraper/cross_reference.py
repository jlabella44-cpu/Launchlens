"""
Cross-reference consensus logic for property data verification.

Compares API-sourced property fields against scraped data from multiple
sites and produces a confidence score and mismatch report.
"""

from __future__ import annotations

# Numeric fields that use fuzzy tolerance for matching
_SQFT_FIELDS = {"sqft", "lot_sqft"}
_SQFT_TOLERANCE = 0.05      # 5% tolerance for sqft
_LOT_SQFT_TOLERANCE = 0.10  # 10% tolerance for lot_sqft


def _values_match(field: str, api_val, scraped_val) -> bool:
    """Return True if api_val and scraped_val are considered equivalent."""
    if api_val is None or scraped_val is None:
        return False

    if field in _SQFT_FIELDS:
        try:
            a = float(api_val)
            b = float(scraped_val)
            if a == 0:
                return b == 0
            tolerance = _LOT_SQFT_TOLERANCE if field == "lot_sqft" else _SQFT_TOLERANCE
            return abs(a - b) / a <= tolerance
        except (TypeError, ValueError):
            return api_val == scraped_val

    return api_val == scraped_val


def cross_reference(api_data: dict, scraped: dict[str, dict]) -> dict:
    """
    Compare API data against scraped sources to produce a verification result.

    Parameters
    ----------
    api_data:
        Fields returned by the primary API (e.g. ATTOM). None values are skipped.
    scraped:
        Mapping of site name → dict of fields scraped from that site.

    Returns
    -------
    dict with keys:
        status          "verified" | "mismatches_found" | "partial"
        field_confidence  {field: float} — 0.0–1.0 per field
        mismatches      list of field names where sources disagree
        sources_checked list of scraped site names used
    """
    sources = list(scraped.keys())

    # No scraped data at all → partial, no confidence
    if not sources:
        field_confidence = {
            field: 0.5
            for field, val in api_data.items()
            if val is not None
        }
        return {
            "status": "partial",
            "field_confidence": field_confidence,
            "mismatches": [],
            "sources_checked": [],
        }

    field_confidence: dict[str, float] = {}
    mismatches: list[str] = []

    for field, api_val in api_data.items():
        if api_val is None:
            continue

        matching = 0
        disagreeing = 0

        for site_data in scraped.values():
            if field not in site_data or site_data[field] is None:
                # This source doesn't have the field — don't count either way
                continue
            if _values_match(field, api_val, site_data[field]):
                matching += 1
            else:
                disagreeing += 1

        total = matching + disagreeing
        if total == 0:
            # No source had this field
            field_confidence[field] = 0.5
        else:
            field_confidence[field] = matching / total

        # Mismatch: 2+ sources disagree, or 1 disagrees and 0 agree
        if disagreeing >= 2 or (disagreeing >= 1 and matching == 0):
            mismatches.append(field)

    status = "mismatches_found" if mismatches else "verified"

    return {
        "status": status,
        "field_confidence": field_confidence,
        "mismatches": mismatches,
        "sources_checked": sources,
    }
