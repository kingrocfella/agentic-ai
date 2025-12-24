"""Unit tests for agents routes."""

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient


def _mock_sse_generator(_query: str, _agent_type: str) -> Generator[str, None, None]:
    """Default mock SSE generator for tests."""
    yield 'data: {"event": "message", "data": "Hello"}\n\n'
    yield 'data: {"event": "done", "data": ""}\n\n'


# =============================================================================
# Basic Chat Tests
# =============================================================================


def test_chat_success_with_ollama(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test successful chat with ollama agent."""
    with patch(
        "app.routes.agents.generate_sse_events", side_effect=_mock_sse_generator
    ):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "What is 2+2?"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_chat_returns_streaming_headers(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test that chat returns proper streaming headers."""
    with patch(
        "app.routes.agents.generate_sse_events", side_effect=_mock_sse_generator
    ):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "Hello"},
            headers=auth_headers,
        )

        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"


def test_chat_invalid_agent_type(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test chat with an invalid agent type."""
    response = client.get(
        "/agents/chat",
        params={"agent_type": "invalid_agent", "query": "Hello"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid agent type"


# =============================================================================
# Authentication Tests
# =============================================================================


def test_chat_without_authentication(client: TestClient) -> None:
    """Test chat without authentication token."""
    response = client.get(
        "/agents/chat",
        params={"agent_type": "ollama", "query": "Hello"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_chat_with_invalid_token(client: TestClient) -> None:
    """Test chat with an invalid authentication token."""
    response = client.get(
        "/agents/chat",
        params={"agent_type": "ollama", "query": "Hello"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_chat_with_blacklisted_token(
    client: TestClient,
    auth_headers: dict[str, str],
    auth_token: str,
    mock_redis: Any,
) -> None:
    """Test chat with a blacklisted token."""
    mock_redis.set(f"blacklist:{auth_token}", "1")

    response = client.get(
        "/agents/chat",
        params={"agent_type": "ollama", "query": "Hello"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Parameter Validation Tests
# =============================================================================


def test_chat_missing_query_parameter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test chat with missing query parameter."""
    response = client.get(
        "/agents/chat",
        params={"agent_type": "ollama"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_missing_agent_type_parameter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test chat with missing agent_type parameter."""
    response = client.get(
        "/agents/chat",
        params={"query": "Hello"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_empty_query(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test chat with an empty query string."""
    with patch(
        "app.routes.agents.generate_sse_events", side_effect=_mock_sse_generator
    ):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": ""},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# SSE Format Tests
# =============================================================================


def test_sse_message_format(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test that SSE messages follow the correct format."""
    with patch(
        "app.routes.agents.generate_sse_events", side_effect=_mock_sse_generator
    ):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "Hi"},
            headers=auth_headers,
        )

        content = response.content.decode()
        lines = content.strip().split("\n\n")

        for line in lines:
            assert line.startswith("data: ")
            json_data = json.loads(line.replace("data: ", ""))
            assert "event" in json_data
            assert "data" in json_data


def test_sse_done_event_at_end(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test that SSE stream ends with a done event."""

    def generator(_q: str, _a: str) -> Generator[str, None, None]:
        yield 'data: {"event": "message", "data": "Processing..."}\n\n'
        yield 'data: {"event": "done", "data": ""}\n\n'

    with patch("app.routes.agents.generate_sse_events", side_effect=generator):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "Process"},
            headers=auth_headers,
        )

        content = response.content.decode()
        lines = [line for line in content.strip().split("\n\n") if line]
        last_event = json.loads(lines[-1].replace("data: ", ""))

        assert last_event["event"] == "done"


# =============================================================================
# Response Content Tests
# =============================================================================


def test_current_weather_query_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test current weather query returns weather data."""

    def generator(_q: str, _a: str) -> Generator[str, None, None]:
        yield 'data: {"event": "message", "data": "Current Weather in London: 15°C"}\n\n'
        yield 'data: {"event": "done", "data": ""}\n\n'

    with patch("app.routes.agents.generate_sse_events", side_effect=generator):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "What's the weather in London?"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Weather" in response.content.decode()


def test_historical_weather_query_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test historical weather query returns past weather data."""

    def generator(_q: str, _a: str) -> Generator[str, None, None]:
        yield 'data: {"event": "message", "data": "Historical Weather in Paris on 2024-06-15"}\n\n'
        yield 'data: {"event": "done", "data": ""}\n\n'

    with patch("app.routes.agents.generate_sse_events", side_effect=generator):
        response = client.get(
            "/agents/chat",
            params={
                "agent_type": "ollama",
                "query": "What was the weather in Paris on June 15, 2024?",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Weather" in response.content.decode()


def test_forecast_weather_query_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test forecast weather query returns future weather data."""

    def generator(_q: str, _a: str) -> Generator[str, None, None]:
        yield 'data: {"event": "message", "data": "Weather Forecast for Tokyo"}\n\n'
        yield 'data: {"event": "done", "data": ""}\n\n'

    with patch("app.routes.agents.generate_sse_events", side_effect=generator):
        response = client.get(
            "/agents/chat",
            params={
                "agent_type": "ollama",
                "query": "What will the weather be in Tokyo next week?",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Weather" in response.content.decode()


def test_math_query_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test math query returns correct answer."""

    def generator(_q: str, _a: str) -> Generator[str, None, None]:
        yield 'data: {"event": "message", "data": "2 + 2 = 4"}\n\n'
        yield 'data: {"event": "done", "data": ""}\n\n'

    with patch("app.routes.agents.generate_sse_events", side_effect=generator):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "What is 2 + 2?"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "4" in response.content.decode()


# =============================================================================
# Edge Cases
# =============================================================================


def test_chat_with_special_characters(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test chat with special characters in the query."""
    with patch(
        "app.routes.agents.generate_sse_events", side_effect=_mock_sse_generator
    ):
        response = client.get(
            "/agents/chat",
            params={
                "agent_type": "ollama",
                "query": "What about @#$%^&*()? And émojis 🎉?",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


def test_chat_with_long_query(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test chat with a very long query string."""
    long_query = "Hello " * 1000

    with patch(
        "app.routes.agents.generate_sse_events", side_effect=_mock_sse_generator
    ):
        response = client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": long_query},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


def test_generator_called_with_correct_params(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test that the SSE generator is called with correct parameters."""
    with patch("app.routes.agents.generate_sse_events") as mock_sse:
        mock_sse.side_effect = _mock_sse_generator

        client.get(
            "/agents/chat",
            params={"agent_type": "ollama", "query": "Test query"},
            headers=auth_headers,
        )

        mock_sse.assert_called_once_with("Test query", "ollama")


# =============================================================================
# Config Tests
# =============================================================================


def test_supported_agents_contains_ollama() -> None:
    """Test that SUPPORTED_AGENTS contains ollama."""
    from app.config import SUPPORTED_AGENTS

    assert "ollama" in SUPPORTED_AGENTS
    assert isinstance(SUPPORTED_AGENTS, tuple)
