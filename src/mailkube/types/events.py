"""Typed models for inbound webhook event payloads.

The models are lenient (``extra="allow"``) and server-controlled string fields are kept
as ``str`` (never ``Literal``/enum), so a new field or a new enum value never breaks
parsing. Any event ``type`` the installed SDK version does not recognize is routed to
:class:`UnknownEvent` instead of raising — so adding a server event type never forces an
SDK upgrade on receivers.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag


class _Model(BaseModel):
    """Base model: populate by field name or alias, and keep unknown fields."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# --- Nested context blocks (shared, de-duplicated) --------------------------------


class MessageContext(_Model):
    """Fields shared by every ``email.*`` event's ``data``."""

    email_id: str
    created_at: str
    domain: str
    subject: str
    to: list[str]
    from_: str = Field(alias="from")


class DeliveryContext(_Model):
    """A single-recipient delivery outcome (``email.delivered``)."""

    recipient: str
    timestamp: str


class FailureContext(DeliveryContext):
    """A delivery failure with a status code and reason (``bounced`` / ``delivery_delayed``)."""

    code: int
    reason: str


class EngagementContext(_Model):
    """An open interaction (``email.opened``); nested keys are camelCase on the wire."""

    ip_address: str = Field(alias="ipAddress")
    user_agent: str = Field(alias="userAgent")
    timestamp: str


class ClickContext(EngagementContext):
    """A click interaction (``email.clicked``) — an open plus the clicked link."""

    link: str


class SuppressionContext(_Model):
    """The recipients suppressed for a send (``email.suppressed``)."""

    recipients: list[str]
    timestamp: str


class DomainStatusPrevious(_Model):
    """The prior domain state in a ``domain.status`` change."""

    status: str
    onboarding_state: str


class WebhookStatusPrevious(_Model):
    """The prior endpoint state in a ``webhook.status`` change."""

    is_active: bool
    is_deleted: bool
    disabled_reason: str


# --- Per-event data payloads -------------------------------------------------------


class DeliveredData(MessageContext):
    """``data`` for ``email.delivered``."""

    delivery: DeliveryContext


class BouncedData(MessageContext):
    """``data`` for ``email.bounced``."""

    bounce: FailureContext


class DelayedData(MessageContext):
    """``data`` for ``email.delivery_delayed``."""

    delay: FailureContext


class SuppressedData(MessageContext):
    """``data`` for ``email.suppressed``."""

    suppression: SuppressionContext


class OpenedData(MessageContext):
    """``data`` for ``email.opened``."""

    open: EngagementContext


class ClickedData(MessageContext):
    """``data`` for ``email.clicked``."""

    click: ClickContext


class DomainStatusData(_Model):
    """``data`` for ``domain.status`` (no message context)."""

    domain: str
    status: str
    onboarding_state: str
    previous: DomainStatusPrevious


class WebhookStatusData(_Model):
    """``data`` for ``webhook.status`` (no message context)."""

    endpoint_url: str
    is_active: bool
    is_deleted: bool
    disabled_reason: str
    previous: WebhookStatusPrevious


# --- Event envelopes ---------------------------------------------------------------


class _Event(_Model):
    """Common webhook envelope: ``type`` + ``created_at`` + ``data``."""

    created_at: str


class EmailDeliveredEvent(_Event):
    """A message was accepted by the receiving mail server."""

    type: Literal["email.delivered"]
    data: DeliveredData


class EmailBouncedEvent(_Event):
    """A message permanently failed to deliver."""

    type: Literal["email.bounced"]
    data: BouncedData


class EmailDeliveryDelayedEvent(_Event):
    """A message was temporarily deferred."""

    type: Literal["email.delivery_delayed"]
    data: DelayedData


class EmailSuppressedEvent(_Event):
    """A message was suppressed (prior hard bounce or topic opt-out)."""

    type: Literal["email.suppressed"]
    data: SuppressedData


class EmailOpenedEvent(_Event):
    """A recipient opened a message."""

    type: Literal["email.opened"]
    data: OpenedData


class EmailClickedEvent(_Event):
    """A recipient clicked a tracked link."""

    type: Literal["email.clicked"]
    data: ClickedData


class DomainStatusEvent(_Event):
    """A sending domain's status or onboarding state changed."""

    type: Literal["domain.status"]
    data: DomainStatusData


class WebhookStatusEvent(_Event):
    """A webhook endpoint's status changed."""

    type: Literal["webhook.status"]
    data: WebhookStatusData


class UnknownEvent(_Event):
    """Fallback for an event ``type`` this SDK version does not recognize.

    ``type`` and the raw ``data`` dict are still available, so receivers keep working
    when the platform introduces a new event type — no SDK upgrade required.
    """

    type: str
    data: dict[str, object]


_KNOWN_TAGS = frozenset(
    {
        "email.delivered",
        "email.bounced",
        "email.delivery_delayed",
        "email.suppressed",
        "email.opened",
        "email.clicked",
        "domain.status",
        "webhook.status",
    }
)


def _event_discriminator(value: object) -> str:
    """Return the union tag for a payload, mapping any unknown ``type`` to ``"unknown"``."""
    tag = value.get("type") if isinstance(value, dict) else getattr(value, "type", None)
    return tag if isinstance(tag, str) and tag in _KNOWN_TAGS else "unknown"


WebhookEvent = Annotated[
    Annotated[EmailDeliveredEvent, Tag("email.delivered")]
    | Annotated[EmailBouncedEvent, Tag("email.bounced")]
    | Annotated[EmailDeliveryDelayedEvent, Tag("email.delivery_delayed")]
    | Annotated[EmailSuppressedEvent, Tag("email.suppressed")]
    | Annotated[EmailOpenedEvent, Tag("email.opened")]
    | Annotated[EmailClickedEvent, Tag("email.clicked")]
    | Annotated[DomainStatusEvent, Tag("domain.status")]
    | Annotated[WebhookStatusEvent, Tag("webhook.status")]
    | Annotated[UnknownEvent, Tag("unknown")],
    Discriminator(_event_discriminator),
]
"""Discriminated union of all webhook events, with an :class:`UnknownEvent` fallback."""
