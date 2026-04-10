# src/listingjet/providers/mock.py
"""Mock provider implementations for tests and local development."""
import hashlib
import json

from .base import ImageEditProvider, LLMProvider, TemplateProvider, VirtualStagingProvider, VisionLabel, VisionProvider

# Pools of realistic labels for deterministic variety based on image URL
_ROOM_LABELS = [
    ("living room", 0.97), ("kitchen", 0.95), ("primary bedroom", 0.94),
    ("bathroom", 0.93), ("dining room", 0.91), ("home office", 0.90),
    ("garage", 0.89), ("laundry room", 0.87), ("patio", 0.92),
]
_FEATURE_LABELS = [
    ("hardwood floor", 0.91), ("granite countertops", 0.89),
    ("stainless appliances", 0.88), ("crown molding", 0.85),
    ("recessed lighting", 0.84), ("open concept", 0.86),
    ("walk-in closet", 0.83), ("tile backsplash", 0.82),
]
_QUALITY_LABELS = [
    ("natural light", 0.88), ("well staged", 0.85),
    ("clean lines", 0.82), ("bright interior", 0.87),
]


def _pick(pool: list, seed: int, count: int = 1) -> list:
    """Deterministic selection from a pool based on seed."""
    return [pool[(seed + i) % len(pool)] for i in range(count)]


class MockVisionProvider(VisionProvider):
    async def analyze(self, image_url: str) -> list[VisionLabel]:
        seed = int(hashlib.md5(image_url.encode()).hexdigest()[:8], 16)
        room = _pick(_ROOM_LABELS, seed, 1)[0]
        feature = _pick(_FEATURE_LABELS, seed >> 4, 1)[0]
        quality = _pick(_QUALITY_LABELS, seed >> 8, 1)[0]
        return [
            VisionLabel(name=room[0], confidence=room[1], category="room"),
            VisionLabel(name=feature[0], confidence=feature[1], category="feature"),
            VisionLabel(name=quality[0], confidence=quality[1], category="quality"),
        ]

    async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
        seed = int(hashlib.md5(image_url.encode()).hexdigest()[:8], 16)
        bedrooms = 2 + (seed % 3)  # 2-4
        bathrooms = 1.5 + (seed % 3) * 0.5  # 1.5-2.5
        total_sqft = 1200 + (seed % 10) * 150  # 1200-2550
        rooms = [
            {"name": "Living Room", "area_sqft": 240 + (seed % 80),
             "features": ["hardwood floors", "crown molding", "bay window"]},
            {"name": "Kitchen", "area_sqft": 150 + (seed % 60),
             "features": ["granite countertops", "stainless appliances", "island"]},
            {"name": "Primary Bedroom", "area_sqft": 180 + (seed % 80),
             "features": ["walk-in closet", "en-suite bath", "vaulted ceiling"]},
        ]
        for i in range(1, bedrooms):
            rooms.append({"name": f"Bedroom {i + 1}", "area_sqft": 120 + (seed % 60),
                          "features": ["carpet", "closet"]})
        rooms.append({"name": "Primary Bath", "area_sqft": 80 + (seed % 30),
                      "features": ["double vanity", "soaking tub", "walk-in shower"]})
        if bathrooms >= 2:
            rooms.append({"name": "Half Bath", "area_sqft": 35,
                          "features": ["pedestal sink"]})
        rooms.append({"name": "Garage", "area_sqft": 380 + (seed % 80),
                      "features": ["2-car", "epoxy floor"]})
        return json.dumps({
            "rooms": rooms,
            "total_sqft": total_sqft,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
        })

    async def analyze_with_prompt_multi(
        self, image_urls: list[str], prompt: str
    ) -> str:
        if not image_urls:
            raise ValueError("image_urls must be non-empty")
        return json.dumps({
            "floor_label": "First Floor",
            "level": 1,
            "structure": "main_house",
            "overall_width_meters": 12.0,
            "overall_height_meters": 9.0,
            "wall_height_meters": 2.7,
            "rooms": [
                {
                    "label": "living_room",
                    "polygon": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.4], [0.0, 0.4]],
                    "width_meters": 6.0,
                    "height_meters": 4.5,
                    "doors": [{"wall": "south", "position": 0.5}],
                    "windows": [{"wall": "east", "position": 0.3}],
                    "wall_color": "#E8E2D0",
                    "flooring": "hardwood",
                    "decor_tags": ["beige walls", "white trim"],
                    "furniture": [
                        {"type": "sectional", "x": 0.3, "y": 0.5, "rotation_degrees": 0},
                        {"type": "coffee_table", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                    ],
                },
                {
                    "label": "kitchen",
                    "polygon": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.4], [0.5, 0.4]],
                    "width_meters": 5.0,
                    "height_meters": 4.5,
                    "doors": [{"wall": "west", "position": 0.5}],
                    "windows": [],
                    "wall_color": "#FFFFFF",
                    "flooring": "tile",
                    "decor_tags": ["white cabinets"],
                    "furniture": [
                        {"type": "kitchen_island", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                    ],
                },
                {
                    "label": "bedroom",
                    "polygon": [[0.0, 0.4], [0.5, 0.4], [0.5, 1.0], [0.0, 1.0]],
                    "width_meters": 6.0,
                    "height_meters": 5.0,
                    "doors": [{"wall": "north", "position": 0.3}],
                    "windows": [{"wall": "west", "position": 0.5}],
                    "wall_color": "#D6CFC4",
                    "flooring": "carpet",
                    "decor_tags": [],
                    "furniture": [
                        {"type": "queen_bed", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                    ],
                },
            ],
        })


class MockLLMProvider(LLMProvider):
    async def complete(self, prompt: str, context: dict, temperature: float | None = None, system_prompt: str | None = None) -> str:
        return "Stunning home with modern finishes and abundant natural light."


class MockImageEditProvider(ImageEditProvider):
    provider_name = "mock"

    async def remove_object(self, image_url: str, object_description: str) -> bytes:
        return b"\xff\xd8\xff\xe0mock-edited-jpeg"

    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        return b"\xff\xd8\xff\xe0mock-enhanced-jpeg"


class MockVirtualStagingProvider(VirtualStagingProvider):
    provider_name = "mock"

    async def stage_image(self, image_url: str, room_type: str, style: str = "modern") -> bytes:
        return b"\xff\xd8\xff\xe0mock-staged-jpeg-" + f"{room_type}-{style}".encode()


class MockTemplateProvider(TemplateProvider):
    async def render(self, template_id: str, data: dict) -> bytes:
        return b"%PDF-mock-content"
