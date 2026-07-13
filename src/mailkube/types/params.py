"""Typed request parameters for the email send call.

These are ``TypedDict`` shapes used with :pep:`692` ``Unpack`` so callers get
per-keyword autocomplete and static checking while the field list stays defined in
one place. Nothing here is validated at runtime — the server is the source of truth
for validation, and its error names are richer than anything the SDK would reproduce.
"""

from __future__ import annotations

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
    """A name/value tag.

    Accepted for Resend payload parity; Mailkube currently ignores tags (they are
    validated for shape then dropped, never forwarded).

    Attributes:
        name: Tag name.
        value: Tag value.
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
        tags: Name/value tags (accepted for parity; currently a no-op server-side).
        template_id: UUID of a saved template to render instead of raw content.
        template_version: Template version number or ``"latest"``.
        variables: Values for the template's ``{{variable}}`` placeholders.
        topic: Mailing-list topic slug this send is attributed to.
        idempotency_key: Idempotency key; sent as the ``Idempotency-Key`` header.
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
