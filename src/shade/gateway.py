from __future__ import annotations

from typing import Any, Dict, Optional

from .http import AsyncHTTPClient, SyncHTTPClient, DEFAULT_MAX_RETRIES


class Gateway:
    """
    Main entry point for the Shade Payment Gateway.

    Parameters
    ----------
    api_key : str
        Your Shade API key.
    base_url : str
        Override the default API base URL (useful for testing).
    max_retries : int
        Number of automatic retries on HTTP 429.  Defaults to
        ``DEFAULT_MAX_RETRIES`` (3).  Set to ``0`` to disable.
    timeout : float
        Per-request socket timeout in seconds.
    """

    _DEFAULT_BASE_URL = "https://api.shadeprotocol.io/v1"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        self.api_key = api_key
        self._base_url = base_url or self._DEFAULT_BASE_URL
        self._http = SyncHTTPClient(
            base_url=self._base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )
        self._async_http = AsyncHTTPClient(
            base_url=self._base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Sync API
    # ------------------------------------------------------------------

    def process_payment(self, amount: float, currency: str) -> Dict[str, Any]:
        """
        Process a payment (sync).

        Parameters
        ----------
        amount : float
            Payment amount.
        currency : str
            ISO 4217 currency code (e.g. ``"USD"``).

        Returns
        -------
        dict
            API response body.
        """
        return self._http.request(
            "POST",
            "/payments",
            {"amount": amount, "currency": currency},
        )

    # ------------------------------------------------------------------
    # Async API
    # ------------------------------------------------------------------

    async def process_payment_async(
        self, amount: float, currency: str
    ) -> Dict[str, Any]:
        """Async variant of :meth:`process_payment`."""
        return await self._async_http.request(
            "POST",
            "/payments",
            {"amount": amount, "currency": currency},
        )