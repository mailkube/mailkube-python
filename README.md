# mailkube

[![CI](https://github.com/mailkube/mailkube/actions/workflows/ci.yml/badge.svg)](https://github.com/mailkube/mailkube/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mailkube)](https://pypi.org/project/mailkube/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-purple.svg)](CODE_OF_CONDUCT.md)

The official Python SDK for [Mailkube](https://mailkube.com) — send transactional email and verify
inbound webhooks. Fully typed, sync **and** async, Python 3.12+.

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
    api_key="mk_...",                    # or set MAILKUBE_API_KEY
    base_url="https://api.mailkube.com/mta/v1/",  # or set MAILKUBE_BASE_URL; this is the default
    timeout=30.0,                        # per-request timeout in seconds
)
```

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
`reply_to`, `headers`, `attachments`, `template_id`, `topic`, `idempotency_key`, …).

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
API error exposes `.error_name`, `.message`, and `.status_code`.

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

An unrecognized event `type` is returned as `UnknownEvent` instead of raising, so a new server event
type never forces an SDK upgrade on receivers.

## Logging

Silent by default. Turn on request/response logging with:

```python
import mailkube

mailkube.enable_logging(level="DEBUG")
```

or set the `MAILKUBE_LOG` environment variable. `Authorization` and `Idempotency-Key` headers are
redacted from log output.

## Client lifecycle

Create one client and reuse it. `Mailkube` is thread-safe; `AsyncMailkube` is bound to its event
loop. Use the client as a (async) context manager, or call `.close()` / `.aclose()`.

## More examples

Runnable scripts in [`examples/`](examples):

- [`simple_send.py`](examples/simple_send.py) — basic sync send
- [`async_send.py`](examples/async_send.py) — async send, then thread a reply onto it
- [`send_with_attachments.py`](examples/send_with_attachments.py) — attach a file from raw bytes
- [`send_with_template.py`](examples/send_with_template.py) — send from a saved template
- [`webhook_receiver_flask.py`](examples/webhook_receiver_flask.py) — verify and dispatch webhooks
  in a Flask app

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and the quality gates every change
must pass. Security issues: see [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE) © 2026 Mailtactic, Corp.
