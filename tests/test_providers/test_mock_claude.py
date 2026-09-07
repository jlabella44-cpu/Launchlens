"""Regression coverage for MockClaudeClient and its _defaults_for helper.

Uses small local Pydantic schemas rather than production schemas so this
suite stays independent of any future schema changes elsewhere.
"""
import enum

import pytest
from pydantic import BaseModel

from listingjet.providers.mock import MockClaudeClient, _defaults_for


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class Nested(BaseModel):
    label: str
    count: int


class Kitchen(BaseModel):
    room: str
    score: int
    confidence: float
    verified: bool
    tags: list[str]
    color: Color
    detail: Nested
    note: str | None


def test_defaults_for_primitive_types():
    data = _defaults_for(Kitchen)
    assert data["room"] == "mock"
    assert data["score"] == 1
    assert data["confidence"] == 0.5
    assert data["verified"] is False
    assert data["tags"] == []


def test_defaults_for_enum_uses_first_member():
    data = _defaults_for(Kitchen)
    assert data["color"] == Color.RED.value


def test_defaults_for_nested_model_recurses():
    data = _defaults_for(Kitchen)
    assert data["detail"] == {"label": "mock", "count": 1}


def test_defaults_for_optional_field_validates():
    data = _defaults_for(Kitchen)
    instance = Kitchen.model_validate(data)
    assert instance.note is None or isinstance(instance.note, str)
    # Whatever _defaults_for produced for the Optional[str] field, the
    # resulting dict must validate against the schema.
    assert isinstance(instance, Kitchen)


@pytest.mark.asyncio
async def test_complete_json_returns_validated_instance_when_queue_empty():
    client = MockClaudeClient()
    result = await client.complete_json("classify", Kitchen)
    assert isinstance(result, Kitchen)
    assert result.room == "mock"
    assert result.score == 1


@pytest.mark.asyncio
async def test_complete_json_pops_queue_in_order_then_falls_back():
    client = MockClaudeClient()
    first = Kitchen(
        room="kitchen", score=90, confidence=0.9, verified=True,
        tags=["a"], color=Color.BLUE, detail=Nested(label="d1", count=2), note="n1",
    )
    second = Kitchen(
        room="bath", score=10, confidence=0.1, verified=False,
        tags=[], color=Color.RED, detail=Nested(label="d2", count=3), note=None,
    )
    client.responses[Kitchen] = [first, second]

    out1 = await client.complete_json("x", Kitchen)
    out2 = await client.complete_json("x", Kitchen)
    out3 = await client.complete_json("x", Kitchen)

    assert out1 == first
    assert out2 == second
    # Queue exhausted — falls back to schema-default generation.
    assert isinstance(out3, Kitchen)
    assert out3.room == "mock"


@pytest.mark.asyncio
async def test_analyze_images_returns_validated_instance():
    client = MockClaudeClient()
    result = await client.analyze_images(["https://x/1.jpg"], "which room", Kitchen)
    assert isinstance(result, Kitchen)


@pytest.mark.asyncio
async def test_analyze_images_raises_on_empty_urls():
    client = MockClaudeClient()
    with pytest.raises(ValueError):
        await client.analyze_images([], "which room", Kitchen)


@pytest.mark.asyncio
async def test_analyze_images_uses_response_queue():
    client = MockClaudeClient()
    queued = Kitchen(
        room="office", score=5, confidence=0.3, verified=True,
        tags=["b"], color=Color.BLUE, detail=Nested(label="d", count=1), note=None,
    )
    client.responses[Kitchen] = [queued]
    result = await client.analyze_images(["https://x/1.jpg"], "which room", Kitchen)
    assert result == queued


@pytest.mark.asyncio
async def test_complete_text_returns_nonempty_string():
    client = MockClaudeClient()
    result = await client.complete_text("write copy")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_photo_analysis_defaults_pass_packaging_quality_floor():
    """PhotoAnalysis's schema-shape defaults alone would produce is_photo=False
    and quality=1 — real photos in mock-provider test fixtures would then be
    silently dropped by the packaging quality floor. The schema-name override
    in `_SCHEMA_DEFAULT_OVERRIDES` keeps mock output realistic."""
    from listingjet.agents.packaging import MIN_QUALITY_SCORE
    from listingjet.agents.photo_analysis import PhotoAnalysis

    client = MockClaudeClient()
    result = await client.analyze_images(["https://x/1.jpg"], "which room", PhotoAnalysis)

    assert result.is_photo is True
    assert result.quality >= MIN_QUALITY_SCORE
