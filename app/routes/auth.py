import json
from datetime import timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import redis_client
from app.schemas import UserRegister, UserLogin, UserResponse, LoginResponse, Token
from app.middleware import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    security,
)
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
def register(user: UserRegister) -> UserResponse:
    """Register a new user"""
    logger.info("Registration attempt for email: %s", user.email)

    if redis_client.get(f"user:{user.email}"):
        logger.warning("Registration failed - email already exists: %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Store user in Redis
    user_data = {"email": user.email, "password": hash_password(user.password)}
    redis_client.set(f"user:{user.email}", json.dumps(user_data))

    logger.info("User registered successfully: %s", user.email)
    return UserResponse(message="User registered successfully")


@router.post("/login", response_model=LoginResponse)
def login(user: UserLogin) -> LoginResponse:
    """Login a user"""
    logger.info("Login attempt for email: %s", user.email)

    user_data = redis_client.get(f"user:{user.email}")
    if not user_data:
        logger.warning("Login failed - user not found: %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    user_dict = json.loads(cast(str, user_data))

    # Verify password
    if not verify_password(user.password, user_dict["password"]):
        logger.warning("Login failed - invalid password for: %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.info("User logged in successfully: %s", user.email)
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
    logger.info("Logout attempt for user: %s", current_user)

    token = credentials.credentials

    # Blacklist the token until it expires
    redis_client.setex(f"blacklist:{token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")

    logger.info("User logged out successfully: %s", current_user)
    return UserResponse(message="Successfully logged out")
