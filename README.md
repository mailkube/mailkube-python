# mailkube

[![CI](https://github.com/mailkube/mailkube-python/actions/workflows/ci.yml/badge.svg)](https://github.com/mailkube/mailkube-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mailkube)](https://pypi.org/project/mailkube/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-purple.svg)](CODE_OF_CONDUCT.md)

The official Python SDK for [Mailkube](https://mailkube.com) — send transactional email and verify
inbound webhooks. Fully typed, sync **and** async, Python 3.12+.

Full product and API documentation: [mailkube.com/docs](https://mailkube.com/docs).

## Install

```bash
pip install mailkube
# or
uv add mailkube
```

## Configuration

```python
from mailkube import Mailkube

client = Mailkube(
    api_key="mk_...",  # or set MAILKUBE_API_KEY
    base_url="https://api.mailkube.com/mta/v1/",  # or set MAILKUBE_BASE_URL; this is the default
    timeout=30.0,  # per-request timeout in seconds
    user_agent_suffix="my-cli/1.0.0",  # optional; identifies software wrapping this SDK
)
```

`user_agent_suffix` is for tools built *on* the SDK — a CLI, an internal service, a framework
integration. It is appended after this SDK's own token, which always leads:
`mailkube-python/1.5.0 my-cli/1.0.0`. Surrounding whitespace is trimmed; a value containing CR or
LF is ignored outright rather than cleaned up, because a header value that could split the request
is not one this package will send.

`AsyncMailkube` takes the same arguments. Both also accept `http_client=` — your own
`httpx.Client` / `httpx.AsyncClient` — if you need custom transport, proxies, or mTLS; the SDK
will not close a client you pass in.

## Send an email

```python
from mailkube import Mailkube

with Mailkube() as client:
    email = client.emails.send(
        from_="Acme <hello@yourdomain.com>",
        to="customer@example.com",
        cc="manager@example.com",
        reply_to="support@yourdomain.com",
        subject="Hello world",
        html="<p>It works!</p>",
    )
    print(email.id, email.message_id)
```

`from_` maps to the wire `from` field (`from` is a reserved keyword). Supply `html` and/or `text`, or
a `template_id` with `template_version` and `variables`. Attachments accept raw `bytes` or a base64
string. See [`SendEmailParams`](src/mailkube/types/params.py) for the full field list (`cc`, `bcc`,
`reply_to`, `headers`, `attachments`, `tags`, `template_id`, `topic`, `idempotency_key`, …).

### Async

```python
import asyncio
from mailkube import AsyncMailkube


async def main():
    async with AsyncMailkube() as client:
        email = await client.emails.send(
            from_="Acme <hello@yourdomain.com>",
            to="customer@example.com",
            subject="Hello world",
            html="<p>It works!</p>",
        )
        print(email.id)


asyncio.run(main())
```

### Idempotency

Pass `idempotency_key` to safely retry a send without risking a duplicate — sent as the
`Idempotency-Key` header, not in the body:

```python
email = client.emails.send(
    from_="Acme <hello@yourdomain.com>",
    to="customer@example.com",
    subject="Your receipt",
    html="<p>Thanks for your order.</p>",
    idempotency_key="order-4821-receipt",
)
print(email.idempotent_replayed)  # True if this key was already used
```

Reusing a key with a different payload raises `ConflictError` instead of silently sending the new
content.

### Errors

Every failure raises a subclass of `MailkubeError` (`AuthenticationError`, `InvalidRequestError`,
`RateLimitError` — which carries `.retry_after` — `ServerError`, `MailkubeConnectionError`, …). Each
API error exposes `.error_name`, `.message`, `.status_code`, and `.request_id` (quote it to support).

The HTTP status picks the exception class; `.error_name` says precisely what went wrong. Compare it
against the `ErrorName` constants — it stays a plain string, so an error name newer than your
installed SDK is still reported verbatim rather than crashing:

```python
from mailkube import ErrorName, InvalidRequestError

try:
    client.emails.send(...)
except InvalidRequestError as exc:
    if exc.error_name == ErrorName.QUOTA_EXCEEDED:
        ...
```

### Threading

Echo a message's `message_id` in the `In-Reply-To` / `References` headers of a later send:

```python
reply = client.emails.send(
    from_="Acme <hello@yourdomain.com>",
    to="customer@example.com",
    subject="Re: Your order",
    html="<p>An update.</p>",
    headers={"In-Reply-To": first.message_id, "References": first.message_id},
)
```

### Tags

Attach free-form `{"name": ..., "value": ...}` pairs to a send. The server denormalizes them
onto the sending-log, so you can filter, export, and dashboard by tag, and they ride along on
delivery webhooks:

```python
email = client.emails.send(
    from_="Acme <hello@yourdomain.com>",
    to="customer@example.com",
    subject="Welcome aboard",
    html="<p>Glad you're here.</p>",
    tags=[{"name": "campaign", "value": "spring24"}, {"name": "plan", "value": "pro"}],
)
```

Validation is server-side: names and values allow the `[A-Za-z0-9_-]` charset, a name is at most
16 characters and a value at most 32, values may be blank, at most 20 tags per send, and names must
be unique. Tag
values are not encrypted, so keep personal data out of them.

## Schedule an email

Pass `scheduled_at` and the message is accepted now and delivered later. Give it either an
ISO-8601 string **with a timezone offset** or a timezone-aware `datetime`; it must be in the
future and within your plan's scheduling horizon (30 days by default):

```python
from datetime import datetime, timedelta, UTC

email = client.emails.send(
    from_="Acme <hello@yourdomain.com>",
    to="customer@example.com",
    subject="Your weekly digest",
    html="<p>Here's what happened.</p>",
    scheduled_at=datetime.now(UTC) + timedelta(hours=2),
    batch_id="digest-2026-08",  # optional: group sends so you can move or cancel them together
)

email.is_scheduled  # True
email.status  # "scheduled"
email.scheduled_at  # "2026-08-20T07:00:00Z"
email.id  # use this to retrieve, reschedule, or cancel it
```

An immediate send is unaffected: `is_scheduled` is `False` and `status` / `scheduled_at` /
`batch_id` stay `None`. `batch_id` is only valid alongside `scheduled_at`.

## Manage scheduled emails

Until it is due, a scheduled email lives in `client.scheduled_emails`:

```python
email = client.scheduled_emails.get(email_id)
email = client.scheduled_emails.update(email_id, scheduled_at="2026-08-21T07:00:00Z")
client.scheduled_emails.cancel(email_id)
```

### Listing

`list` returns one page; `iter_all` walks every page lazily, following the links the API
returns:

```python
page = client.scheduled_emails.list(status="scheduled", batch_id="digest-2026-08")
page.data  # list[ScheduledEmail]
page.pagination.total_count
page.has_more

for email in client.scheduled_emails.iter_all(status=["scheduled", "failed"]):
    print(email.id, email.scheduled_at, email.subject)
```

| Filter | Accepts |
|---|---|
| `status` | `"scheduled"`, `"canceled"`, `"failed"` — one, or a list. A sent email has left the collection, so `"sent"` is a validation error, not an empty result. |
| `batch_id` | The batch label used at send time. |
| `scheduled_at_gte` / `scheduled_at_lte` | ISO-8601 with an offset, or an aware `datetime`. |
| `page` | 1-based page number. |

Timestamps come back as the verbatim ISO-8601 strings the API sent — call
`datetime.fromisoformat` if you want objects.

### Batches

Everything sent under one `batch_id` moves or cancels together:

```python
result = client.scheduled_emails.batches.update("digest-2026-08", scheduled_at="2026-08-21T07:00:00Z")
result.rescheduled_count  # 2

result = client.scheduled_emails.batches.cancel("digest-2026-08")
result.canceled_count  # 2
```

An unknown batch is a no-op reporting `0`, not an error.

`AsyncMailkube` exposes the identical surface — `await client.scheduled_emails.get(...)`, and
`async for email in client.scheduled_emails.iter_all(...)`.

### Scheduling errors

The names specific to this surface:

```python
from mailkube import ErrorName, InvalidRequestError, NotFoundError

try:
    client.scheduled_emails.cancel(email_id)
except NotFoundError:
    ...  # scheduled_email_not_found
except InvalidRequestError as exc:
    if exc.error_name == ErrorName.SCHEDULED_EMAIL_NOT_PENDING:
        ...  # already sent or canceled
```

Every API error also carries `.request_id` — quote it when contacting support.

## Verify webhooks

`webhooks.verify` is a pure, stdlib-only helper — call it in your request handler with the raw body:

```python
from mailkube import verify, SignatureVerificationError, UnknownEvent

try:
    event = verify(raw_body, request.headers, signing_secret)
except SignatureVerificationError:
    ...  # reject with 400

if isinstance(event, UnknownEvent):
    ...  # a newer event type than this SDK version knows about — still usable
else:
    print(event.type)
```

### Signing, for your tests

`sign` is the mirror of verification: give it the id, the timestamp, the raw body and the secret,
and it returns the `X-Webhook-Sig` value. Use it to build a delivery your handler will accept
without waiting on a real one. Reimplementing the HMAC from the description above is the
alternative, and it makes your fixtures agree with your reading of the docs rather than with this
SDK.

```python
from mailkube import sign

timestamp = datetime.now(UTC).isoformat()
headers = {
    "X-Webhook-Id": "wh_1",
    "X-Webhook-Ts": timestamp,
    "X-Webhook-Sig": sign("wh_1", timestamp, raw_body, signing_secret),
}
```

It signs the timestamp you hand it and does not check freshness, so replaying an old capture
reproduces its original signature exactly. Production code verifies; it does not sign.

An unrecognized event `type` is returned as `UnknownEvent` instead of raising, so a new server event
type never forces an SDK upgrade on receivers.

### Event types

This version parses the following into typed models. Anything else arrives as `UnknownEvent`.

| `type` | Model | `data` carries |
| --- | --- | --- |
| `email.sent` | `EmailSentEvent` | `sent` — accepted and spooled for transmission |
| `email.delivered` | `EmailDeliveredEvent` | `delivery` — accepted by the receiving server |
| `email.bounced` | `EmailBouncedEvent` | `bounce` — permanent failure, with code and reason |
| `email.delivery_delayed` | `EmailDeliveryDelayedEvent` | `delay` — transient failure, may still succeed |
| `email.scheduled` | `EmailScheduledEvent` | `scheduled` — accepted for later transmission |
| `email.failed` | `EmailFailedEvent` | `failed` — dropped at dispatch time, never transmitted |
| `email.suppressed` | `EmailSuppressedEvent` | `suppression` — recipients dropped before sending |
| `email.opened` | `EmailOpenedEvent` | `open` — tracking pixel loaded |
| `email.clicked` | `EmailClickedEvent` | `click` — tracked link followed |
| `domain.status` | `DomainStatusEvent` | a sending domain's status or onboarding transition |
| `webhook.status` | `WebhookStatusEvent` | a webhook endpoint's status transition |

Every `email.*` event shares a message-context block (`email_id`, `created_at`, `from`, `to`,
`subject`, `domain`, `tags`). `tags` echoes the tags attached at send time and is `[]` when there
were none. The four transaction-derived fields (`from`, `to`, `subject`, `domain`) can be `null`.

## Logging

Silent by default. Turn on request/response logging with:

```python
import mailkube

mailkube.enable_logging(level="DEBUG")
```

or set the `MAILKUBE_LOG` environment variable to a **level name** — `MAILKUBE_LOG=DEBUG`,
`MAILKUBE_LOG=WARNING`. It is a level, not an on/off switch; an unrecognized value falls back to
`DEBUG` rather than failing the import.

Each request logs its method, URL and headers; each response logs its status and `request_id`.
`Authorization` and `Idempotency-Key` headers are redacted. Message bodies are never logged at any
level, so no recipient address, subject or content reaches a log record.

## Client lifecycle

Create one client and reuse it. `Mailkube` is thread-safe; `AsyncMailkube` is bound to its event
loop. Use the client as a (async) context manager, or call `.close()` / `.aclose()`.

## More examples

Runnable scripts in [`examples/`](examples):

- [`simple_send.py`](examples/simple_send.py) — basic sync send
- [`async_send.py`](examples/async_send.py) — async send, then thread a reply onto it
- [`send_with_attachments.py`](examples/send_with_attachments.py) — attach a file from raw bytes
- [`send_with_tags.py`](examples/send_with_tags.py) — tag a send for filtering and reporting
- [`send_with_template.py`](examples/send_with_template.py) — send from a saved template
- [`schedule_send.py`](examples/schedule_send.py) — schedule a send, then inspect the ack
- [`manage_scheduled_emails.py`](examples/manage_scheduled_emails.py) — list, paginate,
  retrieve, reschedule and cancel
- [`schedule_batch.py`](examples/schedule_batch.py) — schedule a batch, then move or cancel it
  as a unit
- [`webhook_receiver_flask.py`](examples/webhook_receiver_flask.py) — verify and dispatch webhooks
  in a Flask app
- [`sign_webhook.py`](examples/sign_webhook.py) — sign a payload to build a fixture your own tests
  can replay

## Extending this SDK

Before adding a resource, verb, paginated listing or webhook event, read
[`.rules/SDK_CONTRACT.md`](.rules/SDK_CONTRACT.md) (the decisions every mailkube SDK shares) and
[`.rules/SDK_DESIGN.md`](.rules/SDK_DESIGN.md) (how they are realized in Python). Both carry a
step-by-step checklist, and every checklist ends with adding a runnable example.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and the quality gates every change
must pass. Security issues: see [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE) © 2026 Mail Tactic Corporation
