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
"""Untrash emails action for Gmail connector."""

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

from google_service import GoogleServiceBuilder, GMAIL_SEND_SCOPE

logger = getLogger()


class UntrashEmailParams(Params):
    """Parameters for untrash_email action."""

    id: str = Param(
        description="Email message IDs to untrash (comma-separated)",
        primary=True,
        cef_types=["gmail email id"],
        allow_list=True,
        column_name="Email ID",
    )
    email: str = Param(
        description="Email address of mailbox owner",
        primary=True,
        cef_types=["email"],
        column_name="Email",
    )


class UntrashEmailSummary(ActionOutput):
    """Summary of untrash results."""

    untrashed_emails: list[str] = OutputField(example_values=["email_id_1", "email_id_2"])
    ignored_ids: list[str] = OutputField(example_values=["invalid_id"])


def untrash_email(
    params: UntrashEmailParams, soar: SOARClient, asset
) -> UntrashEmailSummary:
    """
    Restore emails from trash in a user's mailbox (idempotent).

    Removes one or more emails from the Trash label by their message IDs. If a
    message ID doesn't exist, it is treated as successful and added to ignored_ids.

    Args:
        params: Action parameters with email and message IDs
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        Summary of untrashed and ignored email IDs

    Raises:
        ActionFailure: If no valid email IDs are provided, or if any untrash
            operation fails for a reason other than the message not existing (404)
    """
    logger.progress(f"Untrashing emails from {params.email}...")

    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "gmail",
        "v1",
        [GMAIL_SEND_SCOPE],
        delegated_user=params.email,
    )

    email_ids = [
        message_id.strip() for message_id in params.id.split(",") if message_id.strip()
    ]

    if not email_ids:
        raise ActionFailure("No valid email IDs provided")

    logger.progress(f"Processing {len(email_ids)} emails...")

    untrashed_ids = []
    ignored_ids = []

    for email_id in email_ids:
        try:
            service.users().messages().untrash(
                userId=params.email, id=email_id
            ).execute()
            untrashed_ids.append(email_id)
            logger.progress(f"Untrashed email {email_id}")
        except Exception as e:
            error_str = str(e).lower()
            if (
                "404" in error_str
                or "not found" in error_str
                or "invalid id value" in error_str
            ):
                logger.progress(f"Email {email_id} not found or invalid ID (ignored)")
                ignored_ids.append(email_id)
            else:
                raise ActionFailure(f"Failed to untrash email {email_id}: {e}") from e

    logger.progress(
        f"Successfully untrashed {len(untrashed_ids)} emails, {len(ignored_ids)} ignored"
    )

    summary = UntrashEmailSummary(
        untrashed_emails=untrashed_ids,
        ignored_ids=ignored_ids,
    )
    soar.set_summary(summary)
    return summary
