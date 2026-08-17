"""Shared distributed abuse controls."""

import hashlib
import time

from fastapi import HTTPException, status

from app import database


def identity_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def enforce_rate_limit(
    action: str,
    identity: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """Enforce a Redis-backed fixed-window quota."""
    bucket = int(time.time()) // window_seconds
    key = f"rate:v1:{action}:{identity_fingerprint(identity)}:{bucket}"
    pipeline = database.redis_client.pipeline()
    pipeline.incr(key)
    pipeline.expire(key, window_seconds + 1)
    count, _ = pipeline.execute()
    if int(count) > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(window_seconds)},
        )


def acquire_agent_slot(user: str, ttl_seconds: int = 180) -> str:
    """Allow one expensive agent stream per account at a time."""
    key = f"agent:active:{identity_fingerprint(user)}"
    if not database.redis_client.set(key, "1", nx=True, ex=ttl_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="An agent request is already in progress",
            headers={"Retry-After": "5"},
        )
    return key


def release_agent_slot(key: str) -> None:
    database.redis_client.delete(key)


def purge_user_security_state(user: str) -> None:
    """Remove short-lived abuse-control state tied only to a deleted account."""
    fingerprint = identity_fingerprint(user)
    keys = list(database.redis_client.scan_iter(match=f"rate:v1:agent:{fingerprint}:*"))
    keys.append(f"agent:active:{fingerprint}")
    if keys:
        database.redis_client.delete(*keys)
