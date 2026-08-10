"""Rendering Python values for the wire.

One home for every "how does this value become JSON or a query string" decision, shared by
the request builders in :mod:`mailkube._base_client` and by the resource spec builders.
Nothing here validates: an offset-less or past instant is rejected by the server, which is
the authority on what a value means. These functions only make values transmissible.
"""

from __future__ import annotations

import base64
from datetime import datetime

from .types.params import Attachment


def to_iso(value: object) -> str:
    """Render an instant for the wire, passing any non-``datetime`` through as text.

    Args:
        value: A ``datetime`` or an already-formatted ISO-8601 string.

    Returns:
        The ISO-8601 rendering of a ``datetime``, else ``str(value)``.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def query_value(value: object) -> str:
    """Render one query-string parameter.

    A list becomes a comma-separated value rather than a repeated parameter: the API
    accepts both, and a flat ``dict[str, str]`` keeps the transport seam simple in every
    SDK that mirrors this design.

    Args:
        value: The parameter value — a scalar, a ``datetime``, or a list of either.

    Returns:
        The parameter's string form.
    """
    if isinstance(value, list):
        return ",".join(to_iso(item) for item in value)
    return to_iso(value)


def encode_attachments(attachments: list[Attachment]) -> list[dict[str, object]]:
    """Return attachments with any raw ``bytes`` ``content`` base64-encoded to ``str``.

    Args:
        attachments: The attachments as supplied by the caller.

    Returns:
        JSON-serializable attachment mappings.
    """
    encoded: list[dict[str, object]] = []
    for attachment in attachments:
        item = dict(attachment)
        content = item.get("content")
        if isinstance(content, bytes):
            item["content"] = base64.b64encode(content).decode("ascii")
        encoded.append(item)
    return encoded
