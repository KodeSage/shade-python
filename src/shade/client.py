from typing import Any, Mapping, Optional

import httpx

from shade._debug import log_request, log_response
from shade.config import config


class ShadeClient:
    """HTTP client for the Shade Payment Gateway API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.shadeprotocol.io",
        debug: bool = False,
        http_client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self._http = http_client or httpx.Client()
        self._owns_http_client = http_client is None

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> "ShadeClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _should_debug(self) -> bool:
        return self.debug or config.debug

    def _default_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json: Any = None,
        content: Optional[bytes] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        request_headers = {**self._default_headers(), **(headers or {})}

        if self._should_debug():
            log_request(method, url, request_headers, content if content is not None else json)

        response = self._http.request(
            method,
            url,
            headers=request_headers,
            json=json,
            content=content,
        )

        if self._should_debug():
            log_response(response.status_code, response.headers, response.text)

        return response
