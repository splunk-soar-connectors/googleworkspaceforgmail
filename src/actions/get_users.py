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
"""List users action for Gmail connector."""

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

from google_service import GoogleServiceBuilder, ADMIN_DIRECTORY_SCOPE

logger = getLogger()


class ListUsersParams(Params):
    """Parameters for get_users action."""

    max_items: float | None = Param(
        description="Maximum number of users to retrieve (default 500, max 500)",
        default=500.0,
    )
    page_token: str | None = Param(
        description="Token to retrieve the next page of results",
        primary=True,
        cef_types=["gsuite page token"],
    )


class EmailOutput(ActionOutput):
    """Email address entry."""

    address: str = OutputField(cef_types=["email"])
    primary: bool = OutputField(example_values=[True, False])
    type: str = OutputField(example_values=["work"])


class NameOutput(ActionOutput):
    """User name information."""

    family_name: str = OutputField()
    full_name: str = OutputField()
    given_name: str = OutputField()


class GetUsersOutput(ActionOutput):
    """Single user entry in list."""

    agreed_to_terms: bool = OutputField(example_values=[True, False])
    archived: bool = OutputField(example_values=[False])
    change_password_at_next_login: bool = OutputField(example_values=[False])
    creation_time: str = OutputField()
    customer_id: str = OutputField()
    emails: list[EmailOutput] = OutputField()
    etag: str = OutputField()
    id: str = OutputField()
    include_in_global_address_list: bool = OutputField(example_values=[True])
    is_admin: bool = OutputField(example_values=[False])
    is_mailbox_setup: bool = OutputField(example_values=[True])
    kind: str = OutputField()
    last_login_time: str = OutputField()
    name: NameOutput = OutputField()
    primary_email: str = OutputField(cef_types=["email"])
    suspended: bool = OutputField(example_values=[False])
    suspension_reason: str = OutputField(example_values=["ADMIN"])


class GetUsersSummary(ActionOutput):
    """Summary for get_users action with pagination."""

    next_page_token: str = OutputField(cef_types=["gsuite page token"])
    total_users_returned: int = OutputField()


def list_users(
    params: ListUsersParams, soar: SOARClient, asset
) -> list[GetUsersOutput]:
    """
    List users in the Google Workspace domain.

    Uses the Admin SDK to retrieve users with pagination support.

    Args:
        params: Action parameters with optional max_items and page_token
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        List of user profiles

    Raises:
        ActionFailure: If user listing fails
    """
    raw_max = params.max_items if params.max_items is not None else 500.0
    if not float(raw_max).is_integer():
        raise ActionFailure(
            "Please provide a valid non-zero positive integer value in the 'max_items' parameter"
        )
    max_items = int(raw_max)
    if max_items <= 0:
        raise ActionFailure(
            "Please provide a valid non-zero positive integer value in the 'max_items' parameter"
        )
    if max_items > 500:
        raise ActionFailure(
            "Please provide a value less than or equal to 500 in the 'max_items' parameter"
        )

    logger.progress(f"Retrieving up to {max_items} users from domain...")

    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "admin",
        "directory_v1",
        [ADMIN_DIRECTORY_SCOPE],
        delegated_user=asset.login_email,
    )

    domain = asset.login_email.split("@")[1]

    # Build query parameters
    kwargs = {
        "domain": domain,
        "maxResults": max_items,
        "orderBy": "email",
        "sortOrder": "ASCENDING",
    }

    if params.page_token:
        kwargs["pageToken"] = params.page_token

    # Execute the request
    try:
        response = service.users().list(**kwargs).execute()
    except Exception as e:
        raise ActionFailure(f"Failed to retrieve users: {e}") from e

    users = response.get("users", [])
    logger.progress(f"Retrieved {len(users)} users")

    # Add next page token to summary if available
    if "nextPageToken" in response:
        soar.set_summary(
            GetUsersSummary(
                next_page_token=response["nextPageToken"],
                total_users_returned=len(users),
            )
        )

    # Convert results to output objects
    results = []
    for user in users:
        # Process emails
        emails = []
        for email_entry in user.get("emails", []):
            emails.append(
                EmailOutput(
                    address=email_entry.get("address", ""),
                    primary=email_entry.get("primary", False),
                    type=email_entry.get("type", ""),
                )
            )

        # Process name
        name_data = user.get("name", {})
        name = NameOutput(
            family_name=name_data.get("familyName", ""),
            full_name=name_data.get("fullName", ""),
            given_name=name_data.get("givenName", ""),
        )

        results.append(
            GetUsersOutput(
                agreed_to_terms=user.get("agreedToTerms", False),
                archived=user.get("archived", False),
                change_password_at_next_login=user.get(
                    "changePasswordAtNextLogin", False
                ),
                creation_time=user.get("creationTime", ""),
                customer_id=user.get("customerId", ""),
                emails=emails,
                etag=user.get("etag", ""),
                id=user.get("id", ""),
                include_in_global_address_list=user.get(
                    "includeInGlobalAddressList", False
                ),
                is_admin=user.get("isAdmin", False),
                is_mailbox_setup=user.get("isMailboxSetup", False),
                kind=user.get("kind", ""),
                last_login_time=user.get("lastLoginTime", ""),
                name=name,
                primary_email=user.get("primaryEmail", ""),
                suspended=user.get("suspended", False),
                suspension_reason=user.get("suspensionReason", ""),
            )
        )

    return results


def render_list_users_view(output: list[GetUsersOutput]) -> dict:
    """
    View handler for list_users action.

    Formats the user list output for display in the custom view template.

    Args:
        output: The list of GetUsersOutput from the list_users action

    Returns:
        Dictionary with users list for template rendering
    """
    return {"users": output}
