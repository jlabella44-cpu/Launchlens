from fastapi import APIRouter, Depends

from listingjet import features
from listingjet.api.deps import get_current_user

router = APIRouter()


@router.get("/features")
async def list_features(_user=Depends(get_current_user)) -> dict:
    return {"features": sorted(features.enabled_set())}
