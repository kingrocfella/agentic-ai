from fastapi import APIRouter

from app.schemas import UserResponse

router = APIRouter()


@router.get("/health", response_model=UserResponse)
def health_check() -> UserResponse:
    """Check the health of the API"""
    return UserResponse(message="API is healthy")
