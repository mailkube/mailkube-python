"""Shared, transport-agnostic client core.

:class:`BaseClient` owns everything that does not depend on the HTTP library: config
resolution, default headers, the request-body serializer, and response processing. The
sync and async clients subclass it and add only the ~few lines of I/O that genuinely
differ (a blocking call vs an ``await``).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import cast
from urllib.parse import urljoin, urlsplit

from ._exceptions import MailkubeError, raise_for_response
from ._logging import get_logger, redact_headers
from ._serialization import encode_attachments, to_iso
from ._transport import ModelT, RequestSpec
from ._version import __version__
from .types.params import Attachment, SendEmailParams
from .types.responses import Email

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://api.mailkube.com/mta/v1/"
_SEND_PATH = "emails"
_OK_STATUS = range(200, 300)
_WIRE_RENAMES = {"from_": "from"}
_HEADER_PARAMS = {"idempotency_key": "Idempotency-Key"}
_ISO_PARAMS = frozenset({"scheduled_at", "scheduled_at_gte", "scheduled_at_lte"})


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


def _optional_str(body: Mapping[str, object], key: str) -> str | None:
    """Return ``body[key]`` as text, or ``None`` when absent or explicitly null."""
    value = body.get(key)
    return None if value is None else str(value)


def _origin(url: str) -> tuple[str, str]:
    """Return the ``(scheme, netloc)`` origin of a URL."""
    parts = urlsplit(url)
    return parts.scheme, parts.netloc


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

        A :class:`RequestSpec` may also carry an absolute URL the API itself issued — a
        pagination link. ``urljoin`` returns such a URL unchanged, so following one needs
        no special plumbing, but it must not be followed blindly: every request carries the
        ``Authorization`` header, so a link naming a foreign host would hand the API key to
        that host. Absolute URLs are therefore accepted only from the base URL's own origin.

        Args:
            path: A path relative to the base URL (e.g. ``"emails"``), or an absolute URL
                previously issued by the API.

        Returns:
            The absolute request URL.

        Raises:
            MailkubeError: If ``path`` is an absolute URL on a different origin.
        """
        url = urljoin(self._base_url, path)
        if _origin(url) != _origin(self._base_url):
            raise MailkubeError(  # noqa: TRY003 — names the offending URL, which is the whole point
                f"Refusing to follow {url!r}: it is not on the configured API origin."
            )
        return url

    def _prepare(self, spec: RequestSpec) -> tuple[str, dict[str, str]]:
        """Return the absolute URL and the merged headers for a request.

        Args:
            spec: The request to prepare.

        Returns:
            The request URL and the default headers overlaid with the spec's own.
        """
        return self._build_url(spec.path), {**self._default_headers(), **spec.headers}

    @staticmethod
    def _log_request(method: str, url: str, headers: Mapping[str, str]) -> None:
        """Emit the outbound half of a request/response pair at DEBUG.

        Deliberately logs the envelope only — method, URL and headers. The request **body** is
        never logged at any level: it is where the recipient addresses, the subject and the message
        content live, and a debug flag must not turn the SDK into a PII exfiltration path. The URL
        is safe by construction: the send path is a constant and the only query string the SDK
        builds is the scheduled-email filter set (status, batch id, due-time bounds, page).

        Args:
            method: The HTTP method.
            url: The absolute request URL.
            headers: The outgoing headers, redacted here before they reach a record.
        """
        logger.debug("request %s %s headers=%s", method, url, redact_headers(headers))

    @staticmethod
    def _log_response(method: str, url: str, status_code: int, headers: Mapping[str, str]) -> None:
        """Emit the inbound half of a request/response pair at DEBUG.

        Carries the request id so a customer's own logs and a support ticket describe the same
        request. The response body is omitted for the same reason the request body is.

        Args:
            method: The HTTP method.
            url: The absolute request URL.
            status_code: The HTTP status code.
            headers: The response headers, redacted here before they reach a record.
        """
        logger.debug(
            "response %s %s status=%s request_id=%s headers=%s",
            method,
            url,
            status_code,
            _header(headers, "x-request-id"),
            redact_headers(headers),
        )

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
        ``Idempotency-Key`` header, renders ``datetime`` instants as ISO-8601, and
        base64-encodes any ``bytes`` attachment content.

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
                body["attachments"] = encode_attachments(cast("list[Attachment]", value))
            elif key in _ISO_PARAMS:
                body[key] = to_iso(value)
            else:
                body[_WIRE_RENAMES.get(key, key)] = value
        return RequestSpec(path=_SEND_PATH, json=body, headers=headers)

    @staticmethod
    def _ok_body(status_code: int, raw_bytes: bytes, headers: Mapping[str, str]) -> object:
        """Return the decoded body of a successful response, or raise the mapped error.

        This is the single place a non-2xx status becomes an exception, so every verb —
        present and future — reports failures identically.

        Args:
            status_code: The HTTP status code.
            raw_bytes: The raw response body.
            headers: The response headers.

        Returns:
            The decoded 2xx body (``None`` when empty or undecodable).

        Raises:
            APIError: On any non-2xx response (subclass chosen by status).
        """
        body = _decode_json(raw_bytes)
        if status_code in _OK_STATUS:
            return body
        raise_for_response(
            status_code,
            body,
            _parse_retry_after(_header(headers, "retry-after")),
            _header(headers, "x-request-id"),
        )

    @classmethod
    def _process_response(cls, status_code: int, raw_bytes: bytes, headers: Mapping[str, str]) -> Email:
        """Turn a raw send response into an :class:`Email` or raise the mapped error.

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
        body = cls._ok_body(status_code, raw_bytes, headers)
        if not isinstance(body, dict) or "id" not in body:
            raise MailkubeError(  # noqa: TRY003 — surfaces a malformed success body clearly
                f"Expected a JSON body with an 'id' from a {status_code} response."
            )
        replayed = (_header(headers, "idempotent-replayed") or "").lower() == "true"
        return Email(
            id=str(body["id"]),
            message_id=_optional_str(body, "message_id"),
            idempotent_replayed=replayed,
            request_id=_header(headers, "x-request-id"),
            headers=dict(headers),
            status=_optional_str(body, "status"),
            scheduled_at=_optional_str(body, "scheduled_at"),
            batch_id=_optional_str(body, "batch_id"),
        )

    @classmethod
    def _process_model(
        cls,
        model: type[ModelT],
        status_code: int,
        raw_bytes: bytes,
        headers: Mapping[str, str],
    ) -> ModelT:
        """Parse a successful JSON-object response into ``model``.

        Args:
            model: The response model to validate the body against.
            status_code: The HTTP status code.
            raw_bytes: The raw response body.
            headers: The response headers.

        Returns:
            The parsed model.

        Raises:
            MailkubeError: On a 2xx response whose body is not a JSON object.
            APIError: On any non-2xx response (subclass chosen by status).
        """
        body = cls._ok_body(status_code, raw_bytes, headers)
        if not isinstance(body, dict):
            raise MailkubeError(  # noqa: TRY003 — surfaces a malformed success body clearly
                f"Expected a JSON object from a {status_code} response."
            )
        return model.model_validate(body)
