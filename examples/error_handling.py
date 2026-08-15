"""The errors you will actually hit, and how to tell them apart.

    MAILKUBE_API_KEY=mk_... python examples/error_handling.py

Every failure arrives as a ``MailkubeError`` subclass carrying ``error_name`` — the server's stable
machine-readable name — alongside ``status_code``. Branch on ``error_name`` (an ``ErrorName``
enum), never on the human-readable message, which is free to change.

Nothing here sends a message: each call is designed to be refused.
"""

import os
from datetime import UTC, datetime, timedelta

from mailkube import ErrorName, Mailkube, MailkubeError

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

failures = 0


def expect(label: str, expected: ErrorName, call) -> None:
    """Run ``call`` and report whether it failed with ``expected``."""
    global failures
    try:
        call()
    except MailkubeError as exc:
        ok = exc.error_name == expected
        print(f"{'ok  ' if ok else 'BAD '} {label}: {exc.error_name} ({exc.status_code})")
        if not ok:
            failures += 1
        return
    print(f"BAD  {label}: expected {expected}, but the call succeeded")
    failures += 1


with Mailkube() as client:
    # A message with no body at all: html, text and template_id are mutually required-one-of.
    expect(
        "missing body",
        ErrorName.VALIDATION_ERROR,
        lambda: client.emails.send(from_=SENDER, to=RECIPIENT, subject="No body"),
    )

    # scheduled_at must carry an offset and be strictly in the future.
    expect(
        "past scheduled_at",
        ErrorName.VALIDATION_ERROR,
        lambda: client.emails.send(
            from_=SENDER,
            to=RECIPIENT,
            subject="Yesterday",
            text="...",
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
        ),
    )

    # batch_id is a grouping label for scheduled sends and means nothing without scheduled_at.
    expect(
        "batch_id without scheduled_at",
        ErrorName.VALIDATION_ERROR,
        lambda: client.emails.send(
            from_=SENDER, to=RECIPIENT, subject="Ungrouped", text="...", batch_id="b1"
        ),
    )

    # A sent email has left the scheduled collection, so filtering for it is a contract error
    # rather than an empty page — the distinction tells you your assumption was wrong.
    expect(
        'list status "sent"',
        ErrorName.VALIDATION_ERROR,
        lambda: client.scheduled_emails.list(status="sent"),
    )

# A bad key is refused identically whether it is malformed, unknown or absent, so nothing about
# the key space leaks.
with Mailkube(api_key="mk_notarealkey_" + "0" * 64) as anonymous:
    expect(
        "bad api key",
        ErrorName.INVALID_API_KEY,
        lambda: anonymous.emails.send(from_=SENDER, to=RECIPIENT, subject="Nope", text="..."),
    )

if failures:
    raise SystemExit(f"{failures} case(s) did not behave as documented")
print("all error cases behaved as documented")
