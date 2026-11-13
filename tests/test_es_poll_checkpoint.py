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
    if not hasattr(app.soar_client, "_get_es_finding_context"):
        pytest.skip("Requires the AR-2061 SDK wheel; see TESTING_ES_POLL.md")
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
def test_failed_batch_replays_without_repeating_successful_batches(runtime, manner):
    context = runtime
    context.asset.ingest_manner = manner
    expected = expected_order(context)
    context.failed = expected[2]
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == expected[:4]
    result = module.app.actions_manager.add_result.call_args.args[0]
    assert result.get_summary()["failed"] == 1
    assert not context.asset.ingest_state.in_transaction
    context.failed = None
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == expected[2:]
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
    assert context.sent == expected[2:]
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
    assert context.sent == expected[2:]
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-7"]


def test_latest_first_page_token_replays_failed_window(runtime):
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
    assert context.sent == ["mail-4", "mail-3"]
    assert context.asset.ingest_state["page_token"] == "2"
    context.failed = None
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-4", "mail-3"]
    context.sent.clear()
    assert module.on_es_poll(OnESPollParams())
    assert context.sent == ["mail-2", "mail-1"]
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
