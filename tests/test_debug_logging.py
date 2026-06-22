import logging

import httpx
import pytest

from shade import ShadeClient, config
from shade._debug import mask_headers, truncate_body


@pytest.fixture(autouse=True)
def reset_config():
    original = config.debug
    config.debug = False
    yield
    config.debug = original


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def test_mask_authorization_header():
    headers = {"Authorization": "Bearer sk_test_abcdefghij", "Content-Type": "application/json"}
    masked = mask_headers(headers)

    assert masked["Content-Type"] == "application/json"
    assert masked["Authorization"].endswith("ghij")
    assert masked["Authorization"][:-4] == "*" * (len("Bearer sk_test_abcdefghij") - 4)


def test_mask_short_authorization_header():
    masked = mask_headers({"Authorization": "abc"})
    assert masked["Authorization"] == "****"


def test_truncate_body():
    body = "x" * 2500
    truncated = truncate_body(body)

    assert truncated.endswith("[truncated]")
    assert len(truncated) == 2000 + len("[truncated]")


def test_truncate_body_under_limit():
    body = "short body"
    assert truncate_body(body) == body


def test_debug_logs_request_and_response(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"}, headers={"X-Request-Id": "req-1"})

    transport = _mock_transport(handler)
    http_client = httpx.Client(transport=transport)

    with caplog.at_level(logging.DEBUG, logger="shade"):
        with ShadeClient(
            api_key="sk_test_secret_key_1234",
            base_url="https://api.example.com",
            debug=True,
            http_client=http_client,
        ) as client:
            client.request("POST", "/payments", json={"amount": 100})

    assert any("Request: POST https://api.example.com/payments" in record.message for record in caplog.records)
    assert any("Response: status=200" in record.message for record in caplog.records)
    assert not any("sk_test_secret_key_1234" in record.message for record in caplog.records)
    assert any("1234" in record.message for record in caplog.records)


def test_debug_false_does_not_log(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    transport = _mock_transport(handler)
    http_client = httpx.Client(transport=transport)

    with caplog.at_level(logging.DEBUG, logger="shade"):
        with ShadeClient(
            api_key="sk_test_secret_key_1234",
            base_url="https://api.example.com",
            debug=False,
            http_client=http_client,
        ) as client:
            client.request("GET", "/health")

    shade_records = [record for record in caplog.records if record.name == "shade"]
    assert shade_records == []


def test_global_config_debug_enables_logging(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, text='{"created": true}')

    transport = _mock_transport(handler)
    http_client = httpx.Client(transport=transport)
    config.debug = True

    with caplog.at_level(logging.DEBUG, logger="shade"):
        with ShadeClient(
            api_key="sk_test_secret_key_5678",
            base_url="https://api.example.com",
            debug=False,
            http_client=http_client,
        ) as client:
            client.request("POST", "/items")

    assert any("Request: POST https://api.example.com/items" in record.message for record in caplog.records)
    assert any("Response: status=201" in record.message for record in caplog.records)


def test_response_body_truncated_in_logs(caplog):
    long_body = "y" * 3000

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=long_body)

    transport = _mock_transport(handler)
    http_client = httpx.Client(transport=transport)

    with caplog.at_level(logging.DEBUG, logger="shade"):
        with ShadeClient(
            api_key="sk_test_key_abcd",
            base_url="https://api.example.com",
            debug=True,
            http_client=http_client,
        ) as client:
            client.request("GET", "/large")

    response_logs = [record.message for record in caplog.records if "Response: status=200" in record.message]
    assert len(response_logs) == 1
    assert "[truncated]" in response_logs[0]
    assert "y" * 3000 not in response_logs[0]
