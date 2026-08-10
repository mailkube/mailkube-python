"""The synchronous Mailkube client."""

from __future__ import annotations

from types import TracebackType

import httpx

from ._base_client import BaseClient
from ._exceptions import MailkubeConnectionError
from ._transport import ModelT, RequestSpec
from .resources.emails import EmailsResource
from .resources.scheduled_emails import ScheduledEmailsResource
from .types.params import SendEmailParams
from .types.responses import Email


class Mailkube(BaseClient):
    """Synchronous client for the Mailkube API.

    Create one instance and reuse it — it is safe to share across threads. Use it as a
    context manager (``with Mailkube() as client:``) or call :meth:`close` to release the
    underlying connection pool.

    Example:
        >>> client = Mailkube(api_key="mk_...")
        >>> email = client.emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="<p>Hi</p>")
        >>> email.id
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Create the client.

        Args:
            api_key: The API key (falls back to ``MAILKUBE_API_KEY``).
            base_url: Override the API base URL (falls back to ``MAILKUBE_BASE_URL``).
            timeout: Per-request timeout in seconds (ignored when ``http_client`` is given).
            http_client: An optional ``httpx.Client`` to use instead of a built-in one. When
                supplied, the caller owns its lifecycle — :meth:`close` will not close it.
        """
        super().__init__(api_key, base_url=base_url, timeout=timeout)
        self._owns_http = http_client is None
        self._http = http_client if http_client is not None else httpx.Client(timeout=self._timeout)
        self.emails = EmailsResource(self)
        self.scheduled_emails = ScheduledEmailsResource(self)

    def _raw(self, spec: RequestSpec) -> httpx.Response:
        """Perform one HTTP round trip.

        This is the only method in the package that differs between the sync and async
        clients; everything else — spec building, serialization, response parsing — is
        shared, which is what keeps the two flavours from drifting.

        Args:
            spec: The request to perform.

        Returns:
            The raw response.

        Raises:
            MailkubeConnectionError: On a transport failure or timeout.
        """
        url, headers = self._prepare(spec)
        try:
            return self._http.request(spec.method, url, json=spec.json, params=spec.params, headers=headers)
        except httpx.TransportError as exc:
            raise MailkubeConnectionError(str(exc)) from exc

    def send_email(self, params: SendEmailParams) -> Email:
        """Build and POST a send request, returning the typed :class:`Email`.

        Args:
            params: The keyword parameters collected by ``emails.send``.

        Returns:
            The accepted-send result.

        Raises:
            MailkubeConnectionError: On a transport failure or timeout.
            APIError: On any non-2xx response.
        """
        response = self._raw(self._build_send_body(params))
        return self._process_response(response.status_code, response.content, response.headers)

    def request(self, spec: RequestSpec, model: type[ModelT]) -> ModelT:
        """Perform a request and parse its body into ``model``.

        Args:
            spec: The request to perform.
            model: The response model to parse into.

        Returns:
            The parsed model.

        Raises:
            MailkubeConnectionError: On a transport failure or timeout.
            APIError: On any non-2xx response.
        """
        response = self._raw(spec)
        return self._process_model(model, response.status_code, response.content, response.headers)

    def close(self) -> None:
        """Close the underlying HTTP client, unless it was injected by the caller."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Mailkube:
        """Enter the runtime context and return the client."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client on context exit."""
        self.close()
