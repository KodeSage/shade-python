from __future__ import annotations

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
    """Raised when an API resource cannot be found."""


class NetworkError(ShadeError):
    """Raised when the SDK cannot complete a network request."""
