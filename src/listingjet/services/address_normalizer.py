"""
Address normalization service for property lookup.

Used by PropertyLookupService to:
- Generate stable cache keys (address_hash)
- Retry lookups with alternate suffixes when API returns no results
- Standardize addresses for comparison
"""

import hashlib
import re

# Mapping from abbreviation (lowercase) to full form (lowercase)
SUFFIX_EXPANSIONS: dict[str, str] = {
    "st": "street",
    "ct": "court",
    "ter": "terrace",
    "cir": "circle",
    "blvd": "boulevard",
    "dr": "drive",
    "ln": "lane",
    "ave": "avenue",
    "pl": "place",
    "pkwy": "parkway",
    "rd": "road",
    "hwy": "highway",
    "trl": "trail",
}

# Reverse mapping: full form → abbreviation
SUFFIX_CONTRACTIONS: dict[str, str] = {v: k for k, v in SUFFIX_EXPANSIONS.items()}

# Regex to strip unit/apt designators:
# Matches patterns like "Apt 4B", "Unit 2", "Suite 100", "#4", "# 4B"
_UNIT_RE = re.compile(
    r"\s+(?:apt|unit|suite|ste|#)\s*[\w-]+$",
    re.IGNORECASE,
)


def normalize_address(address: str) -> str:
    """
    Normalize an address string:
    - Strip leading/trailing whitespace
    - Strip unit/apt designators (e.g. "Apt 4B", "#4")
    - Lowercase
    - Expand street suffix abbreviations (e.g. St → Street)
    """
    address = address.strip()
    # Strip unit numbers before lowercasing so the regex is case-insensitive
    address = _UNIT_RE.sub("", address)
    address = address.lower()

    # Split into tokens and expand the last token if it is a known abbreviation.
    # We only expand the final token to avoid mangling street names like "St Paul".
    tokens = address.split()
    if tokens:
        last = tokens[-1]
        if last in SUFFIX_EXPANSIONS:
            tokens[-1] = SUFFIX_EXPANSIONS[last]
        # Also handle already-expanded suffixes — they pass through unchanged.

    return " ".join(tokens)


def address_hash(address: str) -> str:
    """
    Return a SHA-256 hex digest of the normalized address.
    Suitable for use as a cache key.
    """
    normalized = normalize_address(address)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_alternates(address: str) -> list[str]:
    """
    Generate alternate forms of an address by swapping the street suffix.

    - If the suffix is an abbreviation, also return the expanded form.
    - If the suffix is already expanded, also return the abbreviated form.
    - If the suffix is not recognized, return an empty list.

    The returned addresses are normalized (lowercased, unit-stripped) but
    expressed with the alternate suffix.
    """
    normalized = normalize_address(address)
    tokens = normalized.split()
    if not tokens:
        return []

    last = tokens[-1]
    base = tokens[:-1]

    if last in SUFFIX_CONTRACTIONS:
        # Full form → abbreviated form
        alternate_suffix = SUFFIX_CONTRACTIONS[last]
        return [" ".join(base + [alternate_suffix])]

    if last in SUFFIX_EXPANSIONS:
        # Abbreviated form → full form
        alternate_suffix = SUFFIX_EXPANSIONS[last]
        return [" ".join(base + [alternate_suffix])]

    return []
