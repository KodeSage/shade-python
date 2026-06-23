import shade
from shade import (
    AuthenticationError,
    InvalidRequestError,
    NetworkError,
    NotFoundError,
    ShadeError,
)


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
