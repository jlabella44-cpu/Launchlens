"""Video template definitions + room-specific prompts and camera controls for Kling AI."""

from dataclasses import dataclass

ROOM_PROMPTS: dict[str, str] = {
    "drone": (
        "Aerial drone footage gliding forward over residential property, "
        "camera tilts gently downward revealing rooftop and full lot, "
        "trees sway softly, shadows move across manicured lawn, "
        "golden hour sunlight, smooth continuous forward motion, cinematic 4K real estate"
    ),
    "exterior": (
        "Camera pushes steadily forward along front walkway toward entrance, "
        "parallax past landscaping, columns, and architectural details, "
        "late afternoon sun casts warm directional light across facade, "
        "smooth dolly motion, professional real estate cinematography"
    ),
    "exterior_rear": (
        "Camera glides laterally across rear of home revealing patio and outdoor living, "
        "plants sway gently, sunlight dapples through tree canopy onto siding, "
        "smooth tracking shot with natural depth parallax, cinematic real estate"
    ),
    "entryway": (
        "Camera pushes forward through front entry into home, light pours in from doorway, "
        "shadows shift across floor as camera advances, "
        "architectural details emerge with depth parallax, "
        "smooth continuous dolly, welcoming first impression, professional cinematography"
    ),
    "foyer": (
        "Camera enters foyer and slowly pans upward revealing ceiling height, "
        "natural light from adjacent windows creates warm tones, "
        "smooth tilt motion with foreground depth, elegant first impression, cinematic interior"
    ),
    "living_room": (
        "Camera pushes slowly forward through living room, "
        "natural light streams through windows illuminating textures and surfaces, "
        "parallax reveals furniture arrangement and room scale, "
        "warm ambient atmosphere, smooth continuous dolly, professional interior cinematography"
    ),
    "family_room": (
        "Camera tracks laterally through family room revealing comfortable layout, "
        "soft window light creates warm atmosphere, "
        "depth parallax between seating and built-in features, "
        "smooth tracking motion, inviting casual living space, cinematic interior"
    ),
    "kitchen": (
        "Camera glides forward into kitchen revealing countertops and cabinetry, "
        "pendant lights cast warm pools of light on work surfaces, "
        "reflections shift subtly on appliances and stone countertops, "
        "smooth dolly push with natural parallax, bright modern interior, cinematic real estate"
    ),
    "dining_room": (
        "Camera pushes forward into dining area, fixture light creates warm ambiance, "
        "light shifts across table surface and wall details, "
        "parallax between furnishings and background reveals room proportion, "
        "smooth dolly motion, elegant interior, professional real estate cinematography"
    ),
    "breakfast_nook": (
        "Camera glides toward breakfast area adjacent to kitchen, "
        "morning light streams through nearby windows across table, "
        "smooth push-in with subtle parallax, bright casual dining space, cinematic interior"
    ),
    "primary_bedroom": (
        "Camera pushes gently forward into primary suite, "
        "soft light cascades through large windows across bed and furnishings, "
        "parallax reveals room depth and architectural details, "
        "smooth continuous dolly motion, elegant retreat, luxury interior cinematography"
    ),
    "bedroom": (
        "Camera slowly tracks laterally across bedroom, "
        "soft natural light from windows illuminates surfaces, "
        "gentle depth parallax between foreground and background, "
        "peaceful atmosphere, smooth lateral tracking shot, professional interior"
    ),
    "primary_bathroom": (
        "Camera tracks laterally revealing double vanity and spa features, "
        "light plays across tile, stone, and chrome surfaces, "
        "subtle reflections shimmer on glass and mirror, "
        "smooth tracking shot with depth parallax, luxury spa atmosphere, cinematic interior"
    ),
    "bathroom": (
        "Camera glides forward into bathroom revealing tile and fixtures, "
        "light reflects off glass and mirror surfaces, "
        "clean bright illumination with subtle caustic reflections, "
        "smooth push-in motion, spa-like atmosphere, professional real estate"
    ),
    "office": (
        "Camera slowly tracks across home office, window light shifts across desk, "
        "shelving and decor create layered depth with parallax, "
        "smooth lateral tracking shot, focused productive atmosphere, cinematic interior"
    ),
    "laundry": (
        "Camera pushes gently forward into laundry room revealing clean organized space, "
        "bright even illumination across cabinetry and appliances, "
        "smooth dolly motion, functional modern utility space, professional real estate"
    ),
    "mudroom": (
        "Camera glides through mudroom entry revealing storage and organization, "
        "natural light from adjacent door, clean practical space, "
        "smooth forward motion, inviting transitional area, cinematic interior"
    ),
    "closet": (
        "Camera pushes slowly into walk-in closet revealing organization system, "
        "even recessed lighting illuminates shelving and hanging space, "
        "smooth dolly forward, spacious organized storage, professional interior"
    ),
    "staircase": (
        "Camera tilts upward following staircase line revealing second floor landing, "
        "light shifts across railing and wall surfaces, "
        "smooth vertical pan motion, architectural detail, professional real estate"
    ),
    "hallway": (
        "Camera glides forward down hallway, wall art and doorways create depth parallax, "
        "light from adjacent rooms spills across floor, "
        "smooth forward dolly, connecting spaces, cinematic interior"
    ),
    "garage": (
        "Camera pushes forward into spacious garage, overhead lighting illuminates clean floor, "
        "depth parallax reveals storage capacity, "
        "smooth dolly motion, bright even lighting, professional real estate"
    ),
    "pool": (
        "Camera glides slowly forward over pool, water surface ripples and shimmers, "
        "reflections dance across surrounding deck and coping, "
        "resort-style atmosphere, smooth aerial drift, cinematic outdoor luxury"
    ),
    "patio": (
        "Camera tracks laterally across covered patio revealing outdoor living setup, "
        "dappled sunlight through overhead structure, furniture creates foreground depth, "
        "smooth tracking shot, outdoor entertaining space, cinematic real estate"
    ),
    "deck": (
        "Camera glides across deck revealing railing and views beyond, "
        "natural light and shadows from overhead, "
        "smooth lateral tracking with landscape depth, outdoor living, cinematic real estate"
    ),
    "backyard": (
        "Camera tracks laterally across backyard revealing full landscaping, "
        "leaves and grass sway gently in breeze, sunlight filters through trees, "
        "natural depth parallax, smooth tracking shot, inviting outdoor living, cinematic real estate"
    ),
    "basement": (
        "Camera glides forward through finished basement, recessed lighting creates even illumination, "
        "depth parallax reveals entertainment and living area, "
        "smooth dolly motion, modern finished interior, professional real estate"
    ),
    "theater": (
        "Camera pushes slowly forward into home theater, ambient lighting along walls, "
        "seating and screen create dramatic depth, "
        "smooth cinematic dolly, entertainment luxury, professional interior"
    ),
    "gym": (
        "Camera tracks laterally through home gym revealing equipment and mirrors, "
        "bright even lighting, reflections add depth, "
        "smooth tracking shot, active lifestyle space, professional real estate"
    ),
    "wine_cellar": (
        "Camera pushes forward into wine cellar, warm accent lighting across racks, "
        "subtle reflections on glass bottles, temperature-controlled atmosphere, "
        "smooth dolly motion, luxury entertaining feature, cinematic interior"
    ),
    "bonus_room": (
        "Camera glides forward into versatile bonus room, natural light from windows, "
        "flexible open space with depth parallax, "
        "smooth dolly motion, adaptable living area, professional real estate"
    ),
}

ROOM_CAMERA_CONTROLS: dict[str, dict[str, int]] = {
    "drone": {"zoom": 2, "horizontal": 3},
    "exterior": {"zoom": 4, "horizontal": 0},
    "exterior_rear": {"zoom": 3, "horizontal": 2},
    "entryway": {"zoom": 5, "horizontal": 0},
    "foyer": {"zoom": 3, "horizontal": 0},
    "living_room": {"zoom": 4, "horizontal": -2},
    "family_room": {"zoom": 3, "horizontal": -3},
    "kitchen": {"zoom": 5, "horizontal": 0},
    "dining_room": {"zoom": 4, "horizontal": -2},
    "breakfast_nook": {"zoom": 4, "horizontal": 0},
    "primary_bedroom": {"zoom": 4, "horizontal": -2},
    "bedroom": {"zoom": 3, "horizontal": -3},
    "primary_bathroom": {"zoom": 3, "horizontal": 2},
    "bathroom": {"zoom": 3, "horizontal": 0},
    "office": {"zoom": 3, "horizontal": 3},
    "laundry": {"zoom": 3, "horizontal": 0},
    "mudroom": {"zoom": 3, "horizontal": 0},
    "closet": {"zoom": 4, "horizontal": 0},
    "staircase": {"zoom": 2, "horizontal": 0},
    "hallway": {"zoom": 4, "horizontal": 0},
    "garage": {"zoom": 3, "horizontal": 0},
    "pool": {"zoom": 2, "horizontal": 3},
    "patio": {"zoom": 3, "horizontal": -3},
    "deck": {"zoom": 2, "horizontal": -3},
    "backyard": {"zoom": 2, "horizontal": -3},
    "basement": {"zoom": 4, "horizontal": 0},
    "theater": {"zoom": 4, "horizontal": 0},
    "gym": {"zoom": 3, "horizontal": 3},
    "wine_cellar": {"zoom": 4, "horizontal": 0},
    "bonus_room": {"zoom": 3, "horizontal": 0},
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
    "primary_bathroom": ["soaking_tub", "walk_in_shower", "double_vanity", "heated_floors"],
    "living_room": ["vaulted_ceilings", "fireplace", "hardwood_floors", "built_ins"],
    "family_room": ["fireplace", "built_ins", "hardwood_floors"],
    "exterior": ["pool", "outdoor_kitchen", "fire_pit", "deck", "patio"],
    "bedroom": ["walk_in_closet", "tray_ceiling"],
    "primary_bedroom": ["walk_in_closet", "tray_ceiling", "sitting_area"],
    "basement": ["theater", "gym", "wet_bar"],
}

# Walkthrough order for spatial flow (exterior → entry → main living → private → outdoor → aerial close)
# Rooms not in this list are placed by score after the last matched room.
WALKTHROUGH_ORDER: list[str] = [
    "entryway", "foyer",
    "living_room", "family_room",
    "kitchen", "breakfast_nook", "dining_room",
    "office",
    "hallway", "staircase",
    "primary_bedroom", "primary_bathroom", "closet",
    "bedroom", "bathroom",
    "laundry", "mudroom",
    "basement", "theater", "gym", "wine_cellar", "bonus_room",
    "patio", "deck", "pool", "backyard",
    "garage",
]

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
