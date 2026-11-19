## ES Polling Setup Diagnostics

With Splunk SOAR SDK 7.2.4 or newer, setup failures report
`reason=authentication` for rejected credentials or authorization, and
`reason=mailbox` for a missing or inaccessible mailbox/label. The run remains
failed even if no findings were produced. Server response bodies, credentials,
and mailbox names are omitted. Network failures are not labeled as bad credentials.
