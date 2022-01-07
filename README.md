[comment]: # "Auto-generated SOAR connector documentation"
# G Suite for GMail

Publisher: Splunk  
Connector Version: 2\.3\.5  
Product Vendor: Google  
Product Name: GMail  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 4\.10\.0\.40961  

Integrates with G Suite for various investigative and containment actions

[comment]: # " File: readme.md"
[comment]: # "  Copyright (c) 2017-2021 Splunk Inc."
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
    **More controls** from the gray bar at the bottom of the page, then select **Security** from the
    list of controls. If you can't see the controls, make sure you're signed in as an administrator
    for the domain.
-   Select **Show more** and then **Advanced settings** from the list of options.
-   Select **Manage API client access** in the **Authentication** section.
-   In the **Client Name** field enter the service account's **Client ID** . You can find your
    service account's client ID on the [Service accounts
    page](https://console.developers.google.com/permissions/serviceaccounts) or in the service
    account JSON file (key named **client_id** ).
-   In the **One or More API Scopes** field enter the list of scopes that you wish to grant access
    to the App. For example, to enable all the scopes required by this app enter:
    https://mail.google.com/, https://www.googleapis.com/auth/admin.directory.user,
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
**login\_email** |  required  | string | Login \(Admin\) email
**key\_json** |  required  | password | Contents of Service Account JSON file
**label** |  optional  | string | Mailbox Label \(folder\) to be polled
**ingest\_manner** |  optional  | string | How to ingest
**first\_run\_max\_emails** |  optional  | numeric | Maximum Containers for scheduled polling first time
**max\_containers** |  optional  | numeric | Maximum Containers for scheduled polling
**extract\_attachments** |  optional  | boolean | Extract Attachments
**extract\_urls** |  optional  | boolean | Extract URLs
**extract\_ips** |  optional  | boolean | Extract IPs
**extract\_domains** |  optional  | boolean | Extract Domain Names
**extract\_hashes** |  optional  | boolean | Extract Hashes
**download\_eml\_attachments** |  optional  | boolean | Download EML attachments

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  
[list users](#action-list-users) - Get the list of users  
[run query](#action-run-query) - Search emails with query/filtering options  
[delete email](#action-delete-email) - Delete emails  
[on poll](#action-on-poll) - Callback action for the on\-poll ingest functionality  
[get email](#action-get-email) - Retrieve email details via internet message id  

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

Action uses the Admin SDK API to get a list of users\. Requires authorization with the following scope\: <b>https\://www\.googleapis\.com/auth/admin\.directory\.user</b>\.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'list users'
Get the list of users

Type: **investigate**  
Read only: **True**

Action uses the Admin SDK API to get a list of users\. Requires authorization with the following scope\: <b>https\://www\.googleapis\.com/auth/admin\.directory\.user</b>\.<br>The action will limit the number of users returned to <b>max\_items</b> or \(if not specified\) 500\. If the system has any more users, a next page token will be returned in <b>action\_result\.summary\.next\_page\_token</b>\. Use this value as input to <b>page\_token</b> in subsequent calls to <b>list users</b>\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max\_items** |  optional  | Max users to get \(max 500\) | numeric | 
**page\_token** |  optional  | Token to specify next page in list | string |  `gsuite page token` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.max\_items | numeric | 
action\_result\.parameter\.page\_token | string |  `gsuite page token` 
action\_result\.data\.\*\.agreedToTerms | boolean | 
action\_result\.data\.\*\.archived | boolean | 
action\_result\.data\.\*\.changePasswordAtNextLogin | boolean | 
action\_result\.data\.\*\.creationTime | string | 
action\_result\.data\.\*\.customerId | string | 
action\_result\.data\.\*\.emails\.\*\.address | string |  `email` 
action\_result\.data\.\*\.emails\.\*\.primary | boolean | 
action\_result\.data\.\*\.emails\.\*\.type | string | 
action\_result\.data\.\*\.etag | string | 
action\_result\.data\.\*\.id | string | 
action\_result\.data\.\*\.includeInGlobalAddressList | boolean | 
action\_result\.data\.\*\.ipWhitelisted | boolean | 
action\_result\.data\.\*\.isAdmin | boolean | 
action\_result\.data\.\*\.isDelegatedAdmin | boolean | 
action\_result\.data\.\*\.isEnforcedIn2Sv | boolean | 
action\_result\.data\.\*\.isEnrolledIn2Sv | boolean | 
action\_result\.data\.\*\.isMailboxSetup | boolean | 
action\_result\.data\.\*\.kind | string | 
action\_result\.data\.\*\.lastLoginTime | string | 
action\_result\.data\.\*\.name\.familyName | string | 
action\_result\.data\.\*\.name\.fullName | string | 
action\_result\.data\.\*\.name\.givenName | string | 
action\_result\.data\.\*\.nonEditableAliases | string |  `email` 
action\_result\.data\.\*\.orgUnitPath | string | 
action\_result\.data\.\*\.phones\.\*\.type | string | 
action\_result\.data\.\*\.phones\.\*\.value | string | 
action\_result\.data\.\*\.primaryEmail | string |  `email` 
action\_result\.data\.\*\.recoveryEmail | string | 
action\_result\.data\.\*\.suspended | boolean | 
action\_result\.summary\.next\_page\_token | string |  `gsuite page token` 
action\_result\.summary\.total\_users\_returned | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'run query'
Search emails with query/filtering options

Type: **investigate**  
Read only: **True**

Action uses the GMail API to search in a users mailbox \(specified in the <b>email</b> parameter\)\.<br>Requires authorization with the following scope\: <b>https\://www\.googleapis\.com/auth/gmail\.readonly</b>\.<br>If none of the filtering parameters are specified the action will return all emails in the mailbox\. If the <b>query</b> parameter is specified, all other filtering parameters are ignored\.<br>The query parameter uses the same filtering options \(operators\) as the GMail search box\. A brief description of these can be found <a href="https\://support\.google\.com/mail/answer/7190?hl=en">at this link</a>\.<br>To page through results, execute the action without a <b>page\_token</b> parameter and a valid <b>max\_results</b> value\. If the query matches more than <b>max\_results</b>, the action will return a value in the <b>action\_result\.summary\.next\_page\_token</b> data path\. This value should be used as the input value to the <b>page\_token</b> parameter in the next call to <b>run query</b> to get the next set of results\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** |  required  | User's Email \(Mailbox to search in\) | string |  `email` 
**label** |  optional  | Label \(to search in\) | string |  `gmail label` 
**subject** |  optional  | Substring to search in Subject | string | 
**sender** |  optional  | Sender Email address to match | string |  `email` 
**body** |  optional  | Substring to search in Body | string | 
**internet\_message\_id** |  optional  | Internet Message ID | string |  `internet message id` 
**query** |  optional  | Gmail Query string | string | 
**max\_results** |  optional  | Max Results | numeric | 
**page\_token** |  optional  | Next page token | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.body | string | 
action\_result\.parameter\.email | string |  `email` 
action\_result\.parameter\.internet\_message\_id | string |  `internet message id` 
action\_result\.parameter\.label | string |  `gmail label` 
action\_result\.parameter\.max\_results | numeric | 
action\_result\.parameter\.page\_token | string | 
action\_result\.parameter\.query | string | 
action\_result\.parameter\.sender | string |  `email` 
action\_result\.parameter\.subject | string | 
action\_result\.data\.\*\.delivered\_to | string |  `email` 
action\_result\.data\.\*\.from | string |  `email` 
action\_result\.data\.\*\.historyId | string | 
action\_result\.data\.\*\.id | string |  `gmail email id` 
action\_result\.data\.\*\.internalDate | string | 
action\_result\.data\.\*\.labelIds | string | 
action\_result\.data\.\*\.message\_id | string |  `internet message id` 
action\_result\.data\.\*\.sizeEstimate | numeric | 
action\_result\.data\.\*\.snippet | string | 
action\_result\.data\.\*\.subject | string | 
action\_result\.data\.\*\.threadId | string | 
action\_result\.data\.\*\.to | string |  `email` 
action\_result\.summary\.next\_page\_token | string | 
action\_result\.summary\.total\_messages\_returned | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'delete email'
Delete emails

Type: **contain**  
Read only: **False**

Action uses the GMail API\. Requires authorization with the following scope\: <b>https\://mail\.google\.com</b>\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Message IDs to delete\(Comma separated IDs allowed\) | string |  `gmail email id` 
**email** |  required  | Email of the mailbox owner | string |  `email` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.email | string |  `email` 
action\_result\.parameter\.id | string |  `gmail email id` 
action\_result\.data | string | 
action\_result\.summary\.deleted\_emails | string |  `gmail email id` 
action\_result\.summary\.ignored\_ids | string |  `gmail email id` 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'on poll'
Callback action for the on\-poll ingest functionality

Type: **ingest**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start\_time** |  optional  | Parameter Ignored in this app | numeric | 
**end\_time** |  optional  | Parameter Ignored in this app | numeric | 
**container\_id** |  optional  | Parameter Ignored in this app | string | 
**container\_count** |  required  | Maximum number of emails to ingest | numeric | 
**artifact\_count** |  required  | Maximum number of artifact to ingest | numeric | 

#### Action Output
No Output  

## action: 'get email'
Retrieve email details via internet message id

Type: **investigate**  
Read only: **False**

Action uses the GMail API to search in a user's mailbox \(specified in the <b>email</b> parameter\)\. Use the <b>run query</b> action to retrieve <b>internet message id</b>\.<br>Use <b>extract attachments</b> parameter to add attachments to vault and add corresponding vault artifacts\.<br>Requires authorization with the following scope\: <b>https\://www\.googleapis\.com/auth/gmail\.readonly</b>\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** |  required  | User's Email \(Mailbox to search\) | string |  `email` 
**internet\_message\_id** |  required  | Internet Message ID | string |  `internet message id` 
**extract\_attachments** |  optional  | Add attachments to vault and create vault artifacts | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.email | string |  `email` 
action\_result\.parameter\.extract\_attachments | numeric | 
action\_result\.parameter\.internet\_message\_id | string |  `internet message id` 
action\_result\.data\.\*\.email\_headers\.\*\.arc\_authentication\_results | string | 
action\_result\.data\.\*\.email\_headers\.\*\.arc\_message\_signature | string | 
action\_result\.data\.\*\.email\_headers\.\*\.arc\_seal | string | 
action\_result\.data\.\*\.email\_headers\.\*\.authentication\_results | string | 
action\_result\.data\.\*\.email\_headers\.\*\.content\_disposition | string | 
action\_result\.data\.\*\.email\_headers\.\*\.content\_transfer\_encoding | string | 
action\_result\.data\.\*\.email\_headers\.\*\.content\_type | string | 
action\_result\.data\.\*\.email\_headers\.\*\.date | string | 
action\_result\.data\.\*\.email\_headers\.\*\.delivered\_to | string |  `email` 
action\_result\.data\.\*\.email\_headers\.\*\.dkim\_signature | string | 
action\_result\.data\.\*\.email\_headers\.\*\.feedback\_id | string | 
action\_result\.data\.\*\.email\_headers\.\*\.from | string |  `email` 
action\_result\.data\.\*\.email\_headers\.\*\.message\_id | string | 
action\_result\.data\.\*\.email\_headers\.\*\.mime\_version | string | 
action\_result\.data\.\*\.email\_headers\.\*\.received | string | 
action\_result\.data\.\*\.email\_headers\.\*\.received\_spf | string | 
action\_result\.data\.\*\.email\_headers\.\*\.reply\_to | string | 
action\_result\.data\.\*\.email\_headers\.\*\.return\_path | string | 
action\_result\.data\.\*\.email\_headers\.\*\.subject | string | 
action\_result\.data\.\*\.email\_headers\.\*\.to | string |  `email` 
action\_result\.data\.\*\.email\_headers\.\*\.x\_gm\_message\_state | string | 
action\_result\.data\.\*\.email\_headers\.\*\.x\_google\_dkim\_signature | string | 
action\_result\.data\.\*\.email\_headers\.\*\.x\_google\_id | string | 
action\_result\.data\.\*\.email\_headers\.\*\.x\_google\_smtp\_source | string | 
action\_result\.data\.\*\.email\_headers\.\*\.x\_notifications | string | 
action\_result\.data\.\*\.email\_headers\.\*\.x\_received | string | 
action\_result\.data\.\*\.from | string |  `email` 
action\_result\.data\.\*\.historyId | string | 
action\_result\.data\.\*\.id | string | 
action\_result\.data\.\*\.internalDate | string | 
action\_result\.data\.\*\.labelIds | string | 
action\_result\.data\.\*\.parsed\_html\_body | string | 
action\_result\.data\.\*\.parsed\_plain\_body | string | 
action\_result\.data\.\*\.sizeEstimate | numeric | 
action\_result\.data\.\*\.snippet | string | 
action\_result\.data\.\*\.subject | string | 
action\_result\.data\.\*\.threadId | string | 
action\_result\.data\.\*\.to | string |  `email` 
action\_result\.summary\.total\_messages\_returned | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 