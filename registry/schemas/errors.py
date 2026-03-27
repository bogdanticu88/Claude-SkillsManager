# SkillPM Registry - Standard Error Responses
# Author: Bogdan Ticu
# License: MIT
#
# All API errors follow this standard format for consistency and debuggability.

from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum
from datetime import datetime


class ErrorCode(str, Enum):
    """Standard error codes for API responses"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    UNSUPPORTED = "UNSUPPORTED"


class ErrorDetail(BaseModel):
    """Standard error response format"""
    code: ErrorCode
    message: str
    detail: Optional[str] = None
    field: Optional[str] = None
    timestamp: str
    request_id: Optional[str] = None

    @staticmethod
    def create(
        code: ErrorCode,
        message: str,
        detail: Optional[str] = None,
        field: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict:
        """Create a standardized error response"""
        return {
            "code": code.value,
            "message": message,
            "detail": detail,
            "field": field,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        }


# Common error helpers

def validation_error(
    message: str,
    field: Optional[str] = None,
    detail: Optional[str] = None
) -> dict:
    """Return a validation error"""
    return ErrorDetail.create(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        field=field,
        detail=detail or "Check your input and try again",
    )


def unauthorized_error(detail: Optional[str] = None) -> dict:
    """Return an unauthorized error"""
    return ErrorDetail.create(
        code=ErrorCode.UNAUTHORIZED,
        message="Authentication required",
        detail=detail or "Include 'Authorization: Bearer <key>' header",
    )


def forbidden_error(resource: str = "resource") -> dict:
    """Return a forbidden error"""
    return ErrorDetail.create(
        code=ErrorCode.FORBIDDEN,
        message=f"You do not have permission to access this {resource}",
        detail="Contact the owner or administrator",
    )


def not_found_error(resource_type: str, identifier: str) -> dict:
    """Return a not found error"""
    return ErrorDetail.create(
        code=ErrorCode.NOT_FOUND,
        message=f"{resource_type} '{identifier}' not found",
        detail="Check the name/ID and try again",
    )


def conflict_error(reason: str, detail: Optional[str] = None) -> dict:
    """Return a conflict error"""
    return ErrorDetail.create(
        code=ErrorCode.CONFLICT,
        message=reason,
        detail=detail or "This resource already exists or conflicts with another",
    )


def rate_limited_error(retry_after: int = 60) -> dict:
    """Return a rate limit error"""
    return ErrorDetail.create(
        code=ErrorCode.RATE_LIMITED,
        message="Rate limit exceeded",
        detail=f"Wait {retry_after} seconds before making more requests",
    )


def server_error(error_type: str = "Internal Server Error") -> dict:
    """Return a server error"""
    return ErrorDetail.create(
        code=ErrorCode.SERVER_ERROR,
        message=error_type,
        detail="The server encountered an error. Try again later.",
    )
