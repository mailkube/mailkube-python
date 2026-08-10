"""Schedule several sends under one batch, then move or cancel them as a unit.

    MAILKUBE_API_KEY=mk_... python examples/schedule_batch.py
"""

from datetime import UTC, datetime, timedelta

from mailkube import Mailkube

BATCH_ID = "digest-2026-08"
RECIPIENTS = ["a@example.com", "b@example.com", "c@example.com"]

with Mailkube() as client:
    due = datetime.now(UTC) + timedelta(hours=2)
    for recipient in RECIPIENTS:
        email = client.emails.send(
            from_="Acme <hello@yourdomain.com>",
            to=recipient,
            subject="Your weekly digest",
            html="<p>Here's what happened this week.</p>",
            scheduled_at=due,
            batch_id=BATCH_ID,
        )
        print("scheduled:", email.id)

    moved = client.scheduled_emails.batches.update(BATCH_ID, scheduled_at=due + timedelta(hours=2))
    print(f"moved {moved.rescheduled_count} to {moved.scheduled_at}")

    canceled = client.scheduled_emails.batches.cancel(BATCH_ID)
    print(f"canceled {canceled.canceled_count}")
