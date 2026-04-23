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
"""
Google API service creation and management.

This module handles authentication with Google's service account and creation
of Gmail and Admin SDK services with domain-wide delegation.
"""

import json

from google.oauth2 import service_account
from googleapiclient import discovery
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

logger = getLogger()

# OAuth scopes for Gmail operations
GMAIL_READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
GMAIL_SEND_SCOPE = "https://mail.google.com/"
GMAIL_SETTINGS_SCOPE = "https://www.googleapis.com/auth/gmail.settings.sharing"
ADMIN_DIRECTORY_SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"
ADMIN_DIRECTORY_ALIAS_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.user.alias"
)


class GoogleServiceBuilder:
    """Helper class for creating authenticated Google API services."""

    def __init__(self, key_json: str):
        """
        Initialize with a service account JSON key.

        Args:
            key_json: JSON string containing service account credentials

        Raises:
            ActionFailure: If the key JSON is invalid
        """
        try:
            self.key_dict = json.loads(key_json)
        except json.JSONDecodeError as e:
            raise ActionFailure(f"Invalid service account JSON: {e}") from e

    def build_service(
        self,
        api_name: str,
        api_version: str,
        scopes: list[str],
        delegated_user: str | None = None,
    ):
        """
        Build an authenticated Google API service.

        Args:
            api_name: Name of the API (e.g., 'gmail', 'admin')
            api_version: Version of the API (e.g., 'v1', 'directory_v1')
            scopes: List of OAuth scopes to request
            delegated_user: Email address for domain-wide delegation

        Returns:
            Authenticated Google API service resource

        Raises:
            ActionFailure: If credential creation or service building fails
        """
        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.key_dict, scopes=scopes
            )
            logger.debug(f"Created credentials for scopes: {scopes}")
        except Exception as e:
            raise ActionFailure(
                f"Failed to create credentials from service account JSON: {e}"
            ) from e

        # Apply domain-wide delegation if a user is specified
        if delegated_user:
            try:
                credentials = credentials.with_subject(delegated_user)
                logger.debug(
                    f"Applied domain-wide delegation for user: {delegated_user}"
                )
            except Exception as e:
                raise ActionFailure(
                    f"Failed to create delegated credentials for user {delegated_user}: {e}"
                ) from e

        try:
            service = discovery.build(api_name, api_version, credentials=credentials)
            logger.debug(f"Successfully built {api_name} {api_version} service")
            return service
        except Exception as e:
            raise ActionFailure(
                f"Failed to build {api_name} {api_version} service: {e}"
            ) from e
