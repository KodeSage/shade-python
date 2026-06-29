# Shade Python SDK — Issue Backlog (100)

This backlog breaks down the work described in [FEATURES.md](FEATURES.md)
into 100 individually scoped issues, grouped by feature area. Each entry
includes a description, proposed implementation steps, and acceptance
criteria, and is written so it can be copy-pasted directly into a GitHub
issue.

Labels used: `area:*` (feature area), `type:feature` / `type:test` /
`type:docs` / `type:chore`, and `priority:p1` / `priority:p2` / `priority:p3`.

---

## A. Client & Configuration (#1–#6)

---

### #1 — Implement global `shade` module configuration

## **Description:**
The SDK should support module-level configuration (e.g. `shade.api_key = "sk_live_..."`) so developers can configure it once at app startup without instantiating a client object on every call. This mirrors the ergonomics of the Stripe Python SDK. The global config must be thread-safe and readable by all resource classes.

## **Proposed Steps:**
- Create `src/shade/config.py` with module-level variables: `api_key`, `api_base`, `environment`, `timeout`, `max_retries`.
- Expose these on the top-level `shade` namespace via `__init__.py`.
- Write a `get_config()` helper that merges instance-level overrides with global defaults, used internally by all resource methods.
- Guard against `None` api_key at request time and raise `AuthenticationError`.

## **Acceptance Criteria:**
- [ ] `shade.api_key = "sk_live_xxx"` sets the global key accessible across all resource calls.
- [ ] `shade.environment = "sandbox"` switches the active environment.
- [ ] Setting `shade.api_key = None` and then calling any resource raises `AuthenticationError` with a clear message.
- [ ] Global config does not bleed between threads when changed concurrently.

**Labels:** `area:client`, `type:feature`, `priority:p1`

---

### #2 — Implement `ShadeClient` class for per-instance configuration

## **Description:**
While global config is convenient, multi-tenant applications (e.g. a SaaS acting on behalf of multiple merchants) need isolated client instances that carry their own credentials. `ShadeClient` should accept the same parameters as the global config and bind them to a single instance, which is then passed to resource methods.

## **Proposed Steps:**
- Create `src/shade/client.py` with a `ShadeClient` dataclass/class.
- Constructor parameters: `api_key`, `environment`, `api_base`, `timeout`, `max_retries`.
- Each resource class should accept an optional `client=` kwarg and fall back to global config if omitted.
- Provide a `ShadeClient.from_env()` factory that reads `SHADE_API_KEY` and `SHADE_ENVIRONMENT` from environment variables.

## **Acceptance Criteria:**
- [ ] `client = ShadeClient(api_key="sk_test_xxx")` creates an isolated client.
- [ ] Resource calls using this client use its credentials, not global config.
- [ ] Two `ShadeClient` instances with different keys can coexist without interfering.
- [ ] `ShadeClient.from_env()` reads `SHADE_API_KEY` from the environment correctly.
- [ ] Missing `api_key` on the instance when global is also `None` raises `AuthenticationError`.

**Labels:** `area:client`, `type:feature`, `priority:p1`

---

### #3 — Add environment constants (sandbox/production, testnet/mainnet)

## **Description:**
The SDK targets two environments — `sandbox` (Stellar testnet, staging backend) and `production` (Stellar mainnet, live backend). These must be represented as an enum so the HTTP client and Stellar layer automatically resolve the correct API base URL and network passphrase without the user doing the mapping themselves.

## **Proposed Steps:**
- Define an `Environment` enum in `config.py` with values `SANDBOX` and `PRODUCTION`.
- Map each value to its Horizon URL, network passphrase, and Shade backend URL.
- Accept string shorthands `"sandbox"` / `"production"` via a `parse_environment()` coercer.
- Default the SDK to `SANDBOX` so developers don't accidentally hit production.

## **Acceptance Criteria:**
- [ ] `shade.environment = "production"` resolves to the mainnet Horizon URL and production API base.
- [ ] `shade.environment = "sandbox"` resolves to the testnet Horizon URL and staging API base.
- [ ] Invalid strings raise `ValueError` with the list of valid options.
- [ ] The Stellar layer reads `Environment` without separate configuration.

**Labels:** `area:client`, `type:feature`, `priority:p1`

---

### #4 — Add API key format validation

## **Description:**
API keys must conform to a format (e.g. `pk_live_`, `sk_live_`, `pk_test_`, `sk_test_` prefixes). Catching a malformed key before the first network call saves developers from cryptic 401 errors. Validation should also enforce that a live key is not accidentally used with the sandbox environment, and vice versa.

## **Proposed Steps:**
- Write a `validate_api_key(key: str, environment: Environment)` function in `config.py`.
- Check prefix, minimum length, and character set.
- Warn (but do not raise) when a `test_` key is used with `PRODUCTION` or a `live_` key with `SANDBOX`.
- Call this in the `ShadeClient` constructor and in the global setter.

## **Acceptance Criteria:**
- [ ] A key not matching the expected format raises `AuthenticationError` at configuration time, not at request time.
- [ ] A `pk_test_` key used with `environment="production"` emits a `UserWarning`.
- [ ] A valid `sk_live_` key passes validation without error.
- [ ] `None` or empty string raises `AuthenticationError` immediately.

**Labels:** `area:client`, `type:feature`, `priority:p2`

---

### #5 — Implement configurable timeout and retry settings on client

## **Description:**
Network conditions vary; the SDK must let developers tune how long to wait for a response and how many times to retry. These settings should have sane defaults (e.g. 30 s timeout, 3 retries) and be overridable both globally and per `ShadeClient` instance.

## **Proposed Steps:**
- Add `timeout: float = 30.0` and `max_retries: int = 3` to `ShadeClient` and to `config.py`.
- Pass `timeout` through to `httpx.Client`/`httpx.AsyncClient` on construction.
- Pass `max_retries` into the retry middleware on the HTTP client.
- Validate that `timeout > 0` and `0 <= max_retries <= 10`.

## **Acceptance Criteria:**
- [ ] `ShadeClient(timeout=5.0)` times out requests after 5 seconds.
- [ ] `ShadeClient(max_retries=0)` disables retries entirely.
- [ ] Negative or unreasonably large values raise `ValueError`.
- [ ] Global `shade.timeout` and `shade.max_retries` are respected when no client instance is provided.

**Labels:** `area:client`, `type:feature`, `priority:p2`

---

### #6 — Add `shade.api_base` override support

## **Description:**
Teams running a self-hosted Shade backend or a staging environment at a custom URL need to override the default API base without changing the environment enum. `shade.api_base` should provide an escape hatch that takes precedence over the URL resolved from `Environment`.

## **Proposed Steps:**
- Add `api_base: Optional[str] = None` to `ShadeClient` and `config.py`.
- In the HTTP client URL builder, prefer `api_base` when set, otherwise fall back to the `Environment`-resolved URL.
- Trim trailing slashes on the provided value.
- Document that this is intended for development/testing only.

## **Acceptance Criteria:**
- [ ] `shade.api_base = "https://staging.shadeprotocol.io"` routes all requests to that host.
- [ ] `ShadeClient(api_base="http://localhost:8000")` routes that client's requests locally.
- [ ] When `api_base` is set, `Environment` still controls the Stellar network passphrase.
- [ ] Trailing slashes in the provided URL are normalized.

**Labels:** `area:client`, `type:feature`, `priority:p3`

---

## B. HTTP Transport Layer (#7–#14)

---

### #7 — Implement sync HTTP client wrapper using httpx

## **Description:**
All sync resource methods need a shared internal HTTP client. This should wrap `httpx.Client`, set default headers (Content-Type, Accept, User-Agent), and expose a clean internal interface (`get`, `post`, `patch`, `delete`) used only by resource classes — never exposed in the public API.

## **Proposed Steps:**
- Create `src/shade/http_client.py` with class `_SyncHTTPClient`.
- Accept `api_key`, `api_base`, `timeout` in the constructor.
- Implement `request(method, path, params, json)` that builds the full URL and returns a parsed response dict.
- Set `User-Agent: shade-python/{version}` on every request.
- Use `httpx.Client` as a context manager internally; keep a single instance alive per `ShadeClient`.

## **Acceptance Criteria:**
- [ ] GET/POST/PATCH/DELETE requests are issued to the correct fully-qualified URLs.
- [ ] `User-Agent` header is present on every request.
- [ ] `Content-Type: application/json` is set on POST/PATCH bodies.
- [ ] The client does not expose `httpx` types in its public interface.
- [ ] Closing a `ShadeClient` closes the underlying `httpx.Client`.

**Labels:** `area:http`, `type:feature`, `priority:p1`

---

### #8 — Implement async HTTP client wrapper using httpx

## **Description:**
An async counterpart to #7 using `httpx.AsyncClient`, enabling use in async frameworks like FastAPI, Starlette, and Django async views. It should share the same configuration and interface as the sync client so resource methods can delegate to either with minimal branching.

## **Proposed Steps:**
- Add `_AsyncHTTPClient` to `http_client.py`, mirroring the sync interface with `async def request(...)`.
- Accept the same constructor arguments as `_SyncHTTPClient`.
- Use `async with httpx.AsyncClient(...) as client` lifecycle management.
- Extract a shared `_build_request(method, path, params, json)` helper used by both sync and async versions.

## **Acceptance Criteria:**
- [ ] `await client.request("GET", "/payments")` returns the same response shape as the sync version.
- [ ] The async client can be used in a `pytest-asyncio` test without event loop conflicts.
- [ ] Closing the async client (via `aclose()`) is properly awaited.
- [ ] Sync and async clients share URL-building and header logic without duplication.

**Labels:** `area:http`, `type:feature`, `priority:p1`

---

### #9 — Add request authentication header injection

## **Description:**
Every outgoing request must carry an `Authorization: Bearer <secret_key>` header derived from the active config. This logic must live in the HTTP client, not scattered across resource methods, so it is impossible to accidentally omit it.

## **Proposed Steps:**
- In `_SyncHTTPClient` and `_AsyncHTTPClient`, accept `api_key` in the constructor.
- Merge `{"Authorization": f"Bearer {api_key}"}` into the default headers on every request.
- Never log or include the full key in debug output — mask to `sk_live_****xxxx`.
- Ensure public key (`pk_`) cannot be used for mutating requests (POST/PATCH/DELETE) — raise `AuthenticationError`.

## **Acceptance Criteria:**
- [ ] Every request carries an `Authorization` header with the correct bearer token.
- [ ] Debug logs show a masked key, never the full secret.
- [ ] Using a public key for a write request raises `AuthenticationError` before the network call.
- [ ] Changing `api_key` on the client causes subsequent requests to use the new key.

**Labels:** `area:http`, `type:feature`, `priority:p1`

---

### #10 — Implement exponential backoff retry logic

## **Description:**
Transient failures (connection resets, 502/503/504 responses) should be automatically retried with exponential backoff and random jitter rather than immediately surfacing to the caller. This makes the SDK resilient to brief network hiccups.

## **Proposed Steps:**
- Implement a `_retry_with_backoff(fn, max_retries, base_delay)` utility.
- Retry on: `httpx.ConnectError`, `httpx.TimeoutException`, HTTP 502/503/504.
- Delay formula: `min(base_delay * 2**attempt + random.uniform(0, 0.5), 60)`.
- Do NOT retry on 4xx client errors (except 429, handled in #11).
- Log each retry attempt at DEBUG level with attempt number and delay.

## **Acceptance Criteria:**
- [ ] A request that fails twice then succeeds is returned successfully after the retries.
- [ ] A 400 response is NOT retried — it raises `InvalidRequestError` immediately.
- [ ] Retries respect `max_retries`; exceeding it raises `NetworkError`.
- [ ] The delay between retries grows with each attempt.
- [ ] Retry behaviour is testable by injecting a mock transport.

**Labels:** `area:http`, `type:feature`, `priority:p2`

---

### #11 — Implement rate-limit handling

## **Description:**
When the API returns HTTP 429, the SDK should parse the `Retry-After` header (seconds) and either automatically wait and retry (if within `max_retries`) or raise `RateLimitError` with the wait time attached. The caller should never need to implement their own 429 backoff.

## **Proposed Steps:**
- In the response parser, detect HTTP 429 before raising a generic error.
- Parse `Retry-After` header (integer seconds) and attach it to the `RateLimitError`.
- If auto-retry is enabled and `max_retries` is not exhausted, sleep for `retry_after` seconds then retry.
- In the async client, use `asyncio.sleep` instead of `time.sleep`.

## **Acceptance Criteria:**
- [ ] A 429 response raises `RateLimitError` with a `retry_after` attribute.
- [ ] When retrying, the client waits at least `Retry-After` seconds before the next attempt.
- [ ] If `Retry-After` is absent, the client falls back to exponential backoff.
- [ ] Async client uses non-blocking sleep.

**Labels:** `area:http`, `type:feature`, `priority:p2`

---

### #12 — Implement unified response parser

## **Description:**
All resource methods should go through a single `_parse_response(response)` function that handles JSON decoding, success detection, and mapping HTTP error codes to the correct typed exceptions. This prevents per-resource error handling drift.

## **Proposed Steps:**
- Create `_parse_response(response: httpx.Response) -> dict` in `http_client.py`.
- On 2xx: decode JSON and return the dict.
- On 401: raise `AuthenticationError`.
- On 400 / 422: raise `InvalidRequestError` with field-level errors if present.
- On 404: raise `NotFoundError`.
- On 429: raise `RateLimitError` (handled before reaching here in normal flow).
- On 5xx: raise `NetworkError` (subject to retry in #10).
- On JSON decode failure: raise `ShadeError("Invalid response from API")`.

## **Acceptance Criteria:**
- [ ] Every 4xx/5xx response is mapped to the correct exception type.
- [ ] The raw response body and HTTP status are accessible on every exception.
- [ ] A non-JSON response body raises `ShadeError` rather than crashing with a raw `JSONDecodeError`.
- [ ] 2xx responses that contain an `error` key in the body are still treated as errors.

**Labels:** `area:http`, `type:feature`, `priority:p1`

---

### #13 — Add request/response debug logging

## **Description:**
When debugging integration issues, developers need visibility into what the SDK is sending and receiving. A debug mode should log outgoing requests (method, URL, headers, body) and incoming responses (status, headers, body), with sensitive values masked.

## **Proposed Steps:**
- Add `debug: bool = False` to `ShadeClient` and global config.
- When `debug=True`, emit structured logs via Python's `logging` module under the `shade` logger.
- Mask `Authorization` header value in logs (show only last 4 characters).
- Truncate response bodies longer than 2000 characters with a `[truncated]` suffix.

## **Acceptance Criteria:**
- [ ] With `debug=True`, each request logs method, URL, and masked headers.
- [ ] Each response logs status code and truncated body.
- [ ] Authorization header value is always masked in logs.
- [ ] With `debug=False` (default), no request/response content is logged.
- [ ] Logs use `logging.DEBUG` level so they don't appear unless the app enables them.

**Labels:** `area:http`, `type:feature`, `priority:p3`

---

### #14 — Add idempotency key support for write requests

## **Description:**
POST requests that create resources (payments, invoices, transfers) should support an idempotency key so that retries caused by network failures don't create duplicate records. The key is forwarded as an `Idempotency-Key` header and the server will return the same response for duplicate requests.

## **Proposed Steps:**
- Add `idempotency_key: Optional[str] = None` to all create resource methods.
- When provided, include it as `Idempotency-Key: <value>` in the request headers.
- Auto-generate a UUID `idempotency_key` when the HTTP client auto-retries a write (so retries are safe by default).
- Document the idempotency window (typically 24 hours) in docstrings.

## **Acceptance Criteria:**
- [ ] Passing `idempotency_key="my-key"` to a create method sends `Idempotency-Key: my-key` in the header.
- [ ] Omitting `idempotency_key` on auto-retried write requests still sends a generated UUID key.
- [ ] A duplicate request with the same key returns the original resource without error.
- [ ] GET/DELETE requests ignore the `idempotency_key` argument.

**Labels:** `area:http`, `type:feature`, `priority:p2`

---

## C. Exceptions (#15–#22)

---

### #15 — Implement `ShadeError` base exception class

## **Description:**
All SDK-specific errors must inherit from a common `ShadeError` so callers can catch all SDK errors with a single `except ShadeError`. It should carry a human-readable `message`, the HTTP `status_code` (if applicable), and the raw `response_body` for debugging.

## **Proposed Steps:**
- Create `src/shade/errors.py`.
- Define `ShadeError(Exception)` with `__init__(self, message, status_code=None, response_body=None)`.
- Add `__str__` returning a formatted string including the status code when present.
- All other exceptions in this file must subclass `ShadeError`.

## **Acceptance Criteria:**
- [ ] `except shade.ShadeError` catches all SDK errors.
- [ ] `str(error)` includes both the message and the HTTP status code when present.
- [ ] `error.response_body` contains the raw API response as a string.
- [ ] `ShadeError` can be raised standalone (e.g. for contract-level errors with no HTTP context).

**Labels:** `area:errors`, `type:feature`, `priority:p1`

---

### #16 — Implement `AuthenticationError`

## **Description:**
Raised when the API key is missing, malformed, or rejected by the server (HTTP 401). Should tell the developer exactly what is wrong: missing key, wrong key format, or key revoked.

## **Proposed Steps:**
- Define `AuthenticationError(ShadeError)` in `errors.py`.
- Carry an optional `hint` field with corrective guidance (e.g. "Check that you're using a secret key, not a public key").
- The HTTP client raises this on 401 responses.
- Config validation (#4) also raises this before any network call.

## **Acceptance Criteria:**
- [ ] A 401 API response raises `AuthenticationError`.
- [ ] `error.hint` contains actionable guidance.
- [ ] Raised immediately when `shade.api_key` is `None` and a resource method is called.
- [ ] Subclasses `ShadeError`.

**Labels:** `area:errors`, `type:feature`, `priority:p1`

---

### #17 — Implement `InvalidRequestError`

## **Description:**
Raised on HTTP 400/422 responses — malformed parameters, missing required fields, or out-of-range values. Should expose field-level validation details from the API so the developer knows which parameter is wrong.

## **Proposed Steps:**
- Define `InvalidRequestError(ShadeError)` in `errors.py`.
- Add `param: Optional[str]` (the offending field name) and `field_errors: dict` (all field errors from API response).
- Populate from API error response format, e.g. `{"error": {"code": "invalid_param", "param": "amount", "message": "..."}`.

## **Acceptance Criteria:**
- [ ] A 400 response raises `InvalidRequestError`.
- [ ] `error.param` names the offending field when the API provides one.
- [ ] `error.field_errors` contains all field-level errors from the API response.
- [ ] `str(error)` includes the param name in the message.

**Labels:** `area:errors`, `type:feature`, `priority:p1`

---

### #18 — Implement `NotFoundError`

## **Description:**
Raised on HTTP 404 responses. Should include the resource type and ID that was not found, so the developer can distinguish a missing payment from a missing invoice without parsing the message string.

## **Proposed Steps:**
- Define `NotFoundError(ShadeError)` in `errors.py`.
- Add `resource_type: Optional[str]` and `resource_id: Optional[str]` attributes.
- Populate from the 404 response body.

## **Acceptance Criteria:**
- [ ] A 404 response raises `NotFoundError`.
- [ ] `error.resource_type` and `error.resource_id` reflect the queried resource.
- [ ] Subclasses `ShadeError`.

**Labels:** `area:errors`, `type:feature`, `priority:p1`

---

### #19 — Implement `RateLimitError`

## **Description:**
Raised on HTTP 429 responses when retries are exhausted or disabled. Exposes `retry_after` (seconds) so the caller can implement their own wait logic.

## **Proposed Steps:**
- Define `RateLimitError(ShadeError)` in `errors.py`.
- Add `retry_after: Optional[int]` attribute.
- The HTTP client populates this from the `Retry-After` header before raising.

## **Acceptance Criteria:**
- [ ] A 429 response raises `RateLimitError`.
- [ ] `error.retry_after` reflects the `Retry-After` header value.
- [ ] When `Retry-After` is absent, `error.retry_after` is `None`.

**Labels:** `area:errors`, `type:feature`, `priority:p2`

---

### #20 — Implement `NetworkError`

## **Description:**
Raised when a request fails due to a client-side network issue — DNS failure, connection refused, timeout — rather than an API error response. Wraps the underlying `httpx` exception for context.

## **Proposed Steps:**
- Define `NetworkError(ShadeError)` in `errors.py`.
- Add `original_error: Exception` attribute.
- Catch `httpx.ConnectError`, `httpx.TimeoutException`, `httpx.ReadError` in the HTTP client and re-raise as `NetworkError`.

## **Acceptance Criteria:**
- [ ] A connection timeout raises `NetworkError` with `original_error` set to the `httpx` exception.
- [ ] `str(error)` includes a human-readable description of the network failure.
- [ ] Does not suppress `KeyboardInterrupt` or `SystemExit`.

**Labels:** `area:errors`, `type:feature`, `priority:p2`

---

### #21 — Implement `SignatureVerificationError`

## **Description:**
Raised by `Webhook.construct_event()` when the HMAC-SHA256 signature in the `Shade-Signature` header does not match the computed signature for the payload. Should include the expected vs received values (masked) to aid debugging.

## **Proposed Steps:**
- Define `SignatureVerificationError(ShadeError)` in `errors.py`.
- Add `header: str` (received) and a hint about what went wrong (wrong secret, tampered payload).
- Do not expose the expected signature value in the exception to avoid leaking secrets.

## **Acceptance Criteria:**
- [ ] A mismatched signature raises `SignatureVerificationError`.
- [ ] The exception message explains possible causes (wrong secret, payload modified in transit).
- [ ] The full expected HMAC is never included in the exception message.

**Labels:** `area:errors`, `type:feature`, `priority:p1`

---

### #22 — Implement `StellarError`

## **Description:**
Raised when a Stellar/Horizon call fails — rejected transaction, missing trustline, insufficient balance. Should wrap the underlying `stellar_sdk` exception and expose the Stellar result code for programmatic handling.

## **Proposed Steps:**
- Define `StellarError(ShadeError)` in `errors.py`.
- Add `stellar_result_code: Optional[str]` and `original_error: Exception`.
- Catch `stellar_sdk` exceptions in the Stellar integration layer and re-raise as `StellarError`.

## **Acceptance Criteria:**
- [ ] A rejected Stellar transaction raises `StellarError` with the Horizon result code.
- [ ] `error.original_error` gives access to the raw `stellar_sdk` exception.
- [ ] A trustline-missing error surfaces as `StellarError` with a descriptive message.

**Labels:** `area:errors`, `type:feature`, `priority:p2`

---

## D. Data Models (#23–#32)

---

### #23 — Implement base model class with serialization helpers

## **Description:**
All response models should share a common base that provides `from_dict(data: dict)`, `to_dict()`, and a readable `__repr__`. Using Pydantic as the base eliminates boilerplate validation and gives free type coercion.

## **Proposed Steps:**
- Create `src/shade/models/__init__.py` and `src/shade/models/base.py`.
- Define `ShadeObject(pydantic.BaseModel)` with `model_config = ConfigDict(populate_by_name=True, extra="allow")`.
- Add `to_dict()` method wrapping `model.model_dump()`.
- Add a `classmethod from_dict(cls, data: dict)` that constructs the model.
- Override `__repr__` to show class name and primary ID field.

## **Acceptance Criteria:**
- [ ] All models can be round-tripped through `from_dict(m.to_dict())` without data loss.
- [ ] Unknown fields from the API are accepted without raising (`extra="allow"`).
- [ ] `repr(model)` shows the class name and key ID field.
- [ ] Pydantic validation errors surface as `InvalidRequestError`, not raw `ValidationError`.

**Labels:** `area:models`, `type:feature`, `priority:p1`

---

### #24 — Implement `Payment` model

## **Description:**
Represents a Shade payment resource returned by the API. All monetary amounts should be stored as `Decimal` to avoid floating-point precision issues.

## **Proposed Steps:**
- Create `src/shade/models/payment.py`.
- Fields: `id: str`, `status: str`, `amount: Decimal`, `currency: str`, `description: Optional[str]`, `merchant_id: str`, `stellar_tx_hash: Optional[str]`, `payment_address: str`, `created_at: datetime`, `updated_at: datetime`.
- Add a `PaymentStatus` `StrEnum` with values: `pending`, `completed`, `cancelled`, `expired`, `partially_paid`.
- Validate that `amount > 0`.

## **Acceptance Criteria:**
- [ ] `Payment.from_dict(api_response)` constructs the model without error.
- [ ] `payment.amount` is a `Decimal`, not a `float`.
- [ ] `payment.status` is a `PaymentStatus` enum value.
- [ ] Invalid status strings raise a clear validation error.

**Labels:** `area:models`, `type:feature`, `priority:p1`

---

### #25 — Implement `Invoice` model (with line items)

## **Description:**
Represents a Shade invoice, which groups multiple line items into a payable total. The model must support nested `LineItem` objects.

## **Proposed Steps:**
- Create `src/shade/models/invoice.py`.
- Define `LineItem(ShadeObject)` with `description: str`, `quantity: int`, `unit_price: Decimal`, `total: Decimal`.
- Define `Invoice(ShadeObject)` with `id`, `merchant_id`, `customer_email`, `line_items: list[LineItem]`, `total: Decimal`, `currency`, `status`, `payment_url`, `due_date: date`, `created_at`.
- Add `InvoiceStatus` enum: `draft`, `sent`, `paid`, `cancelled`, `expired`.
- Compute and validate that `total == sum(item.total for item in line_items)`.

## **Acceptance Criteria:**
- [ ] `Invoice.from_dict(...)` correctly nests `LineItem` objects.
- [ ] `invoice.total` matches the sum of line item totals.
- [ ] Mismatched totals raise a `ValueError` during construction.
- [ ] `invoice.status` is an `InvoiceStatus` enum.

**Labels:** `area:models`, `type:feature`, `priority:p1`

---

### #26 — Implement `Merchant` model

## **Description:**
Represents the authenticated merchant's profile. Should expose wallet addresses and preferences cleanly.

## **Proposed Steps:**
- Create `src/shade/models/merchant.py`.
- Fields: `id: str`, `name: str`, `email: str`, `wallet_address: Optional[str]`, `business_name: Optional[str]`, `settings: dict`, `created_at: datetime`.
- Validate Stellar account format on `wallet_address` (starts with `G`, length 56) if present.

## **Acceptance Criteria:**
- [ ] `Merchant.from_dict(api_response)` populates all fields.
- [ ] A non-Stellar wallet address raises a `ValueError`.
- [ ] `merchant.settings` is a plain dict for forward-compatibility.

**Labels:** `area:models`, `type:feature`, `priority:p1`

---

### #27 — Implement `Transfer` model

## **Description:**
Represents a payout or transfer of funds from the merchant wallet to a destination address.

## **Proposed Steps:**
- Create `src/shade/models/transfer.py`.
- Fields: `id`, `source_address`, `destination_address`, `amount: Decimal`, `asset: str`, `status`, `stellar_tx_hash: Optional[str]`, `fee: Optional[Decimal]`, `created_at`.
- Add `TransferStatus` enum: `pending`, `processing`, `completed`, `failed`.

## **Acceptance Criteria:**
- [ ] `Transfer.from_dict(api_response)` populates all fields correctly.
- [ ] `transfer.asset` defaults to `"XLM"` when absent from the response.
- [ ] `transfer.status` is a `TransferStatus` enum.

**Labels:** `area:models`, `type:feature`, `priority:p2`

---

### #28 — Implement `SwapPayment` model

## **Description:**
Represents a swap-routed payment where the payer pays in one token and the merchant settles in another. Specific to Shade's cross-asset capabilities.

## **Proposed Steps:**
- Create `src/shade/models/swap.py`.
- Fields: `id`, `pay_in_token`, `settle_out_token`, `amount_in: Decimal`, `amount_out: Optional[Decimal]`, `routing_path: list[str]`, `slippage_tolerance: float`, `status`, `stellar_tx_hash: Optional[str]`, `created_at`.
- Add `SwapStatus` enum: `pending`, `swapping`, `completed`, `failed`, `slippage_exceeded`.
- Validate `0 < slippage_tolerance < 1`.

## **Acceptance Criteria:**
- [ ] `SwapPayment.from_dict(...)` populates all fields including routing path list.
- [ ] `slippage_tolerance` outside `(0, 1)` raises `ValueError`.
- [ ] `status` is a `SwapStatus` enum.

**Labels:** `area:models`, `type:feature`, `priority:p2`

---

### #29 — Implement `WebhookEvent` model

## **Description:**
Represents a parsed, verified webhook event delivered by the Shade platform. The `data` field should be typed as the corresponding resource model rather than a raw dict.

## **Proposed Steps:**
- Create `src/shade/models/webhook.py`.
- Fields: `id`, `type: str`, `data: Any`, `created_at: datetime`, `livemode: bool`.
- Add a `WebhookEventType` constants class.
- The `Webhook.construct_event()` method (issue #66) populates `data` with the typed model.

## **Acceptance Criteria:**
- [ ] `WebhookEvent.from_dict(raw_payload)` populates all fields.
- [ ] `event.livemode` correctly reflects the event origin.
- [ ] `event.data` is the raw dict at model level; typed model coercion happens in the resource layer.

**Labels:** `area:models`, `type:feature`, `priority:p1`

---

### #30 — Implement `Balance` model

## **Description:**
Represents the per-asset balance breakdown returned by `Merchant.get_balance()`. A merchant wallet may hold multiple Stellar assets.

## **Proposed Steps:**
- Create `src/shade/models/balance.py`.
- Define `AssetBalance(ShadeObject)` with `asset_code: str`, `asset_issuer: Optional[str]`, `balance: Decimal`.
- Define `Balance(ShadeObject)` with `balances: list[AssetBalance]` and a `get(asset_code: str)` helper.

## **Acceptance Criteria:**
- [ ] `balance.get("XLM")` returns the native balance `AssetBalance`.
- [ ] `balance.get("USDC")` returns the USDC balance if held.
- [ ] `balance.get("NOTEXIST")` returns `None` rather than raising.
- [ ] All balance amounts are `Decimal`.

**Labels:** `area:models`, `type:feature`, `priority:p2`

---

### #31 — Implement `PaginatedList` generic wrapper

## **Description:**
All list endpoints return a paginated collection. A `PaginatedList` wrapper should expose `data`, `has_more`, and `next_cursor`, and implement Python iterator and `len()` protocols to feel idiomatic.

## **Proposed Steps:**
- Create `src/shade/models/list.py`.
- Define `PaginatedList(Generic[T])` with `data: list[T]`, `has_more: bool`, `next_cursor: Optional[str]`.
- Implement `__iter__`, `__len__`, and `__getitem__`.
- Add `auto_pages()` generator method that auto-fetches subsequent pages.

## **Acceptance Criteria:**
- [ ] `for payment in paginated_list:` iterates the `data` items.
- [ ] `len(paginated_list)` returns the count of items in the current page.
- [ ] `paginated_list.has_more` is `True` when further pages exist.
- [ ] `auto_pages()` yields all items across pages without the caller managing cursors.

**Labels:** `area:models`, `type:feature`, `priority:p1`

---

### #32 — Add model validation via Pydantic schemas

## **Description:**
Each model should enforce its own constraints (required fields, valid ranges, enum values) using Pydantic validators so that malformed API responses are caught at the model layer and never silently passed to the caller as `None` or garbage data.

## **Proposed Steps:**
- Add `@field_validator` decorators to each model for non-trivial constraints.
- Catch `pydantic.ValidationError` in `_parse_response` and re-raise as `ShadeError("Unexpected response format from API")`.
- Add model-level `@model_validator` where cross-field validation is needed (e.g. Invoice total check).
- Write a JSON Schema export method for documentation tooling.

## **Acceptance Criteria:**
- [ ] A `Payment` with `amount = -5` raises a validation error at construction.
- [ ] A `Transfer` with a missing `id` field raises a clear validation error.
- [ ] `pydantic.ValidationError` is never surfaced raw to the SDK consumer — it is always wrapped.
- [ ] Each model's validators are covered by unit tests.

**Labels:** `area:models`, `type:feature`, `priority:p2`

---

## E. Payments Resource (#33–#40)

---

### #33 — Implement `Payment.create()`

## **Description:**
The primary method for initiating a payment request. Returns a `Payment` model containing the `payment_address` the payer should send funds to and the initial `pending` status.

## **Proposed Steps:**
- Create `src/shade/resources/payments.py` with a `Payment` class.
- `create(amount, currency, description=None, metadata=None, idempotency_key=None, client=None)` → `Payment`.
- Validate `amount > 0` and `currency` is a non-empty string before the network call.
- POST to `/v1/payments`.
- Deserialize the response with `Payment.from_dict(response)`.

## **Acceptance Criteria:**
- [ ] Returns a `Payment` model with `status == "pending"` and a non-empty `payment_address`.
- [ ] `amount <= 0` raises `InvalidRequestError` before hitting the network.
- [ ] `idempotency_key` is forwarded as a header.
- [ ] `metadata` dict is serialized in the request body.

**Labels:** `area:payments`, `type:feature`, `priority:p1`

---

### #34 — Implement `Payment.retrieve()`

## **Description:**
Fetch the current state of a single payment by its ID. Used after creation to check whether the payer has completed the on-chain transfer.

## **Proposed Steps:**
- `retrieve(payment_id: str, client=None)` → `Payment`.
- GET `/v1/payments/{payment_id}`.
- Raise `NotFoundError` if the API returns 404.
- Raise `InvalidRequestError` if `payment_id` is empty or `None`.

## **Acceptance Criteria:**
- [ ] Returns a correctly populated `Payment` model.
- [ ] An unknown `payment_id` raises `NotFoundError`.
- [ ] `payment_id=None` raises `InvalidRequestError` before the network call.

**Labels:** `area:payments`, `type:feature`, `priority:p1`

---

### #35 — Implement `Payment.list()` with pagination/filtering

## **Description:**
Returns a `PaginatedList[Payment]` supporting filtering by status and cursor-based pagination.

## **Proposed Steps:**
- `list(status=None, limit=20, starting_after=None, ending_before=None, client=None)` → `PaginatedList[Payment]`.
- GET `/v1/payments` with query params.
- Validate `1 <= limit <= 100`.
- Return a `PaginatedList[Payment]`.

## **Acceptance Criteria:**
- [ ] Returns a `PaginatedList` with correctly typed `Payment` items.
- [ ] `status="completed"` filters results server-side.
- [ ] `limit=0` raises `InvalidRequestError` before the network call.
- [ ] `has_more` and `next_cursor` are correctly populated from the response.

**Labels:** `area:payments`, `type:feature`, `priority:p1`

---

### #36 — Implement `Payment.verify()`

## **Description:**
Cross-checks a payment against Stellar Horizon to confirm the on-chain transaction exists, the amount matches, and the destination address is correct. This is an additional validation layer beyond trusting the backend API status.

## **Proposed Steps:**
- `verify(payment_id: str, client=None)` → `Payment`.
- First call `retrieve(payment_id)` to get the `stellar_tx_hash` and expected amount.
- Use the Stellar layer (#76) to fetch the transaction from Horizon.
- Compare amount, asset, and destination address.
- Raise `StellarError` if the on-chain data doesn't match.

## **Acceptance Criteria:**
- [ ] Returns the `Payment` model with `status == "completed"` on successful verification.
- [ ] Raises `StellarError` if the Horizon transaction amount doesn't match the payment record.
- [ ] Raises `NotFoundError` if the `stellar_tx_hash` is absent (payment not yet settled).

**Labels:** `area:payments`, `type:feature`, `priority:p1`

---

### #37 — Implement `Payment.cancel()`

## **Description:**
Cancels a `pending` payment request, invalidating the payment address. Only applicable before funds are received.

## **Proposed Steps:**
- `cancel(payment_id: str, client=None)` → `Payment`.
- POST `/v1/payments/{payment_id}/cancel`.
- Raise `InvalidRequestError` if the payment is already `completed` or `cancelled`.

## **Acceptance Criteria:**
- [ ] Returns a `Payment` model with `status == "cancelled"`.
- [ ] Cancelling an already-completed payment raises `InvalidRequestError`.
- [ ] Cancelling a non-existent ID raises `NotFoundError`.

**Labels:** `area:payments`, `type:feature`, `priority:p2`

---

### #38 — Add partial payment detection

## **Description:**
If a payer sends less than the requested amount, the payment should surface as `partially_paid` with a `shortfall` amount. Callers should be able to detect and handle this case.

## **Proposed Steps:**
- Add `shortfall: Optional[Decimal]` and `amount_received: Optional[Decimal]` to the `Payment` model.
- In `Payment.retrieve()`, populate these fields from the API response.
- Add a `payment.is_partially_paid` property to the `Payment` model.

## **Acceptance Criteria:**
- [ ] `payment.status == "partially_paid"` when the received amount is less than requested.
- [ ] `payment.shortfall` contains the unpaid remainder as a `Decimal`.
- [ ] `payment.is_partially_paid` returns `True` / `False` correctly.

**Labels:** `area:payments`, `type:feature`, `priority:p3`

---

### #39 — Add payment status polling helper

## **Description:**
A synchronous helper that polls `Payment.retrieve()` until the payment reaches a terminal state (`completed`, `cancelled`, `expired`) or a timeout is exceeded. Useful for scripts and CLI tools where async is not available.

## **Proposed Steps:**
- `Payment.wait_until_confirmed(payment_id, timeout=300, poll_interval=5, client=None)` → `Payment`.
- Loop calling `retrieve()` with `time.sleep(poll_interval)` between calls.
- Raise `NetworkError` (with a descriptive message) if `timeout` is exceeded before a terminal state.
- Immediately return if the initial `retrieve()` is already terminal.

## **Acceptance Criteria:**
- [ ] Returns the `Payment` as soon as `status` becomes terminal.
- [ ] Raises `ShadeError` with a timeout message if `timeout` seconds elapse with no terminal state.
- [ ] `poll_interval` controls the sleep duration between calls.
- [ ] Does not make any additional requests if the payment is already terminal on the first call.

**Labels:** `area:payments`, `type:feature`, `priority:p3`

---

### #40 — Write unit tests for Payments resource

## **Description:**
Full unit test coverage for all Payments resource methods using mocked HTTP responses. No real API calls.

## **Proposed Steps:**
- Use `respx` to mock the `httpx` transport.
- Cover happy paths for `create`, `retrieve`, `list`, `verify`, `cancel`.
- Cover error paths: 404 → `NotFoundError`, 400 → `InvalidRequestError`, 401 → `AuthenticationError`.
- Test pagination: `has_more=True` and `starting_after` parameter.
- Test that client-side validation fires before the HTTP call.

## **Acceptance Criteria:**
- [ ] All Payments methods have at least one passing happy-path test.
- [ ] All error-path tests confirm the correct exception type is raised.
- [ ] No test makes a real network request.
- [ ] Tests run in under 2 seconds.

**Labels:** `area:payments`, `type:test`, `priority:p1`

---

## F. Invoices Resource (#41–#48)

---

### #41 — Implement `Invoice.create()` with line items

## **Description:**
Create a new invoice with one or more line items, a customer email, currency, and optional due date. Returns an `Invoice` model in `draft` status.

## **Proposed Steps:**
- Create `src/shade/resources/invoices.py`.
- `create(line_items, customer_email, currency, due_date=None, idempotency_key=None, client=None)` → `Invoice`.
- Validate `line_items` is non-empty and each item has `description`, `quantity > 0`, and `unit_price > 0`.
- POST `/v1/invoices`.

## **Acceptance Criteria:**
- [ ] Returns an `Invoice` model with `status == "draft"` and a generated `id`.
- [ ] Empty `line_items` raises `InvalidRequestError` before the network call.
- [ ] A line item with `quantity <= 0` raises `InvalidRequestError`.
- [ ] `customer_email` with invalid format raises `InvalidRequestError`.

**Labels:** `area:invoices`, `type:feature`, `priority:p1`

---

### #42 — Implement `Invoice.retrieve()`

## **Description:**
Fetch a single invoice by ID, including its full line items and current status.

## **Proposed Steps:**
- `retrieve(invoice_id: str, client=None)` → `Invoice`.
- GET `/v1/invoices/{invoice_id}`.
- Raise `NotFoundError` for missing IDs, `InvalidRequestError` for blank IDs.

## **Acceptance Criteria:**
- [ ] Returns a correctly populated `Invoice` with nested `LineItem` objects.
- [ ] An unknown `invoice_id` raises `NotFoundError`.
- [ ] Empty `invoice_id` raises `InvalidRequestError` before the network call.

**Labels:** `area:invoices`, `type:feature`, `priority:p1`

---

### #43 — Implement `Invoice.list()` with status filtering

## **Description:**
Returns a `PaginatedList[Invoice]` supporting filtering by status and pagination.

## **Proposed Steps:**
- `list(status=None, limit=20, starting_after=None, client=None)` → `PaginatedList[Invoice]`.
- GET `/v1/invoices` with query params.
- Validate `status` against `InvoiceStatus` enum values if provided.

## **Acceptance Criteria:**
- [ ] Returns a `PaginatedList` with typed `Invoice` items.
- [ ] Invalid `status` string raises `InvalidRequestError` before the call.
- [ ] `has_more` and `next_cursor` are correctly populated.

**Labels:** `area:invoices`, `type:feature`, `priority:p1`

---

### #44 — Implement `Invoice.send()`

## **Description:**
Transitions an invoice from `draft` to `sent` and triggers email delivery to the customer. Returns the updated `Invoice`.

## **Proposed Steps:**
- `send(invoice_id: str, client=None)` → `Invoice`.
- POST `/v1/invoices/{invoice_id}/send`.
- Raise `InvalidRequestError` if the invoice is not in `draft` status.

## **Acceptance Criteria:**
- [ ] Returns an `Invoice` with `status == "sent"`.
- [ ] Sending an already-sent invoice raises `InvalidRequestError`.
- [ ] Sending a `cancelled` invoice raises `InvalidRequestError`.

**Labels:** `area:invoices`, `type:feature`, `priority:p1`

---

### #45 — Implement `Invoice.cancel()`

## **Description:**
Cancels an unpaid invoice, preventing further payment attempts. Returns the updated `Invoice`.

## **Proposed Steps:**
- `cancel(invoice_id: str, client=None)` → `Invoice`.
- POST `/v1/invoices/{invoice_id}/cancel`.
- Raise `InvalidRequestError` if the invoice is already `paid` or `cancelled`.

## **Acceptance Criteria:**
- [ ] Returns an `Invoice` with `status == "cancelled"`.
- [ ] Cancelling a `paid` invoice raises `InvalidRequestError`.
- [ ] Cancelling a non-existent invoice raises `NotFoundError`.

**Labels:** `area:invoices`, `type:feature`, `priority:p2`

---

### #46 — Implement `Invoice.update()` for draft invoices

## **Description:**
Allow editing a draft invoice's line items, customer email, or due date before it is sent.

## **Proposed Steps:**
- `update(invoice_id, line_items=None, customer_email=None, due_date=None, client=None)` → `Invoice`.
- PATCH `/v1/invoices/{invoice_id}`.
- Raise `InvalidRequestError` if the invoice is not in `draft` status.
- Only send fields that are provided (partial update).

## **Acceptance Criteria:**
- [ ] Updating `customer_email` on a draft invoice reflects the change in the returned model.
- [ ] Calling `update` on a `sent` invoice raises `InvalidRequestError`.
- [ ] Passing no update fields raises `InvalidRequestError` before the call.

**Labels:** `area:invoices`, `type:feature`, `priority:p2`

---

### #47 — Add invoice expiry/due-date handling

## **Description:**
Invoices with a `due_date` in the past should surface a clear `is_expired` signal and transition to `expired` status. The model should make this easy to check.

## **Proposed Steps:**
- Add `is_expired` property to `Invoice`: returns `True` when `status == "expired"` or (`due_date` is set and `due_date < date.today()`).
- Add `time_until_due` property returning a `timedelta` (or `None` if no due date).
- Surface a `UserWarning` when `retrieve()` returns an `expired` invoice without the caller checking `is_expired`.

## **Acceptance Criteria:**
- [ ] `invoice.is_expired` is `True` when status is `expired`.
- [ ] `invoice.is_expired` is `True` when `due_date` is in the past, regardless of stored status.
- [ ] `invoice.time_until_due` returns a positive `timedelta` for future due dates and negative for past.

**Labels:** `area:invoices`, `type:feature`, `priority:p3`

---

### #48 — Write unit tests for Invoices resource

## **Description:**
Full unit test coverage for all Invoices methods using mocked HTTP.

## **Proposed Steps:**
- Mock responses for `create`, `retrieve`, `list`, `send`, `cancel`, `update`.
- Test that invalid `line_items` (empty, zero quantity) raise before the call.
- Test status-transition errors (send a sent invoice, cancel a paid invoice).
- Test the `is_expired` property with various `due_date` and `status` combinations.

## **Acceptance Criteria:**
- [ ] All Invoices methods have at least one passing happy-path test.
- [ ] Status-transition violations are confirmed by tests.
- [ ] `is_expired` property is covered by tests with past/future dates.
- [ ] No test makes a real network request.

**Labels:** `area:invoices`, `type:test`, `priority:p1`

---

## G. Merchants Resource (#49–#53)

---

### #49 — Implement `Merchant.retrieve()`

## **Description:**
Fetch the merchant profile associated with the configured API key. This is the primary way a developer confirms their credentials are working and retrieves their merchant ID for other operations.

## **Proposed Steps:**
- Create `src/shade/resources/merchants.py`.
- `retrieve(client=None)` → `Merchant`.
- GET `/v1/merchant/me`.
- Surface `AuthenticationError` on 401 (wrong key).

## **Acceptance Criteria:**
- [ ] Returns a populated `Merchant` model.
- [ ] A valid secret key returns the correct merchant profile.
- [ ] An invalid key raises `AuthenticationError`.

**Labels:** `area:merchants`, `type:feature`, `priority:p1`

---

### #50 — Implement `Merchant.update()`

## **Description:**
Update editable merchant profile fields. Only send fields that are explicitly provided.

## **Proposed Steps:**
- `update(name=None, email=None, business_name=None, settings=None, client=None)` → `Merchant`.
- PATCH `/v1/merchant/me`.
- Raise `InvalidRequestError` if no fields are provided.
- Merge with existing settings dict when `settings` is partial.

## **Acceptance Criteria:**
- [ ] Returns updated `Merchant` model.
- [ ] Only provided fields appear in the PATCH request body.
- [ ] Passing no arguments raises `InvalidRequestError` before the call.

**Labels:** `area:merchants`, `type:feature`, `priority:p2`

---

### #51 — Implement `Merchant.get_balance()`

## **Description:**
Fetch the per-asset balance breakdown for the authenticated merchant's wallet, returning a `Balance` model.

## **Proposed Steps:**
- `get_balance(client=None)` → `Balance`.
- GET `/v1/merchant/me/balance`.
- Return a `Balance` model with a list of `AssetBalance` items.

## **Acceptance Criteria:**
- [ ] Returns a `Balance` model with at least the XLM native balance.
- [ ] `balance.get("XLM")` returns a non-negative `Decimal`.
- [ ] An unauthenticated call raises `AuthenticationError`.

**Labels:** `area:merchants`, `type:feature`, `priority:p1`

---

### #52 — Implement merchant wallet address management

## **Description:**
Allow listing and adding/removing Stellar wallet addresses linked to the merchant account. A merchant may need multiple addresses for different purposes.

## **Proposed Steps:**
- `list_wallets(client=None)` → `list[str]`: GET `/v1/merchant/me/wallets`.
- `add_wallet(address: str, client=None)` → `Merchant`: POST `/v1/merchant/me/wallets`.
- `remove_wallet(address: str, client=None)` → `Merchant`: DELETE `/v1/merchant/me/wallets/{address}`.
- Validate Stellar address format on `add_wallet`.

## **Acceptance Criteria:**
- [ ] `list_wallets()` returns the current list of linked addresses.
- [ ] `add_wallet("G...")` adds the address and returns the updated merchant.
- [ ] Adding a non-Stellar address raises `InvalidRequestError`.
- [ ] `remove_wallet` on a non-linked address raises `NotFoundError`.

**Labels:** `area:merchants`, `type:feature`, `priority:p2`

---

### #53 — Write unit tests for Merchants resource

## **Description:**
Full unit test coverage for all Merchants resource methods using mocked HTTP.

## **Proposed Steps:**
- Mock responses for `retrieve`, `update`, `get_balance`, `list_wallets`, `add_wallet`, `remove_wallet`.
- Test that missing fields in update raise before the call.
- Test `get_balance` parses multi-asset balances correctly.
- Test wallet address validation rejects non-Stellar addresses.

## **Acceptance Criteria:**
- [ ] All Merchant methods have at least one passing happy-path test.
- [ ] Wallet address validation is confirmed by tests.
- [ ] No test makes a real network request.

**Labels:** `area:merchants`, `type:test`, `priority:p1`

---

## H. Transfers Resource (#54–#59)

---

### #54 — Implement `Transfer.create()`

## **Description:**
Send a specified amount of an asset from the merchant wallet to a destination Stellar address via the Shade backend.

## **Proposed Steps:**
- Create `src/shade/resources/transfers.py`.
- `create(destination, amount, asset="XLM", description=None, idempotency_key=None, client=None)` → `Transfer`.
- Validate `destination` as a valid Stellar address.
- Validate `amount > 0`.
- POST `/v1/transfers`.

## **Acceptance Criteria:**
- [ ] Returns a `Transfer` model with `status == "pending"` or `"processing"`.
- [ ] An invalid `destination` address raises `InvalidRequestError` before the call.
- [ ] `amount <= 0` raises `InvalidRequestError` before the call.
- [ ] `idempotency_key` is forwarded as a header.

**Labels:** `area:transfers`, `type:feature`, `priority:p1`

---

### #55 — Implement `Transfer.retrieve()`

## **Description:**
Fetch a single transfer by ID to check its current status and the associated Stellar transaction hash.

## **Proposed Steps:**
- `retrieve(transfer_id: str, client=None)` → `Transfer`.
- GET `/v1/transfers/{transfer_id}`.
- Raise `NotFoundError` for unknown IDs.

## **Acceptance Criteria:**
- [ ] Returns a populated `Transfer` model.
- [ ] Unknown `transfer_id` raises `NotFoundError`.
- [ ] Completed transfers have a non-null `stellar_tx_hash`.

**Labels:** `area:transfers`, `type:feature`, `priority:p1`

---

### #56 — Implement `Transfer.list()`

## **Description:**
Returns a paginated list of all transfers for the authenticated merchant.

## **Proposed Steps:**
- `list(status=None, limit=20, starting_after=None, client=None)` → `PaginatedList[Transfer]`.
- GET `/v1/transfers` with query params.

## **Acceptance Criteria:**
- [ ] Returns a `PaginatedList[Transfer]`.
- [ ] `status` filter works correctly.
- [ ] Pagination fields (`has_more`, `next_cursor`) are populated.

**Labels:** `area:transfers`, `type:feature`, `priority:p1`

---

### #57 — Implement transfer fee estimation helper

## **Description:**
Before committing to a transfer, allow developers to query the expected total fee (network fee + Shade service fee) so the cost can be shown to end users.

## **Proposed Steps:**
- `Transfer.estimate_fee(destination, amount, asset="XLM", client=None)` → `dict`.
- POST or GET `/v1/transfers/estimate`.
- Return a dict with `network_fee: Decimal`, `service_fee: Decimal`, `total_fee: Decimal`.

## **Acceptance Criteria:**
- [ ] Returns fee breakdown without creating a transfer.
- [ ] `amount <= 0` raises `InvalidRequestError`.
- [ ] Unsupported `asset` raises `InvalidRequestError`.

**Labels:** `area:transfers`, `type:feature`, `priority:p3`

---

### #58 — Add multi-asset transfer support

## **Description:**
Transfers must support any Stellar asset the merchant holds (XLM, USDC, and custom issuer tokens), not just the native asset. The `asset` field must handle both native and non-native assets correctly.

## **Proposed Steps:**
- Accept `asset` as either `"XLM"` or a `"CODE:ISSUER"` string (e.g. `"USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"`).
- Validate the format in `Transfer.create()`.
- Parse `CODE:ISSUER` format and pass structured data to the API.

## **Acceptance Criteria:**
- [ ] `asset="XLM"` creates a native XLM transfer.
- [ ] `asset="USDC:GA5Z..."` creates a USDC transfer.
- [ ] Malformed `CODE:ISSUER` string raises `InvalidRequestError`.

**Labels:** `area:transfers`, `type:feature`, `priority:p2`

---

### #59 — Write unit tests for Transfers resource

## **Description:**
Full unit test coverage for all Transfers resource methods using mocked HTTP.

## **Proposed Steps:**
- Cover happy paths for `create`, `retrieve`, `list`, `estimate_fee`.
- Test `destination` address format validation.
- Test multi-asset `CODE:ISSUER` parsing.
- Test error paths: 404, 400, 401.

## **Acceptance Criteria:**
- [ ] All Transfers methods have at least one passing happy-path test.
- [ ] Address and asset format validation tests pass.
- [ ] No test makes a real network request.

**Labels:** `area:transfers`, `type:test`, `priority:p1`

---

## I. Swap Payments Resource (#60–#65)

---

### #60 — Implement `SwapPayment.create()`

## **Description:**
Create a new swap-routed payment where the payer funds in one token and the merchant receives a different token via an automated on-chain swap.

## **Proposed Steps:**
- Create `src/shade/resources/swaps.py`.
- `create(pay_in_token, settle_out_token, amount, routing_path=None, slippage_tolerance=0.005, metadata=None, idempotency_key=None, client=None)` → `SwapPayment`.
- Validate `slippage_tolerance` is in `(0, 1)`.
- POST `/v1/swap-payments`.

## **Acceptance Criteria:**
- [ ] Returns a `SwapPayment` model with a `payment_address` and `status == "pending"`.
- [ ] `slippage_tolerance` outside `(0, 1)` raises `InvalidRequestError` before the call.
- [ ] Both `pay_in_token` and `settle_out_token` are required; missing either raises `InvalidRequestError`.

**Labels:** `area:swaps`, `type:feature`, `priority:p1`

---

### #61 — Implement routing path specification and validation

## **Description:**
An explicit token routing path (e.g. `["XLM", "USDC"]`) can be provided to control how the swap is routed through DEX liquidity pools. The SDK should validate the path client-side before submission.

## **Proposed Steps:**
- Accept `routing_path: Optional[list[str]]` in `SwapPayment.create()`.
- Validate the path is non-empty when provided, starts with `pay_in_token`, and ends with `settle_out_token`.
- When omitted, let the backend determine the optimal path.

## **Acceptance Criteria:**
- [ ] A valid `routing_path` is forwarded in the request body.
- [ ] A path that doesn't start with `pay_in_token` raises `InvalidRequestError`.
- [ ] A path that doesn't end with `settle_out_token` raises `InvalidRequestError`.
- [ ] Omitting `routing_path` sends `null`/omits the field (server chooses).

**Labels:** `area:swaps`, `type:feature`, `priority:p2`

---

### #62 — Implement slippage tolerance parameter handling

## **Description:**
Slippage tolerance controls the maximum acceptable price deviation during the swap. It must be validated, documented clearly, and enforced within a reasonable range.

## **Proposed Steps:**
- Validate `0 < slippage_tolerance < 1` in `SwapPayment.create()`.
- Convert to a percentage string or basis-point integer before sending, matching the backend's expected format.
- Default to `0.005` (0.5%) when not provided.
- Document the valid range and typical values in the docstring.

## **Acceptance Criteria:**
- [ ] `slippage_tolerance=0.005` sends the correct value to the API.
- [ ] `slippage_tolerance=0` raises `InvalidRequestError`.
- [ ] `slippage_tolerance=1.5` raises `InvalidRequestError`.
- [ ] The default `0.005` is applied when the parameter is omitted.

**Labels:** `area:swaps`, `type:feature`, `priority:p2`

---

### #63 — Implement `SwapPayment.retrieve()`

## **Description:**
Fetch a swap payment by ID to check its current status and the final settled amount.

## **Proposed Steps:**
- `retrieve(swap_id: str, client=None)` → `SwapPayment`.
- GET `/v1/swap-payments/{swap_id}`.
- Raise `NotFoundError` for unknown IDs.

## **Acceptance Criteria:**
- [ ] Returns a populated `SwapPayment` model.
- [ ] A completed swap has a non-null `amount_out` field.
- [ ] Unknown `swap_id` raises `NotFoundError`.

**Labels:** `area:swaps`, `type:feature`, `priority:p1`

---

### #64 — Add swap quote/estimate endpoint helper

## **Description:**
Before creating a swap payment, let developers preview the expected `settle_out` amount at current market rates, so they can show a conversion estimate to end users.

## **Proposed Steps:**
- `SwapPayment.get_quote(pay_in_token, settle_out_token, amount, slippage_tolerance=0.005, client=None)` → `dict`.
- GET or POST `/v1/swap-payments/quote`.
- Return `{"estimated_amount_out": Decimal, "rate": Decimal, "expires_at": datetime}`.

## **Acceptance Criteria:**
- [ ] Returns an estimate without creating a swap payment.
- [ ] `estimated_amount_out` is a `Decimal`.
- [ ] Unsupported token pair raises `InvalidRequestError`.
- [ ] `expires_at` indicates how long the quoted rate is valid.

**Labels:** `area:swaps`, `type:feature`, `priority:p2`

---

### #65 — Write unit tests for Swap Payments resource

## **Description:**
Full unit test coverage for all Swap Payments resource methods using mocked HTTP.

## **Proposed Steps:**
- Cover happy paths for `create`, `retrieve`, `get_quote`.
- Test routing path validation (wrong start/end tokens).
- Test `slippage_tolerance` boundary values (0, 1, valid range).
- Test the `slippage_exceeded` status in the retrieve response.

## **Acceptance Criteria:**
- [ ] All Swap Payments methods have at least one passing happy-path test.
- [ ] Routing path and slippage validation tests pass.
- [ ] No test makes a real network request.

**Labels:** `area:swaps`, `type:test`, `priority:p1`

---

## J. Webhooks Resource (#66–#71)

---

### #66 — Implement `Webhook.construct_event()`

## **Description:**
The primary entry point for webhook handling. Takes the raw request body and the `Shade-Signature` header, verifies the signature, and returns a typed `WebhookEvent`. Invalid signatures must hard-fail to prevent replay attacks.

## **Proposed Steps:**
- Create `src/shade/resources/webhooks.py`.
- `construct_event(payload: bytes, sig_header: str, secret: str)` → `WebhookEvent`.
- Call signature verification (#67) first; raise `SignatureVerificationError` on failure.
- Deserialize `payload` JSON into `WebhookEvent.from_dict(...)`.

## **Acceptance Criteria:**
- [ ] Returns a `WebhookEvent` on a valid, correctly signed payload.
- [ ] Raises `SignatureVerificationError` on a tampered payload.
- [ ] Raises `SignatureVerificationError` on a wrong secret.
- [ ] Raises `ShadeError` on non-JSON payloads.
- [ ] `payload` must be `bytes`; a `str` argument raises `TypeError`.

**Labels:** `area:webhooks`, `type:feature`, `priority:p1`

---

### #67 — Implement HMAC signature verification for webhook payloads

## **Description:**
Compute the expected HMAC-SHA256 of the raw payload using the webhook signing secret, then compare it to the provided signature using a constant-time comparison function to prevent timing attacks.

## **Proposed Steps:**
- Extract timestamp and `v1` signature from `Shade-Signature` header (format: `t=timestamp,v1=signature`).
- Compute expected signature: `HMAC-SHA256(secret, f"{timestamp}.{payload}")`.
- Use `hmac.compare_digest` for comparison.
- Reject payloads where `abs(now - timestamp) > tolerance` (default: 300 s) to block replay attacks.

## **Acceptance Criteria:**
- [ ] A correctly signed payload passes verification.
- [ ] A payload with a flipped bit fails verification.
- [ ] A payload older than 300 seconds raises `SignatureVerificationError` with a "timestamp too old" message.
- [ ] Comparison is constant-time (`hmac.compare_digest`).

**Labels:** `area:webhooks`, `type:feature`, `priority:p1`

---

### #68 — Define webhook event type constants

## **Description:**
Provide a constants module for all supported event types so developers don't use magic strings and IDE autocomplete works.

## **Proposed Steps:**
- Create `src/shade/webhook_types.py` with a `WebhookEventType` class (or `StrEnum`).
- Values: `PAYMENT_COMPLETED`, `PAYMENT_CANCELLED`, `PAYMENT_EXPIRED`, `PAYMENT_PARTIALLY_PAID`, `INVOICE_PAID`, `INVOICE_SENT`, `INVOICE_CANCELLED`, `TRANSFER_COMPLETED`, `TRANSFER_FAILED`, `SWAP_COMPLETED`, `SWAP_SLIPPAGE_EXCEEDED`.
- Export from `shade.__init__`.

## **Acceptance Criteria:**
- [ ] `shade.WebhookEventType.PAYMENT_COMPLETED == "payment.completed"`.
- [ ] All event type strings are covered.
- [ ] Using `event.type == shade.WebhookEventType.PAYMENT_COMPLETED` works in conditionals.

**Labels:** `area:webhooks`, `type:feature`, `priority:p2`

---

### #69 — Add webhook event payload parsing into typed models

## **Description:**
After parsing a `WebhookEvent`, the `data` field should be automatically deserialized into the corresponding SDK model based on `event.type`, so callers get a typed `Payment` / `Invoice` / etc. instead of a raw dict.

## **Proposed Steps:**
- Build a registry mapping event type prefix to model class: `{"payment.*": Payment, "invoice.*": Invoice, ...}`.
- In `construct_event`, after basic event parsing, look up and apply the model.
- Store the typed model in `event.data`.
- Fallback to a raw dict for unknown/future event types.

## **Acceptance Criteria:**
- [ ] `event.data` is a `Payment` model when `event.type == "payment.completed"`.
- [ ] `event.data` is an `Invoice` model when `event.type == "invoice.paid"`.
- [ ] An unknown event type results in `event.data` being a plain dict, not an error.

**Labels:** `area:webhooks`, `type:feature`, `priority:p2`

---

### #70 — Implement webhook signing secret rotation support

## **Description:**
During a signing secret rotation, both the old and new secrets are temporarily valid. `construct_event` should accept multiple secrets and succeed if any one of them verifies correctly.

## **Proposed Steps:**
- Change `secret` parameter to `secret: Union[str, list[str]]`.
- When a list is provided, try each secret in order.
- Raise `SignatureVerificationError` only if none of the provided secrets verify.

## **Acceptance Criteria:**
- [ ] `construct_event(payload, sig, [old_secret, new_secret])` succeeds with either secret.
- [ ] Raises `SignatureVerificationError` if all provided secrets fail.
- [ ] Single-string `secret` continues to work unchanged.

**Labels:** `area:webhooks`, `type:feature`, `priority:p3`

---

### #71 — Write unit tests for Webhooks resource

## **Description:**
Full unit test coverage for webhook construction, signature verification, and event parsing.

## **Proposed Steps:**
- Test `construct_event` with a freshly signed payload (happy path).
- Test with a tampered payload, wrong secret, and expired timestamp.
- Test multi-secret rotation (old secret, new secret, both invalid).
- Test that `event.data` is typed correctly for each event type.

## **Acceptance Criteria:**
- [ ] Happy-path test passes with a correctly signed payload.
- [ ] Tampered, wrong-secret, and expired tests raise `SignatureVerificationError`.
- [ ] `event.data` typing tests pass for Payment, Invoice, and Transfer events.
- [ ] Rotation tests confirm both secrets can independently verify.

**Labels:** `area:webhooks`, `type:test`, `priority:p1`

---

## K. Stellar Integration Layer (#72–#81)

---

### #72 — Implement keypair generation helper

## **Description:**
Expose a `generate_wallet()` helper that wraps `stellar_sdk.Keypair.random()` with a friendlier return type, so developers don't need to import `stellar_sdk` directly.

## **Proposed Steps:**
- Create `src/shade/stellar/__init__.py` and `src/shade/stellar/keypair.py`.
- `generate_wallet()` → `{"public_key": str, "secret_seed": str}`.
- Warn the developer to store the secret seed securely (log at `WARNING` level).

## **Acceptance Criteria:**
- [ ] Returns a dict with `public_key` (starts with `G`) and `secret_seed` (starts with `S`).
- [ ] Each call returns a unique keypair.
- [ ] A `UserWarning` is emitted reminding the developer to secure the seed.

**Labels:** `area:stellar`, `type:feature`, `priority:p1`

---

### #73 — Implement keypair import from seed/secret

## **Description:**
Allow importing an existing wallet from a Stellar secret seed, so developers can sign transactions on behalf of a wallet they control.

## **Proposed Steps:**
- `import_wallet(secret_seed: str)` → `{"public_key": str, "keypair": stellar_sdk.Keypair}`.
- Validate seed format (starts with `S`, 56 chars) before calling `stellar_sdk`.
- Raise `InvalidRequestError` on invalid format.

## **Acceptance Criteria:**
- [ ] A valid `S...` seed returns the correct public key.
- [ ] An invalid seed format raises `InvalidRequestError` before calling `stellar_sdk`.
- [ ] The returned `keypair` object can be used to sign transactions.

**Labels:** `area:stellar`, `type:feature`, `priority:p1`

---

### #74 — Implement network passphrase management

## **Description:**
The correct Stellar network passphrase must be applied to all transactions. This should be resolved automatically from the active `Environment` so developers never need to manage passphrases directly.

## **Proposed Steps:**
- In `src/shade/stellar/keypair.py` or a shared `network.py`, create `get_network_passphrase(env: Environment) -> str`.
- Return `stellar_sdk.Network.TESTNET_NETWORK_PASSPHRASE` for `SANDBOX`.
- Return `stellar_sdk.Network.PUBLIC_NETWORK_PASSPHRASE` for `PRODUCTION`.
- Expose `get_horizon_url(env: Environment) -> str` similarly.

## **Acceptance Criteria:**
- [ ] `SANDBOX` returns the testnet passphrase and Horizon testnet URL.
- [ ] `PRODUCTION` returns the mainnet passphrase and public Horizon URL.
- [ ] Both are consumed automatically by the transaction builder without extra configuration.

**Labels:** `area:stellar`, `type:feature`, `priority:p1`

---

### #75 — Implement payment transaction builder

## **Description:**
Build a signed Stellar payment transaction from the merchant's keypair, destination address, amount, and asset. The resulting `TransactionEnvelope` can then be submitted to Horizon.

## **Proposed Steps:**
- Create `src/shade/stellar/transaction.py`.
- `build_payment_tx(source_keypair, destination, amount, asset, memo=None, env=Environment.SANDBOX)` → `TransactionEnvelope`.
- Fetch the source account sequence from Horizon before building.
- Set the transaction fee using the current network base fee (#80 prereq; use a default until then).

## **Acceptance Criteria:**
- [ ] Returns a signed `TransactionEnvelope`.
- [ ] An invalid `destination` address raises `StellarError`.
- [ ] The transaction memo is included when provided.
- [ ] XLM and non-native assets are both supported.

**Labels:** `area:stellar`, `type:feature`, `priority:p1`

---

### #76 — Implement transaction submission and status polling

## **Description:**
Submit a signed `TransactionEnvelope` to Horizon and poll until it is confirmed or rejected, returning the transaction result.

## **Proposed Steps:**
- `submit_transaction(envelope: TransactionEnvelope, env=Environment.SANDBOX)` → `dict`.
- Use `stellar_sdk.Server.submit_transaction`.
- On failure, parse the Horizon error and raise `StellarError` with the `result_code`.
- Provide a `wait_for_transaction(tx_hash, timeout=60, env=...)` polling helper.

## **Acceptance Criteria:**
- [ ] A valid transaction returns a dict with `hash` and `ledger`.
- [ ] A transaction that fails due to insufficient balance raises `StellarError` with result code `INSUFFICIENT_BALANCE`.
- [ ] `wait_for_transaction` raises `StellarError` after `timeout` seconds.

**Labels:** `area:stellar`, `type:feature`, `priority:p1`

---

### #77 — Implement trustline management for non-native assets

## **Description:**
Before a Stellar account can hold a non-native asset (e.g. USDC), it must establish a trustline. Provide helpers to check for and create trustlines.

## **Proposed Steps:**
- `has_trustline(account_id, asset_code, asset_issuer, env=...)` → `bool`.
- `create_trustline(source_keypair, asset_code, asset_issuer, limit=None, env=...)` → `dict`.
- Use `stellar_sdk.ChangeTrustAsset` and `stellar_sdk.ChangeTrust` operations.

## **Acceptance Criteria:**
- [ ] `has_trustline` returns `True` if the account already trusts the asset.
- [ ] `create_trustline` submits a `change_trust` transaction and returns the result.
- [ ] Creating a trustline for an asset already trusted is a no-op (idempotent).

**Labels:** `area:stellar`, `type:feature`, `priority:p2`

---

### #78 — Implement account balance fetcher from Horizon

## **Description:**
Fetch live on-chain balances for a Stellar account directly from Horizon, independently of the Shade backend API. This is used by `Merchant.get_balance()` as a verification layer.

## **Proposed Steps:**
- `get_account_balances(account_id: str, env=Environment.SANDBOX)` → `list[AssetBalance]`.
- Use `stellar_sdk.Server.accounts().account_id(...)` to fetch account details.
- Map the Horizon response `balances` array to `AssetBalance` objects.
- Raise `StellarError` if the account doesn't exist on the network.

## **Acceptance Criteria:**
- [ ] Returns a list of `AssetBalance` objects for all held assets.
- [ ] A non-existent account raises `StellarError`.
- [ ] Native XLM balance is always included in the result.

**Labels:** `area:stellar`, `type:feature`, `priority:p2`

---

### #79 — Implement Soroban smart contract invocation helper

## **Description:**
The Shade protocol uses a Soroban (Stellar's smart contract layer) contract for certain operations. Provide a thin helper for invoking contract functions from the SDK.

## **Proposed Steps:**
- Create `src/shade/stellar/contract.py`.
- `invoke_contract(contract_id, function_name, args, source_keypair, env=...)` → `dict`.
- Build a Soroban `InvokeContractArgs` operation using `stellar_sdk`.
- Submit via `submit_transaction` (#76).
- Parse Soroban return value from the transaction result.

## **Acceptance Criteria:**
- [ ] A valid contract function invocation returns the decoded result.
- [ ] An invalid `contract_id` raises `StellarError`.
- [ ] The helper does not expose raw XDR to the caller.

**Labels:** `area:stellar`, `type:feature`, `priority:p2`

---

### #80 — Implement transaction fee estimation

## **Description:**
Query the current Stellar network base fee from Horizon before building transactions, so fee estimation is dynamic rather than using a hardcoded value.

## **Proposed Steps:**
- `estimate_fee(env=Environment.SANDBOX)` → `int` (stroops).
- Use `stellar_sdk.Server.fetch_base_fee()`.
- Apply a configurable `fee_multiplier` (default `1.5`) to get a competitive fee.
- Cache the result for 30 seconds to avoid excessive Horizon calls.

## **Acceptance Criteria:**
- [ ] Returns a positive integer fee in stroops.
- [ ] The `fee_multiplier` is applied to the base fee.
- [ ] The cached value is used within 30 seconds of the last call.
- [ ] A Horizon failure raises `StellarError`.

**Labels:** `area:stellar`, `type:feature`, `priority:p3`

---

### #81 — Write unit tests for Stellar integration layer (testnet)

## **Description:**
Test the Stellar integration layer against the public Stellar testnet. These are integration tests — they make real network calls to Horizon testnet.

## **Proposed Steps:**
- Use Stellar Friendbot to fund a test account.
- Test `generate_wallet`, `import_wallet`, `build_payment_tx`, `submit_transaction`.
- Test `has_trustline` / `create_trustline` with a test asset.
- Mark these tests with `@pytest.mark.integration` so they can be skipped in offline CI.

## **Acceptance Criteria:**
- [ ] A full payment cycle (generate wallet → fund → build tx → submit → verify) passes on testnet.
- [ ] Trustline creation and detection work on testnet.
- [ ] Integration tests are skipped by default in CI unless `SHADE_RUN_INTEGRATION` is set.

**Labels:** `area:stellar`, `type:test`, `priority:p1`

---

## L. Async Support (#82–#87)

---

### #82 — Add async variant for Payments resource methods

## **Description:**
Provide `async def` variants of all Payments methods (prefixed with `a`) so the SDK works natively in async frameworks without blocking the event loop.

## **Proposed Steps:**
- In `payments.py`, add `acreate`, `aretrieve`, `alist`, `averify`, `acancel` as `async def` methods.
- Delegate to the `_AsyncHTTPClient` (#8) instead of the sync client.
- Share all validation logic with the sync versions (extract to shared helpers).

## **Acceptance Criteria:**
- [ ] `await Payment.acreate(...)` returns a `Payment` model.
- [ ] All async methods are usable in a FastAPI route without blocking.
- [ ] Validation errors raise synchronously (before `await`).
- [ ] Sync and async methods share validation logic without duplication.

**Labels:** `area:async`, `type:feature`, `priority:p2`

---

### #83 — Add async variant for Invoices resource methods

## **Description:**
Provide `async def` variants of all Invoices methods.

## **Proposed Steps:**
- Add `acreate`, `aretrieve`, `alist`, `asend`, `acancel`, `aupdate` to `invoices.py`.
- Delegate to `_AsyncHTTPClient`.

## **Acceptance Criteria:**
- [ ] All Invoice async methods work correctly in an async context.
- [ ] Sync validation is not `await`-able (no `await` inside validation helpers).

**Labels:** `area:async`, `type:feature`, `priority:p2`

---

### #84 — Add async variant for Transfers resource methods

## **Description:**
Provide `async def` variants of all Transfers methods.

## **Proposed Steps:**
- Add `acreate`, `aretrieve`, `alist` to `transfers.py`.
- Delegate to `_AsyncHTTPClient`.

## **Acceptance Criteria:**
- [ ] All Transfer async methods return correctly typed models.
- [ ] Can be used in an async context alongside Payments async methods.

**Labels:** `area:async`, `type:feature`, `priority:p2`

---

### #85 — Add async variant for Merchants resource methods

## **Description:**
Provide `async def` variants of all Merchants methods.

## **Proposed Steps:**
- Add `aretrieve`, `aupdate`, `aget_balance` to `merchants.py`.
- Delegate to `_AsyncHTTPClient`.

## **Acceptance Criteria:**
- [ ] `await Merchant.aretrieve()` returns a `Merchant` model.
- [ ] `await Merchant.aget_balance()` returns a `Balance` model.

**Labels:** `area:async`, `type:feature`, `priority:p2`

---

### #86 — Add async variant for Swap Payments resource methods

## **Description:**
Provide `async def` variants of all Swap Payments methods.

## **Proposed Steps:**
- Add `acreate`, `aretrieve`, `aget_quote` to `swaps.py`.
- Delegate to `_AsyncHTTPClient`.

## **Acceptance Criteria:**
- [ ] `await SwapPayment.acreate(...)` returns a `SwapPayment` model.
- [ ] `await SwapPayment.aget_quote(...)` returns a quote dict.

**Labels:** `area:async`, `type:feature`, `priority:p2`

---

### #87 — Write unit tests for async resource methods

## **Description:**
Unit tests for all async resource methods using `pytest-asyncio` and mocked async HTTP transport.

## **Proposed Steps:**
- Configure `pytest-asyncio` in `pyproject.toml` with `asyncio_mode = "auto"`.
- Write `async def test_*` functions for each async method.
- Use `respx` with async mode to mock `httpx.AsyncClient`.
- Confirm that sync and async variants produce identical output for the same mocked response.

## **Acceptance Criteria:**
- [ ] All async methods have at least one passing test.
- [ ] Sync and async variants of the same method are tested with identical mocked payloads.
- [ ] Tests run correctly with `pytest-asyncio` in auto mode.
- [ ] No event loop warnings in test output.

**Labels:** `area:async`, `type:test`, `priority:p2`

---

## M. Testing & QA (#88–#95)

---

### #88 — Set up pytest-asyncio for async test support

## **Description:**
Install and configure `pytest-asyncio` so all `async def test_*` functions run correctly without boilerplate `@pytest.mark.asyncio` decorators on every test.

## **Proposed Steps:**
- Add `pytest-asyncio` to `[tool.poetry.group.dev.dependencies]` in `pyproject.toml`.
- Add `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`.
- Verify with a trivial `async def test_async_works()` test.

## **Acceptance Criteria:**
- [ ] `async def test_*` functions run without `@pytest.mark.asyncio`.
- [ ] No deprecation warnings about async mode in test output.
- [ ] CI passes with the new configuration.

**Labels:** `area:testing`, `type:chore`, `priority:p1`

---

### #89 — Set up HTTP mocking for resource tests

## **Description:**
Resource tests must never hit the real network. Install `respx` as a dev dependency and document the mocking pattern so all contributors follow the same approach.

## **Proposed Steps:**
- Add `respx` to `[tool.poetry.group.dev.dependencies]`.
- Create `tests/conftest.py` with a shared `mock_shade_api` fixture.
- Document the pattern in a `tests/README.md` (or inline in `conftest.py`).

## **Acceptance Criteria:**
- [ ] `respx` is available in tests.
- [ ] The shared fixture mocks the Shade API base URL.
- [ ] Any test that accidentally makes a real request fails immediately (raise on unmatched routes).

**Labels:** `area:testing`, `type:chore`, `priority:p1`

---

### #90 — Add model serialization/deserialization test suite

## **Description:**
Every model should round-trip through `from_dict(to_dict())` without data loss or type coercion issues.

## **Proposed Steps:**
- Create `tests/models/` with one test file per model.
- Use fixture JSON payloads matching real API response shapes.
- Assert field-by-field equality after round-trip.
- Test that extra fields in the API response are accepted without error.

## **Acceptance Criteria:**
- [ ] All models round-trip successfully.
- [ ] Extra API fields do not raise validation errors.
- [ ] Missing optional fields default to `None` rather than raising.
- [ ] `Decimal` fields do not lose precision.

**Labels:** `area:testing`, `type:test`, `priority:p2`

---

### #91 — Add webhook signature verification test suite

## **Description:**
Dedicated tests for the HMAC signature logic, independent of the full `construct_event` flow.

## **Proposed Steps:**
- Generate known payload + secret + timestamp → expected signature in the test.
- Test with correct signature, flipped bit, wrong secret, expired timestamp.
- Test multi-secret rotation.
- Test `Shade-Signature` header parsing edge cases (missing `t=`, missing `v1=`).

## **Acceptance Criteria:**
- [ ] Valid signature test passes.
- [ ] Tampered payload test raises `SignatureVerificationError`.
- [ ] Expired timestamp test raises `SignatureVerificationError`.
- [ ] Malformed `Shade-Signature` header raises `SignatureVerificationError`.

**Labels:** `area:testing`, `type:test`, `priority:p1`

---

### #92 — Add Stellar testnet integration test suite

## **Description:**
End-to-end tests against real Stellar testnet, covering wallet generation, payment building, submission, and trustline management.

## **Proposed Steps:**
- Create `tests/integration/` folder.
- Mark tests with `@pytest.mark.integration`.
- Skip when `SHADE_RUN_INTEGRATION` env var is not set.
- Test: generate wallet → Friendbot fund → build payment tx → submit → fetch balance.

## **Acceptance Criteria:**
- [ ] Tests are skipped in standard CI runs.
- [ ] When `SHADE_RUN_INTEGRATION=1`, all integration tests pass against Stellar testnet.
- [ ] Friendbot funding is automated within the test setup.

**Labels:** `area:testing`, `type:test`, `priority:p2`

---

### #93 — Add CI matrix for multiple Python versions

## **Description:**
The SDK targets Python 3.10+. CI must verify it works on 3.10, 3.11, and 3.12 to catch version-specific type annotation or stdlib differences.

## **Proposed Steps:**
- Update `matrix.python-version` in `.github/workflows/ci.yml` to `["3.10", "3.11", "3.12"]`.
- Ensure `pyproject.toml` allows all three (`python = "^3.10"`).
- Fix any version-specific issues surfaced by the expanded matrix.

## **Acceptance Criteria:**
- [ ] CI runs pass on Python 3.10, 3.11, and 3.12.
- [ ] No version-specific warnings or deprecations in any test run.

**Labels:** `area:testing`, `type:chore`, `priority:p2`

---

### #94 — Add code coverage reporting in CI

## **Description:**
Track test coverage to prevent regressions and identify untested paths. Coverage should be reported in the CI output and optionally uploaded to a coverage service (e.g. Codecov).

## **Proposed Steps:**
- Add `pytest-cov` to dev dependencies.
- Add `--cov=shade --cov-report=term-missing` to the pytest command in CI.
- Fail the build if coverage drops below 80%.
- Optionally add Codecov or similar via a CI step.

## **Acceptance Criteria:**
- [ ] Coverage percentage is printed in CI output.
- [ ] CI fails if coverage is below the configured threshold.
- [ ] The coverage report shows per-file coverage.

**Labels:** `area:testing`, `type:chore`, `priority:p3`

---

### #95 — Add type checking (mypy) to CI pipeline

## **Description:**
Static type checking ensures that the type annotations across the SDK are internally consistent and that external consumers get meaningful IDE support.

## **Proposed Steps:**
- Add `mypy` to dev dependencies.
- Create `mypy.ini` or `[tool.mypy]` in `pyproject.toml` targeting `src/shade`.
- Enable `strict = true` for the SDK source.
- Add a `mypy` step to the CI workflow.

## **Acceptance Criteria:**
- [ ] `poetry run mypy src/shade` exits 0.
- [ ] CI fails on mypy errors.
- [ ] All public function signatures have type annotations.
- [ ] The `py.typed` marker file is present in `src/shade/` for PEP 561 compliance.

**Labels:** `area:testing`, `type:chore`, `priority:p2`

---

## N. Tooling, Docs & Packaging (#96–#100)

---

### #96 — Add new dependencies to pyproject.toml

## **Description:**
The current `pyproject.toml` only lists `stellar-sdk` as a runtime dependency. Several new packages are needed before implementation can begin.

## **Proposed Steps:**
- Add to `[tool.poetry.dependencies]`: `httpx >= 0.27`, `pydantic >= 2.0`, `cryptography >= 42.0`.
- Add to `[tool.poetry.group.dev.dependencies]`: `pytest-asyncio >= 0.23`, `respx >= 0.21`, `pytest-cov >= 4.0`, `mypy >= 1.9`.
- Run `poetry lock` and `poetry install` to verify the full dependency graph resolves.

## **Acceptance Criteria:**
- [ ] `poetry install` completes without conflicts.
- [ ] All new packages are importable in a clean virtual environment.
- [ ] Python version constraint remains `^3.10`.
- [ ] `poetry.lock` is committed alongside `pyproject.toml`.

**Labels:** `area:tooling`, `type:chore`, `priority:p1`

---

### #97 — Write SDK usage documentation in README.md

## **Description:**
Replace the current placeholder README with comprehensive documentation covering installation, configuration, and a quickstart for each resource.

## **Proposed Steps:**
- Add sections: Installation, Authentication, Quickstart, Payments, Invoices, Merchants, Transfers, Swap Payments, Webhooks, Stellar Utils, Error Handling, Async Usage.
- Include working code examples for each section.
- Document all configuration options (api_key, environment, timeout, max_retries, debug).
- Add a "Testing" section describing how to run the test suite.

## **Acceptance Criteria:**
- [ ] A developer new to the SDK can authenticate and create a payment by following the README alone.
- [ ] All resource methods are represented by at least one code example.
- [ ] The error handling section documents every exception type.
- [ ] The README renders correctly as GitHub Markdown.

**Labels:** `area:docs`, `type:docs`, `priority:p2`

---

### #98 — Add example scripts demonstrating common flows

## **Description:**
Self-contained, runnable example scripts in an `examples/` folder serve as both documentation and smoke tests for common integration patterns.

## **Proposed Steps:**
- Create `examples/create_payment.py` — configure client, create payment, poll status.
- Create `examples/create_invoice.py` — create invoice with line items, send to customer.
- Create `examples/verify_webhook.py` — Flask/FastAPI snippet for verifying a webhook.
- Create `examples/swap_payment.py` — get quote, create swap payment.
- Each script should use `SHADE_API_KEY` from the environment.

## **Acceptance Criteria:**
- [ ] Each example runs end-to-end against the sandbox environment.
- [ ] Examples read credentials from environment variables, not hardcoded strings.
- [ ] Each example includes inline comments explaining each step.

**Labels:** `area:docs`, `type:docs`, `priority:p3`

---

### #99 — Add CHANGELOG.md and versioning policy

## **Description:**
Adopt semantic versioning and maintain a changelog so developers integrating the SDK know what changed between versions and can assess upgrade impact.

## **Proposed Steps:**
- Create `CHANGELOG.md` with an initial `[Unreleased]` section.
- Follow [Keep a Changelog](https://keepachangelog.com) format: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- Document the semantic versioning policy in `CONTRIBUTING.md` or `README.md`.
- Tag the first release as `v0.1.0` once the p1 issues are complete.

## **Acceptance Criteria:**
- [ ] `CHANGELOG.md` exists with an `[Unreleased]` section.
- [ ] The changelog format is clearly documented.
- [ ] A `v0.1.0` git tag exists when the initial feature set is released.

**Labels:** `area:tooling`, `type:chore`, `priority:p3`

---

### #100 — Configure package for PyPI distribution

## **Description:**
Finalize `pyproject.toml` metadata and add a GitHub Actions release workflow so new versions can be published to PyPI with a single git tag push.

## **Proposed Steps:**
- Fill in `pyproject.toml` metadata: `license`, `homepage`, `repository`, `classifiers`, `keywords`.
- Add a `py.typed` marker file for PEP 561.
- Create `.github/workflows/publish.yml` triggered on `push: tags: ["v*"]`.
- The publish workflow should run tests first, then `poetry publish --build`.
- Use a PyPI API token stored as a GitHub secret (`PYPI_TOKEN`).

## **Acceptance Criteria:**
- [ ] `poetry build` produces valid `.tar.gz` and `.whl` artifacts.
- [ ] Pushing a `v*` tag triggers the publish workflow.
- [ ] The package is installable via `pip install shade` after the first publish.
- [ ] Package metadata (classifiers, license) is correct on PyPI.

**Labels:** `area:tooling`, `type:chore`, `priority:p2`
