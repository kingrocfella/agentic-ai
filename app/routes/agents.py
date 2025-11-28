from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import SUPPORTED_AGENTS
from app.middleware import get_current_user
from app.utils import generate_sse_events


router = APIRouter()


@router.post("/agents/chat")
def get_agent_response(
    agent_type: str,
    query: str,
    _: str = Depends(get_current_user),
) -> StreamingResponse:
    """Stream responses from an agent via Server-Sent Events"""
    if agent_type not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent type"
        )

    return StreamingResponse(
        generate_sse_events(query, agent_type),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
