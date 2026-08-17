from fastapi import FastAPI, HTTPException, Request
from starlette.responses import JSONResponse

from app.config import IS_PRODUCTION, MAX_REQUEST_BODY_BYTES, REQUEST_TIMEOUT_SECONDS
from app.middleware import LoggingMiddleware, RequestProtectionMiddleware
from app.routes import agents_router, auth_router, health_router
from app.utils.logger import logger

app = FastAPI(title="AI Agent API")

# Add logging middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    RequestProtectionMiddleware,
    max_body_bytes=MAX_REQUEST_BODY_BYTES,
    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
    enable_hsts=IS_PRODUCTION,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(agents_router)


@app.exception_handler(404)
def not_found_handler(request: Request, _exc: HTTPException):
    """Return a bounded first-party 404 response."""
    logger.warning("404 Not Found: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception: %s %s - %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
