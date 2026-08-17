from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import (
    AGENT_RATE_LIMIT,
    AGENT_RATE_WINDOW_SECONDS,
    AGENT_SLOT_TTL_SECONDS,
    SUPPORTED_AGENTS,
)
from app.middleware import get_current_user
from app.security import acquire_agent_slot, enforce_rate_limit, release_agent_slot
from app.utils.sse import generate_sse_events
from app.utils.logger import logger


router = APIRouter()


class AgentChatRequest(BaseModel):
    """Chat input belongs in the body so prompts never enter URL/history logs."""

    model_config = ConfigDict(extra="forbid")

    agent_type: str = Field(min_length=1, max_length=32)
    query: str = Field(min_length=1, max_length=4000)


@router.post("/agents/chat")
def get_agent_response(
    request: AgentChatRequest,
    current_user: str = Depends(get_current_user),
) -> StreamingResponse:
    """Stream responses from an agent via Server-Sent Events"""
    enforce_rate_limit(
        "agent",
        current_user,
        limit=AGENT_RATE_LIMIT,
        window_seconds=AGENT_RATE_WINDOW_SECONDS,
    )
    logger.info("Agent chat request - agent: %s", request.agent_type)

    if request.agent_type not in SUPPORTED_AGENTS:
        logger.warning("Invalid agent type requested: %s", request.agent_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent type"
        )

    slot_key = acquire_agent_slot(current_user, ttl_seconds=AGENT_SLOT_TTL_SECONDS)

    def guarded_events() -> Generator[str, None, None]:
        try:
            yield from generate_sse_events(request.query, request.agent_type)
        finally:
            release_agent_slot(slot_key)

    logger.debug("Starting SSE stream for agent: %s", request.agent_type)
    return StreamingResponse(
        guarded_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
