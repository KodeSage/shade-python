"""
Shade SDK exceptions.
"""
from __future__ import annotations

from typing import Optional


class ShadeError(Exception):
    """Base exception for all Shade SDK errors."""


class HTTPError(ShadeError):
    """Raised for non-2xx responses that are not handled by a more specific error."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(HTTPError):
    """
    Raised when the API returns HTTP 429 Too Many Requests and either:
    - auto-retry is disabled, or
    - ``max_retries`` has been exhausted.

    Attributes
    ----------
    retry_after : int | None
        Seconds to wait before the next attempt, parsed from the
        ``Retry-After`` response header.  ``None`` if the header was absent.
    """

    def __init__(self, message: str, retry_after: Optional[int] = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after

    def __str__(self) -> str:  # pragma: no cover
        base = super().__str__()
        if self.retry_after is not None:
            return f"{base} (retry after {self.retry_after}s)"
        return base
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
