"""Resource namespaces exposed on the client (e.g. ``client.emails``)."""

from __future__ import annotations

from .emails import AsyncEmailsResource, EmailsResource
from .scheduled_emails import (
    AsyncScheduledEmailBatchesResource,
    AsyncScheduledEmailsResource,
    ScheduledEmailBatchesResource,
    ScheduledEmailsResource,
)

__all__ = [
    "AsyncEmailsResource",
    "AsyncScheduledEmailBatchesResource",
    "AsyncScheduledEmailsResource",
    "EmailsResource",
    "ScheduledEmailBatchesResource",
    "ScheduledEmailsResource",
]
