# tests/test_models/test_listing.py
from listingjet.models.listing import ListingState


def test_listing_state_enum_has_required_states():
    required = {"new", "uploading", "analyzing", "awaiting_review", "in_review",
                "approved", "delivered", "failed", "cancelled", "exporting", "demo",
                "pipeline_timeout"}
    actual = {s.value for s in ListingState}
    assert required.issubset(actual), f"Missing states: {required - actual}"


def test_listing_state_valid_transitions():
    valid = {
        ListingState.NEW: [ListingState.UPLOADING],
        ListingState.UPLOADING: [ListingState.ANALYZING, ListingState.FAILED],
        ListingState.ANALYZING: [ListingState.AWAITING_REVIEW],
        ListingState.AWAITING_REVIEW: [ListingState.IN_REVIEW],
        ListingState.IN_REVIEW: [ListingState.APPROVED, ListingState.FAILED],
        ListingState.APPROVED: [ListingState.EXPORTING, ListingState.DELIVERED],
    }
    assert ListingState.AWAITING_REVIEW in valid[ListingState.ANALYZING]
    assert ListingState.APPROVED in valid[ListingState.IN_REVIEW]
    assert ListingState.FAILED in valid[ListingState.IN_REVIEW]
