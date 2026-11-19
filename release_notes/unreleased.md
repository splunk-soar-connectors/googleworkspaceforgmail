**Unreleased**

* Require Splunk SOAR SDK 7.2.4 to ingest email attachments while preserving threat-analysis and automation flags.
* Report authentication and mailbox/label setup failures with safe reason codes, without exposing server responses, credentials, or mailbox names. Network failures remain generic; existing polling checkpoints are preserved.
