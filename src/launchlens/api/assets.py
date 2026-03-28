from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.database import get_db

router = APIRouter()


@router.get("")
async def list_assets(db: AsyncSession = Depends(get_db)):
    return []
