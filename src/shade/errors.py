from __future__ import annotations

import json
from typing import Any, Optional

INVALID_REQUEST_STATUS_CODES = (400, 422)


class ShadeError(Exception):
    """Base exception for all Shade SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)

    def __str__(self) -> str:
        if self.status_code is None:
            return self.message
        return f"{self.message} (status code: {self.status_code})"


class AuthenticationError(ShadeError):
    """Raised when authentication fails or credentials are invalid."""


class InvalidRequestError(ShadeError):
    """Raised on HTTP 400/422 responses for malformed or invalid parameters."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        param: Optional[str] = None,
        field_errors: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        parsed = _parse_error_response(response_body)
        self.param: Optional[str] = param if param is not None else parsed.get("param")
        self.field_errors: dict[str, Any] = (
            field_errors if field_errors is not None else parsed.get("field_errors", {})
        )

    def __str__(self) -> str:
        message = self.message
        if self.param:
            message = f"{message} (param: {self.param})"
        if self.status_code is None:
            return message
        return f"{message} (status code: {self.status_code})"

    @classmethod
    def from_response(
        cls,
        status_code: int,
        response_body: Optional[str] = None,
    ) -> "InvalidRequestError":
        """Construct from a raw 400/422 API response body."""
        parsed = _parse_error_response(response_body)
        message = parsed.get("message") or "Invalid request"
        return cls(
            message,
            status_code=status_code,
            response_body=response_body,
            param=parsed.get("param"),
            field_errors=parsed.get("field_errors", {}),
        )


class NotFoundError(ShadeError):
    """Raised when an API resource cannot be found."""


class NetworkError(ShadeError):
    """Raised when the SDK cannot complete a network request."""


def raise_for_invalid_request(
    status_code: int,
    response_body: Optional[str] = None,
) -> None:
    """Raise InvalidRequestError when the API returns 400 or 422."""
    if status_code in INVALID_REQUEST_STATUS_CODES:
        raise InvalidRequestError.from_response(status_code, response_body)


def _parse_body(response_body: Optional[str]) -> dict[str, Any]:
    if not response_body:
        return {}
    try:
        data = json.loads(response_body)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _parse_error_response(response_body: Optional[str]) -> dict[str, Any]:
    data = _parse_body(response_body)
    error = data.get("error", {})
    if not isinstance(error, dict):
        error = {}

    field_errors = error.get("field_errors")
    if not isinstance(field_errors, dict):
        field_errors = data.get("field_errors")
    if not isinstance(field_errors, dict):
        field_errors = {}

    message = error.get("message")
    if not message:
        message = data.get("message")

    return {
        "message": message,
        "param": error.get("param"),
        "field_errors": field_errors,
    }
