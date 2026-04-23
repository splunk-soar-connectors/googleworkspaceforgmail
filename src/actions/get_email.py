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
"""Retrieve email details action for Gmail connector."""

import base64

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

import email as email_module

from soar_sdk.extras.email import extract_email_data

from google_service import GoogleServiceBuilder, GMAIL_READ_SCOPE

logger = getLogger()


class GetEmailParams(Params):
    """Parameters for get_email action."""

    email: str = Param(
        description="User's email address",
        primary=True,
        cef_types=["email"],
    )
    internet_message_id: str = Param(
        description="Internet Message ID to retrieve",
        primary=True,
        cef_types=["internet message id"],
    )
    format: str = Param(
        description="Email format to retrieve",
        default="metadata",
        required=False,
        value_list=["metadata", "minimal", "raw"],
    )
    extract_attachments: bool = Param(
        description="Extract attachments to vault",
        default=False,
        required=False,
    )
    extract_nested: bool = Param(
        description="Extract attachments from nested emails",
        default=False,
        required=False,
    )
    download_email: bool = Param(
        description="Download raw email as EML file to vault",
        default=False,
        required=False,
    )


class HeaderOutput(ActionOutput):
    """Email header entry."""

    name: str = OutputField()
    value: str = OutputField()


class GetEmailOutput(ActionOutput):
    """Email details output."""

    subject: str = OutputField()
    from_: str = OutputField(
        cef_types=["email"],
        alias="from",
    )
    to: str = OutputField(cef_types=["email"])
    date: str = OutputField()
    message_id: str = OutputField(cef_types=["internet message id"])
    id: str = OutputField(cef_types=["gmail email id"])
    thread_id: str = OutputField()
    history_id: str = OutputField()
    internal_date: str = OutputField()
    label_ids: str = OutputField()
    size_estimate: float = OutputField()
    snippet: str = OutputField()
    parsed_plain_body: str = OutputField()
    parsed_html_body: str = OutputField()
    headers: list[HeaderOutput] = OutputField()
    urls: list[str] = OutputField()
    ips: list[str] = OutputField()
    domains: list[str] = OutputField()
    hashes: list[str] = OutputField()
    download_email_vault_id: str | None = OutputField(
        cef_types=["vault id"],
        example_values=["000094000006f00004cd60000b1f8e0000e5fa3e"],
    )


def get_email(params: GetEmailParams, soar: SOARClient, asset) -> GetEmailOutput:
    """
    Retrieve and parse email details.

    Fetches email from Gmail API, parses MIME structure, extracts IOCs and
    optionally downloads attachments and raw email to vault.

    Args:
        params: Action parameters
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        Parsed email with extracted data

    Raises:
        ActionFailure: If email retrieval fails
    """
    logger.progress(f"Retrieving email with message ID {params.internet_message_id}...")

    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "gmail",
        "v1",
        [GMAIL_READ_SCOPE],
        delegated_user=params.email,
    )

    # Build query for internet message ID
    query_string = f"rfc822msgid:{params.internet_message_id}"

    # Search for the email
    try:
        search_response = (
            service.users()
            .messages()
            .list(
                userId=params.email,
                q=query_string,
            )
            .execute()
        )
    except Exception as e:
        raise ActionFailure(f"Failed to search for email: {e}") from e

    messages = search_response.get("messages", [])
    if not messages:
        raise ActionFailure(
            f"Email with message ID {params.internet_message_id} not found"
        )

    # Get the first (and should be only) result
    message_id = messages[0]["id"]
    logger.progress(f"Found email with Gmail ID {message_id}")

    # Fetch message in the requested format
    try:
        full_message = (
            service.users()
            .messages()
            .get(
                userId=params.email,
                id=message_id,
                format=params.format,
            )
            .execute()
        )
    except Exception as e:
        raise ActionFailure(f"Failed to fetch email: {e}") from e

    # Parse body content — only available in raw format
    parsed_plain_body = ""
    parsed_html_body = ""
    headers_list = []
    urls: list[str] = []
    ips: list[str] = []
    domains: list[str] = []
    hashes: list[str] = []
    raw_email_b64 = full_message.get("raw", "")

    if params.format == "raw":
        if not raw_email_b64:
            raise ActionFailure("Failed to retrieve raw email content")

        logger.progress("Parsing email message...")
        raw_email_bytes = base64.urlsafe_b64decode(raw_email_b64.encode("utf-8"))
        msg = email_module.message_from_bytes(raw_email_bytes)
        rfc822_str = msg.as_string()

        parsed = extract_email_data(
            rfc822_str,
            email_id=message_id,
            include_attachment_content=params.extract_attachments,
        )
        logger.progress("Email parsed successfully")

        parsed_plain_body = parsed.body.plain_text or ""
        parsed_html_body = parsed.body.html or ""
        headers_list = [
            HeaderOutput(name=name, value=str(value))
            for name, value in parsed.headers.raw_headers.items()
        ]
        urls = parsed.urls or []

        if params.extract_attachments:
            container_id = soar.get_executing_container_id()
            vault = soar.vault
            for att in parsed.attachments:
                if att.content is None:
                    continue
                content = (
                    att.content
                    if isinstance(att.content, bytes)
                    else att.content.encode("utf-8")
                )
                try:
                    vault_id = vault.create_attachment(
                        container_id,
                        file_content=content,
                        file_name=att.filename,
                    )
                    soar.artifact.create(
                        {
                            "name": "Email Attachment Artifact",
                            "container_id": container_id,
                            "cef": {
                                "vaultId": vault_id,
                                "fileHash": vault_id,
                                "fileName": att.filename,
                            },
                            "run_automation": False,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to extract attachment {att.filename}: {e}")

                # Recurse into nested .eml/.msg attachments
                if params.extract_nested:
                    lower_name = (att.filename or "").lower()
                    if lower_name.endswith(".eml") or lower_name.endswith(".msg"):
                        try:
                            inner = extract_email_data(
                                att.content,
                                include_attachment_content=True,
                            )
                            for inner_att in inner.attachments:
                                if inner_att.content is None:
                                    continue
                                inner_content = (
                                    inner_att.content
                                    if isinstance(inner_att.content, bytes)
                                    else inner_att.content.encode("utf-8")
                                )
                                try:
                                    inner_vault_id = vault.create_attachment(
                                        container_id,
                                        file_content=inner_content,
                                        file_name=inner_att.filename,
                                    )
                                    soar.artifact.create(
                                        {
                                            "name": "Email Attachment Artifact",
                                            "container_id": container_id,
                                            "cef": {
                                                "vaultId": inner_vault_id,
                                                "fileHash": inner_vault_id,
                                                "fileName": inner_att.filename,
                                            },
                                            "run_automation": False,
                                        }
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to extract nested attachment {inner_att.filename}: {e}"
                                    )
                        except Exception as e:
                            logger.warning(
                                f"Failed to parse nested email {att.filename}: {e}"
                            )
    else:
        # For metadata/minimal, surface the headers Gmail returns directly
        headers_list = [
            HeaderOutput(name=h["name"], value=h["value"])
            for h in full_message.get("payload", {}).get("headers", [])
        ]

    # Handle email download to vault if requested (requires raw format)
    download_vault_id = None
    if params.download_email:
        if params.format == "raw" and raw_email_b64:
            logger.progress("Downloading raw email to vault...")
            try:
                vault = soar.vault
                eml_bytes = base64.urlsafe_b64decode(raw_email_b64)
                subject = next(
                    (h.value for h in headers_list if h.name.lower() == "subject"),
                    "email",
                )
                download_vault_id = vault.create_attachment(
                    soar.get_executing_container_id(),
                    file_content=eml_bytes,
                    file_name=f"{subject}.eml",
                )
                logger.progress(f"Email downloaded to vault: {download_vault_id}")
            except Exception as e:
                logger.warning(f"Failed to download email to vault: {e}")
        else:
            logger.warning(
                "download_email requires format='raw'; skipping vault download"
            )

    logger.progress("Building output...")
    soar.set_message("Total messages returned: 1")

    return GetEmailOutput(
        subject=next(
            (h.value for h in headers_list if h.name.lower() == "subject"), ""
        ),
        from_=next((h.value for h in headers_list if h.name.lower() == "from"), ""),
        to=next((h.value for h in headers_list if h.name.lower() == "to"), ""),
        date=next((h.value for h in headers_list if h.name.lower() == "date"), ""),
        message_id=next(
            (h.value for h in headers_list if h.name.lower() == "message-id"), ""
        ),
        id=message_id,
        thread_id=full_message.get("threadId", ""),
        history_id=full_message.get("historyId", ""),
        internal_date=full_message.get("internalDate", ""),
        label_ids=", ".join(full_message.get("labelIds", [])),
        size_estimate=float(full_message.get("sizeEstimate", 0)),
        snippet=full_message.get("snippet", ""),
        parsed_plain_body=parsed_plain_body,
        parsed_html_body=parsed_html_body,
        headers=headers_list,
        urls=urls,
        ips=ips,
        domains=domains,
        hashes=hashes,
        download_email_vault_id=download_vault_id,
    )


def render_get_email_view(output: list[GetEmailOutput]) -> dict:
    """
    View handler for get_email action.

    Formats the email output for display in the custom view template.

    Args:
        output: The GetEmailOutput from the get_email action

    Returns:
        Dictionary with emails list for template rendering
    """
    return {"emails": output}
