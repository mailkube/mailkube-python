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
from .types.params import Attachment, Recipients, SendEmailParams, Tag
from .types.responses import Email
from .webhooks import parse_event, verify, verify_signature

__all__ = [
    "APIError",
    "AsyncMailkube",
    "Attachment",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "DomainStatusEvent",
    "Email",
    "EmailBouncedEvent",
    "EmailClickedEvent",
    "EmailDeliveredEvent",
    "EmailDeliveryDelayedEvent",
    "EmailOpenedEvent",
    "EmailSuppressedEvent",
    "InvalidRequestError",
    "Mailkube",
    "MailkubeConnectionError",
    "MailkubeError",
    "NotFoundError",
    "RateLimitError",
    "Recipients",
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
