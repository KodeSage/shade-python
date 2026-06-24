from __future__ import annotations

import json
from typing import Optional


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
    """Raised when a request is malformed or rejected by validation."""


class NotFoundError(ShadeError):
    """Raised on HTTP 404 responses.

    Attributes:
        resource_type: Kind of resource that was not found (e.g. "payment", "invoice").
        resource_id:   ID of the missing resource.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        parsed = _parse_body(response_body)
        self.resource_type: Optional[str] = resource_type or parsed.get("resource_type")
        self.resource_id: Optional[str] = resource_id or parsed.get("resource_id")

    @classmethod
    def from_response(
        cls,
        message: str,
        response_body: Optional[str] = None,
    ) -> "NotFoundError":
        """Construct from a raw 404 response body."""
        return cls(message, status_code=404, response_body=response_body)


def _parse_body(response_body: Optional[str]) -> dict:
    if not response_body:
        return {}
    try:
        data = json.loads(response_body)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


class NetworkError(ShadeError):
    """Raised when the SDK cannot complete a network request."""
