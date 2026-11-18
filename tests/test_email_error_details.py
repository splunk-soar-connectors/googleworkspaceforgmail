# Copyright (c) 2026 Splunk Inc.
"""Verify useful email diagnostics cannot expose upstream exception contents."""

import binascii
import importlib
import logging

import httpx
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError
from soar_sdk.extras.email import email_data, utils
from soar_sdk.models.finding import Finding


module = importlib.import_module("src.app")
PRIVATE = "Authorization: Bearer private-token https://host/?signature=private-signature email-body"


@pytest.mark.parametrize(
    "status,reason",
    [
        (400, "invalid_request"),
        (401, "authentication"),
        (403, "permission_denied"),
        (404, "not_found"),
        (410, "gone"),
        (413, "payload_too_large"),
        (422, "invalid_data"),
        (429, "rate_limited"),
        (503, "service_unavailable"),
    ],
)
@pytest.mark.parametrize("source", ["status_code", "response", "resp", "graph_prefix"])
def test_http_diagnostics_expose_only_status_and_safe_reason(status, reason, source):
    error = RuntimeError(PRIVATE)
    if source == "status_code":
        error.status_code = status
    elif source == "response":
        error.response = SimpleNamespace(status_code=status, text=PRIVATE)
    elif source == "resp":
        error.resp = SimpleNamespace(status=status)
    else:
        error = RuntimeError(f"API Error {status}: {PRIVATE}")
    result = module._email_failure_reason(error)
    assert result == f"HTTP {status} {reason} (RuntimeError)"
    assert PRIVATE not in result
    assert "signature" not in result


@pytest.mark.parametrize(
    "error,reason",
    [
        (TimeoutError(PRIVATE), "timeout"),
        (ConnectionError(PRIVATE), "connection_failed"),
        (binascii.Error(PRIVATE), "invalid_encoding"),
        (ValueError(PRIVATE), "invalid_data"),
        (RuntimeError(PRIVATE), "processing_failed"),
    ],
)
def test_failure_reason_does_not_include_exception_text(error, reason):
    result = module._email_failure_reason(error)
    assert result.startswith(reason)
    assert PRIVATE not in result
    assert len(result) < 80


def test_validation_diagnostic_identifies_field_without_input():
    with pytest.raises(ValidationError) as caught:
        Finding(rule_title={"secret": PRIVATE})
    assert (
        module._email_failure_reason(caught.value)
        == "validation field=rule_title rule=string_type"
    )


def test_validation_diagnostic_drops_arbitrary_field_names_and_custom_codes():
    error = ValidationError.from_exception_data(
        "Finding",
        [
            {
                "type": PydanticCustomError(PRIVATE, PRIVATE),
                "loc": (PRIVATE,),
                "input": PRIVATE,
            }
        ],
    )
    assert (
        module._email_failure_reason(error)
        == "validation field=payload rule=invalid_value"
    )


def test_unstructured_exception_text_is_not_used_as_a_reason():
    result = module._email_failure_reason(RuntimeError(PRIVATE + " 404 invalid_token"))
    assert result == "processing_failed (RuntimeError)"


@pytest.mark.parametrize(
    "source",
    [
        "/site-packages/soar_sdk/extras/email/utils.py",
        r"C:\site-packages\soar_sdk\extras\email\email_data.py",
    ],
)
def test_sdk_parser_debug_filter_removes_message_args_and_traceback(source):

    record = logging.LogRecord(
        "soar_sdk",
        logging.DEBUG,
        source,
        1,
        PRIVATE + " %s",
        (PRIVATE,),
        (ValueError, ValueError(PRIVATE), None),
    )
    record.exc_text = record.stack_info = PRIVATE
    assert module._EmailParserLogFilter().filter(record)
    assert (
        logging.Formatter().format(record)
        == "SDK email parser debug event; message details omitted"
    )
    assert record.args == ()
    assert record.exc_info is record.exc_text is record.stack_info is None


@pytest.mark.parametrize("failure", ["header", "html"])
def test_real_sdk_parser_failure_logs_do_not_echo_input(mocker, capsys, failure):

    if failure == "header":
        mocker.patch.object(utils, "decode_header", side_effect=ValueError(PRIVATE))
        assert (
            utils.decode_uni_string("=?UTF-8?Q?" + PRIVATE + "?=", "fallback")
            == "fallback"
        )
    else:
        mocker.patch.object(
            email_data, "BeautifulSoup", side_effect=ValueError(PRIVATE)
        )
        email_data._extract_urls_from_content(
            "<body>" + PRIVATE + "</body>", set(), True
        )
    logs = capsys.readouterr().out
    assert "SDK email parser debug event" in logs
    assert "private-token" not in logs
    assert "private-signature" not in logs
    assert "email-body" not in logs


def test_inner_email_warning_omits_filename_and_exception(mocker, capsys):
    outer = SimpleNamespace(
        attachments=[SimpleNamespace(filename=PRIVATE + ".eml", content=b"synthetic")]
    )
    mocker.patch.object(module, "extract_email_data", side_effect=ValueError(PRIVATE))
    assert module._extract_inner_email(outer) is None
    logs = capsys.readouterr().out
    assert "could not be parsed" in logs
    assert PRIVATE not in logs
    assert "private-token" not in logs


def test_domain_extraction_debug_omits_full_url(capsys):
    asset = SimpleNamespace(
        extract_ips=False,
        extract_urls=False,
        extract_domains=True,
        extract_hashes=False,
    )
    parsed = SimpleNamespace(
        body=SimpleNamespace(plain_text="", html=""),
        urls=["https://[invalid/?signature=" + PRIVATE],
    )
    module.Asset._extract_iocs(asset, parsed, False)
    logs = capsys.readouterr().out
    assert "domain extraction failed" in logs
    assert PRIVATE not in logs


@pytest.mark.parametrize(
    "path,level",
    [
        ("/connector/src/app.py", logging.DEBUG),
        ("/site-packages/soar_sdk/extras/email/utils.py", logging.WARNING),
    ],
)
def test_filter_preserves_other_safe_events(path, level):
    record = logging.LogRecord(
        "soar_sdk", level, path, 1, "Safe status %s", (503,), None
    )
    assert module._EmailParserLogFilter().filter(record)
    assert record.getMessage() == "Safe status 503"


def test_real_httpx_request_log_omits_signed_url_and_credentials(caplog, capsys):
    url = "https://upload.example/email?X-Amz-Signature=private-signature"
    with (
        caplog.at_level(logging.INFO, logger="httpx"),
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(201))
        ) as client,
    ):
        assert (
            client.post(
                url,
                headers={"Authorization": "Bearer private-token"},
                content=b"email-body",
            ).status_code
            == 201
        )
    captured = capsys.readouterr()
    logs = caplog.text + captured.out + captured.err
    assert "POST request returned HTTP 201; URL omitted" in logs
    for secret in (
        "private-token",
        "private-signature",
        "upload.example",
        "email-body",
    ):
        assert secret not in logs
