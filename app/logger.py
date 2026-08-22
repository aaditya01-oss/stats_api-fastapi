"""
logger.py — Structured logging for the Stats API.

Produces JSON logs instead of plain text strings.
Every request gets a unique ID for tracing across services.
"""

import logging
import json
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON instead of plain text.
    Makes logs searchable and parseable by monitoring tools.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        # Add any extra fields passed to the logger
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """
    Sets up structured JSON logging.
    Call once at application startup.
    """
    logger = logging.getLogger("stats_api")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger


logger = setup_logging()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every request and response.

    Middleware sits between the web server and your route functions.
    Every request passes through it automatically — you don't need
    to add logging to each individual route.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Log incoming request
        logger.info(
            "Request received",
            extra={
                "extra": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            }
        )

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Log response
        logger.info(
            "Request completed",
            extra={
                "extra": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            }
        )

        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id
        return response