import logging
from typing import Any, Mapping

logger = logging.getLogger("shade")

BODY_TRUNCATE_LENGTH = 2000


def mask_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive values masked."""
    masked: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            masked[key] = _mask_authorization(value)
        else:
            masked[key] = value
    return masked


def _mask_authorization(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def truncate_body(body: str, max_length: int = BODY_TRUNCATE_LENGTH) -> str:
    if len(body) <= max_length:
        return body
    return body[:max_length] + "[truncated]"


def _body_to_str(body: Any) -> str:
    if body is None:
        return ""
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)


def log_request(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: Any = None,
) -> None:
    logger.debug(
        "Request: %s %s | headers=%s | body=%s",
        method,
        url,
        mask_headers(headers),
        truncate_body(_body_to_str(body)),
    )


def log_response(
    status_code: int,
    headers: Mapping[str, str],
    body: Any = None,
) -> None:
    logger.debug(
        "Response: status=%s | headers=%s | body=%s",
        status_code,
        mask_headers(headers),
        truncate_body(_body_to_str(body)),
    )
