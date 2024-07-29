# File: gsgmail_connector.py
#
# Copyright (c) 2017-2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
# Phantom App imports
import base64
import email
import json
# Fix to add __init__.py in dependencies folder
import os
import sys
from copy import deepcopy
from datetime import datetime

from email import encoders
from email.mime import application, multipart, text, base, image, audio
from email.mime.text import MIMEText
from io import BytesIO

import phantom.app as phantom
import phantom.utils as ph_utils
import phantom.vault as phantom_vault
import requests
from google.oauth2 import service_account
from googleapiclient import errors
from googleapiclient.http import MediaIoBaseUpload
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from requests.structures import CaseInsensitiveDict

from gsgmail_consts import *
from gsgmail_process_email import ProcessMail

init_path = '{}/dependencies/google/__init__.py'.format(  # noqa
    os.path.dirname(os.path.abspath(__file__))  # noqa
)  # noqa
# and _also_ debug the connector as a script via pudb
try:
    open(init_path, 'a+').close()  # noqa
    argv_temp = list(sys.argv)
except Exception:
    pass
sys.argv = ['']

import apiclient  # noqa


class RetVal2(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal2, (val1, val2))


#  Define the App Class
class GSuiteConnector(BaseConnector):

    def __init__(self):

        self._key_dict = None
        self._domain = None
        self._state = {}
        self._login_email = None
        self._dup_emails = 0
        self._last_email_epoch = None

        # Call the BaseConnectors init first
        super(GSuiteConnector, self).__init__()

    def _create_service(self, action_result, scopes, api_name, api_version, delegated_user=None):

        # first the credentials
        try:
            credentials = service_account.Credentials.from_service_account_info(self._key_dict, scopes=scopes)
        except Exception as e:
            return RetVal2(
                action_result.set_status(
                    phantom.APP_ERROR, GSGMAIL_SERVICE_KEY_FAILED, self._get_error_message_from_exception(e)),
                None)

        if delegated_user:
            try:
                credentials = credentials.with_subject(delegated_user)
            except Exception as e:
                return RetVal2(
                    action_result.set_status(
                        phantom.APP_ERROR, GSGMAIL_CREDENTIALS_FAILED, self._get_error_message_from_exception(e)),
                    None)

        try:
            service = apiclient.discovery.build(api_name, api_version, credentials=credentials)
        except Exception as e:
            return RetVal2(action_result.set_status(phantom.APP_ERROR,
                                                    FAILED_CREATE_SERVICE.format(api_name, api_version,
                                                                                 self._get_error_message_from_exception(e),
                                                                                 GSMAIL_USER_VALID_MESSAGE.format(delegated_user)), None))

        return RetVal2(phantom.APP_SUCCESS, service)

    def initialize(self):
        self._state = self.load_state()
        if self._state:
            self._last_email_epoch = self._state.get('last_email_epoch')

        config = self.get_config()

        key_json = config["key_json"]

        try:
            self._key_dict = json.loads(key_json)
        except Exception as e:
            return self.set_status(phantom.APP_ERROR, "Unable to load the key json", self._get_error_message_from_exception(e))

        self._login_email = config['login_email']

        if not ph_utils.is_email(self._login_email):
            return self.set_status(phantom.APP_ERROR, "Asset config 'login_email' failed validation")

        try:
            _, _, self._domain = self._login_email.partition('@')
        except Exception:
            return self.set_status(phantom.APP_ERROR, "Unable to extract domain from login_email")

        return phantom.APP_SUCCESS

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        """
        Validate an integer.

        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :allow_zero: whether zero should be considered as valid value or not
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, integer value of the parameter or None in case of failure
        """
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, GSGMAIL_INVALID_INTEGER_ERROR_MESSAGE.format(msg="", param=key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, GSGMAIL_INVALID_INTEGER_ERROR_MESSAGE.format(msg="", param=key)), None

            if parameter < 0:
                message = GSGMAIL_INVALID_INTEGER_ERROR_MESSAGE.format(msg="non-negative", param=key)
                return action_result.set_status(phantom.APP_ERROR, message), None
            if not allow_zero and parameter == 0:
                msg = "non-zero positive"
                return action_result.set_status(phantom.APP_ERROR, GSGMAIL_INVALID_INTEGER_ERROR_MESSAGE.format(msg=msg, param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = GSGMAIL_ERROR_MESSAGE_UNAVAILABLE

        self.error_print("Error occurred.", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.error_print("Error occurred while fetching exception information. Details: {}".format(str(e)))

        if not error_code:
            error_text = "Error Message: {}".format(error_message)
        else:
            error_text = "Error Code: {}. Error Message: {}".format(error_code, error_message)

        return error_text

    def _get_email_details(self, action_result, email_addr, email_id, service, results_format='metadata'):
        kwargs = {'userId': email_addr, 'id': email_id, 'format': results_format}

        try:
            email_details = service.users().messages().get(**kwargs).execute()
        except Exception as e:
            return RetVal2(action_result.set_status(phantom.APP_ERROR, GSGMAIL_EMAIL_FETCH_FAILED,
                                                    self._get_error_message_from_exception(e)))

        return RetVal2(phantom.APP_SUCCESS, email_details)

    def _map_email_details(self, input_email):

        # The dictionary of header values
        header_dict = dict()

        # list of values that are to be extracted
        headers_to_parse = ['subject', 'delivered-to', 'from', 'to', 'message-id']

        # get the payload
        email_headers = input_email.pop('payload', {}).get('headers')

        if not email_headers:
            return input_email

        for x in email_headers:
            if not headers_to_parse:
                break

            header_name = x.get('name')
            header_value = x.get('value', '')

            if not header_name:
                continue

            if header_name.lower() not in headers_to_parse:
                continue

            key_name = header_name.lower().replace('-', '_')
            header_dict[key_name] = header_value

            headers_to_parse.remove(header_name.lower())

        input_email.update(header_dict)

        return phantom.APP_SUCCESS, input_email

    def _get_email_headers_from_part(self, part):

        email_headers = list(part.items())
        if not email_headers:
            return {}

        # Convert the header tuple into a dictionary
        headers = CaseInsensitiveDict()

        # assume duplicate header names with unique values. ex: received
        for x in email_headers:
            try:
                headers.setdefault(x[0].lower().replace('-', '_').replace(' ', '_'), []).append(x[1])
            except Exception as e:
                error_message = self._get_error_message_from_exception(e)
                err = "Error occurred while converting the header tuple into a dictionary"
                self.error_print("{}. {}".format(err, error_message))
        headers = {k.lower(): '\n'.join(v) for k, v in headers.items()}

        return dict(headers)

    def _handle_run_query(self, param):

        # Implement the handler here, some basic code is already in

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Create the credentials with the required scope
        scopes = [GSGMAIL_AUTH_GMAIL_READ]

        # Create a service here
        self.save_progress("Creating GMail service object")

        user_email = param['email']

        ret_val, service = self._create_service(action_result, scopes, "gmail", "v1", user_email)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # create the query string
        query_string = ""
        query_dict = {
            'label': param.get('label'),
            'subject': param.get('subject'),
            'from': param.get('sender'),
            'rfc822msgid': param.get('internet_message_id')
        }

        query_string = ' '.join('{}:{}'.format(key, value) for key, value in query_dict.items() if value is not None)

        if 'body' in param:
            query_string += " {0}".format(param.get('body'))

        # if query is present, then override everything
        if 'query' in param:
            query_string = param.get('query')

        """
        # Check if there is something present in the query string
        if (not query_string):
            return action_result.set_status(phantom.APP_ERROR, "Please specify at-least one search criteria")
        """

        ret_val, max_results = self._validate_integer(action_result, param.get('max_results', 100), "max_results")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        kwargs = {'maxResults': max_results, 'userId': user_email, 'q': query_string}

        page_token = param.get('page_token')
        if page_token:
            kwargs.update({'pageToken': page_token})

        try:
            messages_resp = service.users().messages().list(**kwargs).execute()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Failed to get messages", self._get_error_message_from_exception(e))

        messages = messages_resp.get('messages', [])
        next_page = messages_resp.get('nextPageToken')
        summary = action_result.update_summary({'total_messages_returned': len(messages)})

        for curr_message in messages:

            curr_email_ar = ActionResult()

            ret_val, email_details_resp = self._get_email_details(curr_email_ar, user_email, curr_message['id'], service)

            if phantom.is_fail(ret_val):
                continue

            ret_val, email_details_resp = self._map_email_details(email_details_resp)

            if phantom.is_fail(ret_val):
                continue

            action_result.add_data(email_details_resp)

        if next_page:
            summary['next_page_token'] = next_page

        return action_result.set_status(phantom.APP_SUCCESS)

    def _body_from_part(self, part):
        charset = part.get_content_charset() or "utf-8"
        # decode the base64 unicode bytestring into plain text
        return part.get_payload(decode=True).decode(
            encoding=charset, errors="ignore"
        )

    def _create_artifact(self, file_name, attach_resp):
        return {
            "name": "Email Attachment Artifact",
            "container_id": self.get_container_id(),
            "cef": {
                "vaultId": attach_resp[phantom.APP_JSON_HASH],
                "fileHash": attach_resp[phantom.APP_JSON_HASH],
                "file_hash": attach_resp[phantom.APP_JSON_HASH],
                "fileName": file_name,
            },
            "run_automation": False,
            "source_data_identifier": None,
        }

    def _parse_email_details(self, part, email_details):
        headers = self._get_email_headers_from_part(part)
        # split out important headers (for output table rendering)
        if headers.get("to"):
            email_details["to"] = headers["to"]

        if headers.get("from"):
            email_details["from"] = headers["from"]

        if headers.get("subject"):
            email_details["subject"] = headers["subject"]

        part_type = part.get_content_type()
        if part_type == "text/plain":
            email_details["plain_bodies"].append(self._body_from_part(part))
        elif part_type == "text/html":
            email_details["html_bodies"].append(self._body_from_part(part))

        email_details["email_headers"].append(headers)

    def _get_payload_content(self, part):
        if part.get_content_type().startswith("message/"):
            return part.get_payload(0).as_string()
        return part.get_payload(decode=True)

    def _extract_attachment(self, part, action_result):
        attach_resp = None
        file_name = part.get_filename()
        try:
            # Create vault item with attachment payload
            attach_resp = Vault.create_attachment(
                self._get_payload_content(part),
                container_id=self.get_container_id(),
                file_name=file_name,
            )
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Unable to add attachment: {file_name} Error: {self._get_error_message_from_exception(e)}",
            )
        if attach_resp.get("succeeded"):
            # Create vault artifact
            ret_val, msg, _ = self.save_artifact(
                self._create_artifact(file_name, attach_resp)
            )
            if phantom.is_fail(ret_val):
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"Could not save artifact to container: {msg}",
                )
        return phantom.APP_SUCCESS

    @staticmethod
    def _is_attachment(part):
        return "attachment" in str(part.get("Content-Disposition"))

    def _init_detail_fields(self, email_details):
        email_details["plain_bodies"] = []
        email_details["html_bodies"] = []
        email_details["email_headers"] = []

    def _join_email_bodies(self, email_details):
        email_details["parsed_plain_body"] = "\n\n".join(
            email_details.pop("plain_bodies")
        )
        email_details["parsed_html_body"] = "\n\n".join(
            email_details.pop("html_bodies")
        )

    def __recursive_part_traverse(
        self,
        part,
        email_details,
        action_result,
        extract_attachments=False,
        extract_nested=False,
        in_attachment=False,
    ):
        is_attachment = self._is_attachment(part)
        # We are only gathering email data from top email, any attachment email should be omitted
        if not is_attachment and not in_attachment:
            self._parse_email_details(part, email_details)

        ret_val = phantom.APP_SUCCESS

        if is_attachment and extract_attachments:
            ret_val = self._extract_attachment(part, action_result)
            if phantom.is_fail(ret_val):
                return ret_val

        if not extract_nested and is_attachment:
            return ret_val

        if part.is_multipart():
            for subpart in part.get_payload():
                # We assume that everything that is under attachment is also an attachment
                ret_val = ret_val and self.__recursive_part_traverse(
                    subpart,
                    email_details,
                    action_result,
                    extract_attachments,
                    extract_nested,
                    is_attachment or in_attachment,
                )
        return ret_val

    def _parse_multipart_message(
        self,
        action_result,
        msg,
        email_details,
        extract_attachments=False,
        extract_nested=False,
    ):
        self._init_detail_fields(email_details)
        ret_val = self.__recursive_part_traverse(
            msg, email_details, action_result, extract_attachments, extract_nested
        )
        self._join_email_bodies(email_details)
        return ret_val

    def _handle_get_email(self, param):

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        scopes = [GSGMAIL_AUTH_GMAIL_READ]
        user_email = param['email']

        self.save_progress("Creating GMail service object")
        ret_val, service = self._create_service(action_result, scopes, "gmail", "v1", user_email)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        query_string = ""
        if 'internet_message_id' in param:
            query_string += " rfc822msgid:{0}".format(param['internet_message_id'])

        kwargs = {'q': query_string, 'userId': user_email}

        try:
            messages_resp = service.users().messages().list(**kwargs).execute()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Failed to get messages", self._get_error_message_from_exception(e))

        messages = messages_resp.get('messages', [])
        action_result.update_summary({'total_messages_returned': len(messages)})

        for curr_message in messages:

            curr_email_ar = ActionResult()

            ret_val, email_details_resp = self._get_email_details(curr_email_ar, user_email, curr_message['id'], service, 'raw')

            if phantom.is_fail(ret_val):
                continue

            raw_encoded = base64.urlsafe_b64decode(email_details_resp.pop('raw').encode('UTF8'))
            msg = email.message_from_bytes(raw_encoded)

            if msg.is_multipart():
                ret_val = self._parse_multipart_message(
                    action_result,
                    msg,
                    email_details_resp,
                    param.get("extract_attachments", False),
                    param.get("extract_nested", False),
                )

                if phantom.is_fail(ret_val):
                    return action_result.get_status()

            else:
                # not multipart
                email_details_resp['email_headers'] = []
                charset = msg.get_content_charset()
                headers = self._get_email_headers_from_part(msg)
                email_details_resp['email_headers'].append(headers)
                try:
                    email_details_resp['parsed_plain_body'] = msg.get_payload(decode=True).decode(encoding=charset, errors="ignore")
                except Exception as e:
                    message = self._get_error_message_from_exception(e)
                    self.error_print(f"Unable to add email body: {message}")

            action_result.add_data(email_details_resp)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_email(self, param):

        # Implement the handler here, some basic code is already in

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Create the credentials with the required scope
        scopes = [GSGMAIL_DELETE_EMAIL]

        # Create a service here
        self.save_progress("Creating GMail service object")

        user_email = param['email']

        ret_val, service = self._create_service(action_result, scopes, "gmail", "v1", user_email)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        email_ids = [x.strip() for x in param['id'].split(',')]
        email_ids = list(filter(None, email_ids))
        if not email_ids:
            return action_result.set_status(phantom.APP_ERROR, "Please provide valid value for 'id' action parameter")

        good_ids = set()
        bad_ids = set()

        for email_id in email_ids:
            kwargs = {
                'id': email_id,
                'userId': user_email
            }
            try:
                get_msg_resp = service.users().messages().get(**kwargs).execute()  # noqa
            except apiclient.errors.HttpError:
                self.error_print("Caught HttpError")
                bad_ids.add(email_id)
                continue
            except Exception as e:
                self.error_print("Exception name: {}".format(e.__class__.__name__))
                error_message = self._get_error_message_from_exception(e)
                return action_result.set_status(
                    phantom.APP_ERROR, 'Error checking email. ID: {} Reason: {}.'.format(email_id, error_message)
                )
            good_ids.add(email_id)

        if not good_ids:
            summary = action_result.update_summary({})
            summary['deleted_emails'] = list(good_ids)
            summary['ignored_ids'] = list(bad_ids)
            return action_result.set_status(
                phantom.APP_SUCCESS,
                "All the provided emails were already deleted, Ignored Ids : {}".format(summary['ignored_ids'])
            )

        kwargs = {'body': {'ids': email_ids}, 'userId': user_email}

        try:
            service.users().messages().batchDelete(**kwargs).execute()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Failed to delete messages", self._get_error_message_from_exception(e))

        summary = action_result.update_summary({})
        summary['deleted_emails'] = list(good_ids)
        summary['ignored_ids'] = list(bad_ids)

        return action_result.set_status(
            phantom.APP_SUCCESS,
            "Messages deleted, Ignored Ids : {}".format(summary['ignored_ids'])
        )

    def _handle_get_users(self, param):

        # Implement the handler here, some basic code is already in

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Create the credentials with the required scope
        scopes = [GSGMAIL_AUTH_GMAIL_ADMIN_DIR]

        # Create a service here
        self.save_progress("Creating AdminSDK service object")

        ret_val, service = self._create_service(action_result, scopes, "admin", "directory_v1", self._login_email)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Getting list of users for domain: {0}".format(self._domain))

        ret_val, max_users = self._validate_integer(action_result, param.get('max_items', 500), "max_items")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        kwargs = {'domain': self._domain, 'maxResults': max_users, 'orderBy': 'email', 'sortOrder': 'ASCENDING'}

        page_token = param.get('page_token')
        if page_token:
            kwargs.update({'pageToken': page_token})

        try:
            users_resp = service.users().list(**kwargs).execute()
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, GSGMAIL_USERS_FETCH_FAILED, error_message)

        users = users_resp.get('users', [])
        num_users = len(users)
        next_page = users_resp.get('nextPageToken')
        summary = action_result.update_summary({'total_users_returned': num_users})

        for curr_user in users:
            action_result.add_data(curr_user)

        if next_page:
            summary['next_page_token'] = next_page

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_test_connectivity(self, param):

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Create the credentials, with minimal scope info for test connectivity
        scopes = [GSGMAIL_AUTH_GMAIL_ADMIN_DIR]

        # Test connectivity does not return any data, it's the status that is more important
        # and the progress messages
        # Create a service here
        self.save_progress("Creating AdminSDK service object")
        ret_val, service = self._create_service(action_result, scopes, "admin", "directory_v1", self._login_email)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Getting list of users for domain: {0}".format(self._domain))

        try:
            service.users().list(domain=self._domain, maxResults=1, orderBy='email', sortOrder="ASCENDING").execute()
        except Exception as e:
            self.save_progress("Test Connectivity Failed")
            return action_result.set_status(phantom.APP_ERROR, "Failed to get users", self._get_error_message_from_exception(e))

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_email_ids_to_process(self, service, action_result, max_results, ingest_manner,
                                  user_id='me', labels=[], include_spam_trash=False, q=None, include_sent=False,
                                  use_ingest_limit=False):

        kwargs = {
            'userId': user_id,
            'includeSpamTrash': include_spam_trash,
            'maxResults': GSMAIL_MAX_RESULT
        }

        label_ids = []
        if labels:
            if 'labels' not in self._state:
                self._state['labels'] = {}
            for label in labels:
                if label.lower() not in self._state['labels']:
                    try:
                        response = service.users().labels().list(userId=user_id).execute()  # pylint: disable=E1101
                        gmail_labels = response['labels']
                        for gmail_label in gmail_labels:
                            if gmail_label['name'].lower() == label.lower():
                                self._state['labels'][label.lower()] = gmail_label['id']
                    except errors.HttpError as error:
                        return action_result.set_status(phantom.APP_ERROR, error), None
                if label.lower() not in self._state['labels']:
                    return action_result.set_status(phantom.APP_ERROR, 'Unable to find label "{}"'.format(label)), None
                label_ids.append(self._state['labels'][label.lower()])

        if label_ids:
            kwargs['labelIds'] = label_ids

        query = []
        if q:
            query.append(q)
        if not include_sent:
            query.append('-in:sent')

        using_oldest = ingest_manner == GSMAIL_OLDEST_INGEST_MANNER
        using_latest = ingest_manner == GSMAIL_LATEST_INGEST_MANNER

        if use_ingest_limit and not self.is_poll_now():
            if self._last_email_epoch and using_oldest:
                query.append('after:{}'.format(self._last_email_epoch))
            elif 'last_ingested_epoch' in self._state and using_latest:
                query.append('after:{}'.format(self._state['last_ingested_epoch']))

        kwargs['q'] = ' '.join(query)

        try:
            response = service.users().messages().list(**kwargs).execute()  # pylint: disable=E1101
            messages = []
            if 'messages' in response:
                messages.extend(response['messages'])
            while 'nextPageToken' in response:
                if max_results and using_latest and len(messages) > max_results:
                    break
                kwargs['pageToken'] = response['nextPageToken']
                response = service.users().messages().list(**kwargs).execute()  # pylint: disable=E1101
                messages.extend(response['messages'])

            message_ids = [x['id'] for x in messages]

            if max_results and len(message_ids) > max_results:
                if using_oldest:
                    message_ids = message_ids[-max_results:]
                else:
                    message_ids = message_ids[:max_results]

            return action_result.set_status(phantom.APP_SUCCESS), message_ids
        except errors.HttpError as error:
            return action_result.set_status(phantom.APP_ERROR, error), None

    def _handle_on_poll(self, param):
        # Implement the handler here, some basic code is already in
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Create the credentials with the required scope
        scopes = [GSGMAIL_AUTH_GMAIL_READ]

        # Create a service here
        self.save_progress("Creating GMail service object")

        # if user_email param is not present use login_email
        config = self.get_config()

        login_email = config['login_email']
        self.save_progress("login_email is {0}".format(login_email))

        ret_val, service = self._create_service(action_result, scopes, "gmail", "v1", login_email)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if self.is_poll_now():
            ret_val, max_emails = self._validate_integer(
                action_result, param.get(phantom.APP_JSON_CONTAINER_COUNT), 'container count', allow_zero=False)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            self.save_progress(GSMAIL_POLL_NOW_PROGRESS)
        else:
            ret_val1, first_run_max_emails = self._validate_integer(
                action_result,
                config.get('first_run_max_emails', GSMAIL_DEFAULT_FIRST_RUN_MAX_EMAIL),
                "first_max_emails",
                allow_zero=False)
            ret_val2, max_containers = self._validate_integer(
                action_result,
                config.get('max_containers', GSMAIL_DEFAULT_MAX_CONTAINER),
                "max_containers",
                allow_zero=False)
            if phantom.is_fail(ret_val1) or phantom.is_fail(ret_val2):
                return action_result.get_status()
            if self._state.get('first_run', True):
                self._state['first_run'] = False
                max_emails = first_run_max_emails
                self.save_progress(GSMAIL_FIRST_INGES_DELETED)
            else:
                max_emails = max_containers

        run_limit = deepcopy(max_emails)
        action_result = self.add_action_result(ActionResult(dict(param)))
        email_id = param.get(phantom.APP_JSON_CONTAINER_ID, False)
        email_ids = [email_id]
        total_ingested = 0
        ingest_manner = config.get('ingest_manner', GSMAIL_OLDEST_INGEST_MANNER)
        while True:
            self._dup_emails = 0
            if not email_id:
                ret_val, email_ids = self._get_email_ids(action_result, config, service, max_emails, ingest_manner)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                if not email_ids:
                    return action_result.set_status(phantom.APP_SUCCESS)
                if not self.is_poll_now():
                    self._update_state()

            self._process_email_ids(action_result, config, service, email_ids)
            total_ingested += max_emails - self._dup_emails

            if ingest_manner == GSMAIL_LATEST_INGEST_MANNER or total_ingested >= run_limit or self.is_poll_now():
                break

            max_emails = max_emails + min(self._dup_emails, run_limit)

        return phantom.APP_SUCCESS

    def _create_message(self, sender, to, cc, bcc, subject, message_text, reply_to=None, additional_headers={}, vault_ids=[]):
        message = multipart.MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        if reply_to:
            message['Reply-To'] = reply_to

        for key, value in additional_headers.items():
            message[key] = value

        part1 = MIMEText(message_text, 'plain')
        message.attach(part1)

        # Attach HTML part with plain text content
        part2 = MIMEText(message_text, 'html')
        message.attach(part2)

        current_size = 0
        mime_consumer = {'text': text.MIMEText,
                     'image': image.MIMEImage,
                     'audio': audio.MIMEAudio }

        for vault_id in vault_ids:
            vault_info = self._get_vault_info(vault_id)
            if not vault_info:
                self.debug_print("Failed to find vault entry {}".format(vault_id))
                continue

            current_size += vault_info["size"]
            if current_size > GSGMAIL_ATTACHMENTS_CUTOFF_SIZE:
                self.debug_print("Total attachment size reached max capacity. No longer adding attachments after vault id {0}".format(vault_id))
                break

            content_type = vault_info['mime_type']
            main_type, sub_type = content_type.split('/', 1)

            consumer = None
            if main_type in mime_consumer:
                consumer = main_type[mime_consumer]
            elif main_type == "application" and sub_type == "pdf":
                consumer = application.MIMEApplication

            self.debug_print("Content type is {0}".format(content_type))
            attachment_part = None
            if not consumer:
                attachment_part = base.MIMEBase(main_type, sub_type)
                with open(vault_info['path'], mode='rb') as file:
                    file_content = file.read()
                    attachment_part.set_payload(file_content)
            else:
                with open(vault_info['path'], mode='rb') as file:
                    attachment_part = consumer(file.read(), _subtype=sub_type)

            encoders.encode_base64(attachment_part)

            attachment_part.add_header(
                'Content-Disposition',
                'attachment; filename={0}'.format(vault_info['name'])
            )
            attachment_part.add_header(
                'Content-Length',
                str(vault_info['size'])  # File size in bytes
            )
            attachment_part.add_header(
                'Content-ID',
                vault_info['vault_id']
            )
            message.attach(attachment_part)

        return message

    def _send_email(self, service, user_id, media, action_result):
        try:
            sent_message = service.users().messages().send(userId=user_id, body={}, media_body=media).execute()
            return phantom.APP_SUCCESS, sent_message
        except Exception as error:
            self.debug_print("Error occured when sending draft: {0}".format(error))
            return action_result.set_status(phantom.APP_ERROR, "Message not sent because of {0}".format(error)), None

    def _get_vault_info(self, vault_id):
        _, _, vault_infos = phantom_vault.vault_info(container_id=self.get_container_id(), vault_id=vault_id)
        if not vault_infos:
            _, _, vault_infos = phantom_vault.vault_info(vault_id=vault_id)
        return vault_infos[0] if vault_infos else None

    def _create_send_as_alias(self, service, user_id, alias_email, display_name=None):
        send_as = {
            "sendAsEmail": alias_email,
            "treatAsAlias": True,
            "isPrimary": False
        }

        if display_name:
            send_as["displayName"] = display_name

        try:
            result = service.users().settings().sendAs().create(userId=user_id, body=send_as).execute()
            return phantom.APP_SUCCESS, result
        except errors.HttpError as error:
            return phantom.APP_ERROR, error

    def _handle_send_email(self, param):
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Create the credentials with the required scope
        scopes = [GSGMAIL_DELETE_EMAIL]

        # Create a service here
        self.save_progress("Creating GMail service object")

        ret_val, service = self._create_service(action_result, scopes, "gmail", "v1", self._login_email)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        from_email = param["from"] if param.get("from", "") else self._login_email

        try:
            headers = json.loads(param.get("headers", "{}"))
        except json.JSONDecodeError as e:
            return action_result.set_status(phantom.APP_ERROR, e), None

        vault_ids = [vault_id for x in param.get('attachments', '').split(',') if (vault_id := x.strip())]

        if param.get("alias_email"):
            alias_email = param.get("alias_email")
            alias_name = param.get("alias_name", "")
            SETTINGS_SCOPE = [GSMAIL_SETTINGS_CHANGE]
            ret_val, settings_service = self._create_service(action_result, SETTINGS_SCOPE, "gmail", "v1", self._login_email)
            ret_val, res = self._create_send_as_alias(settings_service, "me", alias_email, alias_name)
            if ret_val == phantom.APP_SUCCESS:
                self.debug_print("Successfully created alias {0}".format(alias_email))
                from_email = alias_email
            elif res.resp.status == 409 and 'alreadyExists' in res._get_reason():
                self.debug_print("Alias {0} already exists. Using to send emails".format(alias_email))
                from_email = alias_email
            else:
                self.debug_print("Could not create alias {0} because of {1}".format(alias_email, res))

        message = self._create_message(
            from_email,
            param.get("to", ""),
            param.get("cc", ""),
            param.get("bcc", ""),
            param.get("subject", ""),
            param.get("body", ""),
            param.get("reply_to"),
            headers,
            vault_ids
        )

        media = MediaIoBaseUpload(BytesIO(message.as_bytes()), mimetype='message/rfc822', resumable=True)
        ret_val, sent_message = self._send_email(service, "me", media, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, "Email sent with id {0}".format(sent_message["id"]))

    def _process_email_ids(self, action_result, config, service, email_ids):
        for i, emid in enumerate(email_ids):
            self.send_progress("Parsing email id: {0}".format(emid))
            try:
                message = service.users().messages().get(userId='me', id=emid, format='raw').execute()  # pylint: disable=E1101
            except errors.HttpError as error:
                return action_result.set_status(phantom.APP_ERROR, error)

            timestamp = int(message['internalDate']) // 1000
            if not self.is_poll_now() and i == 0:
                self._state['last_email_epoch'] = timestamp + 1
            # the api libraries return the base64 encoded message as a unicode string,
            # but base64 can be represented in ascii with no possible issues
            raw_decode = base64.urlsafe_b64decode(message['raw'].encode("utf-8")).decode("utf-8")
            process_email = ProcessMail(self, config)
            process_email.process_email(raw_decode, emid, timestamp)

    def _update_state(self):
        utc_now = datetime.utcnow()
        epoch = datetime.utcfromtimestamp(0)
        self._state['last_ingested_epoch'] = str(int((utc_now - epoch).total_seconds()))

    def _get_email_ids(self, action_result, config, service, max_emails, ingest_manner):

        self.save_progress("Getting {0} '{1}' email ids".format(max_emails, ingest_manner))
        self.debug_print("Getting {0} '{1}' email ids".format(max_emails, ingest_manner))
        labels = []
        if "label" in config:
            labels_val = config['label']
            labels = [x.strip() for x in labels_val.split(',')]
            labels = list(filter(None, labels))
        return self._get_email_ids_to_process(
            service, action_result, max_emails,
            ingest_manner=ingest_manner, labels=labels, use_ingest_limit=True, include_sent=True)

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):

        """
        import web_pdb
        web_pdb.set_trace()
        """

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'run_query':
            ret_val = self._handle_run_query(param)
        elif action_id == 'delete_email':
            ret_val = self._handle_delete_email(param)
        elif action_id == 'get_users':
            ret_val = self._handle_get_users(param)
        elif action_id == 'get_email':
            ret_val = self._handle_get_email(param)
        elif action_id == 'on_poll':
            ret_val = self._handle_on_poll(param)
        elif action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)
        elif action_id == 'send_email':
            ret_val = self._handle_send_email(param)

        return ret_val


if __name__ == '__main__':

    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

    args = argv_temp.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if (username is not None and password is None):
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if (username and password):
        try:
            print("Accessing the Login page")
            login_url = BaseConnector._get_phantom_base_url() + 'login'
            r = requests.get(login_url, verify=verify, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=DEFAULT_TIMEOUT)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = GSuiteConnector()
        connector.print_progress_message = True

        if (session_id is not None):
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
