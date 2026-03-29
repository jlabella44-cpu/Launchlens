"""Map Vision API raw labels to standardized MLS feature tags.

Extracts property features from VisionResult raw_labels and maps them
to commonly accepted MLS feature descriptors that agents would otherwise
enter manually.
"""

LABEL_TO_FEATURE: dict[str, str] = {
    # Kitchen & countertops
    "granite": "Granite Countertops",
    "marble": "Marble Countertops",
    "quartz": "Quartz Countertops",
    # Flooring
    "hardwood": "Hardwood Floors",
    "tile": "Tile Flooring",
    "carpet": "Carpeted",
    # Appliances
    "stainless steel": "Stainless Steel Appliances",
    # Features
    "fireplace": "Fireplace",
    "pool": "Swimming Pool",
    "swimming pool": "Swimming Pool",
    "hot tub": "Hot Tub/Spa",
    "vaulted ceiling": "Vaulted Ceilings",
    "cathedral ceiling": "Cathedral Ceilings",
    "crown molding": "Crown Molding",
    "wainscoting": "Wainscoting",
    # Light & views
    "natural light": "Abundant Natural Light",
    "skylight": "Skylights",
    "mountain view": "Mountain Views",
    "city view": "City Views",
    "water view": "Water Views",
    "ocean view": "Ocean Views",
    # Layout
    "open plan": "Open Floor Plan",
    "open concept": "Open Floor Plan",
    # Exterior
    "deck": "Deck/Patio",
    "patio": "Deck/Patio",
    "garage": "Garage",
    "fence": "Fenced Yard",
    "landscaping": "Professional Landscaping",
    # Condition
    "renovated": "Recently Renovated",
    "updated": "Updated/Modern",
    "new construction": "New Construction",
}


def extract_features(vision_results: list) -> list[str]:
    """Extract MLS feature tags from VisionResult raw_labels.

    Args:
        vision_results: list of VisionResult objects with raw_labels JSONB

    Returns:
        Sorted list of unique MLS feature tag strings
    """
    features: set[str] = set()
    for vr in vision_results:
        raw = getattr(vr, "raw_labels", None) or {}
        for label_entry in raw.get("labels", []):
            name = label_entry.get("name", "").lower()
            mapped = LABEL_TO_FEATURE.get(name)
            if mapped:
                features.add(mapped)
    return sorted(features)
