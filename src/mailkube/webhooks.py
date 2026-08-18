"""Verify, sign and parse inbound Mailkube webhooks.

Verification is a pure, stdlib-only HMAC check over the raw request bytes — no HTTP, no
client needed — so you call these functions directly inside your webhook handler.

Signature scheme (see ``.rules/SDK_CONTRACT.md``): the signed input is
``f"{X-Webhook-Id}.{X-Webhook-Ts}.".encode() + raw_body``, HMAC-SHA256 keyed by the
endpoint's signing secret (used verbatim as UTF-8 bytes), hex-encoded, and sent as
``X-Webhook-Sig: sha256=<hex>``. ``X-Webhook-Ts`` is an ISO-8601 timestamp checked for
freshness; ``X-Webhook-Id`` is stable across retries (use it to deduplicate).

:func:`sign` is the mirror of :func:`verify_signature`, for anything that needs to *produce* a
delivery — a test fixture, a local replay tool, a fake endpoint in your own suite.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import TypeAdapter

from ._exceptions import SignatureVerificationError
from .types.events import WebhookEvent

_SIGNATURE_PREFIX = "sha256="
_DEFAULT_TOLERANCE_SECONDS = 300
_ID_HEADER = "x-webhook-id"
_TS_HEADER = "x-webhook-ts"
_SIG_HEADER = "x-webhook-sig"

_EVENT_ADAPTER: TypeAdapter[WebhookEvent] = TypeAdapter(WebhookEvent)


def _as_bytes(payload: bytes | str) -> bytes:
    """Return the payload as raw bytes without re-serializing."""
    return payload.encode("utf-8") if isinstance(payload, str) else payload


def _get_header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup."""
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None


def _check_freshness(timestamp: str, tolerance_seconds: int) -> None:
    """Raise if the ISO-8601 ``timestamp`` is outside the tolerance window."""
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise SignatureVerificationError("Malformed X-Webhook-Ts timestamp.") from exc  # noqa: TRY003
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    age = abs((datetime.now(UTC) - parsed).total_seconds())
    if age > tolerance_seconds:
        raise SignatureVerificationError("Webhook timestamp is outside the freshness window.")  # noqa: TRY003


def verify_signature(
    payload: bytes | str,
    headers: Mapping[str, str],
    secret: str,
    *,
    tolerance_seconds: int = _DEFAULT_TOLERANCE_SECONDS,
) -> bytes:
    """Verify a webhook's signature and timestamp freshness over the raw body.

    Verifies against the **raw received bytes** — never parse then re-serialize, or the
    signature will not match.

    Args:
        payload: The raw request body (``bytes`` preferred; a ``str`` is UTF-8 encoded).
        headers: The request headers (``X-Webhook-Id`` / ``-Ts`` / ``-Sig``).
        secret: The endpoint's signing secret.
        tolerance_seconds: Maximum allowed clock skew for the timestamp (default 300s).

    Returns:
        The verified raw body bytes.

    Raises:
        SignatureVerificationError: If a header is missing, the timestamp is malformed or
            stale, or the signature does not match.
    """
    raw = _as_bytes(payload)
    webhook_id = _get_header(headers, _ID_HEADER)
    timestamp = _get_header(headers, _TS_HEADER)
    signature = _get_header(headers, _SIG_HEADER)
    if not webhook_id or not timestamp or not signature:
        raise SignatureVerificationError("Missing required webhook signature headers.")  # noqa: TRY003

    _check_freshness(timestamp, tolerance_seconds)

    expected = _signature_hex(webhook_id, timestamp, raw, secret)
    provided = signature[len(_SIGNATURE_PREFIX) :] if signature.startswith(_SIGNATURE_PREFIX) else signature
    if not hmac.compare_digest(expected, provided):
        raise SignatureVerificationError("Webhook signature mismatch.")  # noqa: TRY003
    return raw


def sign(webhook_id: str, timestamp: str, payload: bytes | str, secret: str) -> str:
    """Produce the ``X-Webhook-Sig`` value for a payload, the mirror of :func:`verify_signature`.

    This exists so anything that produces a delivery — a test fixture, a local replay tool, a
    fake endpoint in your own suite — computes the signature the way this module verifies it.
    A reimplementation from the docstring above agrees with its author's reading of the prose
    rather than with this SDK, and the two drift silently. Production code verifies; it does
    not sign.

    Freshness is not this function's concern: it signs the timestamp it is given, so replaying
    an old capture reproduces the original signature exactly.

    Args:
        webhook_id: The ``X-Webhook-Id`` value.
        timestamp: The ``X-Webhook-Ts`` value, ISO-8601.
        payload: The raw body that will be sent.
        secret: The endpoint's signing secret.

    Returns:
        The header value, including the ``sha256=`` prefix.
    """
    return _SIGNATURE_PREFIX + _signature_hex(webhook_id, timestamp, _as_bytes(payload), secret)


def parse_event(payload: bytes | str) -> WebhookEvent:
    """Parse a raw webhook body into a typed :class:`WebhookEvent`.

    An unrecognized event ``type`` is returned as :class:`~mailkube.types.events.UnknownEvent`
    rather than raising, so new server event types never break a receiver.

    Args:
        payload: The raw request body.

    Returns:
        The parsed event (a concrete event model or ``UnknownEvent``).
    """
    return _EVENT_ADAPTER.validate_json(_as_bytes(payload))


def verify(
    payload: bytes | str,
    headers: Mapping[str, str],
    secret: str,
    *,
    tolerance_seconds: int = _DEFAULT_TOLERANCE_SECONDS,
) -> WebhookEvent:
    """Verify a webhook's signature and return the parsed :class:`WebhookEvent`.

    Convenience combinator: :func:`verify_signature` followed by :func:`parse_event`.

    Args:
        payload: The raw request body.
        headers: The request headers.
        secret: The endpoint's signing secret.
        tolerance_seconds: Maximum allowed clock skew for the timestamp (default 300s).

    Returns:
        The verified, parsed event.

    Raises:
        SignatureVerificationError: If verification fails.
    """
    raw = verify_signature(payload, headers, secret, tolerance_seconds=tolerance_seconds)
    return parse_event(raw)


def _signature_hex(webhook_id: str, timestamp: str, raw: bytes, secret: str) -> str:
    """Return the hex HMAC-SHA256 over the contract's signed input.

    One implementation, so signing and verifying cannot disagree.
    """
    signing_input = f"{webhook_id}.{timestamp}.".encode() + raw
    return hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
