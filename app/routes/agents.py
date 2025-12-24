from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import SUPPORTED_AGENTS
from app.middleware import get_current_user
from app.utils import generate_sse_events
from app.utils.logger import logger


router = APIRouter()


@router.get("/agents/chat")
def get_agent_response(
    agent_type: str,
    query: str,
    current_user: str = Depends(get_current_user),
) -> StreamingResponse:
    """Stream responses from an agent via Server-Sent Events"""
    logger.info(
        "Agent chat request - user: %s, agent: %s, query: %s",
        current_user,
        agent_type,
        query
    )

    if agent_type not in SUPPORTED_AGENTS:
        logger.warning("Invalid agent type requested: %s", agent_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent type"
        )

    logger.debug("Starting SSE stream for agent: %s", agent_type)
    return StreamingResponse(
        generate_sse_events(query, agent_type),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
