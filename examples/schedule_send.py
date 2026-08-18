"""Schedule a send for later instead of delivering it now.

MAILKUBE_API_KEY=mk_... python examples/schedule_send.py
"""

import os
from datetime import UTC, datetime, timedelta

from mailkube import Mailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

with Mailkube() as client:
    email = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
        subject="Your weekly digest",
        html="<p>Here's what happened this week.</p>",
        # An ISO-8601 string with an offset works too: "2026-08-20T07:00:00Z".
        scheduled_at=datetime.now(UTC) + timedelta(hours=2),
    )

    print("scheduled:", email.is_scheduled)
    print("id:       ", email.id)
    print("status:   ", email.status)
    print("due at:   ", email.scheduled_at)
