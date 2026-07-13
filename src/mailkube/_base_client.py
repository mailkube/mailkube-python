"""Shared, transport-agnostic client core.

:class:`BaseClient` owns everything that does not depend on the HTTP library: config
resolution, default headers, the request-body serializer, and response processing. The
sync and async clients subclass it and add only the ~few lines of I/O that genuinely
differ (a blocking call vs an ``await``).
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from typing import cast
from urllib.parse import urljoin

from ._exceptions import MailkubeError, raise_for_response
from ._logging import get_logger
from ._transport import RequestSpec
from ._version import __version__
from .types.params import Attachment, SendEmailParams
from .types.responses import Email

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://api.mailkube.com/mta/v1/"
_SEND_PATH = "emails"
_OK_STATUS = range(200, 300)
_WIRE_RENAMES = {"from_": "from"}
_HEADER_PARAMS = {"idempotency_key": "Idempotency-Key"}


def _encode_attachments(attachments: list[Attachment]) -> list[dict[str, object]]:
    """Return attachments with any raw ``bytes`` ``content`` base64-encoded to ``str``."""
    encoded: list[dict[str, object]] = []
    for attachment in attachments:
        item = dict(attachment)
        content = item.get("content")
        if isinstance(content, bytes):
            item["content"] = base64.b64encode(content).decode("ascii")
        encoded.append(item)
    return encoded


def _decode_json(raw: bytes) -> object:
    """Best-effort JSON decode; returns ``None`` for an empty or undecodable body."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup."""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def _parse_retry_after(value: str | None) -> int | None:
    """Parse a ``Retry-After`` header value into whole seconds, or ``None``."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


class BaseClient:
    """Config, header building, request serialization, and response processing.

    Subclassed by :class:`mailkube.Mailkube` and :class:`mailkube.AsyncMailkube`, which
    supply the concrete HTTP call.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Resolve configuration.

        Args:
            api_key: The API key. Falls back to the ``MAILKUBE_API_KEY`` env var.
            base_url: The API base URL. Falls back to ``MAILKUBE_BASE_URL``, then the
                built-in default. Always resolves to a value.
            timeout: Per-request timeout in seconds.

        Raises:
            MailkubeError: If no API key is provided or found in the environment.
        """
        resolved_key = api_key or os.environ.get("MAILKUBE_API_KEY")
        if not resolved_key:
            raise MailkubeError(  # noqa: TRY003 — a specific, actionable setup message
                "No API key provided. Pass api_key=... or set the MAILKUBE_API_KEY environment variable."
            )
        self._api_key = resolved_key
        self._base_url = base_url or os.environ.get("MAILKUBE_BASE_URL") or DEFAULT_BASE_URL
        self._timeout = timeout

    def _build_url(self, path: str) -> str:
        """Join a relative path onto the (trailing-slash) base URL.

        Args:
            path: A path relative to the base URL (e.g. ``"emails"``).

        Returns:
            The absolute request URL.
        """
        return urljoin(self._base_url, path)

    def _default_headers(self) -> dict[str, str]:
        """Return the auth + non-browser User-Agent headers sent on every request."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": f"mailkube-python/{__version__}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _build_send_body(params: SendEmailParams) -> RequestSpec:
        """Serialize send parameters into a request body + per-request headers.

        Renames ``from_`` to the wire ``from``, splits ``idempotency_key`` into the
        ``Idempotency-Key`` header, and base64-encodes any ``bytes`` attachment content.

        Args:
            params: The keyword parameters passed to ``emails.send``.

        Returns:
            A :class:`RequestSpec` with the JSON body and any per-request headers.
        """
        body: dict[str, object] = {}
        headers: dict[str, str] = {}
        for key, value in params.items():
            if key in _HEADER_PARAMS:
                headers[_HEADER_PARAMS[key]] = str(value)
            elif key == "attachments":
                body["attachments"] = _encode_attachments(cast("list[Attachment]", value))
            else:
                body[_WIRE_RENAMES.get(key, key)] = value
        return RequestSpec(path=_SEND_PATH, json=body, headers=headers)

    def _process_response(self, status_code: int, raw_bytes: bytes, headers: Mapping[str, str]) -> Email:
        """Turn a raw HTTP response into an :class:`Email` or raise the mapped error.

        Args:
            status_code: The HTTP status code.
            raw_bytes: The raw response body.
            headers: The response headers.

        Returns:
            The parsed :class:`Email` on a 2xx response.

        Raises:
            MailkubeError: On a 2xx response with a missing/undecodable body.
            APIError: On any non-2xx response (subclass chosen by status).
        """
        body = _decode_json(raw_bytes)
        if status_code in _OK_STATUS:
            if not isinstance(body, dict) or "id" not in body:
                raise MailkubeError(  # noqa: TRY003 — surfaces a malformed success body clearly
                    f"Expected a JSON body with an 'id' from a {status_code} response."
                )
            message_id = body.get("message_id")
            replayed = (_header(headers, "idempotent-replayed") or "").lower() == "true"
            return Email(
                id=str(body["id"]),
                message_id=str(message_id) if message_id is not None else None,
                idempotent_replayed=replayed,
                request_id=_header(headers, "x-request-id"),
                headers=dict(headers),
            )
        retry_after = _parse_retry_after(_header(headers, "retry-after"))
        raise_for_response(status_code, body, retry_after)
