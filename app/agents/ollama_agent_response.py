from collections.abc import Generator
from typing import Any

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from app.config import OLLAMA_HOST
from app.tools import get_current_weather_by_city

model = ChatOllama(model="llama3.2:latest", temperature=0.5, base_url=OLLAMA_HOST)

tools = [get_current_weather_by_city]

SYSTEM_PROMPT = """You are a helpful AI assistant with access to the following tools:

1. **get_current_weather_by_city**: Use this tool to get current weather information for any city. 
   Simply provide the city name and it will return temperature, conditions, humidity, and wind data.

When the user asks about weather, forecasts, or climate conditions for a specific location, 
you SHOULD use the get_current_weather_by_city tool to provide accurate, real-time information.

For other questions, respond directly using your knowledge.

Always be helpful, concise, and accurate in your responses."""


agent = create_react_agent(model, tools, state_modifier=SYSTEM_PROMPT)


def stream_ollama_agent_response(query: str) -> Generator[dict[str, Any], None, None]:
    """Stream responses from an ollama agent using LangGraph"""
    for chunk in agent.stream(
        {"messages": [("user", query)]},
        stream_mode="messages",
    ):

        message, metadata = chunk
        if hasattr(message, "content") and message.content:
            yield {
                "event": "message",
                "data": message.content,
                "metadata": metadata,
            }
