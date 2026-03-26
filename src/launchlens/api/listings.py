from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from launchlens.database import get_db

router = APIRouter()


@router.get("")
async def list_listings(db: AsyncSession = Depends(get_db)):
    return []


@router.get("/{listing_id}")
async def get_listing(listing_id: str, db: AsyncSession = Depends(get_db)):
    raise HTTPException(status_code=404)
