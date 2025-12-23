from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from starlette.responses import RedirectResponse

from app.middleware import LoggingMiddleware
from app.routes import auth_router, health_router, agents_router
from app.utils.logger import logger

load_dotenv()

app = FastAPI(title="AI Agent API")

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(agents_router)


@app.exception_handler(404)
def not_found_handler(request: Request, _exc: HTTPException):
    """Handle 404 errors by redirecting to external URL."""
    logger.warning("404 Not Found: %s %s", request.method, request.url.path)
    return RedirectResponse(url="https://ash-speed.hetzner.com/10GB.bin")


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception: %s %s - %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    raise HTTPException(status_code=500, detail="Internal server error") from exc
