"""mailkube — the Mailkube Python SDK.

Send transactional email and verify inbound webhooks:

    >>> from mailkube import Mailkube
    >>> client = Mailkube(api_key="mk_...")
    >>> email = client.emails.send(
    ...     from_="Acme <hello@yourdomain.com>",
    ...     to="customer@example.com",
    ...     subject="Hello world",
    ...     html="<p>It works!</p>",
    ... )
    >>> email.id

Schedule a send for later and manage it until it is due:

    >>> email = client.emails.send(..., scheduled_at="2026-08-20T07:00:00Z")
    >>> client.scheduled_emails.update(email.id, scheduled_at="2026-08-21T07:00:00Z")
    >>> client.scheduled_emails.cancel(email.id)

    >>> from mailkube import verify
    >>> event = verify(raw_body, request.headers, signing_secret)
"""

from __future__ import annotations

from ._async_client import AsyncMailkube
from ._client import Mailkube
from ._exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ErrorName,
    InvalidRequestError,
    MailkubeConnectionError,
    MailkubeError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SignatureVerificationError,
)
from ._logging import enable_logging
from ._version import __version__
from .types.events import (
    DomainStatusEvent,
    EmailBouncedEvent,
    EmailClickedEvent,
    EmailDeliveredEvent,
    EmailDeliveryDelayedEvent,
    EmailOpenedEvent,
    EmailSuppressedEvent,
    UnknownEvent,
    WebhookEvent,
    WebhookStatusEvent,
)
from .types.params import (
    Attachment,
    Recipients,
    ScheduledEmailBatchUpdateParams,
    ScheduledEmailListParams,
    ScheduledEmailUpdateParams,
    SendEmailParams,
    Tag,
)
from .types.responses import (
    CanceledScheduledEmail,
    Email,
    PageSteps,
    Pagination,
    ScheduledEmail,
    ScheduledEmailBatchCancel,
    ScheduledEmailBatchUpdate,
    ScheduledEmailPage,
)
from .webhooks import parse_event, verify, verify_signature

__all__ = [
    "APIError",
    "AsyncMailkube",
    "Attachment",
    "AuthenticationError",
    "BadRequestError",
    "CanceledScheduledEmail",
    "ConflictError",
    "DomainStatusEvent",
    "Email",
    "EmailBouncedEvent",
    "EmailClickedEvent",
    "EmailDeliveredEvent",
    "EmailDeliveryDelayedEvent",
    "EmailOpenedEvent",
    "EmailSuppressedEvent",
    "ErrorName",
    "InvalidRequestError",
    "Mailkube",
    "MailkubeConnectionError",
    "MailkubeError",
    "NotFoundError",
    "PageSteps",
    "Pagination",
    "RateLimitError",
    "Recipients",
    "ScheduledEmail",
    "ScheduledEmailBatchCancel",
    "ScheduledEmailBatchUpdate",
    "ScheduledEmailBatchUpdateParams",
    "ScheduledEmailListParams",
    "ScheduledEmailPage",
    "ScheduledEmailUpdateParams",
    "SendEmailParams",
    "ServerError",
    "SignatureVerificationError",
    "Tag",
    "UnknownEvent",
    "WebhookEvent",
    "WebhookStatusEvent",
    "__version__",
    "enable_logging",
    "parse_event",
    "verify",
    "verify_signature",
]
