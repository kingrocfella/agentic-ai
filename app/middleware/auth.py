from datetime import datetime, timedelta, timezone
import hashlib
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import cast

from app.config import ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, SECRET_KEY
from app.database import redis_client
from app.utils.logger import logger

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password"""
    logger.debug("Hashing password")
    return pwd_context.hash(password)


def token_fingerprint(token: str) -> str:
    """Return a non-reversible identifier for Redis revocation keys."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    logger.debug("Verifying password")
    result = pwd_context.verify(plain_password, hashed_password)
    if not result:
        logger.debug("Password verification failed")
    return result


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create an access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    issued_at = datetime.now(timezone.utc)
    to_encode.update(
        {
            "aud": JWT_AUDIENCE,
            "exp": expire,
            "iat": issued_at,
            "iss": JWT_ISSUER,
            "jti": str(uuid4()),
            "type": "access",
        }
    )

    logger.debug(
        "Creating access token for sub: %s, expires: %s",
        data.get("sub"),
        expire.isoformat(),
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Get the current user"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check if token is blacklisted
    if redis_client.get(f"blacklist:{token_fingerprint(token)}"):
        logger.warning("Attempted use of blacklisted token")
        raise credentials_exception

    email: str | None = None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        if (
            payload.get("type") != "access"
            or not payload.get("jti")
            or not payload.get("iat")
        ):
            raise JWTError("Missing required token claims")
        email = cast(str, payload.get("sub"))
        logger.debug("Token decoded successfully")
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", type(exc).__name__)
        raise credentials_exception from exc

    if email and redis_client.get(f"user:{email}"):
        return email

    logger.warning("Token account is missing or inactive")
    raise credentials_exception
