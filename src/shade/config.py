from __future__ import annotations

from enum import Enum
from typing import Optional

from stellar_sdk import Network

# Module-level API base URL override. Intended for development and testing only.
# Set this before creating any client to route all requests to a custom host.
api_base: Optional[str] = None


class Environment(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"

    @property
    def base_url(self) -> str:
        _urls: dict[str, str] = {
            "mainnet": "https://api.shadeprotocol.io/v1",
            "testnet": "https://testnet.api.shadeprotocol.io/v1",
        }
        return _urls[self.value]

    @property
    def network_passphrase(self) -> str:
        _passphrases: dict[str, str] = {
            "mainnet": Network.PUBLIC_NETWORK_PASSPHRASE,
            "testnet": Network.TESTNET_NETWORK_PASSPHRASE,
        }
        return _passphrases[self.value]
