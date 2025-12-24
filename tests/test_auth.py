"""Unit tests for authentication routes."""

import json
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient


# =============================================================================
# Register Tests
# =============================================================================


def test_register_success(client: TestClient, mock_redis: Any) -> None:
    """Test successful user registration."""
    response = client.post(
        "/register",
        json={"email": "newuser@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["message"] == "User registered successfully"

    # Verify user was stored in Redis
    stored_user = mock_redis.get("user:newuser@example.com")
    assert stored_user is not None
    user_data = json.loads(stored_user)
    assert user_data["email"] == "newuser@example.com"
    assert "password" in user_data
    assert user_data["password"] != "StrongPass123!"  # Password should be hashed


def test_register_duplicate_email(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    """Test registration with an already registered email."""
    response = client.post(
        "/register",
        json={"email": registered_user["email"], "password": "AnotherPass123!"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email already registered"


def test_register_invalid_email(client: TestClient) -> None:
    """Test registration with an invalid email format."""
    response = client.post(
        "/register",
        json={"email": "not-an-email", "password": "StrongPass123!"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_missing_password(client: TestClient) -> None:
    """Test registration with missing password."""
    response = client.post(
        "/register",
        json={"email": "test@example.com"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_missing_email(client: TestClient) -> None:
    """Test registration with missing email."""
    response = client.post(
        "/register",
        json={"password": "StrongPass123!"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_empty_body(client: TestClient) -> None:
    """Test registration with empty request body."""
    response = client.post("/register", json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Login Tests
# =============================================================================


def test_login_success(client: TestClient, registered_user: dict[str, str]) -> None:
    """Test successful login."""
    response = client.post("/login", json=registered_user)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "User logged in successfully"
    assert "data" in data
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


def test_login_wrong_password(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    """Test login with incorrect password."""
    response = client.post(
        "/login",
        json={"email": registered_user["email"], "password": "WrongPassword123!"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_user(client: TestClient) -> None:
    """Test login with non-existent email."""
    response = client.post(
        "/login",
        json={"email": "nonexistent@example.com", "password": "SomePass123!"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password"


def test_login_invalid_email_format(client: TestClient) -> None:
    """Test login with invalid email format."""
    response = client.post(
        "/login",
        json={"email": "invalid-email", "password": "SomePass123!"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_missing_credentials(client: TestClient) -> None:
    """Test login with missing credentials."""
    response = client.post("/login", json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_token_is_valid_jwt(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    """Test that the returned token is a valid JWT."""
    from jose import jwt

    from app.config import ALGORITHM, SECRET_KEY

    response = client.post("/login", json=registered_user)
    token = response.json()["data"]["access_token"]

    # Decode and verify the token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == registered_user["email"]
    assert "exp" in payload


# =============================================================================
# Logout Tests
# =============================================================================


def test_logout_success(
    client: TestClient,
    auth_headers: dict[str, str],
    auth_token: str,
    mock_redis: Any,
) -> None:
    """Test successful logout."""
    response = client.get("/logout", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Successfully logged out"

    # Verify token is blacklisted
    assert mock_redis.get(f"blacklist:{auth_token}") == "1"


def test_logout_without_token(client: TestClient) -> None:
    """Test logout without authentication token."""
    response = client.get("/logout")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_logout_with_invalid_token(client: TestClient) -> None:
    """Test logout with an invalid token."""
    response = client.get(
        "/logout",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or expired token"


def test_logout_with_blacklisted_token(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test logout with an already blacklisted token."""
    # First logout
    client.get("/logout", headers=auth_headers)

    # Second logout with same token should fail
    response = client.get("/logout", headers=auth_headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or expired token"


def test_logout_with_malformed_auth_header(client: TestClient) -> None:
    """Test logout with malformed authorization header."""
    response = client.get(
        "/logout",
        headers={"Authorization": "NotBearer token"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Auth Flow Integration Tests
# =============================================================================


def test_register_login_logout_flow(client: TestClient) -> None:
    """Test complete auth flow: register -> login -> logout."""
    user_data = {"email": "flowtest@example.com", "password": "FlowTest123!"}

    # Register
    register_response = client.post("/register", json=user_data)
    assert register_response.status_code == status.HTTP_201_CREATED

    # Login
    login_response = client.post("/login", json=user_data)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    # Logout
    logout_response = client.get(
        "/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == status.HTTP_200_OK

    # Try to use the same token after logout (should fail)
    second_logout = client.get(
        "/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_logout.status_code == status.HTTP_401_UNAUTHORIZED


def test_multiple_logins_both_valid(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    """Test that multiple logins both return valid tokens."""
    response1 = client.post("/login", json=registered_user)
    response2 = client.post("/login", json=registered_user)

    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK

    # Both tokens should be valid JWTs
    token1 = response1.json()["data"]["access_token"]
    token2 = response2.json()["data"]["access_token"]

    assert len(token1) > 0
    assert len(token2) > 0
    assert token1.count(".") == 2  # Valid JWT has 3 parts
    assert token2.count(".") == 2


def test_logout_blacklists_token_in_redis(
    client: TestClient,
    auth_headers: dict[str, str],
    auth_token: str,
    mock_redis: Any,
) -> None:
    """Test that logout properly blacklists the token in Redis."""
    # Logout
    response = client.get("/logout", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    # Token should be blacklisted in Redis
    assert mock_redis.get(f"blacklist:{auth_token}") == "1"

    # Subsequent request with same token should fail
    response = client.get("/logout", headers=auth_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
