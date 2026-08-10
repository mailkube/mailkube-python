"""The asynchronous Mailkube client."""

from __future__ import annotations

from types import TracebackType

import httpx

from ._base_client import BaseClient
from ._exceptions import MailkubeConnectionError
from ._transport import ModelT, RequestSpec
from .resources.emails import AsyncEmailsResource
from .resources.scheduled_emails import AsyncScheduledEmailsResource
from .types.params import SendEmailParams
from .types.responses import Email


class AsyncMailkube(BaseClient):
    """Asynchronous client for the Mailkube API.

    Create one instance per event loop and reuse it. Use it as an async context manager
    (``async with AsyncMailkube() as client:``) or call :meth:`aclose` to release the
    connection pool.

    Example:
        >>> async with AsyncMailkube(api_key="mk_...") as client:
        ...     email = await client.emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="<p>Hi</p>")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create the client.

        Args:
            api_key: The API key (falls back to ``MAILKUBE_API_KEY``).
            base_url: Override the API base URL (falls back to ``MAILKUBE_BASE_URL``).
            timeout: Per-request timeout in seconds (ignored when ``http_client`` is given).
            http_client: An optional ``httpx.AsyncClient`` to use instead of a built-in one.
                When supplied, the caller owns its lifecycle — :meth:`aclose` will not close it.
        """
        super().__init__(api_key, base_url=base_url, timeout=timeout)
        self._owns_http = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient(timeout=self._timeout)
        self.emails = AsyncEmailsResource(self)
        self.scheduled_emails = AsyncScheduledEmailsResource(self)

    async def _raw(self, spec: RequestSpec) -> httpx.Response:
        """Perform one HTTP round trip.

        See :meth:`mailkube.Mailkube._raw` — this and its two callers are the only
        async-specific code in the package.

        Args:
            spec: The request to perform.

        Returns:
            The raw response.

        Raises:
            MailkubeConnectionError: On a transport failure or timeout.
        """
        url, headers = self._prepare(spec)
        try:
            return await self._http.request(spec.method, url, json=spec.json, params=spec.params, headers=headers)
        except httpx.TransportError as exc:
            raise MailkubeConnectionError(str(exc)) from exc

    async def send_email(self, params: SendEmailParams) -> Email:
        """Build and POST a send request, returning the typed :class:`Email`.

        Args:
            params: The keyword parameters collected by ``emails.send``.

        Returns:
            The accepted-send result.

        Raises:
            MailkubeConnectionError: On a transport failure or timeout.
            APIError: On any non-2xx response.
        """
        response = await self._raw(self._build_send_body(params))
        return self._process_response(response.status_code, response.content, response.headers)

    async def request(self, spec: RequestSpec, model: type[ModelT]) -> ModelT:
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
        response = await self._raw(spec)
        return self._process_model(model, response.status_code, response.content, response.headers)

    async def aclose(self) -> None:
        """Close the underlying HTTP client, unless it was injected by the caller."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncMailkube:
        """Enter the async runtime context and return the client."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client on context exit."""
        await self.aclose()
