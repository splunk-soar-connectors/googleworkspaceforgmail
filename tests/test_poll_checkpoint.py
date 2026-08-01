# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

from soar_sdk.params import OnPollParams

from src.app import Asset, on_poll


def _service(message_id: str, timestamp: int, next_page_token=None):
    service = MagicMock()
    users = service.users.return_value
    users.labels.return_value.list.return_value.execute.return_value = {
        "labels": [{"name": "INBOX", "id": "INBOX"}]
    }
    response = {"messages": [{"id": message_id}]}
    if next_page_token:
        response["nextPageToken"] = next_page_token
    users.messages.return_value.list.return_value.execute.return_value = response
    users.messages.return_value.get.return_value.execute.return_value = {
        "id": message_id,
        "internalDate": str(timestamp * 1000),
        "raw": base64.urlsafe_b64encode(b"Subject: test\r\n\r\nbody").decode(),
    }
    return service


def _parsed_email():
    return SimpleNamespace(
        body=SimpleNamespace(plain_text="body", html=None),
        headers=SimpleNamespace(
            from_address="sender@example.com",
            to="recipient@example.com",
            raw_headers={},
            subject="test",
        ),
        urls=[],
        attachments=[],
    )


def test_latest_first_checkpoint_waits_for_continuation_to_finish():
    state = {"last_email_epoch": 100}
    first_page = _service("newest", 300, "next-page")
    final_page = _service("older", 200)
    asset = Asset(
        login_email="user@example.com",
        key_json="{}",
        ingest_manner="latest first",
        max_containers=1,
    )

    with (
        patch("src.app.GoogleServiceBuilder") as builder,
        patch("src.app.extract_email_data", return_value=_parsed_email()),
        patch.object(
            Asset, "ingest_state", new_callable=PropertyMock, return_value=state
        ),
    ):
        builder.return_value.build_service.side_effect = [first_page, final_page]

        first_results = list(
            on_poll.__wrapped__(OnPollParams(), MagicMock(), asset)  # type: ignore[attr-defined]
        )
        assert len(first_results) == 1
        assert state["page_token"] == "next-page"
        assert state["latest_first_high_water"] == 300
        assert state["last_email_epoch"] == 100

        second_results = list(
            on_poll.__wrapped__(OnPollParams(), MagicMock(), asset)  # type: ignore[attr-defined]
        )

    assert len(second_results) == 1
    assert state["last_email_epoch"] == 300
    assert "page_token" not in state
    assert "latest_first_high_water" not in state
    second_list_call = (
        final_page.users.return_value.messages.return_value.list.call_args
    )
    assert second_list_call.kwargs["pageToken"] == "next-page"
    assert second_list_call.kwargs["maxResults"] == 1
