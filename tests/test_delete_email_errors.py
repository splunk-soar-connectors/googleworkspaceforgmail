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

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from soar_sdk.exceptions import ActionFailure

from src.actions.delete_email import DeleteEmailParams, delete_email


def _http_error(status: int, message: str) -> HttpError:
    response = SimpleNamespace(status=status, reason=message)
    return HttpError(response, f'{{"error": {{"message": "{message}"}}}}'.encode())


def _run_delete(error: Exception):
    service = MagicMock()
    service.users.return_value.messages.return_value.delete.return_value.execute.side_effect = error
    soar = MagicMock()
    params = DeleteEmailParams(id="message-id", email="user@example.com")

    with patch("src.actions.delete_email.GoogleServiceBuilder") as builder:
        builder.return_value.build_service.return_value = service
        result = delete_email(params, soar, SimpleNamespace(key_json="{}"))

    return result


def test_delete_email_ignores_only_http_404():
    result = _run_delete(_http_error(404, "not found"))

    assert result.deleted_emails == []
    assert result.ignored_ids == ["message-id"]


@pytest.mark.parametrize("message", ["not found", "identifier 404 failed"])
def test_delete_email_rejects_non_404_even_when_message_looks_not_found(message):
    with pytest.raises(ActionFailure, match="Failed to delete email"):
        _run_delete(_http_error(403, message))
