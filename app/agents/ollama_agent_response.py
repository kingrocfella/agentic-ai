from collections.abc import Generator
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from app.config import OLLAMA_HOST
from app.tools import get_current_weather_by_city

# Base model for direct responses
base_model = ChatOllama(model="llama3.2:latest", temperature=0, base_url=OLLAMA_HOST)

# Model for the ReAct agent
agent_model = ChatOllama(model="llama3.2:latest", temperature=0, base_url=OLLAMA_HOST)

tools = [get_current_weather_by_city]

# Classifier prompt to determine if we need tools
CLASSIFIER_PROMPT = """Analyze the following user query and determine if it requires the weather tool.

Respond with ONLY "YES" if the query is asking about:
- Weather conditions in a specific location
- Temperature, humidity, wind, or climate in a city
- Current or forecast weather for a location

Respond with ONLY "NO" if the query is:
- A math question
- General knowledge question
- Any non-weather related query

User query: {query}

Answer (YES or NO):"""

# System prompt for direct responses (no tools)
DIRECT_RESPONSE_PROMPT = """You are a helpful AI assistant. Answer the user's question directly and concisely.

User question: {query}

Your answer:"""

# System prompt for the ReAct agent (with tools)
AGENT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to weather tools.

Use the get_current_weather_by_city tool to answer the user's weather-related question.

Remember to provide accurate, helpful information."""


agent = create_react_agent(agent_model, tools, state_modifier=AGENT_SYSTEM_PROMPT)


def needs_weather_tool(query: str) -> bool:
    """Determine if the query needs the weather tool"""
    classifier_prompt = CLASSIFIER_PROMPT.format(query=query)
    response = base_model.invoke([HumanMessage(content=classifier_prompt)])
    
    # Check if response contains "YES"
    return "yes" in response.content.lower().strip()


def stream_ollama_agent_response(query: str) -> Generator[dict[str, Any], None, None]:
    """Stream responses from an ollama agent using LangGraph"""
    
    # First, determine if we need tools
    if needs_weather_tool(query):
        # Use agent with tools
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
    else:
        # Answer directly without tools
        direct_prompt = DIRECT_RESPONSE_PROMPT.format(query=query)
        for chunk in base_model.stream([HumanMessage(content=direct_prompt)]):
            if hasattr(chunk, "content") and chunk.content:
                yield {
                    "event": "message",
                    "data": chunk.content,
                    "metadata": {},
                }
