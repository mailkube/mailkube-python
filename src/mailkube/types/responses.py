"""Typed responses returned by the API.

Response-model conventions (every SDK in the family follows these):

- **A model mirrors the wire and nothing else.** Transport metadata (headers, request ids)
  does not belong in a response model. :class:`Email` predates this rule and keeps its
  ``headers`` / ``request_id`` / ``idempotent_replayed`` fields for backward compatibility;
  they are a grandfathered exception, not a template. Use :attr:`APIError.request_id` when
  you need to quote a request to support.
- **Every model is frozen and ignores unknown fields**, so a server-side field addition can
  never raise in an already-released client.
- **Timestamps stay strings** — the verbatim ISO-8601 the server sent. The SDK does not
  validate or reinterpret server data; call ``datetime.fromisoformat`` if you want objects.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .params import Tag


class Email(BaseModel):
    """The result of a successful send.

    Built by the client from the response body (``id``, ``message_id``) plus a few
    response headers — it is not parsed directly from the raw JSON.

    A **scheduled** send (one carrying ``scheduled_at``) is acknowledged with ``202`` and a
    richer body; ``status``, ``scheduled_at`` and ``batch_id`` are populated only then, and
    :attr:`is_scheduled` is the discriminator. An immediate send leaves all three ``None``.

    Attributes:
        id: The accepted message's UUID.
        message_id: The RFC Message-ID (``<uuid@host>``) assigned to the message, or
            ``None`` if the deployment does not return one. Echo it in ``In-Reply-To`` /
            ``References`` headers on a later send to thread replies.
        idempotent_replayed: ``True`` when this response replays an earlier request that
            used the same ``Idempotency-Key``.
        request_id: The server's request id for support/debugging, when present.
        headers: The response headers, for callers that need rate-limit or tracing values.
        status: The scheduled email's status (``"scheduled"``), on a scheduled ack only.
        scheduled_at: When the send is due, on a scheduled ack only.
        batch_id: The batch label the send was grouped under, on a scheduled ack only.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    message_id: str | None = None
    idempotent_replayed: bool = False
    request_id: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    status: str | None = None
    scheduled_at: str | None = None
    batch_id: str | None = None

    @property
    def is_scheduled(self) -> bool:
        """``True`` when the send was accepted for later delivery rather than sent now."""
        return self.scheduled_at is not None


class ScheduledEmail(BaseModel):
    """A scheduled email that has not been delivered yet.

    Attributes:
        id: The scheduled email's UUID (the same id the send ack returned).
        message_id: The RFC Message-ID the message will carry.
        object: The resource discriminator, always ``"scheduled_email"``.
        status: One of ``scheduled``, ``canceled``, ``sent`` or ``failed``.
        scheduled_at: When the send is due.
        created_at: When the send was accepted.
        batch_id: The batch label this send was grouped under, if any.
        subject: The message subject.
        recipients: A **summary string** of the recipients, not a list — the first
            recipient plus an overflow count (e.g. ``"a@b.com +2"``). The full recipient
            list stays server-side with the frozen payload.
        topic: The mailing-list topic slug the send is attributed to, if any.
        tags: The message tags attached at send time.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    message_id: str | None = None
    object: str = "scheduled_email"
    status: str = ""
    scheduled_at: str | None = None
    created_at: str | None = None
    batch_id: str | None = None
    subject: str | None = None
    recipients: str | None = None
    topic: str | None = None
    tags: list[Tag] = Field(default_factory=list)


class PageSteps(BaseModel):
    """Links to the adjacent pages of a listing.

    The server **omits** a step at either end of the range rather than sending ``null``, so
    an absent link and a ``None`` value mean the same thing: there is no such page.

    Attributes:
        next: Absolute URL of the following page, or ``None`` on the last page.
        previous: Absolute URL of the preceding page, or ``None`` on the first page.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    next: str | None = None
    previous: str | None = None


class Pagination(BaseModel):
    """Page-number pagination metadata for a listing.

    Attributes:
        steps: Links to the adjacent pages.
        total_count: Total number of matching records across every page.
        current_page: The 1-based number of the page in hand.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    steps: PageSteps = Field(default_factory=PageSteps)
    total_count: int = 0
    current_page: int = 1


class ScheduledEmailPage(BaseModel):
    """One page of scheduled emails.

    Attributes:
        pagination: Page metadata, including the adjacent-page links.
        data: The scheduled emails on this page.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    pagination: Pagination = Field(default_factory=Pagination)
    data: list[ScheduledEmail] = Field(default_factory=list)

    @property
    def has_more(self) -> bool:
        """``True`` when the server offered a link to a following page."""
        return self.pagination.steps.next is not None


class CanceledScheduledEmail(BaseModel):
    """The acknowledgement of a single scheduled-email cancellation.

    Attributes:
        id: The canceled scheduled email's UUID.
        object: The resource discriminator, always ``"scheduled_email"``.
        status: The resulting status, always ``"canceled"``.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "scheduled_email"
    status: str = "canceled"


class ScheduledEmailBatchCancel(BaseModel):
    """The result of canceling a whole batch.

    Attributes:
        object: The resource discriminator, always ``"scheduled_email.batch"``.
        batch_id: The batch that was targeted.
        canceled_count: How many pending emails the cancellation actually affected. An
            unknown batch is a no-op reporting ``0``, not an error.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    object: str = "scheduled_email.batch"
    batch_id: str = ""
    canceled_count: int = 0


class ScheduledEmailBatchUpdate(BaseModel):
    """The result of rescheduling a whole batch.

    Attributes:
        object: The resource discriminator, always ``"scheduled_email.batch"``.
        batch_id: The batch that was targeted.
        rescheduled_count: How many pending emails were moved. An unknown batch is a no-op
            reporting ``0``, not an error.
        scheduled_at: The new due time applied to every moved email.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    object: str = "scheduled_email.batch"
    batch_id: str = ""
    rescheduled_count: int = 0
    scheduled_at: str | None = None


class APIKeyDomain(BaseModel):
    """The sending domain an API key belongs to.

    Attributes:
        name: The domain name, e.g. ``example.com``.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = ""


class APIKeyOrganization(BaseModel):
    """The organization owning an API key's domain.

    Attributes:
        name: The organization's display name.
        alias: The organization's short alias.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = ""
    alias: str = ""


class APIKeyQuota(BaseModel):
    """One send quota of the plan: its limit and what the current period has used.

    Attributes:
        name: Which quota, e.g. ``emails_per_day`` or ``emails_per_month``. A plain string,
            never a closed set.
        limit: The plan's limit for the period, in recipients.
        used: Recipients sent to so far in the period.
        remaining: Recipients left in the period.
        period: The UTC period the figures count: a day (``2026-10-19``) or a month
            (``2026-10``).
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = ""
    limit: int = 0
    used: int = 0
    remaining: int = 0
    period: str = ""


class APIKeyPlan(BaseModel):
    """The organization's plan, its status and its send quotas.

    Attributes:
        code: The plan's UUID.
        name: The plan's name.
        status: The subscription status, e.g. ``active``. A plain string, never a closed set.
        quotas: The send quotas the plan carries. A plan without a daily limit lists the
            monthly quota only: an absent quota is a missing limit, never a limit of zero.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    code: str = ""
    name: str = ""
    status: str = ""
    quotas: list[APIKeyQuota] = Field(default_factory=list)


class APIKey(BaseModel):
    """The API key the client authenticates with, as it describes itself.

    Plan and quota figures can be up to 30 seconds old.

    Attributes:
        object: The resource discriminator, always ``"api_key"``.
        key_id: The key's public identifier.
        name: The key's name.
        description: The key's description, or ``None``.
        created_at: When the key was created.
        last_auth_at: The key's last successful authentication, this call included.
        allowed_source_ips: The networks the key may be used from, in CIDR notation. Empty
            means any address.
        domain: The sending domain the key belongs to.
        organization: The organization owning the domain.
        plan: The organization's plan, or ``None`` when it has no subscription. The API
            sends ``null`` then, and it is never read as an empty plan.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    object: str = "api_key"
    key_id: str
    name: str = ""
    description: str | None = None
    created_at: str = ""
    last_auth_at: str | None = None
    allowed_source_ips: list[str] = Field(default_factory=list)
    domain: APIKeyDomain = Field(default_factory=APIKeyDomain)
    organization: APIKeyOrganization = Field(default_factory=APIKeyOrganization)
    plan: APIKeyPlan | None = None
