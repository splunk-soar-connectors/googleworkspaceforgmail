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
"""Delete emails action for Gmail connector."""

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

from google_service import GoogleServiceBuilder, GMAIL_SEND_SCOPE

logger = getLogger()


class DeleteEmailParams(Params):
    """Parameters for delete_email action."""

    id: str = Param(
        description="Email message IDs to delete (comma-separated)",
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


class DeleteEmailSummary(ActionOutput):
    """Summary of deletion results."""

    deleted_emails: list[str] = OutputField(example_values=["email_id_1", "email_id_2"])
    ignored_ids: list[str] = OutputField(example_values=["invalid_id"])


def delete_email(
    params: DeleteEmailParams, soar: SOARClient, asset
) -> DeleteEmailSummary:
    """
    Delete emails from a user's mailbox (idempotent).

    Deletes one or more emails by their message IDs. If a message ID doesn't exist
    (likely already deleted), it's treated as successful and added to ignored_ids.

    Args:
        params: Action parameters with email and message IDs
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        Summary of deleted and ignored/already-deleted email IDs

    Raises:
        ActionFailure: If no valid email IDs are provided, or if any deletion
            fails for a reason other than the message already being deleted (404)
    """
    logger.progress(f"Deleting emails from {params.email}...")

    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "gmail",
        "v1",
        [GMAIL_SEND_SCOPE],
        delegated_user=params.email,
    )

    # Parse email IDs
    email_ids = [
        message_id.strip() for message_id in params.id.split(",") if message_id.strip()
    ]

    if not email_ids:
        raise ActionFailure("No valid email IDs provided")

    logger.progress(f"Processing {len(email_ids)} emails...")

    deleted_ids = []
    ignored_ids = []

    # Delete each message, treating 404s as already deleted
    for email_id in email_ids:
        try:
            service.users().messages().delete(
                userId=params.email, id=email_id
            ).execute()
            deleted_ids.append(email_id)
            logger.progress(f"Deleted email {email_id}")
        except Exception as e:
            error_str = str(e).lower()
            # Treat 404 (not found) and 400 "invalid id value" as ignorable
            if (
                "404" in error_str
                or "not found" in error_str
                or "invalid id value" in error_str
            ):
                logger.progress(f"Email {email_id} not found or invalid ID (ignored)")
                ignored_ids.append(email_id)
            else:
                raise ActionFailure(f"Failed to delete email {email_id}: {e}") from e

    logger.progress(
        f"Successfully deleted {len(deleted_ids)} emails, {len(ignored_ids)} ignored/already-deleted"
    )

    summary = DeleteEmailSummary(
        deleted_emails=deleted_ids,
        ignored_ids=ignored_ids,
    )
    soar.set_summary(summary)
    return summary
