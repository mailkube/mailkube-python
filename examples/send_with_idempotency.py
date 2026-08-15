"""Retry a send safely with an idempotency key.

    MAILKUBE_API_KEY=mk_... python examples/send_with_idempotency.py

There are no built-in retries in this SDK, so retrying is your call — and a naive retry after a
timeout can send the same message twice, because a request that never returned may still have
succeeded. An idempotency key makes the retry safe: the server remembers the first response for
that key (24 hours by default) and replays it byte for byte instead of sending again.

The key is fingerprinted against the request body. Reusing a key with a DIFFERENT body is an error
rather than a silent replay, which is what stops a recycled key from swallowing a real message.
"""

import os
import time

from mailkube import Mailkube, MailkubeError

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

# In real code this is a stable id for the thing you are sending about — an order id, a job id —
# not a random value, otherwise a retry generates a new key and sends twice.
IDEMPOTENCY_KEY = f"order-{int(time.time())}"

params = {
    "from_": SENDER,
    "to": RECIPIENT,
    "subject": "Sent at most once",
    "html": "<p>Retrying this send cannot duplicate it.</p>",
    "text": "Retrying this send cannot duplicate it.",
    "idempotency_key": IDEMPOTENCY_KEY,
}

with Mailkube() as client:
    first = client.emails.send(**params)
    print("first  call:", first.id)

    # Pretend the first response never reached us and we retried.
    replay = client.emails.send(**params)
    print("replayed   :", replay.id)

    if first.id != replay.id:
        raise SystemExit(f"expected the same id back, got {first.id} then {replay.id} — that is a second send")
    print("same id returned: the retry was replayed, not resent")

    # Same key, different body: refused rather than replayed.
    try:
        client.emails.send(**{**params, "subject": "A different message entirely"})
        raise SystemExit("expected a reused key with a changed body to be rejected")
    except MailkubeError as exc:
        print("key reuse with a changed body correctly rejected:", exc.error_name)
