import pytest
from pydantic import ValidationError

from listingjet.api.schemas.social import CreateListingEventRequest, MarkPostedRequest


def test_create_event_valid_types():
    for t in ["open_house", "sold_pending"]:
        req = CreateListingEventRequest(event_type=t)
        assert req.event_type == t

def test_create_event_rejects_just_listed():
    with pytest.raises(ValidationError):
        CreateListingEventRequest(event_type="just_listed")

def test_mark_posted_valid_platforms():
    for p in ["instagram", "facebook", "tiktok"]:
        req = MarkPostedRequest(platform=p)
        assert req.platform == p

def test_mark_posted_rejects_invalid():
    with pytest.raises(ValidationError):
        MarkPostedRequest(platform="linkedin")
