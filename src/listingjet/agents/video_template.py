"""Video template definitions + room-specific prompts and camera controls for Kling AI."""

from dataclasses import dataclass

ROOM_PROMPTS: dict[str, str] = {
    "drone": "Slow cinematic aerial drift over property, stable horizon, golden hour light",
    "exterior": "Slow cinematic dolly toward front entrance, warm natural light, professional real estate",
    "exterior_rear": "Slow cinematic dolly across backyard, natural light, inviting atmosphere",
    "living_room": "Slow cinematic dolly through living room, warm natural light, spacious feel",
    "kitchen": "Slow cinematic dolly into kitchen, warm natural light, modern finishes",
    "bedroom": "Slow cinematic pan across bedroom, soft natural light, peaceful atmosphere",
    "primary_bedroom": "Slow cinematic dolly into primary suite, soft natural light, luxurious feel",
    "bathroom": "Slow cinematic dolly into bathroom, clean bright light, spa-like atmosphere",
    "primary_bathroom": "Slow cinematic pan across primary bath, bright clean light, luxury finishes",
    "dining_room": "Slow cinematic dolly through dining area, warm ambient light, elegant setting",
    "office": "Slow cinematic pan across office, natural light, productive atmosphere",
    "garage": "Slow cinematic dolly into garage, even lighting, spacious layout",
    "pool": "Slow cinematic drift over pool area, shimmering water, resort atmosphere",
    "backyard": "Slow cinematic pan across backyard, natural light, outdoor living space",
    "entryway": "Slow cinematic dolly through entryway, welcoming light, grand entrance",
    "basement": "Slow cinematic dolly through basement, even lighting, finished space",
}

ROOM_CAMERA_CONTROLS: dict[str, dict[str, int]] = {
    "drone": {"zoom": 2, "horizontal": 3},
    "exterior": {"zoom": 4, "horizontal": 0},
    "exterior_rear": {"zoom": 3, "horizontal": 2},
    "living_room": {"zoom": 4, "horizontal": -2},
    "kitchen": {"zoom": 5, "horizontal": 0},
    "bedroom": {"zoom": 3, "horizontal": -3},
    "primary_bedroom": {"zoom": 4, "horizontal": -2},
    "bathroom": {"zoom": 3, "horizontal": 0},
    "primary_bathroom": {"zoom": 3, "horizontal": 2},
    "dining_room": {"zoom": 4, "horizontal": -2},
    "office": {"zoom": 3, "horizontal": 3},
    "garage": {"zoom": 3, "horizontal": 0},
    "pool": {"zoom": 2, "horizontal": 3},
    "backyard": {"zoom": 2, "horizontal": -3},
    "entryway": {"zoom": 5, "horizontal": 0},
    "basement": {"zoom": 4, "horizontal": 0},
}

NEGATIVE_PROMPT = "shaky camera, fast cuts, blurry, distorted, excessive movement, hallucinated spaces, morphing, artifacts"

FEATURE_TAGS: dict[str, list[str]] = {
    "kitchen": ["island", "quartz_counters", "granite_counters", "stainless_appliances"],
    "bathroom": ["soaking_tub", "walk_in_shower", "double_vanity"],
    "living_room": ["vaulted_ceilings", "fireplace", "hardwood_floors", "built_ins"],
    "exterior": ["pool", "outdoor_kitchen", "fire_pit", "deck", "patio"],
    "bedroom": ["walk_in_closet", "tray_ceiling"],
    "basement": ["theater", "gym", "wet_bar"],
}

# Room buckets for template-based photo selection
DRONE_ROOMS: frozenset[str] = frozenset({"drone"})
EXTERIOR_ROOMS: frozenset[str] = frozenset({"exterior", "exterior_rear"})


@dataclass(frozen=True)
class VideoTemplate:
    """Defines the shape of a generated video: clip count, length, model, structure."""
    name: str
    clip_duration_s: int
    clip_count: int
    kling_model: str = "kling-v2-5-turbo"
    kling_mode: str = "pro"
    transition: str = "cut"  # "cut" = hard cut (no xfade)


STANDARD_60S = VideoTemplate(
    name="standard_60s",
    clip_duration_s=5,
    clip_count=12,
    kling_model="kling-v2-5-turbo",
    kling_mode="pro",
    transition="cut",
)


def get_prompt_for_room(room_label: str, metadata: dict | None = None) -> str:
    """Get the cinematic prompt for a room, optionally enriched with feature tags."""
    base = ROOM_PROMPTS.get(room_label, ROOM_PROMPTS.get("living_room"))
    if metadata and room_label in FEATURE_TAGS:
        features = [f for f in FEATURE_TAGS[room_label] if metadata.get(f)]
        if features:
            base += f", featuring {', '.join(features)}"
    return base


def get_camera_control(room_label: str) -> dict[str, int]:
    """Get camera control settings for a room."""
    return ROOM_CAMERA_CONTROLS.get(room_label, {"zoom": 3, "horizontal": 0})
