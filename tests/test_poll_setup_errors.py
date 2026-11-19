# Copyright (c) 2026 Splunk Inc.
"""Check setup diagnostics never expose upstream response contents."""

from types import SimpleNamespace
import pytest
from google.auth.exceptions import RefreshError
from soar_sdk.exceptions import ActionFailure
from src.poll_errors import MailPollError, _setup_reason, diagnose_es_poll

PRIVATE = "private-password private-mailbox https://host/?token=private-token"


@pytest.mark.parametrize(
    "status, expected",
    [
        (401, "authentication"),
        (403, "authentication"),
        (404, "mailbox"),
        (400, None),
        (429, None),
        (503, None),
    ],
)
@pytest.mark.parametrize("source", ["status", "response", "resp", "graph", "ews"])
def test_only_known_statuses_are_reported(status, expected, source):
    error = RuntimeError(PRIVATE)
    if source == "status":
        error.status_code = status
    elif source == "response":
        error.response = SimpleNamespace(status_code=status)
    elif source == "resp":
        error.resp = SimpleNamespace(status=status)
    elif source == "graph":
        error = ActionFailure(f"API Error {status}: {PRIVATE}")
    else:
        error = RuntimeError(f"Call failed with HTTP Code: {status}. Reason: {PRIVATE}")
    assert _setup_reason(error) == ((expected, status) if expected else None)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("ErrorAccessDenied", "authentication"),
        ("ErrorInvalidCredentials", "authentication"),
        ("ErrorFolderNotFound", "mailbox"),
        ("ErrorNonExistentMailbox", "mailbox"),
        ("ErrorUnknown", None),
    ],
)
def test_ews_uses_only_fixed_protocol_codes(code, expected):
    result = _setup_reason(
        Exception(f"API failed. Status code: {code}. Message: {PRIVATE}")
    )
    assert result == ((expected, None) if expected else None)


@pytest.mark.parametrize(
    "code",
    [
        "invalid_client",
        "invalid_grant",
        "unauthorized_client",
        "invalid_scope",
        "access_denied",
    ],
)
def test_oauth_uses_only_fixed_protocol_codes(code):
    assert _setup_reason(ActionFailure(f"{code}: {PRIVATE}")) == (
        "authentication",
        None,
    )


def test_wrapped_failure_retains_no_upstream_message():
    @diagnose_es_poll
    def poll():
        error = Exception(f"API Error 401: {PRIVATE}")
        raise error
        yield

    with pytest.raises(MailPollError) as caught:
        list(poll())
    assert caught.value.polling_error_code == "authentication"
    assert caught.value.status_code == 401
    assert PRIVATE not in str(caught.value)
    assert caught.value.__suppress_context__


def test_unknown_network_failure_is_not_mislabeled():
    error = ConnectionError(PRIVATE)

    @diagnose_es_poll
    def poll():
        raise error
        yield

    with pytest.raises(ConnectionError) as caught:
        list(poll())
    assert caught.value is error
    assert _setup_reason(error) is None


def test_causes_are_bounded_and_explicit_codes_pass_through():
    cause = Exception("API Error 404: " + PRIVATE)
    error = Exception(PRIVATE)
    error.__cause__ = cause
    assert _setup_reason(error) == ("mailbox", 404)
    cause.__cause__ = error
    cause.args = (PRIVATE,)
    assert _setup_reason(error) is None

    @diagnose_es_poll
    def poll():
        raise MailPollError("mailbox")
        yield

    with pytest.raises(MailPollError, match="Mailbox or folder"):
        list(poll())


@pytest.mark.parametrize("retryable", [False, True])
def test_google_refresh_errors_keep_retryable_transport_failures_generic(retryable):
    error = RefreshError(PRIVATE, retryable=retryable)
    assert _setup_reason(error) == (None if retryable else ("authentication", None))


def test_invalid_service_account_configuration_is_authentication_failure():
    assert _setup_reason(ActionFailure("Invalid service account JSON: " + PRIVATE)) == (
        "authentication",
        None,
    )
