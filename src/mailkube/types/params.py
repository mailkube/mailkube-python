"""Typed request parameters for the email send call.

These are ``TypedDict`` shapes used with :pep:`692` ``Unpack`` so callers get
per-keyword autocomplete and static checking while the field list stays defined in
one place. Nothing here is validated at runtime — the server is the source of truth
for validation, and its error names are richer than anything the SDK would reproduce.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict

Recipients = str | list[str]
"""A single address, or a list of addresses (used for ``to``/``cc``/``bcc``/``reply_to``)."""


class Attachment(TypedDict):
    """A file attached to an email.

    Attributes:
        filename: Name of the attached file.
        content: File content, either raw ``bytes`` (base64-encoded by the SDK) or an
            already base64-encoded ``str``.
        content_type: Optional MIME type; inferred from ``filename`` when omitted.
    """

    filename: str
    content: str | bytes
    content_type: NotRequired[str]


class Tag(TypedDict):
    """A free-form name/value tag attached to an outgoing email.

    Tags are forwarded to the server, which denormalizes them onto the sending-log so
    you can filter, export, and dashboard sends by tag, and so they ride along on
    delivery webhooks. Validation is server-side (the authoritative gate): names and
    values are limited to the ``[A-Za-z0-9_-]`` charset, a name to 16 characters and a value
    to 32, values may be blank, at most 20 tags per send, and names must be unique. Tag values
    are not encrypted, so do not put personal data in them.

    Attributes:
        name: Tag name.
        value: Tag value (may be blank, ``''``).
    """

    name: str
    value: str


class SendEmailParams(TypedDict):
    """Keyword parameters for :meth:`mailkube.resources.emails.EmailsResource.send`.

    A send carries **either** raw content (``html`` and/or ``text``) **or** a saved
    template (``template_id``). ``from_`` maps to the wire ``from`` field (``from`` is a
    reserved Python keyword); ``idempotency_key`` is sent as the ``Idempotency-Key``
    header rather than in the body.

    Attributes:
        from_: Sender address, optionally with a display name. Maps to wire ``from``.
        to: Recipient address or list of addresses.
        subject: Subject line.
        html: HTML body (raw-content send).
        text: Plain-text body (raw-content send).
        cc: Carbon-copy recipient(s).
        bcc: Blind carbon-copy recipient(s).
        reply_to: Reply-To address(es).
        headers: Custom message headers (e.g. ``In-Reply-To`` for threading).
        attachments: File attachments.
        tags: Free-form name/value tags forwarded to the server and denormalized onto
            the sending-log for filtering, export, dashboards, and delivery webhooks.
        template_id: UUID of a saved template to render instead of raw content.
        template_version: Template version number or ``"latest"``.
        variables: Values for the template's ``{{variable}}`` placeholders.
        topic: Mailing-list topic slug this send is attributed to.
        idempotency_key: Idempotency key; sent as the ``Idempotency-Key`` header.
        scheduled_at: When to deliver the message instead of sending it now. ISO-8601
            **with a timezone offset** (``"2026-08-20T07:00:00Z"``), or a timezone-aware
            ``datetime``. Must be in the future and within the plan's scheduling horizon.
            A scheduled send is acknowledged ``202`` and manageable via
            ``client.scheduled_emails``.
        batch_id: A label grouping several scheduled sends so they can be rescheduled or
            canceled together. Only valid alongside ``scheduled_at``.
    """

    from_: str
    to: Recipients
    subject: str
    html: NotRequired[str]
    text: NotRequired[str]
    cc: NotRequired[Recipients]
    bcc: NotRequired[Recipients]
    reply_to: NotRequired[Recipients]
    headers: NotRequired[dict[str, str]]
    attachments: NotRequired[list[Attachment]]
    tags: NotRequired[list[Tag]]
    template_id: NotRequired[str]
    template_version: NotRequired[str]
    variables: NotRequired[dict[str, str]]
    topic: NotRequired[str]
    idempotency_key: NotRequired[str]
    scheduled_at: NotRequired[str | datetime]
    batch_id: NotRequired[str]


class ScheduledEmailListParams(TypedDict, total=False):
    """Filters for :meth:`~mailkube.resources.scheduled_emails.ScheduledEmailsResource.list`.

    Every filter is optional; an omitted filter is simply not applied. The listing is
    scoped server-side to a rolling window around now, so a bound outside that window in
    the direction that can never match is rejected rather than silently ignored.

    Attributes:
        status: One status, or several. Only ``"scheduled"``, ``"canceled"`` and
            ``"failed"`` can be listed — a sent email has left the collection, so
            ``"sent"`` is a validation error rather than an empty result.
        batch_id: Only emails grouped under this batch label.
        scheduled_at_gte: Only emails due at or after this instant. ISO-8601 with an
            offset, or a timezone-aware ``datetime``.
        scheduled_at_lte: Only emails due at or before this instant.
        page: The 1-based page number to fetch.
    """

    status: str | list[str]
    batch_id: str
    scheduled_at_gte: str | datetime
    scheduled_at_lte: str | datetime
    page: int


class ScheduledEmailUpdateParams(TypedDict):
    """Parameters for rescheduling one scheduled email.

    Attributes:
        scheduled_at: The new due time. Same rule as on a send: ISO-8601 with an offset
            (or a timezone-aware ``datetime``), in the future, within the horizon.
        batch_id: Optionally move the email into (or out of) a batch at the same time.
    """

    scheduled_at: str | datetime
    batch_id: NotRequired[str]


class ScheduledEmailBatchUpdateParams(TypedDict):
    """Parameters for rescheduling a whole batch.

    There is deliberately no ``batch_id`` here: the batch is identified by the path, and
    the server rejects a second one in the body rather than let it decide which batch
    actually moves.

    Attributes:
        scheduled_at: The new due time applied to every pending email in the batch.
    """

    scheduled_at: str | datetime
