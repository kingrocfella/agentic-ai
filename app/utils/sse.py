import json
from collections.abc import Generator

from app.agents import stream_ollama_agent_response
from app.utils.logger import logger


def generate_sse_events(query: str, agent_type: str) -> Generator[str, None, None]:
    """Generate Server-Sent Events from agent stream"""
    logger.info("Starting SSE event generation for agent: %s", agent_type)

    event_count = 0

    if agent_type == "ollama":
        for chunk in stream_ollama_agent_response(query):
            event_data = json.dumps(
                {
                    "event": chunk["event"],
                    "data": chunk["data"],
                }
            )
            event_count += 1
            yield f"data: {event_data}\n\n"

    # Send done event
    logger.info("SSE stream completed - %d events sent", event_count)
    yield f"data: {json.dumps({'event': 'done', 'data': ''})}\n\n"
