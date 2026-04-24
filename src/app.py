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
from dataclasses import dataclass, asdict
import re
import base64
import email
from email.utils import parseaddr, parsedate_to_datetime
from datetime import UTC, datetime
from enum import StrEnum
from collections.abc import Generator, Iterator
from urllib.parse import urlparse
from soar_sdk.abstract import SOARClient
from soar_sdk.app import App
from soar_sdk.models import Finding
from soar_sdk.params import OnESPollParams, OnPollParams
from soar_sdk.asset import BaseAsset, AssetField, FieldCategory
from soar_sdk.logging import getLogger
from soar_sdk.models.container import Container
from soar_sdk.models.artifact import Artifact
from soar_sdk.exceptions import ActionFailure
from soar_sdk.extras.email.utils import is_ip

from soar_sdk.models.finding import (
    FindingAttachment,
    FindingEmail,
    FindingEmailAttachment,
    FindingEmailReporter,
)

from email.mime.text import MIMEText

from google_service import (
    GoogleServiceBuilder,
    GMAIL_READ_SCOPE,
    GMAIL_SEND_SCOPE,
    ADMIN_DIRECTORY_SCOPE,
)
from soar_sdk.extras.email import extract_email_data, RFC5322EmailData

from .actions.get_user import render_get_user_view
from .actions.get_users import render_list_users_view
from .actions.get_email import render_get_email_view
from .actions.run_query import RunQuerySummary
from .actions.delete_email import DeleteEmailSummary

logger = getLogger()


class IngestManner(StrEnum):
    OLDEST_FIRST: str = "oldest first"
    LATEST_FIRST: str = "latest first"


@dataclass
class ExtractedEmail:
    message_id: str
    parsed: RFC5322EmailData
    full_message: dict
    extracted_ips: list[str]
    extracted_urls: list[str]
    extracted_domains: list[str]
    extracted_hashes: list[str]


class Asset(BaseAsset):
    login_email: str = AssetField(required=True, description="Login (Admin) email")
    key_json: str = AssetField(
        required=True,
        description="Contents of Service Account JSON file",
        sensitive=True,
    )
    label: str = AssetField(
        required=False, description="Mailbox Label (folder) to be polled", default=""
    )
    ingest_manner: str = AssetField(
        required=False,
        description="How to ingest",
        default="oldest first",
        value_list=["oldest first", "latest first"],
    )
    first_run_max_emails: int = AssetField(
        required=False,
        description="Maximum emails for scheduled polling first time",
        default=1000,
    )
    max_containers: int = AssetField(
        required=False,
        description="Maximum emails for scheduled polling",
        default=100,
    )
    data_type: str = AssetField(
        required=False,
        description="Ingestion data type when polling",
        default="utf-8",
        value_list=["utf-8", "ascii"],
    )
    forwarding_address: str = AssetField(
        required=False, description="Address to forward polled emails to"
    )
    auto_reply: str = AssetField(
        required=False, description="Auto reply to emails with a set body"
    )
    extract_attachments: bool = AssetField(
        required=False,
        description="Extract Attachments",
        default=False,
        category=FieldCategory.INGEST,
    )
    default_format: str = AssetField(
        required=False,
        description="Format used for the get email action",
        default="metadata",
        value_list=["metadata", "minimal", "raw"],
    )
    extract_urls: bool = AssetField(
        required=False,
        description="Extract URLs",
        default=False,
        category=FieldCategory.INGEST,
    )
    extract_ips: bool = AssetField(
        required=False,
        description="Extract IPs",
        default=False,
        category=FieldCategory.INGEST,
    )
    extract_domains: bool = AssetField(
        required=False,
        description="Extract Domain Names",
        default=False,
        category=FieldCategory.INGEST,
    )
    extract_hashes: bool = AssetField(
        required=False,
        description="Extract Hashes",
        default=False,
        category=FieldCategory.INGEST,
    )
    download_eml_attachments: bool = AssetField(
        required=False,
        description="Download EML attachments",
        default=False,
        category=FieldCategory.INGEST,
    )
    extract_eml: bool = AssetField(
        required=False,
        description="Extract root (primary) email as Vault",
        default=True,
        category=FieldCategory.INGEST,
    )

    def _extract_iocs(
        self, parsed: RFC5322EmailData, force_extract_iocs: bool
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        body_text = ""
        if body_plain := parsed.body.plain_text:
            body_text += body_plain
        if body_html := parsed.body.html:
            body_text += body_html

        extracted_ips = []
        if self.extract_ips or force_extract_iocs:
            ip_regex = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            for ip in re.findall(ip_regex, body_text):
                if is_ip(ip):
                    extracted_ips.append(ip)

        extracted_urls = []
        if self.extract_urls or force_extract_iocs:
            extracted_urls = parsed.urls

        extracted_domains = set()
        if self.extract_domains or force_extract_iocs:
            for url in parsed.urls:
                try:
                    domain = urlparse(url).hostname
                    if domain and not is_ip(domain):
                        extracted_domains.add(domain)
                except ValueError as e:
                    logger.debug(f"Failed to extract domain from URL {url}: {e}")
        extracted_domains = list(extracted_domains)

        extracted_hashes = []
        if self.extract_hashes or force_extract_iocs:
            hash_regex = r"\b[0-9a-fA-F]{32}\b|\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{64}\b"
            extracted_hashes = list(set(re.findall(hash_regex, body_text)))

        return extracted_ips, extracted_urls, extracted_domains, extracted_hashes

    def _build_gmail_send_service(self):
        return GoogleServiceBuilder(self.key_json).build_service(
            "gmail", "v1", [GMAIL_SEND_SCOPE], delegated_user=self.login_email
        )

    def _auto_reply(self, message: RFC5322EmailData) -> None:
        reply = MIMEText(self.auto_reply, "plain")
        reply["From"] = self.login_email
        reply["To"] = message.headers.from_address
        subject = message.headers.subject or ""
        reply["Subject"] = (
            subject if subject.lower().startswith("re:") else f"Re: {subject}"
        )
        if message.headers.message_id:
            reply["In-Reply-To"] = message.headers.message_id
            reply["References"] = message.headers.message_id

        raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
        service = self._build_gmail_send_service()
        service.users().messages().send(
            userId=self.login_email, body={"raw": raw}
        ).execute()

    def _forward_email(self, message: RFC5322EmailData) -> None:
        original_body = message.body.plain_text or message.body.html or ""
        subject = message.headers.subject or ""
        forward_body = (
            f"---------- Forwarded message ----------\n"
            f"From: {message.headers.from_address or ''}\n"
            f"Date: {message.headers.date or ''}\n"
            f"Subject: {subject}\n"
            f"To: {message.headers.to or ''}\n\n"
            f"{original_body}"
        )

        fwd = MIMEText(forward_body, "plain")
        fwd["From"] = self.login_email
        fwd["To"] = self.forwarding_address
        fwd["Subject"] = (
            subject if subject.lower().startswith("fwd:") else f"Fwd: {subject}"
        )

        raw = base64.urlsafe_b64encode(fwd.as_bytes()).decode()
        service = self._build_gmail_send_service()
        service.users().messages().send(
            userId=self.login_email, body={"raw": raw}
        ).execute()

    def fetch_and_parse_emails(
        self, max_emails: int, force_extract_iocs: bool = False
    ) -> Iterator[ExtractedEmail]:
        """
        Poll Gmail and yield parsed email objects with metadata and (optionally) IOCs.

        Args:
            max_emails: How many emails to retrieve
            force_extract_iocs: Ignore the asset settings and always extract IPs/domains/hashes
        """
        logger.progress("Starting Gmail poll...")

        # Ingest state / checkpoints
        state = self.ingest_state
        last_email_epoch = state.get("last_email_epoch", 0)
        label_cache = state.setdefault("label_cache", {})
        processed_message_ids = state.get("processed_message_ids", [])

        # Get Gmail client
        service = GoogleServiceBuilder(self.key_json).build_service(
            "gmail", "v1", [GMAIL_READ_SCOPE], delegated_user=self.login_email
        )

        # Look up label ID
        if not (label_name := self.label):
            label_name = "INBOX"
        if not (label_id := label_cache.get(label_name)):
            logger.progress(f"Looking up label ID for {label_name}...")
            labels = service.users().labels().list(userId=self.login_email).execute()
            for label in labels.get("labels", []):
                if label["name"].lower() == label_name.lower():
                    label_id = label["id"]
                    label_cache[label_name] = label_id
                    break
            else:
                raise ActionFailure(f"Label {label_name} not found")

        query_parts = []
        if last_email_epoch:
            query_parts.append(f"after:{int(last_email_epoch)}")
        query = " ".join(query_parts)
        logger.progress(f"Searching for emails with query: {query}...")

        messages = []
        kwargs = {"userId": self.login_email, "q": query, "labelIds": [label_id]}
        if page_token := state.get("page_token"):
            kwargs["pageToken"] = page_token
        ingest_manner = IngestManner(self.ingest_manner)

        while True:
            search_response = service.users().messages().list(**kwargs).execute()
            page_messages = search_response.get("messages", [])
            messages.extend(page_messages)
            logger.progress(
                f"Fetched {len(page_messages)} messages, total so far: {len(messages)}"
            )

            if not (next_page_token := search_response.get("nextPageToken")):
                break
            if (
                ingest_manner == IngestManner.LATEST_FIRST
                and len(messages) >= max_emails
            ):
                break
            # Keep only a rolling window to avoid unbounded memory growth;
            # we'll take the tail (oldest = last returned) after pagination.
            if (
                ingest_manner == IngestManner.OLDEST_FIRST
                and len(messages) > max_emails
            ):
                messages = messages[-max_emails:]
            kwargs["pageToken"] = next_page_token
        logger.progress(f"Found {len(messages)} total messages")

        if ingest_manner == IngestManner.OLDEST_FIRST:
            messages = messages[-max_emails:]
        else:
            messages = messages[:max_emails]

        for message_info in messages:
            message_id = message_info["id"]
            if message_id in processed_message_ids:
                logger.debug(f"Skipping already-processed message {message_id}")
                continue
            logger.debug(f"Fetching message {message_id}")
            full_message = (
                service.users()
                .messages()
                .get(userId=self.login_email, id=message_id, format="raw")
                .execute()
            )
            if not (raw_b64 := full_message.get("raw")):
                logger.warning(f"Message {message_id} has no raw content")
                continue
            raw_email_bytes = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
            msg = email.message_from_bytes(raw_email_bytes)
            rfc822_str = msg.as_string()
            parsed = extract_email_data(
                rfc822_str,
                email_id=message_id,
                include_attachment_content=self.extract_attachments
                or force_extract_iocs,
            )

            extracted_ips, extracted_urls, extracted_domains, extracted_hashes = (
                self._extract_iocs(parsed, force_extract_iocs)
            )

            if self.auto_reply:
                self._auto_reply(parsed)
            if self.forwarding_address:
                self._forward_email(parsed)

            yield ExtractedEmail(
                message_id,
                parsed,
                full_message,
                extracted_ips,
                extracted_urls,
                extracted_domains,
                extracted_hashes,
            )


def _extract_address(header_value: str | None) -> str | None:
    """Extract the bare email address from an RFC 5322 From header."""
    if not header_value:
        return None
    _, addr = parseaddr(header_value)
    return addr or None


def _format_date_fallback(date_header: str | None) -> str:
    """Format an RFC 5322 date header as 'YYYY-MM-DD HH:mm UTC', falling back to now."""
    if date_header:
        try:
            dt = parsedate_to_datetime(date_header)
            return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            pass
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _extract_inner_email(
    parsed: RFC5322EmailData,
) -> tuple[RFC5322EmailData, int] | None:
    """Return the first .eml/.msg attachment parsed as an email, plus its index.

    Returns None if no such attachment exists or all candidates fail to parse.
    """
    for i, att in enumerate(parsed.attachments):
        if att.content is None:
            continue
        lower_name = (att.filename or "").lower()
        if not (lower_name.endswith(".eml") or lower_name.endswith(".msg")):
            continue
        try:
            inner = extract_email_data(att.content, include_attachment_content=False)
            return inner, i
        except Exception:
            logger.warning(f"Failed to parse inner email attachment: {att.filename}")
    return None


app = App(
    name="G Suite for GMail",
    app_type="email",
    logo="logo_google.svg",
    logo_dark="logo_google_dark.svg",
    product_vendor="Google",
    product_name="GMail",
    publisher="Splunk",
    appid="9c73f233-2c4a-406a-855e-41d8d2497d0e",
    fips_compliant=True,
    asset_cls=Asset,
)


@app.on_poll()
def on_poll(
    params: OnPollParams,
    soar: SOARClient,
    asset: Asset,
) -> Iterator[Container | Artifact]:
    """
    Poll for new emails from Gmail and yield Container objects.
    """
    if not params.is_manual_poll() or not (max_emails := params.container_count):
        if not asset.ingest_state.get("last_email_epoch"):
            max_emails = asset.first_run_max_emails
        else:
            max_emails = asset.max_containers

    logger.debug(f"Polling for max {max_emails} containers")

    ingest_state = asset.ingest_state
    processed_message_ids = ingest_state.get("processed_message_ids", [])
    container_count = 0
    max_email_epoch = 0

    for email_obj in asset.fetch_and_parse_emails(max_emails=max_emails):
        artifacts = [
            {
                "run_automation": False,
                "name": "Email Artifact",
                "cef": {
                    "fromEmail": email_obj.parsed.headers.from_address or "",
                    "toEmail": email_obj.parsed.headers.to or "",
                    "emailHeaders": {
                        key.lower(): value
                        for key, value in email_obj.parsed.headers.raw_headers.items()
                    },
                    "emailId": email_obj.message_id,
                },
                "cef_types": {
                    "fromEmail": ["email"],
                    "toEmail": ["email"],
                    "emailId": ["gmail email id"],
                },
            },
        ]

        for ip in email_obj.extracted_ips:
            artifacts.append(
                {
                    "run_automation": False,
                    "name": "IP Artifact",
                    "cef": {"sourceAddress": ip},
                    "cef_types": {"sourceAddress": ["ip"]},
                }
            )

        for url in email_obj.extracted_urls:
            artifacts.append(
                {
                    "run_automation": False,
                    "name": "URL Artifact",
                    "cef": {"requestURL": url},
                    "cef_types": {"requestURL": ["url"]},
                }
            )

        for domain in email_obj.extracted_domains:
            artifacts.append(
                {
                    "run_automation": False,
                    "name": "Domain Artifact",
                    "cef": {"destinationDnsDomain": domain},
                    "cef_types": {"destinationDnsDomain": ["domain"]},
                }
            )

        for hash_val in email_obj.extracted_hashes:
            artifacts.append(
                {
                    "run_automation": False,
                    "name": "Hash Artifact",
                    "cef": {"fileHash": hash_val},
                    "cef_types": {"fileHash": ["hash"]},
                }
            )

        if artifacts:
            artifacts[-1]["run_automation"] = True

        subject = email_obj.parsed.headers.subject or "(No Subject)"
        from_addr = email_obj.parsed.headers.from_address or "(Unknown)"

        yield Container(
            source_data_identifier=email_obj.message_id,
            name=f"Email: {subject}",
            description=f"From: {from_addr}",
            artifacts=artifacts,
        )

        processed_message_ids.append(email_obj.message_id)
        if len(processed_message_ids) > 1000:
            processed_message_ids = processed_message_ids[-1000:]
        internal_date_ms = int(email_obj.full_message.get("internalDate", "0"))
        max_email_epoch = max(max_email_epoch, internal_date_ms // 1000)
        container_count += 1

    ingest_state["processed_message_ids"] = processed_message_ids
    if max_email_epoch:
        ingest_state["last_email_epoch"] = max_email_epoch
    ingest_state.pop("page_token", None)
    logger.progress(f"Poll complete. Created {container_count} containers.")


@app.on_es_poll()
def on_es_poll(
    params: OnESPollParams, soar: SOARClient, asset: Asset
) -> Generator[Finding, int | None]:
    """
    Poll for new emails and yield Finding objects for ES ingestion.
    """
    if not params.is_manual_poll() or not (max_emails := params.container_count):
        if not asset.ingest_state.get("last_email_epoch"):
            max_emails = asset.first_run_max_emails
        else:
            max_emails = asset.max_containers

    ingest_state = asset.ingest_state
    processed_message_ids = ingest_state.get("processed_message_ids", [])
    findings_count = 0
    max_email_epoch = 0

    for email_obj in asset.fetch_and_parse_emails(
        max_emails=max_emails, force_extract_iocs=True
    ):
        parsed = email_obj.parsed
        inner_result = _extract_inner_email(parsed)

        # Build finding title
        sender = (
            _extract_address(parsed.headers.from_address)
            or parsed.headers.from_address
            or "Unknown sender"
        )
        if inner_result is not None:
            inner_email, inner_att_index = inner_result
            original_sender = (
                _extract_address(inner_email.headers.from_address)
                or inner_email.headers.from_address
                or "Unknown sender"
            )
            inner_subject = inner_email.headers.subject
            if inner_subject:
                title = (
                    f"{sender} reported email from {original_sender} - {inner_subject}"
                )
            else:
                date_str = _format_date_fallback(inner_email.headers.date)
                title = f"{sender} reported email from {original_sender} - No subject ({date_str})"
        else:
            outer_subject = parsed.headers.subject
            if outer_subject:
                title = f"{sender} reported email - {outer_subject}"
            else:
                date_str = _format_date_fallback(parsed.headers.date)
                title = f"{sender} reported email - No subject ({date_str})"
        if len(title) > 100:
            title = title[:97] + "..."

        # Build attachments list; insert inner EML right after the raw outer email
        attachments = [
            FindingAttachment(
                file_name=f"email_{email_obj.message_id}.eml",
                data=parsed.raw_email.encode("utf-8"),
                is_raw_email=True,
            ),
        ]
        email_attachments = []
        inner_att_finding = None

        for idx, att in enumerate(parsed.attachments):
            finding_att = None
            if att.content is not None:
                data = (
                    att.content
                    if isinstance(att.content, bytes)
                    else att.content.encode("utf-8")
                )
                finding_att = FindingAttachment(
                    file_name=att.filename,
                    data=data,
                    is_raw_email=False,
                )
            email_attachments.append(
                FindingEmailAttachment(
                    filename=att.filename,
                    filesize=att.size,
                )
            )
            if (
                inner_result is not None
                and idx == inner_att_index
                and finding_att is not None
            ):
                inner_att_finding = finding_att
            elif finding_att is not None:
                attachments.append(finding_att)

        if inner_att_finding is not None:
            attachments.insert(1, inner_att_finding)

        # Build FindingEmail; use inner email data and populate reporter when forwarded
        if inner_result is not None:
            inner_email_attachments = [
                FindingEmailAttachment(
                    filename=att.filename,
                    filesize=att.size,
                )
                for att in inner_email.attachments
            ]
            reporter = FindingEmailReporter(
                from_=sender,
                to=parsed.headers.to,
                cc=parsed.headers.cc,
                bcc=parsed.headers.bcc,
                subject=parsed.headers.subject,
                message_id=parsed.headers.message_id,
                id=email_obj.message_id,
                body=(parsed.body.plain_text or parsed.body.html or None),
                date=parsed.headers.date,
            )
            finding_email = FindingEmail(
                headers=asdict(inner_email.headers),
                body=(inner_email.body.plain_text or inner_email.body.html or None),
                urls=inner_email.urls,
                attachments=inner_email_attachments,
                reporter=reporter,
            )
        else:
            finding_email = FindingEmail(
                headers=asdict(parsed.headers),
                body=(parsed.body.plain_text or parsed.body.html or None),
                urls=parsed.urls,
                attachments=email_attachments,
            )

        yield Finding(
            rule_title=title,
            attachments=attachments,
            email=finding_email,
        )

        processed_message_ids.append(email_obj.message_id)
        if len(processed_message_ids) > 1000:
            processed_message_ids = processed_message_ids[-1000:]
        internal_date_ms = int(email_obj.full_message.get("internalDate", "0"))
        max_email_epoch = max(max_email_epoch, internal_date_ms // 1000)
        findings_count += 1

    ingest_state["processed_message_ids"] = processed_message_ids
    if max_email_epoch:
        ingest_state["last_email_epoch"] = max_email_epoch
    ingest_state.pop("page_token", None)
    logger.progress(f"ES Poll complete. Created {findings_count} findings.")


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """
    Test connectivity to Google Workspace.

    Verifies that the service account credentials are valid and can access
    the configured domain.
    """
    logger.progress("Testing service account credentials...")

    # Build the service
    builder = GoogleServiceBuilder(asset.key_json)
    service = builder.build_service(
        "admin",
        "directory_v1",
        [ADMIN_DIRECTORY_SCOPE],
        delegated_user=asset.login_email,
    )

    logger.progress("Retrieving domain users to verify domain access...")

    # Test by listing a single user to verify domain access
    try:
        service.users().list(
            domain=asset.login_email.split("@")[1], maxResults=1
        ).execute()
        logger.progress("Test connectivity passed")
    except Exception as e:
        raise ActionFailure(f"Test connectivity failed: {e}") from e


# Register all other actions from their modules
app.register_action(
    "actions.get_user.get_user",
    view_handler=render_get_user_view,
    view_template="get_user.html",
)
app.register_action(
    "actions.get_users.list_users",
    view_handler=render_list_users_view,
    view_template="list_users.html",
)
app.register_action(
    "actions.run_query.run_query", render_as="table", summary_type=RunQuerySummary
)
app.register_action(
    "actions.delete_email.delete_email",
    render_as="table",
    summary_type=DeleteEmailSummary,
)
app.register_action(
    "actions.get_email.get_email",
    view_handler=render_get_email_view,
    view_template="get_email.html",
)
app.register_action("actions.send_email.send_email", render_as="table")


if __name__ == "__main__":
    app.cli()
