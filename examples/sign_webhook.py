"""Sign a payload the way the platform signs it, to build fixtures for your own tests.

    python examples/sign_webhook.py '{"type":"email.sent","data":{"id":"e1"}}'

Production code never signs — it verifies. This is for the other side of your test suite: when
you need a request that ``verify`` will accept, so you can exercise your handler without waiting
on a real delivery. Reimplementing the HMAC from the docs is the tempting alternative, and it is
how a fixture ends up agreeing with your reading of the prose instead of with the SDK.

``sign`` takes the timestamp you give it and does not judge its freshness, so an old capture
re-signs to exactly its original signature. The verifier still applies the 300s window, which is
why the fixture written below stamps *now*.
"""

import json
import sys
from datetime import UTC, datetime

from mailkube import sign, verify_signature

SECRET = "whsec_example_do_not_use_in_production"
WEBHOOK_ID = "wh_example_1"

# A complete envelope, not a stub: the fixture printed below is meant to feed
# examples/verify_webhook.py, which parses as well as verifies, and a partial body fails there.
DEFAULT_EVENT = {
    "type": "email.delivered",
    "created_at": "2026-01-01T00:00:00Z",
    "data": {
        "email_id": "e1",
        "created_at": "2026-01-01T00:00:00Z",
        "domain": "acme.com",
        "subject": "Hi",
        "to": ["b@y.com"],
        "from": "a@x.com",
        "delivery": {"recipient": "b@y.com", "timestamp": "2026-01-01T00:00:01Z"},
    },
}

body = sys.argv[1].encode() if len(sys.argv) > 1 else json.dumps(DEFAULT_EVENT).encode()
timestamp = datetime.now(UTC).isoformat()

headers = {
    "X-Webhook-Id": WEBHOOK_ID,
    "X-Webhook-Ts": timestamp,
    "X-Webhook-Sig": sign(WEBHOOK_ID, timestamp, body, SECRET),
}

# Round-trip it, so the file proves its own output rather than asserting it. Deliberately
# verify_signature and not verify: signing is what this example is about, and verify would also
# parse the body against the event schema, failing on any payload you pass that is not a complete
# envelope. The signature does not care what the bytes mean.
verify_signature(body, headers, SECRET)
print(f"signature verifies over {len(body)} bytes")

# The fixture shape examples/verify_webhook.py reads back. Note `body` is the raw string, not a
# nested object: re-serializing parsed JSON changes the bytes and the signature stops matching.
fixture = {
    "name": "signed-locally",
    "secret": SECRET,
    "headers": headers,
    "body": body.decode(),
    "must_verify": True,
}
print(json.dumps(fixture, indent=2))
