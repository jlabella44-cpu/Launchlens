# tests/test_models/test_listing.py
from launchlens.models.listing import ListingState


def test_listing_state_enum_includes_shadow_review():
    assert ListingState.SHADOW_REVIEW in ListingState

def test_listing_state_valid_transitions():
    valid = {
        ListingState.NEW: [ListingState.UPLOADING],
        ListingState.UPLOADING: [ListingState.ANALYZING],
        ListingState.ANALYZING: [ListingState.SHADOW_REVIEW, ListingState.AWAITING_REVIEW],
        ListingState.SHADOW_REVIEW: [ListingState.AWAITING_REVIEW],
        ListingState.AWAITING_REVIEW: [ListingState.IN_REVIEW],
        ListingState.IN_REVIEW: [ListingState.APPROVED],
        ListingState.APPROVED: [ListingState.GENERATING],
        ListingState.GENERATING: [ListingState.DELIVERING],
        ListingState.DELIVERING: [ListingState.DELIVERED],
    }
    assert ListingState.SHADOW_REVIEW in valid[ListingState.ANALYZING]
    assert ListingState.AWAITING_REVIEW in valid[ListingState.SHADOW_REVIEW]
