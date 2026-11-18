# Copyright (c) 2026 Splunk Inc.
"""Check source progress using the SDK's real ES polling decorator."""

import base64
import importlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from types import SimpleNamespace

import httpx
import pytest
from soar_sdk.asset_state import AssetState
from soar_sdk.params import OnESPollParams

module = importlib.import_module("src.app")


def raw_email(identifier):
    message = EmailMessage()
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message["Subject"] = identifier
    message.set_content("Synthetic checkpoint test")
    return message.as_bytes()


@pytest.fixture
def runtime(monkeypatch, mocker):
    app = module.app
    mocker.patch("soar_sdk.decorators._es_poll.sleep")
    asset = make_asset()
    saved = {}
    mocker.patch.object(
        app.actions_manager, "load_state", side_effect=lambda: dict(saved)
    )
    mocker.patch.object(app.actions_manager, "save_state", side_effect=saved.update)
    asset._ingest_state = AssetState(
        app.actions_manager, "ingest", "1", encrypted=False
    )
    monkeypatch.setattr(app, "_asset", asset, raising=False)
    monkeypatch.setattr(app, "_es_ingest_config", {"es_security_domain": "threat"})
    monkeypatch.setattr(app.soar_client, "MAX_BULK_FINDINGS", 2)
    monkeypatch.setitem(
        sys.modules,
        "es_poll_api",
        SimpleNamespace(get_es_context=lambda: ("https://es.example", "test-token")),
    )
    mocker.patch.object(app.actions_manager, "add_result")
    mocker.patch.object(
        app.soar_client, "get", side_effect=AssertionError("SOAR REST called")
    )
    mocker.patch.object(
        app.soar_client, "post", side_effect=AssertionError("SOAR REST called")
    )
    mocker.patch(
        "soar_sdk.decorators._es_poll._upload_poll_attachments",
        side_effect=lambda client, findings, *args: [[] for _ in findings],
    )
    context = SimpleNamespace(
        asset=asset, sent=[], failed=None, rows={}, pages={}, mime="valid"
    )
    for number in range(1, 7):
        identifier = f"mail-{number}"
        context.rows[identifier] = {
            "id": identifier,
            "subject": identifier,
            "receivedDateTime": (
                datetime(2026, 11, 13, tzinfo=UTC) + timedelta(minutes=number)
            ).isoformat(),
        }

    def create(client, url, *, content, headers):
        payload = json.loads(content)
        identifier = re.search(r"mail-\d+$", payload["rule_title"]).group()
        context.sent.append(identifier)
        if identifier == context.failed:
            return httpx.Response(429)
        return httpx.Response(201, json={"_time": "now", "finding_id": identifier})

    mocker.patch.object(httpx.Client, "post", autospec=True, side_effect=create)
    mock_mailbox(context, mocker)
    return context


@pytest.mark.parametrize("manner", ["oldest first", "latest first"])
def test_failed_email_is_skipped_without_replaying_processed_mail(runtime, manner):
    context = runtime
    context.asset.ingest_manner = manner
    expected = expected_order(context)
    context.failed = expected[2]
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == expected[:4] + [expected[2]] * 2 + expected[4:]
    result = module.app.actions_manager.add_result.call_args.args[0]
    assert result.get_summary()["failed"] == 1
    assert not context.asset.ingest_state.in_transaction
    context.failed = None
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []
    assert not context.asset.ingest_state.in_transaction


def test_equal_timestamps_retain_previously_checkpointed_ids(runtime):
    context = runtime
    context.asset.ingest_manner = "oldest first"
    timestamp = context.rows["mail-1"]["receivedDateTime"]
    context.rows = {
        key: {**value, "receivedDateTime": timestamp}
        for key, value in context.rows.items()
    }
    expected = expected_order(context)
    context.failed = expected[2]
    assert module.on_es_poll(OnESPollParams())
    context.failed = None
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []


def make_asset():
    return module.Asset(
        login_email="test@example.com",
        key_json="{}",
        first_run_max_emails=50,
        max_containers=50,
    )


def expected_order(context):
    # Gmail selects the oldest tail when requested, retaining API order within it.
    return sorted(
        context.rows,
        key=lambda key: context.rows[key]["receivedDateTime"],
        reverse=True,
    )


def mock_mailbox(context, mocker):
    service = mocker.Mock()
    service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
        "labels": [{"name": "INBOX", "id": "INBOX"}]
    }

    def page(**kwargs):
        after = int(kwargs.get("q", "").removeprefix("after:") or 0)
        ids = [
            key
            for key in expected_order(context)
            if int(
                datetime.fromisoformat(
                    context.rows[key]["receivedDateTime"]
                ).timestamp()
            )
            > after
        ]
        start = int(kwargs.get("pageToken", "0"))
        size = min(3, kwargs.get("maxResults", 3))
        result = {"messages": [{"id": key} for key in ids[start : start + size]]}
        if start + size < len(ids):
            result["nextPageToken"] = str(start + size)
        return SimpleNamespace(execute=lambda: result)

    def get(**kwargs):
        identifier = kwargs["id"]
        row = context.rows[identifier]
        result = {
            "id": identifier,
            "internalDate": str(
                int(datetime.fromisoformat(row["receivedDateTime"]).timestamp() * 1000)
            ),
            "raw": base64.urlsafe_b64encode(raw_email(identifier)).decode(),
        }
        if identifier == getattr(context, "no_raw", None):
            result.pop("raw")
        return SimpleNamespace(execute=lambda: result)

    service.users.return_value.messages.return_value.list.side_effect = page
    service.users.return_value.messages.return_value.get.side_effect = get
    mocker.patch.object(
        module, "GoogleServiceBuilder"
    ).return_value.build_service.return_value = service


def test_latest_first_pending_window_survives_new_mail_arrival(runtime):
    context = runtime
    context.asset.ingest_manner = "latest first"
    expected = expected_order(context)
    context.failed = expected[2]
    assert module.on_es_poll(OnESPollParams())
    context.rows["mail-7"] = {
        "id": "mail-7",
        "subject": "mail-7",
        "receivedDateTime": (
            datetime(2026, 11, 13, tzinfo=UTC) + timedelta(minutes=7)
        ).isoformat(),
    }
    context.failed = None
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-7"]
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []


def test_latest_first_page_token_advances_past_failed_email(runtime):
    context = runtime
    context.asset.ingest_manner = "latest first"
    context.asset.first_run_max_emails = 2
    context.asset.max_containers = 2
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-6", "mail-5"]
    assert context.asset.ingest_state["page_token"] == "2"
    assert not context.asset.ingest_state.get("last_email_epoch")
    context.failed = "mail-4"
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-4", "mail-3", "mail-4", "mail-4"]
    assert context.asset.ingest_state["page_token"] == "4"
    context.failed = None
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-2", "mail-1"]
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []
    assert "page_token" not in context.asset.ingest_state
    assert context.asset.ingest_state["last_email_epoch"] == int(
        datetime.fromisoformat(context.rows["mail-6"]["receivedDateTime"]).timestamp()
    )


def test_missing_raw_email_does_not_strand_pending_ids(runtime):
    context = runtime
    context.asset.ingest_manner = "latest first"
    context.no_raw = "mail-1"
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == [f"mail-{i}" for i in range(6, 1, -1)]
    assert "es_pending_message_ids" not in context.asset.ingest_state
    assert "page_token" not in context.asset.ingest_state
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []


@pytest.mark.parametrize("manner", ["oldest first", "latest first"])
@pytest.mark.parametrize("bad_number", [1, 3, 6])
@pytest.mark.parametrize("kind", ["fetch", "base64", "parse", "build", "missing_raw"])
def test_individual_message_failure_advances_persisted_checkpoint(
    runtime, mocker, manner, bad_number, kind, capsys
):
    context = runtime
    context.asset.ingest_manner = manner
    bad_id = f"mail-{bad_number}"
    private_error = "private-message-body-never-log"
    if kind == "build":
        original = module._build_es_finding

        def build(email_obj):
            if email_obj.message_id == bad_id:
                raise ValueError(private_error)
            return original(email_obj)

        mocker.patch.object(module, "_build_es_finding", side_effect=build)
    elif kind == "parse":
        original = module.extract_email_data

        def parse(raw, *, email_id, **kwargs):
            if email_id == bad_id:
                raise ValueError(private_error)
            return original(raw, email_id=email_id, **kwargs)

        mocker.patch.object(module, "extract_email_data", side_effect=parse)
    else:
        service = module.GoogleServiceBuilder.return_value.build_service.return_value
        get = service.users.return_value.messages.return_value.get
        original = get.side_effect

        def fetch(**kwargs):
            if kind == "fetch" and kwargs["id"] == bad_id:
                raise RuntimeError(private_error)
            response = original(**kwargs).execute()
            if kwargs["id"] == bad_id:
                if kind == "missing_raw":
                    response.pop("raw")
                else:
                    response["raw"] = "a"
            return SimpleNamespace(execute=lambda: response)

        get.side_effect = fetch
    expected = [
        identifier for identifier in expected_order(context) if identifier != bad_id
    ]
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == expected
    logs = capsys.readouterr().out
    assert "Skipping" in logs
    assert private_error not in logs
    context.asset._ingest_state = AssetState(
        module.app.actions_manager, "ingest", "1", encrypted=False
    )
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []


@pytest.mark.parametrize("kind", ["fetch", "base64", "build"])
def test_all_failed_messages_do_not_replay(runtime, mocker, kind):
    context = runtime
    if kind == "build":
        mocker.patch.object(
            module, "_build_es_finding", side_effect=ValueError("Synthetic failure")
        )
    else:
        service = module.GoogleServiceBuilder.return_value.build_service.return_value
        get = service.users.return_value.messages.return_value.get
        original = get.side_effect

        def fetch(**kwargs):
            if kind == "fetch":
                raise RuntimeError("Synthetic failure")
            response = original(**kwargs).execute()
            response["raw"] = "a"
            return SimpleNamespace(execute=lambda: response)

        get.side_effect = fetch
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []
    assert set(context.asset.ingest_state["processed_message_ids"]) == set(context.rows)
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == []


def test_latest_first_continuation_advances_past_parse_failure(runtime):
    context = runtime
    context.asset.ingest_manner = "latest first"
    context.asset.first_run_max_emails = context.asset.max_containers = 2
    context.no_raw = "mail-5"
    for _ in range(4):
        assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-6", "mail-4", "mail-3", "mail-2", "mail-1"]
    assert not context.asset.ingest_state.get("page_token")


def test_mailbox_listing_failure_does_not_advance_checkpoint(runtime):
    context = runtime
    service = module.GoogleServiceBuilder.return_value.build_service.return_value
    service.users.return_value.messages.return_value.list.side_effect = RuntimeError(
        "Synthetic listing failure"
    )
    before = context.asset.ingest_state.get_all()
    assert not module.on_es_poll(OnESPollParams())
    assert context.asset.ingest_state.get_all() == before
    assert context.sent == []
