# Testing ES polling checkpoints

The connector stages source progress before yielding each finding. Unprocessed
message IDs and API continuations stay in ingest state so the SDK can checkpoint
processed batches, including skipped failures in an initial latest-first
window. After bounded SDK retries, rejected findings do not replay on the next
poll. Connector code does not retry ES requests itself.

The connector requires published Splunk SOAR SDK 7.2.2 or later. The commands
below use the released version pinned in `uv.lock`.

```sh
uv run --frozen --python 3.13 pytest -q
```

`tests/test_es_poll_checkpoint.py` exercises the real SDK decorator and connector
polling handler with simulated mailbox responses and finding HTTP responses.
Upload preparation is stubbed: these tests establish checkpoint behavior, not
live upload, association, or SAA behavior. Transient finding failures exercise
the SDK retries before verifying that rejected emails are skipped and later
messages continue without replay. Individual email read/parse/build failures are
also tested. Mailbox connection and listing failures still stop the poll.

For Python 3.15, use a separate environment and a compatible test runner without
changing the connector's existing pytest constraint:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/connector-checkpoint-py315 \
  uv run --frozen --python 3.15 --no-dev \
  --with 'pytest>=9,<10' --with pytest-mock pytest -q
```

Live ES polling additionally requires the matching ingestion runtime. An ad-hoc
action invocation is not a semantic ingestion run.

Individual failed emails are skipped with their ID and error category in warning
logs, without message contents or upstream error text. Skipped messages are not
automatically replayed, so data can be lost; this change adds no dead letter
queue. Source failures before a message can be identified still stop polling.

Connector-local log filters redact released SDK parser debug details and HTTPX
request URLs while retaining debug events and HTTP methods/statuses. SDK source
is unchanged. Regression tests exercise real parser logging and HTTPX request
logging with simulated secrets at DEBUG/INFO levels.
