**Unreleased**

* Continue ES ingestion past failed emails and preserve unread IDs and continuations at each checkpoint.
* Require Splunk SOAR SDK 7.2.2 to skip failed findings and advance ES ingestion checkpoints.
* Skip individual email processing failures with safe diagnostics instead of blocking later messages.
* Add concise email failure diagnostics with stage, safe reason, HTTP status, and validation field where available.
* Keep message data, attachment names, exception text and signed URLs out of ES ingestion diagnostics, including SDK parser debug and HTTP request logs.
