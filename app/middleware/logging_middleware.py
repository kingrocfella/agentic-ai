"""Middleware for logging API requests."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            "API Request: %s %s - Client: %s - Query: %s",
            request.method,
            request.url.path,
            client_ip,
            dict(request.query_params),
        )

        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log successful response
            logger.info(
                "API Response: %s %s - Status: %s - Time: %.3fs",
                request.method,
                request.url.path,
                response.status_code,
                process_time,
            )

            return response

        except Exception as exc:  # pylint: disable=broad-exception-caught
            process_time = time.time() - start_time

            # Log error
            logger.error(
                "API Error: %s %s - Client: %s - Time: %.3fs - Error: %s",
                request.method,
                request.url.path,
                client_ip,
                process_time,
                str(exc),
                exc_info=True,
            )
            raise
