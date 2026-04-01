"""Property lookup API endpoint."""

from fastapi import APIRouter, Depends, Query

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.properties import PropertyLookupResponse
from listingjet.models.user import User
from listingjet.services.property_lookup import PropertyLookupService

router = APIRouter()


@router.get("/lookup", response_model=PropertyLookupResponse)
async def lookup_property(
    address: str = Query(..., min_length=5, description="Full street address"),
    current_user: User = Depends(get_current_user),
):
    svc = PropertyLookupService()
    return await svc.lookup(address)
