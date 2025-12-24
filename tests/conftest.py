"""Pytest configuration and fixtures for testing."""

import json
import os
from collections.abc import Generator
from unittest.mock import patch

import fakeredis
import pytest
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["REDIS_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["WEATHER_API_KEY"] = "test-weather-api-key"
os.environ["WEATHER_API_BASE_URL"] = "https://api.weatherapi.com/v1"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"


@pytest.fixture
def fake_redis() -> fakeredis.FakeRedis:
    """Create a fake Redis instance for testing."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_redis(
    fake_redis: fakeredis.FakeRedis,
) -> Generator[fakeredis.FakeRedis, None, None]:
    """Mock the Redis client with fake Redis."""
    with patch("app.database.redis_client", fake_redis):
        with patch("app.routes.auth.redis_client", fake_redis):
            with patch("app.middleware.auth.redis_client", fake_redis):
                yield fake_redis


@pytest.fixture
def client(mock_redis: fakeredis.FakeRedis) -> TestClient:
    """Create a test client with mocked Redis."""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def registered_user(mock_redis: fakeredis.FakeRedis) -> dict[str, str]:
    """Create a registered user in fake Redis and return credentials."""
    from app.middleware.auth import hash_password

    email = "testuser@example.com"
    password = "SecurePassword123!"

    user_data = {
        "email": email,
        "password": hash_password(password),
    }
    mock_redis.set(f"user:{email}", json.dumps(user_data))

    return {"email": email, "password": password}


@pytest.fixture
def auth_token(client: TestClient, registered_user: dict[str, str]) -> str:
    """Get an authentication token for a registered user."""
    response = client.post(
        "/login",
        json=registered_user,
    )
    return response.json()["data"]["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Get authorization headers with a valid token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_sse_generator() -> Generator[None, None, None]:
    """Mock the SSE event generator."""

    def fake_generator(_query: str, _agent_type: str) -> Generator[str, None, None]:
        yield 'data: {"event": "message", "data": "Hello"}\n\n'
        yield 'data: {"event": "message", "data": " World"}\n\n'
        yield 'data: {"event": "done", "data": ""}\n\n'

    with patch("app.routes.agents.generate_sse_events", side_effect=fake_generator):
        yield
