"""Exception hierarchy and the response-to-exception mapping.

Every error the SDK raises derives from :class:`MailkubeError`. Server-returned errors
become an :class:`APIError` subclass chosen by HTTP status; the machine-readable
``error_name`` from the envelope is preserved as data so callers can branch finer.
"""

from __future__ import annotations

from typing import NoReturn


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
        message: The human-readable message.
        status_code: The HTTP status code.
        body: The parsed response body, when available.
        retry_after: Seconds to wait before retrying, from the ``Retry-After`` header
            (only set on :class:`RateLimitError`).
    """

    def __init__(
        self,
        *,
        error_name: str,
        message: str,
        status_code: int,
        body: object = None,
        retry_after: int | None = None,
    ) -> None:
        """Store the error fields and initialize the base ``Exception`` with ``message``."""
        super().__init__(message or error_name or f"HTTP {status_code}")
        self.error_name = error_name
        self.message = message
        self.status_code = status_code
        self.body = body
        self.retry_after = retry_after


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


def raise_for_response(status_code: int, body: object, retry_after: int | None = None) -> NoReturn:
    """Raise the :class:`APIError` subclass matching an error response.

    Dispatch is status-code-first: an exact status match wins, any other ``5xx`` maps to
    :class:`ServerError`, and everything else falls back to the base :class:`APIError`.
    The envelope's ``name``/``message`` are carried through on the exception.

    Args:
        status_code: The HTTP status code of the response.
        body: The parsed response body (expected to be a ``{name, message, ...}`` dict).
        retry_after: Seconds from the ``Retry-After`` header, if any.

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
    )
