"""The transport seam (dependency inversion boundary).

Resources depend on the narrow protocols declared here rather than on a concrete client
or on ``httpx`` directly, so they can be tested with a fake and stay ignorant of the HTTP
library.

There is deliberately **one protocol pair per capability** rather than a single wide one:
``EmailsResource`` needs only :meth:`SendTransport.send_email` and must not acquire a
dependency on :meth:`ScheduledTransport.request`. New resources add a protocol; they never
widen an existing one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .types.params import SendEmailParams
from .types.responses import Email

ModelT = TypeVar("ModelT", bound=BaseModel)
"""The response model a request is parsed into."""


@dataclass(frozen=True)
class RequestSpec:
    """A fully-built request ready to send.

    Attributes:
        path: The path relative to the client's base URL (e.g. ``"emails"``), or an
            absolute URL previously issued by the API itself (a pagination link). An
            absolute URL is only followed when it shares the base URL's origin.
        method: The HTTP method.
        json: The JSON request body, or ``None`` for a body-less request.
        params: Query-string parameters, already serialized to strings.
        headers: Per-request headers (e.g. ``Idempotency-Key``), merged with the client's
            default auth/User-Agent headers at send time.
    """

    path: str
    method: str = "POST"
    json: dict[str, object] | None = None
    params: dict[str, str] | None = None
    headers: dict[str, str] = field(default_factory=dict)


class SendTransport(Protocol):
    """A synchronous transport capable of sending an email."""

    def send_email(self, params: SendEmailParams) -> Email:
        """Build and send an email, returning the typed result."""
        ...


class AsyncSendTransport(Protocol):
    """An asynchronous transport capable of sending an email."""

    async def send_email(self, params: SendEmailParams) -> Email:
        """Build and send an email, returning the typed result."""
        ...


class ScheduledTransport(Protocol):
    """A synchronous transport capable of performing an arbitrary typed request."""

    def request(self, spec: RequestSpec, model: type[ModelT]) -> ModelT:
        """Perform the request described by ``spec`` and parse the body into ``model``."""
        ...


class AsyncScheduledTransport(Protocol):
    """An asynchronous transport capable of performing an arbitrary typed request."""

    async def request(self, spec: RequestSpec, model: type[ModelT]) -> ModelT:
        """Perform the request described by ``spec`` and parse the body into ``model``."""
        ...
