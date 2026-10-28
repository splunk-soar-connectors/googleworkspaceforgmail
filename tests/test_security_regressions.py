# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import base64
import email
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from soar_sdk.exceptions import ActionFailure
from soar_sdk.extras.email import extract_email_data
from soar_sdk.params import OnPollParams
from soar_sdk.views.template_renderer import JinjaTemplateRenderer

from src.app import Asset, on_poll
from src.actions.get_email import GetEmailParams, get_email


def _gmail_service(page_responses):
    service = MagicMock()
    users = service.users.return_value
    users.labels.return_value.list.return_value.execute.return_value = {
        "labels": [{"name": "INBOX", "id": "INBOX"}]
    }
    users.messages.return_value.list.return_value.execute.side_effect = page_responses
    return service


def _asset() -> Asset:
    return Asset(login_email="user@example.com", key_json="{}")


def test_poll_rejects_repeated_page_token():
    service = _gmail_service(
        [
            {"messages": [], "nextPageToken": "repeated"},
            {"messages": [], "nextPageToken": "repeated"},
        ]
    )

    with (
        patch("src.app.GoogleServiceBuilder") as builder,
        patch.object(Asset, "ingest_state", new_callable=PropertyMock, return_value={}),
    ):
        builder.return_value.build_service.return_value = service

        with pytest.raises(ActionFailure, match="repeated page token"):
            next(_asset().fetch_and_parse_emails(max_emails=10))


def test_poll_enforces_page_safety_limit():
    page_number = 0

    def next_page():
        nonlocal page_number
        page_number += 1
        return {"messages": [], "nextPageToken": f"page-{page_number}"}

    service = _gmail_service(next_page)

    with (
        patch("src.app.GoogleServiceBuilder") as builder,
        patch.object(Asset, "ingest_state", new_callable=PropertyMock, return_value={}),
        patch("src.app.MAX_POLL_PAGES", 2),
    ):
        builder.return_value.build_service.return_value = service

        with pytest.raises(ActionFailure, match="safety limit of 2 pages"):
            next(_asset().fetch_and_parse_emails(max_emails=10))

    assert page_number == 2


@pytest.mark.parametrize("ingest_manner", ["latest first", "oldest first"])
@pytest.mark.parametrize("raw_fields", [{}, {"raw": ""}], ids=["missing", "empty"])
def test_poll_unexpected_missing_raw_warns_and_continues(
    ingest_manner: str, raw_fields: dict
):
    # Synthetic API-contract violation: Gmail documents raw content for format=raw.
    state = {"last_email_epoch": 100}
    service = _gmail_service(
        [
            {
                "messages": [
                    {"id": "healthy-before"},
                    {"id": "unexpected-no-raw"},
                    {"id": "healthy-after"},
                ]
            }
        ]
    )
    raw = base64.urlsafe_b64encode(
        b"Subject: healthy message\r\nFrom: sender@example.com\r\n"
        b"To: recipient@example.com\r\n\r\nbody"
    ).decode()
    service.users.return_value.messages.return_value.get.return_value.execute.side_effect = [
        {"id": "healthy-before", "internalDate": "300000", "raw": raw},
        {"id": "unexpected-no-raw", "internalDate": "250000", **raw_fields},
        {"id": "healthy-after", "internalDate": "200000", "raw": raw},
    ]
    asset = Asset(
        login_email="user@example.com",
        key_json="{}",
        ingest_manner=ingest_manner,
        max_containers=3,
    )

    with (
        patch("src.app.GoogleServiceBuilder") as builder,
        patch.object(
            Asset, "ingest_state", new_callable=PropertyMock, return_value=state
        ),
        patch("src.app.logger.warning") as warning,
    ):
        builder.return_value.build_service.return_value = service
        results = list(
            on_poll.__wrapped__(OnPollParams(), MagicMock(), asset)  # type: ignore[attr-defined]
        )

    assert [result.source_data_identifier for result in results] == [
        "healthy-before",
        "healthy-after",
    ]
    warning.assert_called_once()
    assert "unexpected-no-raw" in warning.call_args.args[0]
    assert state["last_email_epoch"] == 300
    assert "page_token" not in state
    assert "latest_first_high_water" not in state
    assert state["processed_message_ids"] == ["healthy-before", "healthy-after"]


def test_get_email_widget_uses_jinja_json_for_context_values():
    template = (Path(__file__).parents[1] / "templates" / "get_email.html").read_text()

    assert "{{ email.to|tojson }}" in template
    assert "{{ email.from_|tojson }}" in template
    assert "{{ email.download_email_vault_id|tojson }}" in template
    assert "escapejs" not in template


def test_list_users_widget_renders_email_as_json_with_sdk_renderer():
    renderer = JinjaTemplateRenderer(str(Path(__file__).parents[1] / "templates"))
    rendered = renderer.render_template(
        "list_users.html",
        {
            "users": [
                {
                    "name": {"full_name": "Test Analyst"},
                    "primary_email": "alice'o@example.test",
                }
            ],
            "container": {"id": 1},
        },
    )

    assert '"value": "alice\\u0027o@example.test"' in rendered


def test_email_parser_extracts_mixed_case_and_internationalized_urls():
    raw_email = (
        b"Subject: links\r\nContent-Type: text/plain; charset=utf-8\r\n"
        b"Content-Transfer-Encoding: 8bit\r\n\r\nHTTPS://EVIL-UPPER.TEST/path "
        + "hTtPs://пример.рф/путь".encode()
    )
    parsed = extract_email_data(email.message_from_bytes(raw_email).as_string())

    assert "HTTPS://EVIL-UPPER.TEST/path" in parsed.urls
    assert "hTtPs://пример.рф/путь" in parsed.urls


def test_get_email_passes_raw_bytes_directly_to_bounded_extractor():
    raw_email = b"Subject: test\r\nFrom: sender@example.com\r\n\r\nbody"
    service = MagicMock()
    users = service.users.return_value
    users.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "message-id"}]
    }
    users.messages.return_value.get.return_value.execute.return_value = {
        "id": "message-id",
        "threadId": "thread-id",
        "raw": base64.urlsafe_b64encode(raw_email).decode(),
    }
    parsed = SimpleNamespace(
        body=SimpleNamespace(plain_text="body", html=None),
        headers=SimpleNamespace(
            raw_headers={
                "Subject": "test",
                "From": "sender@example.com",
            }
        ),
        urls=[],
        attachments=[],
    )
    extractor = MagicMock(return_value=parsed)

    with (
        patch("src.actions.get_email.GoogleServiceBuilder") as builder,
        patch("src.actions.get_email.extract_email_data", new=extractor),
    ):
        builder.return_value.build_service.return_value = service
        get_email(
            GetEmailParams(
                email="recipient@example.com",
                internet_message_id="internet-message-id",
                format="raw",
            ),
            MagicMock(),
            SimpleNamespace(key_json="{}"),
        )

    assert extractor.call_args.args[0] == raw_email
