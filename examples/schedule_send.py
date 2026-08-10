"""Schedule a send for later instead of delivering it now.

    MAILKUBE_API_KEY=mk_... python examples/schedule_send.py
"""

from datetime import UTC, datetime, timedelta

from mailkube import Mailkube

with Mailkube() as client:
    email = client.emails.send(
        from_="Acme <hello@yourdomain.com>",
        to="customer@example.com",
        subject="Your weekly digest",
        html="<p>Here's what happened this week.</p>",
        # An ISO-8601 string with an offset works too: "2026-08-20T07:00:00Z".
        scheduled_at=datetime.now(UTC) + timedelta(hours=2),
    )

    print("scheduled:", email.is_scheduled)
    print("id:       ", email.id)
    print("status:   ", email.status)
    print("due at:   ", email.scheduled_at)
