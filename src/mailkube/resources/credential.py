"""The ``credential`` resource: namespaced under ``client.credential``.

It describes the API key the client was constructed with. It holds no setter: a client takes
its key at construction and keeps it, which is what makes one instance safe to share across
threads; a second key is a second client.

The request builder is a module-level function, so the synchronous and asynchronous
namespaces share one definition of the URL. It is a function rather than a constant because
``RequestSpec.headers`` is a mutable dict.
"""

from __future__ import annotations

from .._resource import Resource
from .._transport import AsyncCredentialTransport, CredentialTransport, RequestSpec
from ..types.responses import APIKey

_INFO_PATH = "api-keys/me"


def _info_spec() -> RequestSpec:
    """Build the request describing the calling key."""
    return RequestSpec(path=_INFO_PATH, method="GET")


class CredentialResource(Resource[CredentialTransport]):
    """The ``client.credential`` namespace."""

    def info(self) -> APIKey:
        """Describe the API key this client authenticates with.

        Returns its domain, organization, source-IP allowlist, plan and send-quota usage. The
        key is checked exactly as a send checks it, so a key that cannot send raises
        :class:`~mailkube.AuthenticationError` (``invalid_api_key``), which also makes this
        the way to verify a key. The call counts as a use of the key. Plan and quota figures
        can be up to 30 seconds old.

        Returns:
            The calling API key.
        """
        return self._transport.request(_info_spec(), APIKey)


class AsyncCredentialResource(Resource[AsyncCredentialTransport]):
    """The ``client.credential`` namespace (async)."""

    async def info(self) -> APIKey:
        """Describe the API key this client authenticates with (async).

        See :meth:`CredentialResource.info`.

        Returns:
            The calling API key.
        """
        return await self._transport.request(_info_spec(), APIKey)
