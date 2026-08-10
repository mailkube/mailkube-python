"""List, retrieve, reschedule and cancel scheduled emails.

    MAILKUBE_API_KEY=mk_... python examples/manage_scheduled_emails.py
"""

from datetime import UTC, datetime, timedelta

from mailkube import ErrorName, InvalidRequestError, Mailkube, NotFoundError

with Mailkube() as client:
    # One page, with the pagination metadata.
    page = client.scheduled_emails.list(status="scheduled")
    print(f"{page.pagination.total_count} scheduled, page {page.pagination.current_page}")

    # Or every page, fetched lazily as you consume it.
    for email in client.scheduled_emails.iter_all(status=["scheduled", "failed"]):
        print(f"  {email.id}  {email.scheduled_at}  {email.recipients}  {email.subject}")

    if not page.data:
        raise SystemExit("nothing scheduled to work with")

    email_id = page.data[0].id
    print("subject:", client.scheduled_emails.get(email_id).subject)

    moved = client.scheduled_emails.update(email_id, scheduled_at=datetime.now(UTC) + timedelta(days=1))
    print("moved to:", moved.scheduled_at)

    try:
        print("canceled:", client.scheduled_emails.cancel(email_id).status)
    except NotFoundError:
        print("no such scheduled email")
    except InvalidRequestError as exc:
        if exc.error_name != ErrorName.SCHEDULED_EMAIL_NOT_PENDING:
            raise
        print("already sent or canceled")
