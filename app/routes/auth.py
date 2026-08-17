import json
from datetime import timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    LOGIN_RATE_LIMIT,
    LOGIN_RATE_WINDOW_SECONDS,
    REGISTER_RATE_LIMIT,
    REGISTER_RATE_WINDOW_SECONDS,
)
from app.database import redis_client
from app.schemas import (
    DeleteAccountRequest,
    LoginResponse,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.middleware import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    security,
    token_fingerprint,
)
from app.security import enforce_rate_limit, purge_user_security_state
from app.utils.logger import logger

router = APIRouter()

# Precomputed hash used to equalize login timing on the unknown-account branch so
# response latency cannot be used to enumerate registered emails.
_TIMING_EQUALIZER_HASH = hash_password("timing-equalizer-placeholder")


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
def register(user: UserRegister, request: Request) -> UserResponse:
    """Register a new user"""
    client_host = request.client.host if request.client else "unknown"
    enforce_rate_limit(
        "register",
        client_host,
        limit=REGISTER_RATE_LIMIT,
        window_seconds=REGISTER_RATE_WINDOW_SECONDS,
    )
    logger.info("Registration attempt")

    if redis_client.get(f"user:{user.email}"):
        logger.info("Registration request matched an existing account")
        return UserResponse(message="User registered successfully")

    # Store user in Redis
    user_data = {"email": user.email, "password": hash_password(user.password)}
    redis_client.set(f"user:{user.email}", json.dumps(user_data))

    logger.info("User registered successfully")
    return UserResponse(message="User registered successfully")


@router.post("/login", response_model=LoginResponse)
def login(user: UserLogin, request: Request) -> LoginResponse:
    """Login a user"""
    client_host = request.client.host if request.client else "unknown"
    enforce_rate_limit(
        "login",
        f"{client_host}:{user.email.lower()}",
        limit=LOGIN_RATE_LIMIT,
        window_seconds=LOGIN_RATE_WINDOW_SECONDS,
    )
    logger.info("Login attempt")

    user_data = redis_client.get(f"user:{user.email}")
    if not user_data:
        # Run a dummy verify so the unknown-account path costs the same as a real
        # bcrypt comparison; otherwise the timing delta enumerates valid emails.
        verify_password(user.password, _TIMING_EQUALIZER_HASH)
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    user_dict = json.loads(cast(str, user_data))

    # Verify password
    if not verify_password(user.password, user_dict["password"]):
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.info("User logged in successfully")
    return LoginResponse(
        message="User logged in successfully",
        data=Token(access_token=access_token, token_type="bearer"),
    )


@router.post("/logout", response_model=UserResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: str = Depends(get_current_user),
) -> UserResponse:
    """Logout a user"""
    logger.info("Logout attempt")

    token = credentials.credentials

    # Blacklist the token until it expires
    redis_client.setex(
        f"blacklist:{token_fingerprint(token)}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1"
    )

    logger.info("User logged out successfully")
    return UserResponse(message="Successfully logged out")


@router.delete("/account", response_model=UserResponse)
def delete_account(
    request: DeleteAccountRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: str = Depends(get_current_user),
) -> UserResponse:
    """Permanently delete the authenticated account and invalidate every session."""
    stored = redis_client.get(f"user:{current_user}")
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_data = json.loads(cast(str, stored))
    if not verify_password(request.password, user_data["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = credentials.credentials
    redis_client.setex(
        f"blacklist:{token_fingerprint(token)}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1"
    )
    redis_client.delete(f"user:{current_user}")
    purge_user_security_state(current_user)
    logger.info("Account permanently deleted")
    return UserResponse(message="Account permanently deleted")
