"""List the sends still waiting to go out: one page for the metadata, then the lazy walk.

Read-only: nothing is scheduled, moved or canceled. Run with your API key in the environment:

    MAILKUBE_API_KEY=mk_... python examples/list_scheduled_emails.py

``list`` returns one page plus its pagination block. ``iter_all`` follows the links the server
issues and fetches the next page only once the loop asks for it, so stopping after ``SHOWN``
rows with ``islice`` means the remaining pages are never requested at all.
"""

from itertools import islice

from mailkube import Mailkube

SHOWN = 20

with Mailkube() as client:  # reads MAILKUBE_API_KEY from the environment
    first = client.scheduled_emails.list(status="scheduled")
    pagination = first.pagination
    print(
        f"page {pagination.current_page}: {len(first.data)} of {pagination.total_count} scheduled, "
        f"more: {first.has_more}"
    )

    for email in islice(client.scheduled_emails.iter_all(status="scheduled"), SHOWN):
        print(email.scheduled_at, email.id, email.batch_id or "-", email.subject or "")
    print(f"stopped after at most {SHOWN}; later pages were never fetched")
