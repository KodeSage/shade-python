import pytest
import shade
from shade import (
    AuthenticationError,
    InvalidRequestError,
    NetworkError,
    NotFoundError,
    ShadeError,
)
from shade.errors import raise_for_invalid_request


def test_shade_error_can_be_raised_standalone():
    error = ShadeError("contract rejected payment")

    assert str(error) == "contract rejected payment"
    assert error.message == "contract rejected payment"
    assert error.status_code is None
    assert error.response_body is None


def test_shade_error_includes_http_context():
    error = ShadeError(
        "invalid request",
        status_code=422,
        response_body='{"error":"missing amount"}',
    )

    assert str(error) == "invalid request (status code: 422)"
    assert error.status_code == 422
    assert error.response_body == '{"error":"missing amount"}'


def test_specific_errors_inherit_from_shade_error():
    for error_type in (
        AuthenticationError,
        InvalidRequestError,
        NetworkError,
        NotFoundError,
    ):
        error = error_type("request failed", status_code=400, response_body="raw")

        assert isinstance(error, ShadeError)
        assert str(error) == "request failed (status code: 400)"
        assert error.response_body == "raw"


def test_package_root_exports_error_classes():
    assert shade.ShadeError is ShadeError
    assert shade.AuthenticationError is AuthenticationError
    assert shade.InvalidRequestError is InvalidRequestError
    assert shade.NetworkError is NetworkError
    assert shade.NotFoundError is NotFoundError


def test_invalid_request_error_parses_param_from_body():
    body = (
        '{"error": {"code": "invalid_param", "param": "amount", '
        '"message": "Amount must be greater than zero"}}'
    )
    error = InvalidRequestError("invalid request", status_code=400, response_body=body)

    assert error.param == "amount"
    assert error.message == "invalid request"


def test_invalid_request_error_parses_field_errors_from_body():
    body = (
        '{"error": {"code": "invalid_param", "param": "amount", "message": "Validation failed", '
        '"field_errors": {"amount": "must be positive", "currency": "is required"}}}'
    )
    error = InvalidRequestError.from_response(400, body)

    assert error.param == "amount"
    assert error.field_errors == {
        "amount": "must be positive",
        "currency": "is required",
    }


def test_invalid_request_error_str_includes_param():
    body = (
        '{"error": {"code": "invalid_param", "param": "amount", '
        '"message": "Amount must be greater than zero"}}'
    )
    error = InvalidRequestError.from_response(400, body)

    assert "amount" in str(error)
    assert "Amount must be greater than zero" in str(error)
    assert str(error) == "Amount must be greater than zero (param: amount) (status code: 400)"


def test_invalid_request_error_explicit_attrs_override_body():
    body = (
        '{"error": {"param": "currency", "field_errors": {"currency": "invalid"}}, '
        '"field_errors": {"amount": "too small"}}'
    )
    error = InvalidRequestError(
        "invalid request",
        status_code=422,
        response_body=body,
        param="amount",
        field_errors={"amount": "required"},
    )

    assert error.param == "amount"
    assert error.field_errors == {"amount": "required"}


def test_400_response_raises_invalid_request_error():
    body = (
        '{"error": {"code": "invalid_param", "param": "amount", '
        '"message": "Amount must be greater than zero"}}'
    )

    with pytest.raises(InvalidRequestError) as exc_info:
        raise_for_invalid_request(400, body)

    error = exc_info.value
    assert error.status_code == 400
    assert error.param == "amount"
    assert isinstance(error, ShadeError)


def test_422_response_raises_invalid_request_error():
    body = '{"error": {"param": "email", "message": "Invalid email format"}}'

    with pytest.raises(InvalidRequestError) as exc_info:
        raise_for_invalid_request(422, body)

    assert exc_info.value.param == "email"
    assert exc_info.value.status_code == 422


def test_raise_for_invalid_request_ignores_other_status_codes():
    raise_for_invalid_request(404, '{"error": {"message": "not found"}}')
    raise_for_invalid_request(500, '{"error": {"message": "server error"}}')
