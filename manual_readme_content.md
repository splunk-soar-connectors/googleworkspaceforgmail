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
