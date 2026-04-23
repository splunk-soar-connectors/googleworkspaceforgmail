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
"""Search emails action for Gmail connector."""

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

from google_service import GoogleServiceBuilder, GMAIL_READ_SCOPE

logger = getLogger()


class RunQueryParams(Params):
    """Parameters for run_query action."""

    email: str = Param(
        description="User's email address (mailbox to search)",
        primary=True,
        cef_types=["email"],
    )
    label: str | None = Param(
        description="Label/folder to search in",
        primary=True,
        default="INBOX",
        cef_types=["gmail label"],
    )
    subject: str | None = Param(
        description="Substring to search in email subject",
    )
    sender: str | None = Param(
        description="Sender email address to match",
        primary=True,
        cef_types=["email"],
    )
    body: str | None = Param(
        description="Substring to search in email body",
    )
    internet_message_id: str | None = Param(
        description="Internet Message ID to search for",
        primary=True,
        cef_types=["internet message id"],
    )
    query: str | None = Param(
        description="Gmail query string (overrides other filters if provided)",
    )
    max_results: float | None = Param(
        description="Maximum number of results to return",
        default=100.0,
    )
    page_token: str | None = Param(
        description="Token for pagination to get next page of results",
    )


class RunQueryOutput(ActionOutput):
    """Individual email result from search."""

    delivered_to: str = OutputField(cef_types=["email"])
    id: str = OutputField(cef_types=["gmail email id"], column_name="Email ID")
    from_: str = OutputField(
        cef_types=["email"],
        example_values=["user@example.com"],
        alias="from",
        column_name="From",
    )
    to: str = OutputField(cef_types=["email"], column_name="To")
    subject: str = OutputField(column_name="Subject")
    history_id: str = OutputField()
    internal_date: str = OutputField()
    label_ids: str = OutputField()
    message_id: str = OutputField(
        cef_types=["internet message id"], column_name="Internet Message ID"
    )
    size_estimate: float = OutputField()
    snippet: str = OutputField()
    thread_id: str = OutputField()


class RunQuerySummary(ActionOutput):
    """Summary for run_query action with pagination."""

    next_page_token: str = OutputField()
    total_messages_returned: int = OutputField()


def run_query(params: RunQueryParams, soar: SOARClient, asset) -> list[RunQueryOutput]:
    """
    Search emails in a user's mailbox.

    Constructs a Gmail query from provided filters and returns matching emails
    with pagination support.

    Args:
        params: Action parameters for search filters
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        List of matching email messages

    Raises:
        ActionFailure: If search fails
    """
    logger.progress(f"Searching emails in {params.email}...")

    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "gmail",
        "v1",
        [GMAIL_READ_SCOPE],
        delegated_user=params.email,
    )

    # Build query string
    query_parts = []

    if params.query:
        # If explicit query provided, use it and ignore other filters
        query_string = params.query
        logger.progress(f"Using provided query: {query_string}")
    else:
        # Build query from individual filters
        if params.label:
            query_parts.append(f"label:{params.label}")

        if params.subject:
            query_parts.append(f"subject:{params.subject}")

        if params.sender:
            query_parts.append(f"from:{params.sender}")

        if params.body:
            query_parts.append(f"{params.body}")

        if params.internet_message_id:
            query_parts.append(f"rfc822msgid:{params.internet_message_id}")

        query_string = " ".join(query_parts)

    logger.progress(f"Executing query: {query_string}")

    # Build request parameters
    max_results = int(params.max_results) if params.max_results else 100
    kwargs = {
        "userId": params.email,
        "q": query_string,
        "maxResults": max_results,
    }

    if params.page_token:
        kwargs["pageToken"] = params.page_token

    # Execute search
    try:
        response = service.users().messages().list(**kwargs).execute()
    except Exception as e:
        raise ActionFailure(f"Failed to search emails: {e}") from e

    messages = response.get("messages", [])
    logger.progress(f"Found {len(messages)} matching emails")

    # Add pagination info to summary
    if "nextPageToken" in response:
        soar.set_summary(
            RunQuerySummary(
                next_page_token=response["nextPageToken"],
                total_messages_returned=len(messages),
            )
        )
    else:
        soar.set_summary(
            RunQuerySummary(
                next_page_token="",
                total_messages_returned=len(messages),
            )
        )

    # Fetch full headers for each message
    results = []
    for msg_header in messages:
        msg_id = msg_header["id"]
        try:
            # Get full message details
            full_msg = (
                service.users()
                .messages()
                .get(
                    userId=params.email,
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=[
                        "Subject",
                        "From",
                        "To",
                        "Date",
                        "Message-ID",
                        "Delivered-To",
                    ],
                )
                .execute()
            )

            headers = {
                h["name"]: h["value"]
                for h in full_msg.get("payload", {}).get("headers", [])
            }

            results.append(
                RunQueryOutput(
                    delivered_to=headers.get("Delivered-To", ""),
                    from_=headers.get("From", ""),
                    history_id=full_msg.get("historyId", ""),
                    id=full_msg.get("id", ""),
                    internal_date=full_msg.get("internalDate", ""),
                    label_ids=", ".join(full_msg.get("labelIds", [])),
                    message_id=headers.get("Message-ID", ""),
                    size_estimate=float(full_msg.get("sizeEstimate", 0)),
                    snippet=full_msg.get("snippet", ""),
                    subject=headers.get("Subject", ""),
                    thread_id=full_msg.get("threadId", ""),
                    to=headers.get("To", ""),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to fetch details for message {msg_id}: {e}")
            continue

    soar.set_message(f"Total messages returned: {len(results)}")
    return results
