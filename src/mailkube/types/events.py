"""Typed models for inbound webhook event payloads.

The models are lenient (``extra="allow"``) and server-controlled string fields are kept
as ``str`` (never ``Literal``/enum), so a new field or a new enum value never breaks
parsing. Any event ``type`` the installed SDK version does not recognize is routed to
:class:`UnknownEvent` instead of raising — so adding a server event type never forces an
SDK upgrade on receivers.
"""

from __future__ import annotations

from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Discriminator, Field
from pydantic import Tag as UnionTag

from .params import Tag


class _Model(BaseModel):
    """Base model: populate by field name or alias, and keep unknown fields."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# --- Nested context blocks (shared, de-duplicated) --------------------------------


class MessageContext(_Model):
    """Fields shared by every ``email.*`` event's ``data``.

    ``domain``, ``subject``, ``to`` and ``from`` are always sent as keys but their values may
    be ``null``: the server resolves them through the sending transaction, which a
    per-recipient event can briefly outlive. ``tags`` reuses the send-side :class:`~mailkube.Tag`
    so one public type describes a tag in both directions, and defaults to ``[]`` for a server
    predating message tags.
    """

    email_id: str
    created_at: str
    domain: str | None
    subject: str | None
    to: list[str] | None
    from_: str | None = Field(alias="from")
    tags: list[Tag] = Field(default_factory=list)


class DeliveryContext(_Model):
    """A single-recipient delivery outcome (``email.delivered``)."""

    recipient: str
    timestamp: str


class FailureContext(DeliveryContext):
    """A delivery failure with a status code and reason (``bounced`` / ``delivery_delayed``)."""

    code: int
    reason: str


class EngagementContext(_Model):
    """An open interaction (``email.opened``); nested keys are camelCase on the wire.

    ``ip_address`` and ``user_agent`` are **deprecated and default to ``None``**. The platform no
    longer records the recipient's address or client, so a current server sends neither key. They
    are kept as optional fields rather than removed, so that code written against an earlier
    version keeps working and an event replayed from an archive still parses. Declaring them
    required was also a contract defect in its own right: a released client must never raise on a
    payload it has not seen.
    """

    ip_address: str | None = Field(default=None, alias="ipAddress")
    user_agent: str | None = Field(default=None, alias="userAgent")
    timestamp: str


class ClickContext(EngagementContext):
    """A click interaction (``email.clicked``) — an open plus the clicked link."""

    link: str


class SuppressionContext(_Model):
    """The recipients suppressed for a send (``email.suppressed``)."""

    recipients: list[str]
    timestamp: str


class ScheduledContext(_Model):
    """A send accepted for later transmission (``email.scheduled``).

    Unlike the engagement blocks, these keys are snake_case on the wire. ``batch_id`` is
    ``null`` when the send was not grouped into a batch.
    """

    scheduled_at: str
    batch_id: str | None


class SendFailureContext(_Model):
    """An accepted send dropped at dispatch time, before transmission (``email.failed``).

    Distinct from :class:`FailureContext`, which reports what a receiving mail server said
    about one recipient. This is message-level and carries no recipient: the send never left.
    ``reason`` is a stable server-side code (``suppressed_at_dispatch``, ``mta_unreachable``,
    …) and stays a plain ``str``, so a newly added reason never breaks parsing.
    """

    reason: str
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


class SentData(MessageContext):
    """``data`` for ``email.sent``."""

    sent: DeliveryContext


class BouncedData(MessageContext):
    """``data`` for ``email.bounced``."""

    bounce: FailureContext


class DelayedData(MessageContext):
    """``data`` for ``email.delivery_delayed``."""

    delay: FailureContext


class SuppressedData(MessageContext):
    """``data`` for ``email.suppressed``."""

    suppression: SuppressionContext


class ScheduledData(MessageContext):
    """``data`` for ``email.scheduled``."""

    scheduled: ScheduledContext


class FailedData(MessageContext):
    """``data`` for ``email.failed``."""

    failed: SendFailureContext


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


class EmailSentEvent(_Event):
    """A message was accepted and spooled by the sending infrastructure.

    The moment of acceptance, not a delivery outcome: :class:`EmailDeliveredEvent` reports
    whether the receiving mail server took it.
    """

    type: Literal["email.sent"]
    data: SentData


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


class EmailScheduledEvent(_Event):
    """A send was accepted for later transmission.

    ``data.email_id`` correlates this event to the :class:`EmailSentEvent` emitted when the
    send is eventually transmitted.
    """

    type: Literal["email.scheduled"]
    data: ScheduledData


class EmailFailedEvent(_Event):
    """An accepted send was dropped at dispatch time and will never be transmitted."""

    type: Literal["email.failed"]
    data: FailedData


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


_UNKNOWN_TAG = "unknown"


def _event_discriminator(value: object) -> str:
    """Return the union tag for a payload, mapping any unrecognized ``type`` to ``"unknown"``."""
    tag = value.get("type") if isinstance(value, dict) else getattr(value, "type", None)
    return tag if isinstance(tag, str) and tag in _KNOWN_TAGS else _UNKNOWN_TAG


WebhookEvent = Annotated[
    Annotated[EmailSentEvent, UnionTag("email.sent")]
    | Annotated[EmailDeliveredEvent, UnionTag("email.delivered")]
    | Annotated[EmailBouncedEvent, UnionTag("email.bounced")]
    | Annotated[EmailDeliveryDelayedEvent, UnionTag("email.delivery_delayed")]
    | Annotated[EmailSuppressedEvent, UnionTag("email.suppressed")]
    | Annotated[EmailScheduledEvent, UnionTag("email.scheduled")]
    | Annotated[EmailFailedEvent, UnionTag("email.failed")]
    | Annotated[EmailOpenedEvent, UnionTag("email.opened")]
    | Annotated[EmailClickedEvent, UnionTag("email.clicked")]
    | Annotated[DomainStatusEvent, UnionTag("domain.status")]
    | Annotated[WebhookStatusEvent, UnionTag("webhook.status")]
    | Annotated[UnknownEvent, UnionTag(_UNKNOWN_TAG)],
    Discriminator(_event_discriminator),
]
"""Discriminated union of all webhook events, with an :class:`UnknownEvent` fallback."""


def _union_tags() -> frozenset[str]:
    """Return every concrete event tag declared on :data:`WebhookEvent`.

    The union is the catalogue. Deriving the discriminator's known-tag set from it means a new
    event is wired up by adding one arm and cannot be half-registered — a hand-maintained set
    that missed an arm would route the new type to :class:`UnknownEvent` silently.
    """
    arms = get_args(get_args(WebhookEvent)[0])
    return frozenset(
        meta.tag
        for arm in arms
        for meta in get_args(arm)[1:]
        if isinstance(meta, UnionTag) and meta.tag != _UNKNOWN_TAG
    )


_KNOWN_TAGS = _union_tags()
