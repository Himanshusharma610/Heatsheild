"""Application exceptions and centralized error handlers.

Adheres to Module 2 API error contract:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description.",
    "details": [...]  # optional
  }
}
"""

import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception for managed API errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class BadRequestException(AppException):
    """400 Bad Request."""

    def __init__(self, message: str = "Bad request", details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class UnauthorizedException(AppException):
    """401 Unauthorized."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    """403 Forbidden."""

    def __init__(self, message: str = "Access forbidden") -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundException(AppException):
    """404 Not Found."""

    def __init__(self, message: str = "Requested resource not found") -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictException(AppException):
    """409 Conflict."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )


class ValidationException(AppException):
    """422 Validation Error."""

    def __init__(self, message: str = "Validation failed", details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class RateLimitedException(AppException):
    """429 Rate Limited."""

    def __init__(self, message: str = "Too many requests. Please try again later.") -> None:
        super().__init__(
            message=message,
            code="RATE_LIMITED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ServiceUnavailableException(AppException):
    """503 Service Unavailable."""

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# Mapping from standard HTTP status codes to machine-readable error codes
HTTP_STATUS_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def build_error_payload(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Format an error payload adhering to the API specification."""
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return payload


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    payload = build_error_payload(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI and Pydantic request validation errors."""
    details: list[dict[str, Any]] = []
    for error in exc.errors():
        # Build field path omitting the top-level 'body' prefix if present
        loc = error.get("loc", ())
        field_parts = [str(part) for part in loc if part != "body"]
        field_name = ".".join(field_parts) if field_parts else "body"

        detail_entry: dict[str, Any] = {
            "field": field_name,
            "message": error.get("msg", "Invalid value"),
        }
        if "input" in error:
            detail_entry["value"] = error["input"]
        details.append(detail_entry)

    payload = build_error_payload(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=details,
    )
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content=payload,
    )


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard Starlette / FastAPI HTTPExceptions."""
    code = HTTP_STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if isinstance(exc.detail, str) else "HTTP error"
    payload = build_error_payload(code=code, message=message)
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions to prevent information disclosure."""
    logger.exception("Unhandled server exception: %s", exc)
    payload = build_error_payload(
        code="INTERNAL_ERROR",
        message="An unexpected internal server error occurred.",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized error handlers with the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
