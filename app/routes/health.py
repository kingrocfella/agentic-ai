from fastapi import APIRouter

from app.schemas import UserResponse
from app.utils.logger import logger

router = APIRouter()


@router.get("/health", response_model=UserResponse)
def health_check() -> UserResponse:
    """Check the health of the API"""
    logger.debug("Health check endpoint called")
    return UserResponse(message="AI Agent API is healthy")
