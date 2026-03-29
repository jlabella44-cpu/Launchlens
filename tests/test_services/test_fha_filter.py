import pytest

from listingjet.services.fha_filter import fha_check


@pytest.mark.parametrize("text,should_flag", [
    # Protected class — family status
    ("Perfect for families", True),
    ("family-friendly neighborhood", True),
    ("PERFECT FOR FAMILIES", True),          # case insensitive
    # Protected class — other demographics
    ("Great for young professionals", True),
    ("ideal for retirees", True),
    ("perfect for couples", True),
    # Source-based steering
    ("walking distance to church", True),
    ("minutes from mosque", True),
    ("2 minutes to synagogue", True),
    # Vouchers / HUD
    ("No Section 8", True),
    ("no vouchers accepted", True),
    ("no hud accepted", True),
    # Neighborhood steering
    ("safe neighborhood", True),
    ("great schools nearby", True),
    ("exclusive community", True),
    ("exclusive neighborhood", True),
    # Clean copy — must NOT flag
    ("Spacious kitchen with granite countertops", False),
    ("3 bed 2 bath, open floor plan", False),
    ("Recently renovated master suite", False),
    ("Walking distance to coffee shops and parks", False),  # "walking distance" without religious ref
    ("Award-winning school district", False),               # "school" alone is not a violation
])
def test_fha_patterns(text, should_flag):
    result = fha_check({"description": text})
    assert result.passed == (not should_flag), f"Failed for: {text!r}"


def test_fha_checks_all_json_fields():
    # Violation in headline, not description
    result = fha_check({"headline": "Perfect for families", "description": "Clean copy"})
    assert not result.passed


def test_fha_checks_social_variants_list():
    # social_variants is a list — fha_check must handle list values without breaking
    result = fha_check({"social_variants": ["No Section 8 vouchers", "Beautiful home"]})
    assert not result.passed


def test_fha_clean_social_variants_list():
    result = fha_check({"social_variants": ["Stunning views", "Chef's kitchen"]})
    assert result.passed


def test_fha_returns_violation_details():
    result = fha_check({"description": "No Section 8 accepted"})
    assert len(result.violations) > 0
    assert "section" in result.violations[0].lower()
