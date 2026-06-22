import pytest
from unittest.mock import patch
from shade import Gateway


def test_gateway_initialization():
    gateway = Gateway(api_key="test-key")
    assert gateway is not None


def test_process_payment():
    gateway = Gateway(api_key="test-key")
    mock_response = {"id": "pay_001", "status": "ok"}

    with patch.object(gateway._http, "request", return_value=mock_response) as mock_req:
        result = gateway.process_payment(100.0, "USD")

    assert result == mock_response
    mock_req.assert_called_once_with(
        "POST", "/payments", {"amount": 100.0, "currency": "USD"}
    )