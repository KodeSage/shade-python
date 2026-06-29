# Shade Python SDK — Pending Features

This document tracks the work required to take `shade-python` from its current
skeleton state to a production-ready SDK in the style of the Stripe / Paystack
Python SDKs.

## Current State

- `Gateway` class with a single placeholder method (`process_payment`) that
  just prints and returns `True`.
- `base.py`, `invoice.py`, `merchant.py` are empty stub files.
- One trivial test file (`tests/test_gateway.py`).
- Only declared dependency is `stellar-sdk`; dev tooling is `pytest`,
  `flake8`, `black`, `isort`.

## 1. Client & Configuration Layer

The SDK entry point — mirrors how Stripe/Paystack SDKs work.

```python
import shade
shade.api_key = "sk_live_..."
shade.environment = "production"  # or "sandbox"
```

- API key management (public key + secret key)
- Environment switching (Stellar testnet vs mainnet)
- Global config vs per-instance config (`ShadeClient`)
- Timeout and retry settings
- Configurable API base URL (self-hosted backend support)

## 2. HTTP Transport Layer (`shade/http_client.py`)

- Wraps `httpx` (sync + async) for REST calls to the Shade backend
- Request signing / auth header injection (`Authorization: Bearer sk_...`)
- Automatic retry with exponential backoff on transient failures
- Rate limit handling (parse `Retry-After` headers)
- Unified response parsing — raises typed exceptions on 4xx/5xx
- Idempotency key support for write requests
- Debug-mode request/response logging

## 3. Exceptions (`shade/errors.py`)

Typed exception hierarchy, like Stripe's:

| Exception | When |
|---|---|
| `ShadeError` | Base for all SDK errors |
| `AuthenticationError` | Invalid or missing API key |
| `InvalidRequestError` | Bad parameters (400) |
| `NotFoundError` | Resource doesn't exist (404) |
| `RateLimitError` | Too many requests (429) |
| `NetworkError` | Connection/timeout failures |
| `SignatureVerificationError` | Bad webhook signature |
| `StellarError` | On-chain transaction failures |

## 4. Data Models (`shade/models/`)

Typed response objects (Pydantic) for everything the API returns — no raw
dicts leaked to the user.

- `Payment` — id, status, amount, currency, stellar_tx_hash, created_at, etc.
- `Invoice` — id, merchant_id, line items, total, status, payment_url, expiry
- `Merchant` — id, name, wallet_address, settings
- `Transfer` — id, from/to address, amount, asset, status
- `SwapPayment` — pay-in token, settle-out token, routing path, slippage
- `WebhookEvent` — type, data, signature
- `Balance` — per-asset balance breakdown
- `PaginatedList` — generic wrapper for list endpoints

## 5. Resource Modules

### Payments (`shade/resources/payments.py`)
```python
shade.Payment.create(amount=100, currency="XLM", description="Order #42")
shade.Payment.retrieve("pay_xxx")
shade.Payment.list(limit=20, status="completed")
shade.Payment.verify("pay_xxx")  # check on-chain confirmation
```

### Invoices (`shade/resources/invoices.py`)
```python
shade.Invoice.create(line_items=[...], customer_email="...", due_date="...")
shade.Invoice.retrieve("inv_xxx")
shade.Invoice.list(status="pending")
shade.Invoice.send("inv_xxx")     # trigger email delivery
shade.Invoice.cancel("inv_xxx")
```

### Merchants (`shade/resources/merchants.py`)
```python
shade.Merchant.retrieve()         # current authenticated merchant
shade.Merchant.update(name="...")
shade.Merchant.get_balance()      # all asset balances
```

### Transfers / Payouts (`shade/resources/transfers.py`)
```python
shade.Transfer.create(destination="G...", amount=50, asset="USDC")
shade.Transfer.retrieve("txn_xxx")
shade.Transfer.list()
```

### Swap Payments (`shade/resources/swaps.py`) — Shade-specific
```python
shade.SwapPayment.create(
    pay_in_token="XLM",
    settle_out_token="USDC",
    amount=100,
    routing_path=["XLM", "USDC"],
    slippage_tolerance=0.005
)
```

### Webhooks (`shade/resources/webhooks.py`)
```python
event = shade.Webhook.construct_event(
    payload=request.body,
    sig_header=request.headers["Shade-Signature"],
    secret="whsec_..."
)
if event.type == "payment.completed":
    ...
```

## 6. Stellar Integration Layer (`shade/stellar/`)

Direct on-chain operations using the already-included `stellar-sdk`:

- Keypair generation / import helpers
- Build and submit payment transactions
- Asset trust line management (for USDC etc.)
- Transaction status polling
- Network passphrase management (testnet vs mainnet)
- Soroban smart contract invocation for the Shade contract
- Transaction fee estimation

## 7. Async Support

Every resource should expose an async variant:

```python
# Sync
payment = shade.Payment.create(amount=100, currency="XLM")

# Async
payment = await shade.Payment.acreate(amount=100, currency="XLM")
```

## 8. Test Suite (`tests/`)

- Unit tests with mocked HTTP (no real API calls)
- Stellar keypair/transaction tests against testnet
- Webhook signature verification tests
- Model serialization/deserialization tests
- CI matrix across supported Python versions
- Type checking (mypy) in CI

## Proposed File Structure

```
src/shade/
├── __init__.py           # top-level exports + global config
├── client.py             # ShadeClient class (per-instance config)
├── config.py             # global settings + environment constants
├── errors.py             # exception hierarchy
├── http_client.py        # HTTP transport (sync + async via httpx)
├── models/
│   ├── __init__.py
│   ├── payment.py
│   ├── invoice.py
│   ├── merchant.py
│   ├── transfer.py
│   ├── swap.py
│   └── webhook.py
├── resources/
│   ├── __init__.py
│   ├── payments.py
│   ├── invoices.py
│   ├── merchants.py
│   ├── transfers.py
│   ├── swaps.py
│   └── webhooks.py
└── stellar/
    ├── __init__.py
    ├── keypair.py        # wallet helpers
    ├── transaction.py    # tx builders
    └── contract.py       # Soroban smart contract calls
```

## Missing Dependencies to Add

- `httpx` — HTTP client (sync + async)
- `pydantic` — data models with validation
- `cryptography` — webhook HMAC signature verification
- `pytest-asyncio` — async test support
- `respx` or `pytest-httpx` — mock HTTP in tests

## Suggested Build Order

1. Client + Config
2. HTTP layer + Errors
3. Models
4. Payments resource
5. Webhooks
6. Invoices / Transfers
7. Stellar layer
8. Swap Payments
9. Async support
10. Test suite hardening + tooling/docs/packaging

See [ISSUES.md](ISSUES.md) for this roadmap broken into 100 individually
scoped issues.
