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
"""Get user profile action for Gmail connector."""

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

from google_service import GoogleServiceBuilder, GMAIL_READ_SCOPE

logger = getLogger()


class GetUserParams(Params):
    """Parameters for get_user action."""

    email: str = Param(
        description="User's Email address",
        primary=True,
        cef_types=["email"],
    )


class GetUserOutput(ActionOutput):
    """Output for get_user action."""

    email_address: str = OutputField(
        cef_types=["email"],
        example_values=["user@example.com"],
    )
    messages_total: float = OutputField(example_values=[1234])
    threads_total: float = OutputField(example_values=[567])
    history_id: str = OutputField(example_values=["987654321"])


def get_user(params: GetUserParams, soar: SOARClient, asset) -> GetUserOutput:
    """
    Retrieve user profile information.

    Uses the Gmail API to get user profile metadata including message and
    thread counts.

    Args:
        params: Action parameters containing email address
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        User profile information

    Raises:
        ActionFailure: If user retrieval fails
    """
    logger.progress(f"Retrieving user profile for {params.email}")

    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "gmail",
        "v1",
        [GMAIL_READ_SCOPE],
        delegated_user=params.email,
    )

    # Get user profile
    try:
        user_profile = service.users().getProfile(userId="me").execute()
        logger.progress("User profile retrieved successfully")
        return GetUserOutput(
            email_address=user_profile.get("emailAddress", ""),
            messages_total=float(user_profile.get("messagesTotal", 0)),
            threads_total=float(user_profile.get("threadsTotal", 0)),
            history_id=user_profile.get("historyId", ""),
        )
    except Exception as e:
        raise ActionFailure(f"Failed to retrieve user: {e}") from e


def render_get_user_view(output: list[GetUserOutput]) -> dict:
    """
    View handler for get_user action.

    Formats the user profile output for display in the custom view template.

    Args:
        output: The GetUserOutput from the get_user action

    Returns:
        Dictionary with users list for template rendering
    """
    return {"users": output}
