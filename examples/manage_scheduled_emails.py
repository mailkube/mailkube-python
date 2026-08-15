"""List, retrieve, reschedule and cancel scheduled emails.

    MAILKUBE_API_KEY=mk_... python examples/manage_scheduled_emails.py

The example schedules its own email under a unique batch id and then works only inside that
batch. That is deliberate: an unfiltered ``list``/``iter_all`` walks every pending send on the
account, which on a real account means paging through thousands of rows and then mutating
whichever one came back first. Scoping to a batch you just created keeps the example bounded,
repeatable, and safe to run against a live key.
"""

import os
import time
from datetime import UTC, datetime, timedelta

from mailkube import ErrorName, InvalidRequestError, Mailkube, NotFoundError

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

BATCH_ID = f"example-manage-{int(time.time())}"

with Mailkube() as client:
    created = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
        subject="Scheduled for management",
        html="<p>This one exists to be listed, moved and canceled.</p>",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        batch_id=BATCH_ID,
    )
    print(f"scheduled {created.id} in batch {BATCH_ID}")

    # Reads are rate-limited (60/minute by default), so pace a script that walks pages rather
    # than relying on catching the 429.
    time.sleep(0.6)

    # One page, with the pagination metadata.
    page = client.scheduled_emails.list(status="scheduled", batch_id=BATCH_ID)
    print(f"{page.pagination.total_count} scheduled, page {page.pagination.current_page}")
    time.sleep(0.6)

    # Or every page, fetched lazily as you consume it. Only scheduled/canceled/failed can be
    # listed: a sent email has left the collection, so status "sent" is a validation error.
    for email in client.scheduled_emails.iter_all(status=["scheduled", "failed"], batch_id=BATCH_ID):
        print(f"  {email.id}  {email.scheduled_at}  {email.recipients}  {email.subject}")

    if not page.data:
        raise SystemExit("nothing scheduled in this batch")

    email_id = page.data[0].id
    time.sleep(0.6)
    print("subject:", client.scheduled_emails.get(email_id).subject)
    time.sleep(0.6)

    moved = client.scheduled_emails.update(email_id, scheduled_at=datetime.now(UTC) + timedelta(days=1))
    print("moved to:", moved.scheduled_at)
    time.sleep(0.6)

    try:
        print("canceled:", client.scheduled_emails.cancel(email_id).status)
    except NotFoundError:
        print("no such scheduled email")
    except InvalidRequestError as exc:
        if exc.error_name != ErrorName.SCHEDULED_EMAIL_NOT_PENDING:
            raise
        print("already sent or canceled")
