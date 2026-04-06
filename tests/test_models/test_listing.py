# tests/test_models/test_listing.py
from listingjet.models.listing import ListingState


def test_draft_state_exists():
    """DRAFT state should exist and have value 'draft'."""
    assert ListingState.DRAFT == "draft"
    assert ListingState.DRAFT.value == "draft"


def test_draft_state_ordering():
    """DRAFT should be a valid state that comes before NEW."""
    states = list(ListingState)
    draft_idx = states.index(ListingState.DRAFT)
    new_idx = states.index(ListingState.NEW)
    assert draft_idx < new_idx, f"DRAFT (index {draft_idx}) should come before NEW (index {new_idx})"


def test_listing_state_enum_has_required_states():
    required = {"draft", "new", "uploading", "analyzing", "awaiting_review", "in_review",
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
