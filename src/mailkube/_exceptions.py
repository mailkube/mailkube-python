"""Exception hierarchy and the response-to-exception mapping.

Every error the SDK raises derives from :class:`MailkubeError`. Server-returned errors
become an :class:`APIError` subclass chosen by HTTP status; the machine-readable
``error_name`` from the envelope is preserved as data so callers can branch finer.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NoReturn


class ErrorName(StrEnum):
    """The documented ``name`` values of the API error envelope.

    These are constants for discoverability, **not** a closed set: :attr:`APIError.error_name`
    stays a plain ``str`` at runtime, so a name this release has never heard of is reported
    verbatim instead of crashing an older client. Because :class:`~enum.StrEnum` members
    compare equal to their value, ``exc.error_name == ErrorName.QUOTA_EXCEEDED`` works either
    way. The list tracks the public error reference; add a member when the API adds a name.
    """

    APPLICATION_ERROR = "application_error"
    BODY_CONTENT_REJECTED = "body_content_rejected"
    BROWSER_NOT_ALLOWED = "browser_not_allowed"
    CONCURRENT_IDEMPOTENT_REQUESTS = "concurrent_idempotent_requests"
    FROM_DOMAIN_NOT_ALLOWED = "from_domain_not_allowed"
    INVALID_API_KEY = "invalid_api_key"
    INVALID_ATTACHMENT = "invalid_attachment"
    INVALID_FROM_ADDRESS = "invalid_from_address"
    INVALID_IDEMPOTENCY_KEY = "invalid_idempotency_key"
    INVALID_IDEMPOTENT_REQUEST = "invalid_idempotent_request"
    INVALID_REQUEST_BODY = "invalid_request_body"
    LINK_REPUTATION_BLOCKED = "link_reputation_blocked"
    MAX_MESSAGE_SIZE_EXCEEDED = "max_message_size_exceeded"
    MAX_RECIPIENTS_EXCEEDED = "max_recipients_exceeded"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    MISSING_REQUIRED_VARIABLE = "missing_required_variable"
    MISSING_USER_AGENT = "missing_user_agent"
    NOT_ACCEPTABLE = "not_acceptable"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SCHEDULED_EMAIL_NOT_FOUND = "scheduled_email_not_found"
    SCHEDULED_EMAIL_NOT_PENDING = "scheduled_email_not_pending"
    SCHEDULING_NOT_INCLUDED = "scheduling_not_included"
    TEMPLATE_NOT_FOUND = "template_not_found"
    TEMPLATE_NOT_PUBLISHED = "template_not_published"
    TOPIC_DISABLED = "topic_disabled"
    TOPIC_NOT_FOUND = "topic_not_found"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    VALIDATION_ERROR = "validation_error"


class MailkubeError(Exception):
    """Base class for every error raised by the SDK."""


class MailkubeConnectionError(MailkubeError):
    """A transport-level failure (connection error or timeout) with no HTTP response."""


class SignatureVerificationError(MailkubeError):
    """A webhook signature could not be verified (bad signature, stale, or malformed headers)."""


class APIError(MailkubeError):
    """An error returned by the API as a ``{name, message, statusCode}`` envelope.

    Attributes:
        error_name: The machine-readable error name from the envelope (e.g. ``quota_exceeded``).
            Compare it against :class:`ErrorName` for the documented values.
        message: The human-readable message.
        status_code: The HTTP status code.
        body: The parsed response body, when available.
        retry_after: Seconds to wait before retrying, from the ``Retry-After`` header
            (only set on :class:`RateLimitError`).
        request_id: The server's request id, when present — quote it to support.
    """

    def __init__(  # noqa: PLR0913 — a keyword-only data carrier; every field is part of the envelope
        self,
        *,
        error_name: str,
        message: str,
        status_code: int,
        body: object = None,
        retry_after: int | None = None,
        request_id: str | None = None,
    ) -> None:
        """Store the error fields and initialize the base ``Exception`` with ``message``."""
        super().__init__(message or error_name or f"HTTP {status_code}")
        self.error_name = error_name
        self.message = message
        self.status_code = status_code
        self.body = body
        self.retry_after = retry_after
        self.request_id = request_id


class BadRequestError(APIError):
    """The request envelope was invalid (HTTP 400) — e.g. ``missing_user_agent``."""


class AuthenticationError(APIError):
    """Authentication failed or is forbidden (HTTP 403) — e.g. ``invalid_api_key``."""


class NotFoundError(APIError):
    """A referenced resource was not found (HTTP 404) — e.g. ``template_not_found``."""


class ConflictError(APIError):
    """An idempotency conflict (HTTP 409) — e.g. ``invalid_idempotent_request``."""


class InvalidRequestError(APIError):
    """The request was rejected by a send-policy check (HTTP 422) — e.g. ``validation_error``."""


class RateLimitError(APIError):
    """The rate limit was exceeded (HTTP 429). Inspect :attr:`APIError.retry_after`."""


class ServerError(APIError):
    """An unexpected server error (HTTP 5xx) — safe to retry with backoff."""


_STATUS_EXCEPTIONS: dict[int, type[APIError]] = {
    400: BadRequestError,
    403: AuthenticationError,
    404: NotFoundError,
    409: ConflictError,
    422: InvalidRequestError,
    429: RateLimitError,
}
_SERVER_ERRORS = range(500, 600)


def raise_for_response(
    status_code: int,
    body: object,
    retry_after: int | None = None,
    request_id: str | None = None,
) -> NoReturn:
    """Raise the :class:`APIError` subclass matching an error response.

    Dispatch is status-code-first: an exact status match wins, any other ``5xx`` maps to
    :class:`ServerError`, and everything else falls back to the base :class:`APIError`.
    The envelope's ``name``/``message`` are carried through on the exception.

    Args:
        status_code: The HTTP status code of the response.
        body: The parsed response body (expected to be a ``{name, message, ...}`` dict).
        retry_after: Seconds from the ``Retry-After`` header, if any.
        request_id: The server's request id from the response headers, if any.

    Raises:
        APIError: Always — the appropriate subclass for ``status_code``.
    """
    error_name = ""
    message = ""
    if isinstance(body, dict):
        error_name = str(body.get("name", ""))
        message = str(body.get("message", ""))

    exc_cls = _STATUS_EXCEPTIONS.get(status_code)
    if exc_cls is None:
        exc_cls = ServerError if status_code in _SERVER_ERRORS else APIError

    raise exc_cls(
        error_name=error_name,
        message=message,
        status_code=status_code,
        body=body,
        retry_after=retry_after,
        request_id=request_id,
    )
