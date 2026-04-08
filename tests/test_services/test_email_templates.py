"""Tests for email_templates — verify each template returns (subject, html_body)."""
from listingjet.services.email_templates import TEMPLATES


def test_all_templates_return_subject_and_body():
    """Every registered template should return a (subject, html_body) tuple."""
    assert len(TEMPLATES) >= 5, f"Expected at least 5 templates, got {len(TEMPLATES)}"


def test_listing_delivered():
    from listingjet.services.email_templates import listing_delivered
    subject, body = listing_delivered(
        name="John", address="123 Main St",
        download_url="https://example.com/dl", listing_url="https://example.com/l",
    )
    assert "ready" in subject.lower() or "listing" in subject.lower()
    assert "123 Main St" in body
    assert isinstance(body, str) and len(body) > 50


def test_credits_low():
    from listingjet.services.email_templates import credits_low
    subject, body = credits_low(name="Jane", balance="2", buy_url="https://example.com/buy")
    assert "credit" in subject.lower() or "low" in subject.lower()
    assert "2" in body


def test_welcome_drip_1():
    from listingjet.services.email_templates import welcome_drip_1
    subject, body = welcome_drip_1(name="Alex", upload_url="https://example.com/upload")
    assert isinstance(subject, str) and len(subject) > 0
    assert "Alex" in body


def test_review_approved():
    from listingjet.services.email_templates import review_approved
    subject, body = review_approved(name="Pat", address="456 Oak Ave")
    assert "456 Oak Ave" in body


def test_review_rejected():
    from listingjet.services.email_templates import review_rejected
    subject, body = review_rejected(name="Sam", address="789 Elm", reason="quality", detail="Blurry photos")
    assert "789 Elm" in body
