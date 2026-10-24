"""Common response schemas for HeatShield Bharat API."""

from typing import Any
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Field-level error detail."""

    field: str = Field(..., description="Target field name or path")
    message: str = Field(..., description="Description of the validation failure")
    value: Any = Field(default=None, description="Supplied input value (if safe to reflect)")


class ErrorBody(BaseModel):
    """Standard error response body."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable summary message")
    details: list[ErrorDetail] | None = Field(default=None, description="Optional field-level errors")


class ErrorResponse(BaseModel):
    """Standard top-level error response envelope."""

    error: ErrorBody
