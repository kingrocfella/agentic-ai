from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check the health of the API"""
    return {"status": "healthy"}
