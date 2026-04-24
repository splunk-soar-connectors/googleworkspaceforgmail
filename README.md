# G Suite for GMail

Publisher: Splunk <br>
Connector Version: 3.0.1 <br>
Product Vendor: Google <br>
Product Name: GMail <br>
Minimum Product Version: 7.0.0

Integrates with G Suite for various investigative and containment actions

### Configuration variables

This table lists the configuration variables required to operate G Suite for GMail. These variables are specified when configuring a GMail asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**login_email** | required | string | Login (Admin) email |
**key_json** | required | password | Contents of Service Account JSON file |
**label** | optional | string | Mailbox Label (folder) to be polled |
**ingest_manner** | optional | string | How to ingest |
**first_run_max_emails** | optional | numeric | Maximum emails for scheduled polling first time |
**max_containers** | optional | numeric | Maximum emails for scheduled polling |
**data_type** | optional | string | Ingestion data type when polling |
**forwarding_address** | optional | string | Address to forward polled emails to |
**auto_reply** | optional | string | Auto reply to emails with a set body |
**extract_attachments** | optional | boolean | Extract Attachments |
**default_format** | optional | string | Format used for the get email action |
**extract_urls** | optional | boolean | Extract URLs |
**extract_ips** | optional | boolean | Extract IPs |
**extract_domains** | optional | boolean | Extract Domain Names |
**extract_hashes** | optional | boolean | Extract Hashes |
**download_eml_attachments** | optional | boolean | Download EML attachments |
**extract_eml** | optional | boolean | Extract root (primary) email as Vault |

### Supported Actions

[on poll](#action-on-poll) - Poll for new emails from Gmail and yield Container objects. <br>
[on es poll](#action-on-es-poll) - Poll for new emails and yield Finding objects for ES ingestion. <br>
[test connectivity](#action-test-connectivity) - Test connectivity to Google Workspace.

Verifies that the service account credentials are valid and can access
the configured domain. <br>
[get user](#action-get-user) - Retrieve user profile information.

Uses the Gmail API to get user profile metadata including message and
thread counts.

Args:
params: Action parameters containing email address
soar: SOAR client instance
asset: Asset configuration object

Returns:
User profile information

Raises:
ActionFailure: If user retrieval fails <br>
[list users](#action-list-users) - List users in the Google Workspace domain.

Uses the Admin SDK to retrieve users with pagination support.

Args:
params: Action parameters with optional max_items and page_token
soar: SOAR client instance
asset: Asset configuration object

Returns:
List of user profiles

Raises:
ActionFailure: If user listing fails <br>
[run query](#action-run-query) - Search emails in a user's mailbox.

Constructs a Gmail query from provided filters and returns matching emails
with pagination support.

Args:
params: Action parameters for search filters
soar: SOAR client instance
asset: Asset configuration object

Returns:
List of matching email messages

Raises:
ActionFailure: If search fails <br>
[delete email](#action-delete-email) - Delete emails from a user's mailbox (idempotent).

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
fails for a reason other than the message already being deleted (404) <br>
[get email](#action-get-email) - Retrieve and parse email details.

Fetches email from Gmail API, parses MIME structure, extracts IOCs and
optionally downloads attachments and raw email to vault.

Args:
params: Action parameters
soar: SOAR client instance
asset: Asset configuration object

Returns:
Parsed email with extracted data

Raises:
ActionFailure: If email retrieval fails <br>
[send email](#action-send-email) - Send email via Gmail.

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

## action: 'on poll'

Poll for new emails from Gmail and yield Container objects.

Type: **ingest** <br>
Read only: **True**

Callback action for the on_poll ingest functionality

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Start of time range, in epoch time (milliseconds). | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds). | numeric | |
**container_count** | optional | Maximum number of container records to query for. | numeric | |
**artifact_count** | optional | Maximum number of artifact records to query for. | numeric | |
**container_id** | optional | Comma-separated list of container IDs to limit the ingestion to. | string | |

#### Action Output

No Output

## action: 'on es poll'

Poll for new emails and yield Finding objects for ES ingestion.

Type: **ingest** <br>
Read only: **True**

Callback action for the on_es_poll ingest functionality

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Start of time range, in epoch time (milliseconds). | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds). | numeric | |
**container_count** | optional | Maximum number of findings to query for. | numeric | |

#### Action Output

No Output

## action: 'test connectivity'

Test connectivity to Google Workspace.

Verifies that the service account credentials are valid and can access
the configured domain.

Type: **test** <br>
Read only: **True**

Basic test for app.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user'

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

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | User's Email address | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.email | string | `email` | |
action_result.data.\*.email_address | string | `email` | user@example.com |
action_result.data.\*.messages_total | numeric | | 1234 |
action_result.data.\*.threads_total | numeric | | 567 |
action_result.data.\*.history_id | string | | 987654321 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list users'

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

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_items** | optional | Maximum number of users to retrieve (default 500, max 500) | numeric | |
**page_token** | optional | Token to retrieve the next page of results | string | `gsuite page token` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.max_items | numeric | | |
action_result.parameter.page_token | string | `gsuite page token` | |
action_result.data.\*.agreed_to_terms | boolean | | True False |
action_result.data.\*.archived | boolean | | True False |
action_result.data.\*.change_password_at_next_login | boolean | | True False |
action_result.data.\*.creation_time | string | | |
action_result.data.\*.customer_id | string | | |
action_result.data.\*.emails.\*.address | string | `email` | |
action_result.data.\*.emails.\*.primary | boolean | | True False |
action_result.data.\*.emails.\*.type | string | | work |
action_result.data.\*.etag | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.include_in_global_address_list | boolean | | True False |
action_result.data.\*.is_admin | boolean | | True False |
action_result.data.\*.is_mailbox_setup | boolean | | True False |
action_result.data.\*.kind | string | | |
action_result.data.\*.last_login_time | string | | |
action_result.data.\*.name.family_name | string | | |
action_result.data.\*.name.full_name | string | | |
action_result.data.\*.name.given_name | string | | |
action_result.data.\*.primary_email | string | `email` | |
action_result.data.\*.suspended | boolean | | True False |
action_result.data.\*.suspension_reason | string | | ADMIN |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

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

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | User's email address (mailbox to search) | string | `email` |
**label** | optional | Label/folder to search in | string | `gmail label` |
**subject** | optional | Substring to search in email subject | string | |
**sender** | optional | Sender email address to match | string | `email` |
**body** | optional | Substring to search in email body | string | |
**internet_message_id** | optional | Internet Message ID to search for | string | `internet message id` |
**query** | optional | Gmail query string (overrides other filters if provided) | string | |
**max_results** | optional | Maximum number of results to return | numeric | |
**page_token** | optional | Token for pagination to get next page of results | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.email | string | `email` | |
action_result.parameter.label | string | `gmail label` | |
action_result.parameter.subject | string | | |
action_result.parameter.sender | string | `email` | |
action_result.parameter.body | string | | |
action_result.parameter.internet_message_id | string | `internet message id` | |
action_result.parameter.query | string | | |
action_result.parameter.max_results | numeric | | |
action_result.parameter.page_token | string | | |
action_result.data.\*.delivered_to | string | `email` | |
action_result.data.\*.id | string | `gmail email id` | |
action_result.data.\*.from | string | `email` | user@example.com |
action_result.data.\*.to | string | `email` | |
action_result.data.\*.subject | string | | |
action_result.data.\*.history_id | string | | |
action_result.data.\*.internal_date | string | | |
action_result.data.\*.label_ids | string | | |
action_result.data.\*.message_id | string | `internet message id` | |
action_result.data.\*.size_estimate | numeric | | |
action_result.data.\*.snippet | string | | |
action_result.data.\*.thread_id | string | | |
action_result.summary.next_page_token | string | | |
action_result.summary.total_messages_returned | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete email'

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

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Email message IDs to delete (comma-separated) | string | `gmail email id` |
**email** | required | Email address of mailbox owner | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.id | string | `gmail email id` | |
action_result.parameter.email | string | `email` | |
action_result.data.\*.deleted_emails.\* | string | | email_id_1 email_id_2 |
action_result.data.\*.ignored_ids.\* | string | | invalid_id |
action_result.summary.deleted_emails.\* | string | | email_id_1 email_id_2 |
action_result.summary.ignored_ids.\* | string | | invalid_id |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get email'

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

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | User's email address | string | `email` |
**internet_message_id** | required | Internet Message ID to retrieve | string | `internet message id` |
**format** | optional | Email format to retrieve | string | |
**extract_attachments** | optional | Extract attachments to vault | boolean | |
**extract_nested** | optional | Extract attachments from nested emails | boolean | |
**download_email** | optional | Download raw email as EML file to vault | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.email | string | `email` | |
action_result.parameter.internet_message_id | string | `internet message id` | |
action_result.parameter.format | string | | |
action_result.parameter.extract_attachments | boolean | | |
action_result.parameter.extract_nested | boolean | | |
action_result.parameter.download_email | boolean | | |
action_result.data.\*.subject | string | | |
action_result.data.\*.from | string | `email` | |
action_result.data.\*.to | string | `email` | |
action_result.data.\*.date | string | | |
action_result.data.\*.message_id | string | `internet message id` | |
action_result.data.\*.id | string | `gmail email id` | |
action_result.data.\*.thread_id | string | | |
action_result.data.\*.history_id | string | | |
action_result.data.\*.internal_date | string | | |
action_result.data.\*.label_ids | string | | |
action_result.data.\*.size_estimate | numeric | | |
action_result.data.\*.snippet | string | | |
action_result.data.\*.parsed_plain_body | string | | |
action_result.data.\*.parsed_html_body | string | | |
action_result.data.\*.headers.\*.name | string | | |
action_result.data.\*.headers.\*.value | string | | |
action_result.data.\*.urls.\* | string | | |
action_result.data.\*.ips.\* | string | | |
action_result.data.\*.domains.\* | string | | |
action_result.data.\*.hashes.\* | string | | |
action_result.data.\*.download_email_vault_id | string | `vault id` | 000094000006f00004cd60000b1f8e0000e5fa3e |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'send email'

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

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from** | optional | User's email address | string | `email` |
**to** | required | Recipients | string | `email` |
**subject** | required | Email subject | string | |
**body** | required | Email body (HTML) | string | |
**cc** | optional | CC recipients | string | `email` |
**bcc** | optional | BCC recipients | string | `email` |
**reply_to** | optional | Reply-To address | string | `email` |
**headers** | optional | Additional headers as JSON | string | |
**attachments** | optional | Vault IDs to attach (comma-separated) | string | |
**alias_email** | optional | Send from alias email address | string | `email` |
**alias_name** | optional | Alias name for send-as | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.from | string | `email` | |
action_result.parameter.to | string | `email` | |
action_result.parameter.subject | string | | |
action_result.parameter.body | string | | |
action_result.parameter.cc | string | `email` | |
action_result.parameter.bcc | string | `email` | |
action_result.parameter.reply_to | string | `email` | |
action_result.parameter.headers | string | | |
action_result.parameter.attachments | string | | |
action_result.parameter.alias_email | string | `email` | |
action_result.parameter.alias_name | string | | |
action_result.data.\*.id | string | `gmail email id` | |
action_result.data.\*.thread_id | string | | |
action_result.data.\*.label_ids | string | | |
action_result.data.\*.from_email | string | `email` | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
