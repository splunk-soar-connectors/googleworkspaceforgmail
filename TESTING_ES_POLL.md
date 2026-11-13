# Testing ES polling checkpoints

The connector stages source progress before yielding each finding. Unprocessed
message IDs and API continuations stay in ingest state so the SDK can checkpoint
successful batches and replay a failed batch, including an initial latest-first
window. Successful findings within a failed batch may be duplicated. Connector
code does not retry ES requests itself.

Build the SDK wheel from the neighbouring AR-2061 checkout, then run the full
connector suite against that wheel:

```sh
(cd ../splunk-soar-sdk && uv build --wheel --out-dir ../SDK_TEST_DIST)
SDK_WHEEL="../SDK_TEST_DIST/splunk_soar_sdk-7.1.3-py3-none-any.whl"
uv run --frozen --python 3.13 --with "$SDK_WHEEL" pytest -q
```

The filename reflects the current source version, not a published SDK release
containing these changes. Adjust it if the SDK version changes. No connector
dependency or lockfile change is required for the preview wheel.

`tests/test_es_poll_checkpoint.py` exercises the real SDK decorator and connector
polling handler with simulated mailbox responses and finding HTTP responses.
Upload preparation is stubbed: these tests establish checkpoint behavior, not
live upload, association, or SAA behavior. The new integration cases skip when
the installed SDK lacks the AR-2061 execution-context hook.

For Python 3.15, use a separate environment and a compatible test runner without
changing the connector's existing pytest constraint:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/connector-checkpoint-py315 \
  uv run --frozen --python 3.15 --no-dev --with "$SDK_WHEEL" \
  --with 'pytest>=9,<10' --with pytest-mock pytest -q
```

Live ES polling additionally requires the matching ingestion runtime. An ad-hoc
action invocation is not a semantic ingestion run.
