from __future__ import annotations

from enum import Enum
from typing import Optional

from stellar_sdk import Network

# Module-level API base URL override. Intended for development and testing only.
# Set this before creating any client to route all requests to a custom host.
api_base: Optional[str] = None

# Default HTTP client settings. Override via ``shade.timeout`` / ``shade.max_retries``
# or per-client constructor arguments on ``ShadeClient`` / ``Gateway``.
DEFAULT_TIMEOUT: float = 30.0
DEFAULT_MAX_RETRIES: int = 3
MAX_RETRIES_LIMIT: int = 10

timeout: float = DEFAULT_TIMEOUT
max_retries: int = DEFAULT_MAX_RETRIES


def validate_client_settings(timeout: float, max_retries: int) -> None:
    """Raise ValueError for out-of-range timeout or retry settings."""
    if timeout <= 0:
        raise ValueError(f"timeout must be greater than 0, got {timeout!r}")
    if max_retries < 0 or max_retries > MAX_RETRIES_LIMIT:
        raise ValueError(
            f"max_retries must be between 0 and {MAX_RETRIES_LIMIT}, got {max_retries!r}"
        )


class Environment(str, Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"

    @property
    def base_url(self) -> str:
        _urls: dict[str, str] = {
            "sandbox": "https://testnet.api.shadeprotocol.io/v1",
            "production": "https://api.shadeprotocol.io/v1",
        }
        return _urls[self.value]

    @property
    def network_passphrase(self) -> str:
        _passphrases: dict[str, str] = {
            "sandbox": Network.TESTNET_NETWORK_PASSPHRASE,
            "production": Network.PUBLIC_NETWORK_PASSPHRASE,
        }
        return _passphrases[self.value]

    @property
    def horizon_url(self) -> str:
        _horizons: dict[str, str] = {
            "sandbox": "https://horizon-testnet.stellar.org",
            "production": "https://horizon.stellar.org",
        }
        return _horizons[self.value]


def parse_environment(value: str | Environment) -> Environment:
    if isinstance(value, Environment):
        return value
    if isinstance(value, str):
        try:
            return Environment(value.lower())
        except ValueError:
            pass
    raise ValueError("Invalid environment. Valid options are: 'sandbox', 'production'")

environment: Environment = Environment.SANDBOX
