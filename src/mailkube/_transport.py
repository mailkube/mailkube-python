"""The transport seam (dependency inversion boundary).

Resources depend on the narrow ``SendTransport`` / ``AsyncSendTransport`` protocols
rather than on a concrete client or on ``httpx`` directly, so they can be tested with a
fake and stay ignorant of the HTTP library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .types.params import SendEmailParams
from .types.responses import Email


@dataclass(frozen=True)
class RequestSpec:
    """A fully-built request ready to send.

    Attributes:
        path: The path relative to the client's base URL (e.g. ``"emails"``).
        json: The JSON request body.
        headers: Per-request headers (e.g. ``Idempotency-Key``), merged with the client's
            default auth/User-Agent headers at send time.
    """

    path: str
    json: dict[str, object]
    headers: dict[str, str]


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
