"""Resource namespaces exposed on the client (e.g. ``client.emails``)."""

from __future__ import annotations

from .emails import AsyncEmailsResource, EmailsResource

__all__ = ["AsyncEmailsResource", "EmailsResource"]
