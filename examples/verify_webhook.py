"""Verify a webhook signature without running a server.

    python examples/verify_webhook.py path/to/fixture.json [more.json...]

The Flask receiver shows verification inside a framework. This one strips that away: it feeds
captured deliveries straight to ``verify`` so you can see exactly what is accepted and what is
not. Useful for testing your own handler against saved payloads.

A fixture is JSON: ``{secret, headers: {...}, body: "<raw body string>", must_verify: bool}``.
The body must be the EXACT bytes the server sent — re-serializing parsed JSON will not reproduce
the signature, which is the single most common integration bug.
"""

import json
import sys
from pathlib import Path

from mailkube import SignatureVerificationError, UnknownEvent, verify

paths = sys.argv[1:]
if not paths:
    raise SystemExit("usage: python examples/verify_webhook.py <fixture.json> [more.json...]")

failures = 0

for path in paths:
    fixture = json.loads(Path(path).read_text())
    raw_body = fixture["body"].encode()

    verified = False
    detail = ""
    try:
        event = verify(raw_body, fixture["headers"], fixture["secret"])
        verified = True
        # A type newer than this SDK version still arrives, just untyped.
        detail = f"event {'unknown' if isinstance(event, UnknownEvent) else event.type}"
    except SignatureVerificationError as exc:
        detail = str(exc)

    expected = fixture.get("must_verify") is True
    ok = verified == expected
    if not ok:
        failures += 1
    print(
        f"{'ok  ' if ok else 'BAD '} {fixture.get('name', path)}: "
        f"{'verified' if verified else 'rejected'} "
        f"(expected {'verified' if expected else 'rejected'}) {detail}"
    )

if failures:
    raise SystemExit(f"{failures} fixture(s) did not verify as expected")
print("all fixtures behaved as expected")
