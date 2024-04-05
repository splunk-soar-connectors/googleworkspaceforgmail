**Unreleased**

* [PAPP-33478] Multipart message parsing improvement. 
    * Implemented parsing nested attachments.
    * Fixed email attachments overriding main email metadata.
    * Added `extract_nested` action, which creates artifacts from attachments from nested email attachments. Works only when `extract_attachments` is set to `true`.
