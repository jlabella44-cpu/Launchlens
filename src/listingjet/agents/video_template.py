"""Video template definitions + room-specific prompts and camera controls for Kling AI."""

from dataclasses import dataclass

ROOM_PROMPTS: dict[str, str] = {
    "drone": (
        "Aerial drone footage slowly gliding forward over residential property, "
        "camera tilts gently downward revealing rooftop and landscaping, "
        "trees sway softly in the breeze, shadows shift across the lawn, "
        "golden hour sunlight, smooth continuous forward motion, cinematic 4K real estate"
    ),
    "exterior": (
        "Camera steadily pushes forward along walkway toward front door of house, "
        "parallax movement past landscaping and columns, porch light glows warmly, "
        "leaves rustle gently, late afternoon sun casts long shadows across facade, "
        "smooth dolly motion, professional real estate cinematography"
    ),
    "exterior_rear": (
        "Camera glides laterally across backyard revealing patio and outdoor living space, "
        "plants sway gently in breeze, sunlight dapples through tree canopy, "
        "smooth tracking shot with natural depth parallax, cinematic real estate"
    ),
    "living_room": (
        "Camera pushes slowly forward through spacious living room, "
        "natural light streams through windows casting moving shadows on floor, "
        "curtains drift gently, parallax reveals furniture depth and room scale, "
        "warm ambient atmosphere, smooth continuous dolly, professional interior cinematography"
    ),
    "kitchen": (
        "Camera glides forward into kitchen revealing countertops and cabinetry, "
        "overhead pendant lights cast warm pools of light on surfaces, "
        "subtle reflections shift on stainless steel and stone countertops, "
        "smooth dolly push with natural parallax, bright modern interior, cinematic real estate"
    ),
    "bedroom": (
        "Camera slowly tracks right to left across bedroom, "
        "soft natural light from windows illuminates bedding and furniture, "
        "gentle depth parallax between foreground and background elements, "
        "peaceful serene atmosphere, smooth lateral tracking shot, professional interior"
    ),
    "primary_bedroom": (
        "Camera pushes gently forward into luxurious primary suite, "
        "morning light cascades through large windows, soft shadows move across bed, "
        "parallax reveals room depth and architectural details, "
        "smooth continuous dolly motion, elegant luxury interior cinematography"
    ),
    "bathroom": (
        "Camera glides forward into bathroom revealing tile work and fixtures, "
        "light reflects and shimmers off glass shower door and mirror surfaces, "
        "clean bright illumination with subtle caustic reflections on tile, "
        "smooth push-in motion, spa-like atmosphere, professional real estate"
    ),
    "primary_bathroom": (
        "Camera tracks laterally across primary bathroom revealing double vanity and soaking tub, "
        "light plays across marble surfaces and chrome fixtures, water-like reflections shimmer, "
        "smooth tracking shot with depth parallax, luxury spa interior cinematography"
    ),
    "dining_room": (
        "Camera pushes forward through dining area, chandelier light creates warm ambiance, "
        "subtle light shifts across table surface and wall art, "
        "parallax between chairs and background reveals room depth, "
        "smooth dolly motion, elegant interior, professional real estate cinematography"
    ),
    "office": (
        "Camera slowly tracks across home office, natural window light shifts across desk surface, "
        "bookshelves and decor create layered depth with parallax movement, "
        "smooth lateral tracking shot, productive modern atmosphere, cinematic interior"
    ),
    "garage": (
        "Camera pushes forward into spacious garage, overhead lighting illuminates clean floor, "
        "depth parallax reveals storage and organization, "
        "smooth dolly motion, even bright lighting, professional real estate"
    ),
    "pool": (
        "Camera glides slowly forward over pool, water surface ripples and shimmers with light, "
        "reflections dance across surrounding deck, palm fronds sway gently overhead, "
        "resort-style atmosphere, smooth aerial drift, cinematic outdoor luxury"
    ),
    "backyard": (
        "Camera tracks laterally across backyard revealing landscaping and outdoor features, "
        "leaves and grass sway gently in breeze, sunlight filters through trees, "
        "natural depth parallax, smooth tracking shot, inviting outdoor living, cinematic real estate"
    ),
    "entryway": (
        "Camera pushes forward through grand entryway, light pours in from above, "
        "shadows shift across floor as camera advances, architectural details emerge with parallax, "
        "smooth continuous dolly into home, welcoming atmosphere, professional cinematography"
    ),
    "basement": (
        "Camera glides forward through finished basement, recessed lighting creates even illumination, "
        "depth parallax reveals entertainment area and living space, "
        "smooth dolly motion, modern finished interior, professional real estate"
    ),
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

NEGATIVE_PROMPT = (
    "static image, still photo, no movement, frozen, slideshow, ken burns, "
    "shaky camera, fast cuts, blurry, distorted, excessive movement, "
    "hallucinated objects, morphing walls, warping furniture, artifacts, "
    "people appearing, phantom figures, text overlay, watermark"
)

# Room labels that should NEVER appear in video (non-photo content)
VIDEO_EXCLUDED_LABELS: frozenset[str] = frozenset({
    "floorplan", "floor_plan", "diagram", "map", "site_plan",
    "document", "text", "logo", "screenshot", "virtual_tour",
    "3d_render", "cad", "blueprint",
})

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
