"""Send against a mailing-list topic.

    MAILKUBE_API_KEY=mk_... python examples/send_with_topic.py [topic-slug]

A topic is a subscription group your recipients can opt out of individually, and ``topic`` is the
slug you configured for it (16 characters max). Sending under one means the unsubscribe link
removes the recipient from that topic rather than from everything you send.

The slug must already exist and be enabled on the sending domain's apex. An unknown or disabled
slug is rejected outright, BEFORE the message is charged or queued — so a typo costs you nothing,
but it does not silently fall back to sending untopiced either. The second half of this example
triggers that rejection on purpose.
"""

import os
import sys

from mailkube import APIError, ErrorName, Mailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")
TOPIC = sys.argv[1] if len(sys.argv) > 1 else "newsletter"

with Mailkube() as client:
    email = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
        subject=f'Sent under the "{TOPIC}" topic',
        html="<p>Unsubscribing from this removes you from this topic only.</p>",
        text="Unsubscribing from this removes you from this topic only.",
        topic=TOPIC,
    )
    print(f"sent: {email.id} under topic {TOPIC}")

    # The negative case: a slug that was never configured.
    try:
        client.emails.send(
            from_=SENDER,
            to=RECIPIENT,
            subject="This one never leaves the building",
            text="You should not be reading this.",
            topic="no-such-topic",
        )
        raise SystemExit("expected an unknown topic to be rejected, but it was accepted")
    except APIError as exc:
        if exc.error_name != ErrorName.TOPIC_NOT_FOUND:
            raise
        print("unknown topic correctly rejected:", exc.error_name)
