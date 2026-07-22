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
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from soar_sdk.exceptions import ActionFailure

from src.app import Asset


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


def test_get_email_widget_escapes_javascript_context_values():
    template = (Path(__file__).parents[1] / "templates" / "get_email.html").read_text()

    assert "{{ email.to|escapejs }}" in template
    assert "{{ email.from_|escapejs }}" in template
    assert "{{ email.download_email_vault_id|escapejs }}" in template
