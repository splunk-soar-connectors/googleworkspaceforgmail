# Testing ES polling checkpoints

The connector stages source progress before yielding each finding. Unprocessed
message IDs and API continuations stay in ingest state so the SDK can checkpoint
successful batches and replay a failed batch, including an initial latest-first
window. Successful findings within a failed batch may be duplicated. Connector
code does not retry ES requests itself.

The connector requires the published Splunk SOAR SDK 7.2.1 or later. Run the full
suite with the released version pinned in `uv.lock`:

```sh
uv run --frozen --python 3.13 pytest -q
```

`tests/test_es_poll_checkpoint.py` exercises the real SDK decorator and connector
polling handler with simulated mailbox responses and finding HTTP responses.
Upload preparation is stubbed: these tests establish checkpoint behavior, not
live upload, association, or SAA behavior. Transient finding failures exercise
the SDK retries before verifying that the failed batch remains replayable.

For Python 3.15, use a separate environment and a compatible test runner without
changing the connector's existing pytest constraint:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/connector-checkpoint-py315 \
  uv run --frozen --python 3.15 --no-dev \
  --with 'pytest>=9,<10' --with pytest-mock pytest -q
```

Live ES polling additionally requires the matching ingestion runtime. An ad-hoc
action invocation is not a semantic ingestion run.
