"""Tests for endcard generation service."""
from listingjet.services.endcard import generate_endcard


def test_generate_endcard_returns_png_bytes():
    result = generate_endcard(brokerage_name="Acme Realty", agent_name="John Doe")
    assert isinstance(result, bytes)
    assert len(result) > 100
    # PNG magic bytes
    assert result[:4] == b"\x89PNG"


def test_generate_endcard_default_params():
    result = generate_endcard()
    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_generate_endcard_with_custom_color():
    result = generate_endcard(primary_color="#FF5500", agent_name="Jane")
    assert isinstance(result, bytes)
    assert len(result) > 100
