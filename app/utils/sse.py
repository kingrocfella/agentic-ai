import json
from collections.abc import Generator

from app.agents import stream_ollama_agent_response


def generate_sse_events(query: str, agent_type: str) -> Generator[str, None, None]:
    """Generate Server-Sent Events from agent stream"""
    if agent_type == "ollama":
        for chunk in stream_ollama_agent_response(query):
            event_data = json.dumps(
                {
                    "event": chunk["event"],
                    "data": chunk["data"],
                }
            )
            yield f"data: {event_data}\n\n"

    # Send done event
    yield f"data: {json.dumps({'event': 'done', 'data': ''})}\n\n"
