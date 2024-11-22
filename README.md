[comment]: # "Auto-generated SOAR connector documentation"
# G Suite for GMail

Publisher: Splunk  
Connector Version: 2.6.0  
Product Vendor: Google  
Product Name: GMail  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.1 

Integrates with G Suite for various investigative and containment actions

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2017-2024 Splunk Inc."
[comment]: # ""
[comment]: # "  Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)"
[comment]: # ""
### Service Account

This app requires a pre-configured service account to operate. Please follow the procedure outlined
at [this link](https://support.google.com/a/answer/7378726?hl=en) to create a service account.  
The following APIs will need to be enabled:

-   AdminSDK
-   GMail API

At the end of the creation process, the admin console should ask you to save the config as a JSON
file. Copy the contents of the JSON file in the clipboard and paste it as the value of the
**key_json** asset configuration parameter.

### Scopes

Once the service account has been created and APIs enabled, the next step is to configure scopes on
these APIs to allow the App to access them. Every action requires different scopes to operate, these
are listed in the action documentation.  
To enable scopes please complete the following steps:

-   Go to your G Suite domain's [Admin console.](http://admin.google.com/)
-   Select **Security** from the list of controls. If you don't see **Security** listed, select
    **Show More** , then select **Security** from the list of controls. If you can't see the
    controls, make sure you're signed in as an administrator for the domain.
-   Select **API controls** in the **Access and data control** section.
-   Select **MANAGE DOMAIN WIDE DELEGATIONS** in the **Domain wide delegation** section.
-   Select **Add new** in the API clients section
-   In the **Client ID** field enter the service account's **Client ID** . You can find your service
    account's client ID in the [Service accounts credentials
    page](https://console.developers.google.com/apis/credentials) or the service account JSON file
    (key named **client_id** ).
-   In the **One or More API Scopes** field enter the list of scopes that you wish to grant access
    to the App. For example, to enable all the scopes required by this app enter:
    https://mail.google.com/, https://www.googleapis.com/auth/admin.directory.user.readonly,
    https://www.googleapis.com/auth/gmail.readonly
-   Click **Authorize** .

### On-Poll

-   API provides created time of the email and gmail searches based on the received time of the
    email.

-   Use the large container numbers in asset to avoid any kind of data loss for emails which
    received at the same time.

      
      
      
    **Configuration:**  

<!-- -->

-   label - To fetch the emails from the given folder name (default - all folders).  
    **Note:-** Reply email in the email thread would not be ingested if you provide a specific label
    in the configuration (eg. Inbox). It will ingest the reply email only if you leave the label
    configuration parameter empty.  
-   ingest_manner - To select the oldest first or newest first preference for ingestion (default -
    oldest first).
-   first_run_max_emails - Maximum containers to poll for the first scheduled polling (default -
    1000).
-   max_containers - Maximum containers to poll after the first scheduled poll completes (default -
    100).
-   extract_attachments - Extract all the attachments included in emails.
-   download_eml_attachments - Downloads the EML file attached with the mail.
-   extract_urls - Extracts the URLs present in the emails.
-   extract_ips - Extracts the IP addresses present in the emails.
-   extract_domains - Extract the domain names present in the emails.
-   extract_hashes - Extract the hashes present in the emails (MD5).


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a GMail asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**login_email** |  required  | string | Login (Admin) email
**key_json** |  required  | password | Contents of Service Account JSON file
**label** |  optional  | string | Mailbox Label (folder) to be polled
**ingest_manner** |  optional  | string | How to ingest
**first_run_max_emails** |  optional  | numeric | Maximum Containers for scheduled polling first time
**max_containers** |  optional  | numeric | Maximum Containers for scheduled polling
**data_type** |  optional  | string | Ingestion data type when polling
**forwarding_address** |  optional  | string | Address to forward polled emails to
**auto_reply** |  optional  | string | Auto reply to emails with a set body
**extract_attachments** |  optional  | boolean | Extract Attachments
**default_format** |  optional  | string | Format used for the get email action
**extract_urls** |  optional  | boolean | Extract URLs
**extract_ips** |  optional  | boolean | Extract IPs
**extract_domains** |  optional  | boolean | Extract Domain Names
**extract_hashes** |  optional  | boolean | Extract Hashes
**download_eml_attachments** |  optional  | boolean | Download EML attachments
**extract_eml** |  optional  | boolean | Extract root (primary) email as Vault

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  
[list users](#action-list-users) - Get the list of users  
[run query](#action-run-query) - Search emails with query/filtering options  
[delete email](#action-delete-email) - Delete emails  
[on poll](#action-on-poll) - Callback action for the on-poll ingest functionality  
[get email](#action-get-email) - Retrieve email details via internet message id  
[get user](#action-get-user) - Retrieve user details via email address  
[send email](#action-send-email) - Send emails  

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

Action uses the Admin SDK API to get a list of users. Requires authorization with the following scope: <b>https://www.googleapis.com/auth/admin.directory.user.readonly</b>.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'list users'
Get the list of users

Type: **investigate**  
Read only: **True**

Action uses the Admin SDK API to get a list of users. Requires authorization with the following scope: <b>https://www.googleapis.com/auth/admin.directory.user.readonly</b>.<br>The action will limit the number of users returned to <b>max_items</b> or (if not specified) 500. If the system has any more users, a next page token will be returned in <b>action_result.summary.next_page_token</b>. Use this value as input to <b>page_token</b> in subsequent calls to <b>list users</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_items** |  optional  | Max users to get (max 500) | numeric | 
**page_token** |  optional  | Token to specify next page in list | string |  `gsuite page token` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.max_items | numeric |  |   500 
action_result.parameter.page_token | string |  `gsuite page token`  |   0a38f80195e2ffffffff9c9e8c8c9e919b8d9ed19c9e9691bf979a8d929e919c908d8fd19d9685ff00fefffecccfc9c7c6c6c8c7ccc8c7cbfffe100221b346550b02f34e6639000000001d6afe00480150005a0b09f1d40ed2266dadd0100360f4b2c2bc03 
action_result.data.\*.agreedToTerms | boolean |  |   True  False 
action_result.data.\*.archived | boolean |  |   True  False 
action_result.data.\*.changePasswordAtNextLogin | boolean |  |   True  False 
action_result.data.\*.creationTime | string |  |  
action_result.data.\*.customerId | string |  |  
action_result.data.\*.emails.\*.address | string |  `email`  |  
action_result.data.\*.emails.\*.primary | boolean |  |   True  False 
action_result.data.\*.emails.\*.type | string |  |   work 
action_result.data.\*.etag | string |  |  
action_result.data.\*.id | string |  |  
action_result.data.\*.includeInGlobalAddressList | boolean |  |   True  False 
action_result.data.\*.ipWhitelisted | boolean |  |   True  False 
action_result.data.\*.isAdmin | boolean |  |   True  False 
action_result.data.\*.isDelegatedAdmin | boolean |  |   True  False 
action_result.data.\*.isEnforcedIn2Sv | boolean |  |   True  False 
action_result.data.\*.isEnrolledIn2Sv | boolean |  |   True  False 
action_result.data.\*.isMailboxSetup | boolean |  |   True  False 
action_result.data.\*.kind | string |  |  
action_result.data.\*.languages.\*.languageCode | string |  |   en 
action_result.data.\*.languages.\*.preference | string |  |   preferred 
action_result.data.\*.lastLoginTime | string |  |  
action_result.data.\*.name.familyName | string |  |  
action_result.data.\*.name.fullName | string |  |  
action_result.data.\*.name.givenName | string |  |  
action_result.data.\*.nonEditableAliases | string |  `email`  |  
action_result.data.\*.orgUnitPath | string |  |  
action_result.data.\*.phones.\*.type | string |  |   work 
action_result.data.\*.phones.\*.value | string |  |   9898989898 
action_result.data.\*.primaryEmail | string |  `email`  |  
action_result.data.\*.recoveryEmail | string |  |   admin@testcorp.biz 
action_result.data.\*.suspended | boolean |  |   True  False 
action_result.summary.next_page_token | string |  `gsuite page token`  |  
action_result.summary.total_users_returned | numeric |  |  
action_result.message | string |  |   Successfully retrieved 10 users 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'run query'
Search emails with query/filtering options

Type: **investigate**  
Read only: **True**

Action uses the GMail API to search in a users mailbox (specified in the <b>email</b> parameter).<br>Requires authorization with the following scope: <b>https://www.googleapis.com/auth/gmail.readonly</b>.<br>If none of the filtering parameters are specified the action will return all emails in the mailbox. If the <b>query</b> parameter is specified, all other filtering parameters are ignored.<br>The query parameter uses the same filtering options (operators) as the GMail search box. A brief description of these can be found <a href="https://support.google.com/mail/answer/7190?hl=en">at this link</a>.<br>To page through results, execute the action without a <b>page_token</b> parameter and a valid <b>max_results</b> value. If the query matches more than <b>max_results</b>, the action will return a value in the <b>action_result.summary.next_page_token</b> data path. This value should be used as the input value to the <b>page_token</b> parameter in the next call to <b>run query</b> to get the next set of results.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** |  required  | User's Email (Mailbox to search in) | string |  `email` 
**label** |  optional  | Label (to search in) | string |  `gmail label` 
**subject** |  optional  | Substring to search in Subject | string | 
**sender** |  optional  | Sender Email address to match | string |  `email` 
**body** |  optional  | Substring to search in Body | string | 
**internet_message_id** |  optional  | Internet Message ID | string |  `internet message id` 
**query** |  optional  | Gmail Query string | string | 
**max_results** |  optional  | Max Results | numeric | 
**page_token** |  optional  | Next page token | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.body | string |  |   Mail content 
action_result.parameter.email | string |  `email`  |   admin@testcorp.biz 
action_result.parameter.internet_message_id | string |  `internet message id`  |   <EgJbSMFdx8wUfrVUc7r7Jg@notifications.test.com> 
action_result.parameter.label | string |  `gmail label`  |   Inbox 
action_result.parameter.max_results | numeric |  |   100 
action_result.parameter.page_token | string |  |   0a38f80195e2ffffffff9c9e8c8c9e919b8d9ed19c9e9691bf979a8d929e919c908d8fd19d9685ff00fefffecccfc9c7c6c6c8c7ccc8c7cbfffe100221b346550b02f34e6639000000001d6afe00480150005a0b09f1d40ed2266dadd0100360f4b2c2bc03 
action_result.parameter.query | string |  |   in:sent after:1388552400 
action_result.parameter.sender | string |  `email`  |   no-reply@accounts.test.com 
action_result.parameter.subject | string |  |   Password reset 
action_result.data.\*.delivered_to | string |  `email`  |  
action_result.data.\*.from | string |  `email`  |  
action_result.data.\*.historyId | string |  |  
action_result.data.\*.id | string |  `gmail email id`  |  
action_result.data.\*.internalDate | string |  |  
action_result.data.\*.labelIds | string |  |  
action_result.data.\*.message_id | string |  `internet message id`  |  
action_result.data.\*.sizeEstimate | numeric |  |  
action_result.data.\*.snippet | string |  |  
action_result.data.\*.subject | string |  |  
action_result.data.\*.threadId | string |  |  
action_result.data.\*.to | string |  `email`  |  
action_result.summary.next_page_token | string |  |   01274238709826297998 
action_result.summary.total_messages_returned | numeric |  |  
action_result.message | string |  |   Total messages returned: 20 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'delete email'
Delete emails

Type: **contain**  
Read only: **False**

Action uses the GMail API. Requires authorization with the following scope: <b>https://mail.google.com</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Message IDs to delete(Comma separated IDs allowed) | string |  `gmail email id` 
**email** |  required  | Email of the mailbox owner | string |  `email` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.email | string |  `email`  |   admin@testcorp.biz 
action_result.parameter.id | string |  `gmail email id`  |   15ec4d28294f950c 
action_result.data | string |  |  
action_result.summary.deleted_emails | string |  `gmail email id`  |   15ec4d28294f950c 
action_result.summary.ignored_ids | string |  `gmail email id`  |   15ec4d28294f950c 
action_result.message | string |  |   All the provided emails were already deleted 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'on poll'
Callback action for the on-poll ingest functionality

Type: **ingest**  
Read only: **True**

Requires authorization with the following scope: <b>https://www.googleapis.com/auth/gmail.readonly</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** |  optional  | Parameter Ignored in this app | numeric | 
**end_time** |  optional  | Parameter Ignored in this app | numeric | 
**container_id** |  optional  | Parameter Ignored in this app | string | 
**container_count** |  required  | Maximum number of emails to ingest | numeric | 
**artifact_count** |  required  | Maximum number of artifact to ingest | numeric | 
**data_type** |  optional  | Encode ingested emails as ASCII or UTF-8 | string | 

#### Action Output
No Output  

## action: 'get email'
Retrieve email details via internet message id

Type: **investigate**  
Read only: **False**

Action uses the GMail API to search in a user's mailbox (specified in the <b>email</b> parameter). Use the <b>run query</b> action to retrieve <b>internet message id</b>.<br>Use <b>extract attachments</b> parameter to add attachments to vault and add corresponding vault artifacts.<br>Requires authorization with the following scope: <b>https://www.googleapis.com/auth/gmail.readonly</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** |  required  | User's Email (Mailbox to search) | string |  `email` 
**internet_message_id** |  required  | Internet Message ID | string |  `internet message id` 
**extract_attachments** |  optional  | Add attachments to vault and create vault artifacts | boolean | 
**extract_nested** |  optional  | Works when `extract_attachments` is set to `true`. Extracts attachments from nested email attachments. | boolean | 
**format** |  optional  | Format used for the get email action | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.email | string |  `email`  |   admin@testcorp.biz 
action_result.parameter.extract_attachments | boolean |  |   False 
action_result.parameter.internet_message_id | string |  `internet message id`  |   <e3d885faf2cc04f261d3874bafe2dc8afc44a230-10004962-100081937@test.com> 
action_result.data.\*.email_headers.\*.arc_authentication_results | string |  |   i=1; mx.test.com;       dkim=pass header.i=@test.com header.s=20161025 header.b=S15AEvGA;       spf=pass (test.com: domain of 33buoybakbvceznb3cih-cdg3ean5dd5a3.1dbz2b7c63gbzc1dge.07o@scoutcamp.bounces.test.com designates 2607:f8b0:4864:20::147 as permitted sender) smtp.mailfrom=33BuOYBAKBVcEzNB3CIH-CDG3EAN5DD5A3.1DBz2B7C63GBzC1DGE.07O@scoutcamp.bounces.test.com;       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=test.com 
action_result.data.\*.email_headers.\*.arc_message_signature | string |  |   i=1; a=rsa-sha256; c=relaxed/relaxed; d=test.com; s=arc-20160816;\\r\\n        h=to:from:subject:message-id:feedback-id:reply-to:date:mime-version\\r\\n         :dkim-signature;\\r\\n        bh=z/kirlEQ2aVcgVc3qMye/grykWqFcVQv0Yr0y2Mbewo=;\\r\\n        b=K0Q7B+6Dq2695j4C/fRV8QlFGfFo42i3i6TNVIVR3/xvcVZcChH7+XcQ4e43rT4bYz\\r\\n         /wZZzTVm1BbohPZOLvAsQE07vFMb0T7eggAAesqpoV0aPqahN7ECabqx6JXSPiYIhK/j\\r\\n         n6BdpvfBdYXhh34tKpNQKgblkkgrpZaiHRYcys+s+e06Xh41W+92j1KahxqKvujgQ50w\\r\\n         MtD0G492zoocCBJdUl1IGYYCNjbxSZTbO48u7UTqWS4xP1KNLmV9vRpPDp/QwjQDv5Ux\\r\\n         69G3NeFGJcH0z3REg1AhqHHKtF1/GX2yngvKSUyO4yUajI/tdQdXF0Uxz93w4aOYH5J7\\r\\n         FV8A== 
action_result.data.\*.email_headers.\*.arc_seal | string |  |   i=1; a=rsa-sha256; t=1619925981; cv=none;\\r\\n        d=test.com; s=arc-20160816;\\r\\n        b=b1K9fT7s6nA56FOt2CMy22w5fhwxHjx63FzKVzpWlWmeHn4neo4mrtpauZFiiy7tQA\\r\\n         /VITLzcFg8GMtPaN7pDWQkHUVQ8qyuUi3Kl8xpYre8DoI1KzLfTUz8LqxaBKuYl3Ln00\\r\\n         rQ/fBj+v16+HuuVOKwd8roet3A5SCmDZBvSOk+pcRfjAtL7GDqF2LVEtDYVDJ0V7eUxx\\r\\n         V6eZjsFOg9tZTkyHTPq8S+pN7e5KCV7rIgelF25MJcYdt+4OJjs6jfmsn2p1NC14QvRP\\r\\n         ONhqWc1lMseCp6/GdtoM2tIDHORdLy/upg3mC63jhi5JDIRWiObg1HC2PI8AFxqhkJCW\\r\\n         rFCQ== 
action_result.data.\*.email_headers.\*.authentication_results | string |  |   mx.test.com;\\r\\n       dkim=pass header.i=@test.com header.s=20161025 header.b=S15AEvGA;\\r\\n       spf=pass (test.com: domain of 33buoybakbvceznb3cih-cdg3ean5dd5a3.1dbz2b7c63gbzc1dge.07o@scoutcamp.bounces.test.com designates 2607:f8b0:4864:20::147 as permitted sender) smtp.mailfrom=33BuOYBAKBVcEzNB3CIH-CDG3EAN5DD5A3.1DBz2B7C63GBzC1DGE.07O@scoutcamp.bounces.test.com;\\r\\n       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=test.com 
action_result.data.\*.email_headers.\*.content_disposition | string |  |   attachment; filename="3902920193.pdf" 
action_result.data.\*.email_headers.\*.content_transfer_encoding | string |  |   quoted-printable 
action_result.data.\*.email_headers.\*.content_type | string |  |   multipart/mixed; boundary="000000000000a2607f05c15068be" 
action_result.data.\*.email_headers.\*.date | string |  |   Sat, 01 May 2021 20:26:20 -0700 
action_result.data.\*.email_headers.\*.delivered_to | string |  `email`  |   admin@testcorp.biz 
action_result.data.\*.email_headers.\*.dkim_signature | string |  |   v=1; a=rsa-sha256; c=relaxed/relaxed;\\r\\n        d=test.com; s=20161025;\\r\\n        h=mime-version:date:reply-to:feedback-id:message-id:subject:from:to;\\r\\n        bh=z/kirlEQ2aVcgVc3qMye/grykWqFcVQv0Yr0y2Mbewo=;\\r\\n        b=S15AEvGAEDpFXZ0KGsbNCqY8YVSzr6At0pUpF7crMh4ik5FmM0vGwomsUR59ONHoNF\\r\\n         SJ4U+IcxvsItH2mgCsQ7RjJK0dLLC7BkbhkDGHPY/IQ1KSZKcGEU0qfTXAsff5HENC3X\\r\\n         6LDYi7UqTdnjvSwv2dQdW1/yS96d27anFiPj9Wua4vd8GilRW5QOBJX1rl6yFas6uHD7\\r\\n         JWQRykXcpcNTKJpj2dvX2JIsT2IKiXy2BCpU69hITTZtvZCrsnl9IQFKM1Ky8H/BjoHv\\r\\n         jUL+fEuQTQUynp0S6yu/Kj9uvFRIXjhdxgHaGGTRMVtg/SE0tc62b8AxCckxHwrhS94G\\r\\n         ac9w== 
action_result.data.\*.email_headers.\*.feedback_id | string |  |   P-58-0:C10004962:M110105571-en-US:gamma 
action_result.data.\*.email_headers.\*.from | string |  `email`  |   Test Payments <payments-noreply@test.com> 
action_result.data.\*.email_headers.\*.message_id | string |  |   <e3d885faf2cc04f261d3874bafe2dc8afc44a230-10004962-100081937@test.com> 
action_result.data.\*.email_headers.\*.mime_version | string |  |   1.0 
action_result.data.\*.email_headers.\*.received | string |  |   by 2002:a05:7110:5426:b029:b6:addf:f84f with SMTP id i6csp1772142geg;\\r\\n        Sat, 1 May 2021 20:26:21 -0700 (PDT)\\nfrom mail-il1-x147.test.com (mail-il1-x147.test.com. [2607:f8b0:4864:20::147])\\r\\n        by mx.test.com with ESMTPS id b3si9189274iot.55.2021.05.01.20.26.20\\r\\n        for <admin@testcorp.biz>\\r\\n        (version=TLS1_3 cipher=TLS_AES_128_GCM_SHA256 bits=128/128);\\r\\n        Sat, 01 May 2021 20:26:21 -0700 (PDT)\\nby mail-il1-x147.test.com with SMTP id d3-20020a9287430000b0290181f7671fa1so1924912ilm.9\\r\\n        for <admin@testcorp.biz>; Sat, 01 May 2021 20:26:20 -0700 (PDT) 
action_result.data.\*.email_headers.\*.received_spf | string |  |   pass (test.com: domain of 33buoybakbvceznb3cih-cdg3ean5dd5a3.1dbz2b7c63gbzc1dge.07o@scoutcamp.bounces.test.com designates 2607:f8b0:4864:20::147 as permitted sender) client-ip=2607:f8b0:4864:20::147; 
action_result.data.\*.email_headers.\*.reply_to | string |  |   Test Payments <payments-noreply@test.com> 
action_result.data.\*.email_headers.\*.return_path | string |  |   <33BuOYBAKBVcEzNB3CIH-CDG3EAN5DD5A3.1DBz2B7C63GBzC1DGE.07O@scoutcamp.bounces.test.com> 
action_result.data.\*.email_headers.\*.subject | string |  |   Test Workspace: Your invoice is available for hermancorp.biz 
action_result.data.\*.email_headers.\*.to | string |  `email`  |   admin@testcorp.biz 
action_result.data.\*.email_headers.\*.x_gm_message_state | string |  |   AOAM532Nl7MnWYp7qLuC9ClJDlpx6s+kHPwvU7xiPvCBqzdGM36I9tqf\\r\\n	LKCzGlzGEDydpiA= 
action_result.data.\*.email_headers.\*.x_google_dkim_signature | string |  |   v=1; a=rsa-sha256; c=relaxed/relaxed;\\r\\n        d=1e100.net; s=20161025;\\r\\n        h=x-gm-message-state:mime-version:date:reply-to:feedback-id\\r\\n         :message-id:subject:from:to;\\r\\n        bh=z/kirlEQ2aVcgVc3qMye/grykWqFcVQv0Yr0y2Mbewo=;\\r\\n        b=tJdaiPfRyc4eMG2Yen3mdbA6h41cGBrVQ4yzJakfk1H+apl/RJq7xh1IYQ7+PXM3oH\\r\\n         IOzDgY6u9CQ2hyEZy6Yu1xuWtHwLYuTZl0iauzV9ve7tvDgXlxPWI7DryZrhge7J8GA/\\r\\n         dHFVfWU6LS9yBSjhAoiekws3Vhje30lg4kShkKoNXlH7QxkrEOYn5i31s5Gelx9E6m1f\\r\\n         Q3bs3xF4BbtyF52berodAZsS9tachQGHG2p124Y9mmLzPRsqi1fMCoXbHCXd0BxIFskJ\\r\\n         twUm+JQnxbX5N/q+MLWifUWYJ6fGkybAZ061JX6JgBp/2RMu0r5E48Q+0lHiUlenj4s6\\r\\n         TNkg== 
action_result.data.\*.email_headers.\*.x_google_id | string |  |   13608031 
action_result.data.\*.email_headers.\*.x_google_smtp_source | string |  |   ABdhPJyqpOGx6rwHwgtf1rUzc0U3BHjsBbH/I0nyqUnNdTHl957rDEZYB4OI7ovt9lbR1X2xjbTp 
action_result.data.\*.email_headers.\*.x_notifications | string |  |   GAMMA:<e3d885faf2cc04f261d3874bafe2dc8afc44a230-10004962-100081937@test.com> 
action_result.data.\*.email_headers.\*.x_notifications_bounce_info | string |  |   AXvZQxfkTaodaY87TxIiHBg1x3Tx1_dOt6hnshnCtGR9SITP7OmGWvNCCGRT9Tyj_2w4772syOqKk6YvkLiVDIng-Xq1VSkKuRhYdIs_aDGwcaNoVypJD4jay6E4wMyaK98V5kVnJjyqjdDHzqLvNjLlPyD_4FB_zfEH2Rn9I9vktuDD8oFQ9PKrZ23DD3xi9OZTp3lJf8nQe0bBukIV3MRyNw-xI7_iB30Auq1WVoyoQ0qTthrFGZuKDHGjkdblAV5LSJwNjAwNjA0MDQxNTM1NTk2OTMzMg 
action_result.data.\*.email_headers.\*.x_received | string |  |   by 2002:a05:6e02:102:: with SMTP id t2mr5411682ilm.182.1619925981145;\\r\\n        Sat, 01 May 2021 20:26:21 -0700 (PDT)\\nby 2002:a05:6e02:d53:: with SMTP id h19mr10186694ilj.232.1619925980569;\\r\\n Sat, 01 May 2021 20:26:20 -0700 (PDT) 
action_result.data.\*.from | string |  `email`  |   Test Payments <payments-noreply@test.com> 
action_result.data.\*.historyId | string |  |   62313 
action_result.data.\*.id | string |  |   1792b1cd66228bf2 
action_result.data.\*.internalDate | string |  |   1619925980000 
action_result.data.\*.labelIds | string |  |   INBOX 
action_result.data.\*.parsed_html_body | string |  |  
action_result.data.\*.parsed_plain_body | string |  |  
action_result.data.\*.sizeEstimate | numeric |  |   55260 
action_result.data.\*.snippet | string |  |   Your test Workspace monthly invoice is available. Please find the PDF document attached at the bottom of this email. IMPORTANT: The balance will be automatically charged so you don&#39;t need to take 
action_result.data.\*.subject | string |  |   Test Workspace: Your invoice is available for hermancorp.biz 
action_result.data.\*.threadId | string |  |   1792b1cd66228bf2 
action_result.data.\*.to | string |  `email`  |   admin@testcorp.biz 
action_result.summary.total_messages_returned | numeric |  |   1 
action_result.message | string |  |   Total messages returned: 1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'get user'
Retrieve user details via email address

Type: **investigate**  
Read only: **False**

Action uses the GMail API to search in a user's mailbox (specified in the <b>email</b> parameter). <br>Requires the users authorization and the following scope: <b>https://www.googleapis.com/auth/gmail.readonly</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** |  required  | User's Email (User to search) | string |  `email` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.message | string |  |   Successfully retrieved user details 
action_result.parameter.email | string |  `email`  |   admin@testcorp.biz 
action_result.data.\*.emailAddress | string |  `email`  |   admin@testcorp.biz 
action_result.data.\*.messagesTotal | numeric |  |   1234 
action_result.data.\*.threadsTotal | numeric |  |   567 
action_result.data.\*.historyId | string |  |   987654321 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'send email'
Send emails

Type: **contain**  
Read only: **False**

Action uses the GMail API. Requires authorization with the following scope: <b>https://www.googleapis.com</b>, <b>https://www.googleapis.com/auth/gmail.settings.sharing</b> and <b>https://www.googleapis.com/auth/admin.directory.user.alias</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from** |  optional  | From field | string |  `email` 
**to** |  required  | List of recipients email addresses | string |  `email` 
**subject** |  required  | Message Subject | string | 
**cc** |  optional  | List of recipients email addresses to include on cc line | string |  `email` 
**bcc** |  optional  | List of recipients email addresses to include on bcc line | string |  `email` 
**reply_to** |  optional  | Address that should recieve replies to the sent email | string |  `email` 
**headers** |  optional  | Serialized json dictionary. Additional email headers to be added to the message | string | 
**body** |  required  | Html rendering of message | string | 
**attachments** |  optional  | List of vault ids of files to attach to the email. Vault id is used as content id | string |  `sha1`  `vault id` 
**alias_email** |  optional  | Custom from send-as alias email | string |  `email` 
**alias_name** |  optional  | Custom from send-as alias name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.alias_email | string |  `email`  |   test@testdomain.abc.com 
action_result.parameter.alias_name | string |  |  
action_result.parameter.attachments | string |  `sha1`  `vault id`  |   da39a3ee5e6b4b0d3255bfef95601890afd80709 
action_result.parameter.bcc | string |  `email`  |   test@testdomain.abc.com 
action_result.parameter.reply_to | string |  `email`  |  
action_result.parameter.body | string |  |   <html><body><p>Have a good time with these.</p></body></html> 
action_result.parameter.cc | string |  `email`  |   test@testdomain.abc.com 
action_result.parameter.from | string |  `email`  |   test@testdomain.abc.com 
action_result.parameter.headers | string |  |   {"x-custom-header":"Custom value"} 
action_result.parameter.subject | string |  |   Example subject 
action_result.parameter.to | string |  `email`  |   test@testdomain.abc.com 
action_result.data.\*.id | string |  |   rfc822t1500000000t3a1d2e0fghijklm 
action_result.data.\*.threadId | string |  |   16d1234567890abcdef 
action_result.data.\*.labelIds | string |  |   INBOX 
action_result.message | string |  |   All the provided emails were already deleted 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 