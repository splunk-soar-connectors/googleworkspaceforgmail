# Copyright (c) 2026 Splunk Inc.
"""Safe setup diagnostics for direct ES polling."""

import re

from google.auth.exceptions import DefaultCredentialsError, MalformedError, RefreshError
from soar_sdk.exceptions import ActionFailure


def _setup_reason(error: Exception) -> tuple[str, int | None] | None:
    """Inspect bounded causes and fixed protocol codes; never return their text."""
    seen = set()
    for _ in range(8):
        if id(error) in seen:
            break
        seen.add(id(error))
        # ActionFailure.__str__ adds a presentation prefix. Parse only the
        # original message for fixed codes, never copy that message to output.
        message = error.message if isinstance(error, ActionFailure) else str(error)
        status = next(
            (
                value
                for value in (
                    getattr(error, "status_code", None),
                    getattr(getattr(error, "response", None), "status_code", None),
                    getattr(getattr(error, "resp", None), "status", None),
                )
                if type(value) is int and 100 <= value <= 599
            ),
            None,
        )
        if status is None:
            match = re.match(
                r"(?:API Error |Error |Empty response with status |Call failed with HTTP Code: )([1-5][0-9]{2})(?::|\.|$)",
                message,
            )
            if match:
                status = int(match[1])
        if status in (401, 403):
            return "authentication", status
        if status == 404:
            return "mailbox", status
        # Fixed EWS SOAP and OAuth error codes, not arbitrary message matching.
        if re.match(
            r"API failed\. Status code: (ErrorAccessDenied|ErrorInvalidClientAccessToken|ErrorInvalidCredentials)\.",
            message,
        ):
            return "authentication", None
        if re.match(
            r"API failed\. Status code: (ErrorFolderNotFound|ErrorNonExistentMailbox|ErrorMailboxStoreUnavailable)\.",
            message,
        ):
            return "mailbox", None
        if re.match(
            r"(?:invalid_client|invalid_grant|unauthorized_client|invalid_scope|access_denied)(?::|$)",
            message,
        ):
            return "authentication", None
        if isinstance(error, DefaultCredentialsError | MalformedError) or (
            isinstance(error, RefreshError) and not error.retryable
        ):
            return "authentication", None
        if isinstance(error, ActionFailure) and message.startswith(
            (
                "Invalid service account JSON:",
                "Failed to create credentials from service account JSON:",
                "Failed to create delegated credentials for user ",
            )
        ):
            return "authentication", None
        cause = error.__cause__
        if cause is None:
            break
        error = cause
    return None
