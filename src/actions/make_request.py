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

import json

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger
from soar_sdk.params import MakeRequestParams, Param

from ..app import Asset, app


logger = getLogger()

DEFAULT_REQUEST_TIMEOUT = 30
GMAIL_API_BASE_URL = "https://gmail.googleapis.com"
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailMakeRequestParams(MakeRequestParams):
    endpoint: str = Param(
        description=(
            "Gmail API endpoint to call, appended to the API base URL. "
            "Example: '/gmail/v1/users/me/profile'. "
            "Note: this action is authorized with the gmail.readonly scope only — "
            "write or modify endpoints will require additional domain-wide delegation."
        ),
        required=True,
    )
    verify_ssl: bool = Param(
        description="Whether to verify the SSL certificate.",
        required=False,
        default=True,
    )


class GmailMakeRequestOutput(ActionOutput):
    status_code: int = OutputField(example_values=[200])
    response_body: str = OutputField(
        example_values=['{"emailAddress": "user@example.com"}']
    )

    @classmethod
    def from_response(cls, response: requests.Response) -> "GmailMakeRequestOutput":
        return cls(status_code=response.status_code, response_body=response.text)


@app.make_request()
def http_action(params: GmailMakeRequestParams, asset: Asset) -> GmailMakeRequestOutput:
    if params.endpoint.startswith(("http://", "https://")):
        raise ActionFailure(
            f"Invalid endpoint: {params.endpoint}. Do not include the base URL — "
            "it is derived from the Gmail API configuration."
        )

    try:
        key_dict = json.loads(asset.key_json)
    except json.JSONDecodeError as e:
        raise ActionFailure(f"Invalid service account JSON: {e}") from e

    try:
        credentials = service_account.Credentials.from_service_account_info(
            key_dict, scopes=DEFAULT_SCOPES
        ).with_subject(asset.login_email)
        credentials.refresh(GoogleAuthRequest())
    except Exception as e:
        raise ActionFailure(f"Failed to obtain access token: {e}") from e

    endpoint = (
        params.endpoint if params.endpoint.startswith("/") else f"/{params.endpoint}"
    )
    url = f"{GMAIL_API_BASE_URL}{endpoint}"

    headers: dict = {
        "Authorization": f"Bearer {credentials.token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if params.headers:
        try:
            headers.update(json.loads(params.headers))
        except (json.JSONDecodeError, TypeError) as e:
            raise ActionFailure(f"Invalid JSON headers: {params.headers}") from e

    query_params = None
    if params.query_parameters:
        try:
            query_params = json.loads(params.query_parameters)
        except (json.JSONDecodeError, TypeError):
            query_string = params.query_parameters.lstrip("?")
            url = f"{url}?{query_string}" if "?" not in url else f"{url}&{query_string}"

    body = None
    json_body = None
    if params.body:
        content_type = headers.get("Content-Type", "").lower()
        if "json" in content_type:
            try:
                json_body = json.loads(params.body)
            except (json.JSONDecodeError, TypeError) as e:
                raise ActionFailure(f"Invalid JSON body: {params.body}") from e
        else:
            body = params.body

    timeout = params.timeout or DEFAULT_REQUEST_TIMEOUT

    try:
        response = requests.request(
            method=params.http_method,
            url=url,
            headers=headers,
            params=query_params,
            data=body,
            json=json_body,
            timeout=timeout,
            verify=params.verify_ssl,
        )
    except Exception as e:
        raise ActionFailure(f"Request failed: {e}") from e

    return GmailMakeRequestOutput.from_response(response)
