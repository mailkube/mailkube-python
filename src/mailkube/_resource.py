"""The resource base.

A resource is a thin, stateless namespace of verbs bound to an injected transport. It
holds no configuration, performs no I/O of its own, and knows nothing about ``httpx`` —
it depends only on the narrow ``Protocol`` its verbs need. Keeping the constructor here
means every resource, sync or async, is bound the same way and none of them repeat it.
"""

from __future__ import annotations


class Resource[TransportT]:
    """Base for API resource namespaces: holds the injected transport, and nothing else.

    The type parameter is the transport ``Protocol`` a concrete resource's verbs require —
    the narrowest one that covers them, never a wider shared interface.
    """

    def __init__(self, transport: TransportT) -> None:
        """Bind the resource to the transport that performs its requests.

        Args:
            transport: The client (or test double) satisfying this resource's protocol.
        """
        self._transport = transport
