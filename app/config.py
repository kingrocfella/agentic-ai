import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _required_setting(name: str, minimum_length: int = 1) -> str:
    """Load a required setting and reject placeholder values."""
    value = os.getenv(name, "").strip()
    if len(value) < minimum_length or value.lower().startswith("change-me"):
        raise RuntimeError(
            f"{name} must be configured with at least {minimum_length} non-placeholder characters"
        )
    return value


SECRET_KEY = _required_setting("REDIS_SECRET_KEY", 32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "agentic-ai-api").strip()
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "agentic-ai-client").strip()
MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", "65536"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
WEATHER_TIMEOUT_SECONDS = float(os.getenv("WEATHER_TIMEOUT_SECONDS", "5"))
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
REDIS_URL = _required_setting("REDIS_URL")
WEATHER_API_KEY = _required_setting("WEATHER_API_KEY")
WEATHER_API_BASE_URL = _required_setting("WEATHER_API_BASE_URL")
OLLAMA_HOST = _required_setting("OLLAMA_HOST")
# The shared VPS runs exactly one Ollama daemon (Lost Vowels'). Keeping the tag
# in .env lets this app converge on a model that daemon already holds, instead
# of forcing it to swap weights on every request.
OLLAMA_MODEL = _required_setting("OLLAMA_MODEL")
SUPPORTED_AGENTS = ("ollama",)

# Abuse controls. These live in .env so a quota can be retuned on the VPS
# without rebuilding the image.
REGISTER_RATE_LIMIT = int(os.getenv("REGISTER_RATE_LIMIT", "5"))
REGISTER_RATE_WINDOW_SECONDS = int(os.getenv("REGISTER_RATE_WINDOW_SECONDS", "3600"))
LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "10"))
LOGIN_RATE_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "900"))
AGENT_RATE_LIMIT = int(os.getenv("AGENT_RATE_LIMIT", "60"))
AGENT_RATE_WINDOW_SECONDS = int(os.getenv("AGENT_RATE_WINDOW_SECONDS", "3600"))
AGENT_SLOT_TTL_SECONDS = int(os.getenv("AGENT_SLOT_TTL_SECONDS", "180"))

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").strip().lower() in {
    "prod",
    "production",
}

if not JWT_ISSUER or not JWT_AUDIENCE:
    raise RuntimeError("JWT_ISSUER and JWT_AUDIENCE must be configured")
if (
    min(
        REGISTER_RATE_LIMIT,
        REGISTER_RATE_WINDOW_SECONDS,
        LOGIN_RATE_LIMIT,
        LOGIN_RATE_WINDOW_SECONDS,
        AGENT_RATE_LIMIT,
        AGENT_RATE_WINDOW_SECONDS,
        AGENT_SLOT_TTL_SECONDS,
    )
    <= 0
):
    raise RuntimeError("Rate-limit quotas, windows, and slot TTL must be positive")
if (
    min(
        MAX_REQUEST_BODY_BYTES,
        REQUEST_TIMEOUT_SECONDS,
        WEATHER_TIMEOUT_SECONDS,
        OLLAMA_TIMEOUT_SECONDS,
    )
    <= 0
):
    raise RuntimeError("Request and upstream timeouts must be positive")

if urlparse(REDIS_URL).scheme not in {"redis", "rediss"}:
    raise RuntimeError("REDIS_URL must use the redis:// or rediss:// scheme")
