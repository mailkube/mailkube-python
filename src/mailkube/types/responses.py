"""Typed responses returned by the API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Email(BaseModel):
    """The result of a successful send.

    Built by the client from the response body (``id``, ``message_id``) plus a few
    response headers — it is not parsed directly from the raw JSON.

    Attributes:
        id: The accepted message's UUID.
        message_id: The RFC Message-ID (``<uuid@host>``) assigned to the message, or
            ``None`` if the deployment does not return one. Echo it in ``In-Reply-To`` /
            ``References`` headers on a later send to thread replies.
        idempotent_replayed: ``True`` when this response replays an earlier request that
            used the same ``Idempotency-Key``.
        request_id: The server's request id for support/debugging, when present.
        headers: The response headers, for callers that need rate-limit or tracing values.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    message_id: str | None = None
    idempotent_replayed: bool = False
    request_id: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
