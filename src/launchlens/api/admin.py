from fastapi import APIRouter

router = APIRouter()


@router.get("/health-detail")
async def health_detail():
    return {"status": "ok", "detail": "admin"}
