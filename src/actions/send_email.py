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
"""Send email action for Gmail connector."""

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json

from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.params import Param, Params
from soar_sdk.logging import getLogger

from google_service import (
    GoogleServiceBuilder,
    GMAIL_SEND_SCOPE,
    GMAIL_SETTINGS_SCOPE,
    ADMIN_DIRECTORY_ALIAS_SCOPE,
)

logger = getLogger()

# 25MB attachment size limit (from GSGMAIL_ATTACHMENTS_CUTOFF_SIZE)
ATTACHMENTS_CUTOFF_SIZE = 26214400  # 25 * 1024 * 1024


class SendEmailParams(Params):
    """Parameters for send_email action."""

    from_: str | None = Param(
        description="User's email address",
        primary=True,
        cef_types=["email"],
        alias="from",
        required=False,
    )
    to: str = Param(
        description="Recipients",
        primary=True,
        cef_types=["email"],
        allow_list=True,
    )
    subject: str = Param(
        description="Email subject",
        primary=True,
    )
    body: str = Param(
        description="Email body (HTML)",
        primary=True,
    )
    cc: str | None = Param(
        description="CC recipients",
        cef_types=["email"],
        allow_list=True,
    )
    bcc: str | None = Param(
        description="BCC recipients",
        cef_types=["email"],
        allow_list=True,
    )
    reply_to: str | None = Param(
        description="Reply-To address",
        cef_types=["email"],
        allow_list=True,
    )
    headers: str | None = Param(
        description="Additional headers as JSON",
    )
    attachments: str | None = Param(
        description="Vault IDs to attach (comma-separated)",
    )
    alias_email: str | None = Param(
        description="Send from alias email address",
        cef_types=["email"],
    )
    alias_name: str | None = Param(
        description="Alias name for send-as",
    )


class SendEmailOutput(ActionOutput):
    """Send email output."""

    id: str = OutputField(cef_types=["gmail email id"])
    thread_id: str = OutputField()
    label_ids: str = OutputField()
    from_email: str = OutputField(cef_types=["email"])


def _create_send_as_alias(
    admin_service, gmail_service, user_email: str, alias_email: str, alias_name: str
) -> None:
    """
    Create alias and send-as setting if they don't exist.

    Args:
        admin_service: Admin Directory service
        gmail_service: Gmail service
        user_email: User's primary email
        alias_email: Alias email address
        alias_name: Display name for alias

    Raises:
        ActionFailure: If alias creation fails
    """
    # Step 1: Create alias in Admin SDK
    logger.progress(f"Creating alias {alias_email}...")
    alias_body = {"alias": alias_email}

    try:
        admin_service.users().aliases().insert(
            userKey=user_email, body=alias_body
        ).execute()
        logger.progress(f"Created alias {alias_email}")
    except Exception as e:
        error_str = str(e)
        # Check if alias already exists (409 conflict)
        if "409" in error_str and "already exists" in error_str.lower():
            logger.progress(f"Alias {alias_email} already exists")
        else:
            raise ActionFailure(f"Failed to create alias: {e}") from e

    # Step 2: Create send-as setting in Gmail API
    logger.progress(f"Creating send-as setting for {alias_email}...")
    send_as = {
        "sendAsEmail": alias_email,
        "replyToAddress": alias_email,
        "treatAsAlias": True,
        "isPrimary": False,
    }

    if alias_name:
        send_as["displayName"] = alias_name

    try:
        gmail_service.users().settings().sendAs().create(
            userId="me", body=send_as
        ).execute()
        logger.progress(f"Successfully created send-as setting for {alias_email}")
    except Exception as e:
        error_str = str(e)
        # Send-as might already exist, which is fine
        if "409" in error_str or "already exists" in error_str.lower():
            logger.progress(f"Send-as setting for {alias_email} already exists")
        else:
            raise ActionFailure(f"Failed to create send-as setting: {e}") from e


def send_email(params: SendEmailParams, soar: SOARClient, asset) -> SendEmailOutput:
    """
    Send email via Gmail.

    Constructs MIME message with attachments, respecting 25MB size limit.
    Optionally creates send-as alias before sending.

    Args:
        params: Action parameters
        soar: SOAR client instance
        asset: Asset configuration object

    Returns:
        Send result with message ID and thread ID

    Raises:
        ActionFailure: If email send fails
    """
    from_email = params.from_
    logger.progress("Building email message...")

    # Create send-as alias if specified
    if params.alias_email:
        logger.progress(f"Setting up send-as alias {params.alias_email}...")

        # Build Admin service for alias creation
        builder = GoogleServiceBuilder(asset.key_json)
        admin_service = builder.build_service(
            "admin",
            "directory_v1",
            [ADMIN_DIRECTORY_ALIAS_SCOPE],
            delegated_user=asset.login_email,
        )

        # Build Gmail service for send-as settings
        gmail_settings_service = builder.build_service(
            "gmail",
            "v1",
            [GMAIL_SETTINGS_SCOPE],
            delegated_user=asset.login_email,
        )

        # Create both alias and send-as setting
        _create_send_as_alias(
            admin_service,
            gmail_settings_service,
            asset.login_email,
            params.alias_email,
            params.alias_name or params.alias_email,
        )

        from_email = params.alias_email

    if from_email is None:
        from_email = asset.login_email

    # Build Gmail service for sending
    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "gmail",
        "v1",
        [GMAIL_SEND_SCOPE],
        delegated_user=asset.login_email,
    )

    # Create MIME message
    message = MIMEMultipart("mixed")
    message["From"] = from_email
    message["To"] = params.to
    message["Subject"] = params.subject

    if params.cc:
        message["Cc"] = params.cc
    if params.bcc:
        message["Bcc"] = params.bcc
    if params.reply_to:
        message["Reply-To"] = params.reply_to

    # Parse additional headers if provided
    if params.headers:
        try:
            extra_headers = json.loads(params.headers)
            for key, value in extra_headers.items():
                message[key] = value
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid headers JSON: {e}")

    # Add body (HTML)
    msg_alternative = MIMEMultipart("alternative")
    message.attach(msg_alternative)
    msg_alternative.attach(MIMEText(params.body, "html"))

    # Add attachments
    current_size = len(message.as_bytes())
    logger.progress(
        f"Base message size: {current_size / 1024 / 1024:.2f}MB, "
        f"attachment limit: {ATTACHMENTS_CUTOFF_SIZE / 1024 / 1024:.1f}MB"
    )

    if params.attachments:
        vault = soar.vault
        vault_ids = [v.strip() for v in params.attachments.split(",") if v.strip()]

        for vault_id in vault_ids:
            try:
                # Get attachment metadata
                attachment_data = vault.get_attachment_metadata(vault_id)
                attachment_size = int(attachment_data.get("size", 0))
                file_name = attachment_data.get("name", "attachment")

                if current_size + attachment_size > ATTACHMENTS_CUTOFF_SIZE:
                    logger.debug(
                        f"Total attachment size reached max capacity. "
                        f"No longer adding attachments after vault id {vault_id}"
                    )
                    break

                logger.progress(f"Adding attachment: {file_name}")

                # Get attachment content
                attachment_content = vault.get_attachment(vault_id)

                # Add to message
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition", f"attachment; filename= {file_name}"
                )
                message.attach(part)

                current_size += attachment_size
                logger.progress(
                    f"Added attachment {file_name} "
                    f"(total size: {current_size / 1024 / 1024:.2f}MB)"
                )

            except Exception as e:
                logger.warning(f"Failed to add attachment {vault_id}: {e}")
                continue

    logger.progress("Sending email...")

    # Encode message
    message_bytes = message.as_bytes()
    message_b64 = base64.urlsafe_b64encode(message_bytes).decode()

    # Send message
    send_message = {"raw": message_b64}
    try:
        result = (
            service.users()
            .messages()
            .send(
                userId=from_email,
                body=send_message,
            )
            .execute()
        )
    except Exception as e:
        raise ActionFailure(f"Failed to send email: {e}") from e

    logger.progress(f"Email sent successfully. Message ID: {result.get('id')}")

    return SendEmailOutput(
        id=result.get("id", ""),
        thread_id=result.get("threadId", ""),
        label_ids=", ".join(result.get("labelIds", [])),
        from_email=from_email,
    )
