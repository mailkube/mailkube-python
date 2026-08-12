"""Both clients are safe to share across concurrent callers, and this proves it.

``SDK_CONTRACT.md`` requires more than "no exception was raised": it requires that concurrent
calls **do not observe each other's responses**. A client holding mutable per-request state
does not crash when two callers overlap, it hands one caller the other's body, which is a
confidentiality bug that any weaker assertion sails straight past.

The shape is therefore: issue N calls whose requests are distinguishable (a distinct
``Idempotency-Key`` each), have the transport echo that value back as the response ``id``, and
assert every caller received **its own** value.

**The transports hold every request at a barrier until all N have arrived**, which buys two
things a sleep cannot. It *proves* the calls genuinely overlap: a client that serialized them
would never fill the barrier and the test would fail rather than quietly passing on a client it
never stressed. And it releases every caller in the same instant, so their continuations
contend for real. That second property is load-bearing. An earlier draft staggered the replies
instead, and when the client was deliberately broken the sync test went red while the async one
stayed green: with replies arriving one at a time, only one task was ever runnable, so it
resumed and read its own state back before any other task could clobber it.

These transports are also deliberately local rather than reused from ``conftest``. The shared
``capturing_handler`` writes into one dict from whichever thread or task is running, so a
concurrent test built on it would race in the *helper* and fail there instead of exercising the
client.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx

from mailkube import AsyncMailkube, Mailkube

CALLS = 32
"""How many callers overlap, and therefore how many parties the barrier waits for."""

GATE_TIMEOUT = 10.0
"""Seconds to wait for every caller to reach the barrier before declaring the test failed."""

MINIMAL = {"from_": "a@x.com", "to": "b@y.com", "subject": "Hi"}


def _echo(request: httpx.Request) -> httpx.Response:
    """Answer with the request's own idempotency key as the resource id.

    Args:
        request: The request being answered.

    Returns:
        A 200 whose body identifies which call it belongs to.
    """
    return httpx.Response(200, json={"id": request.headers["Idempotency-Key"]})


class _EchoTransport(httpx.BaseTransport):
    """A sync transport that answers nobody until every caller has arrived."""

    def __init__(self) -> None:
        self._gate = threading.Barrier(CALLS, timeout=GATE_TIMEOUT)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Hold at the barrier, then echo. A broken barrier means the calls never overlapped."""
        self._gate.wait()
        return _echo(request)


class _AsyncEchoTransport(httpx.AsyncBaseTransport):
    """An async transport that answers nobody until every caller has arrived."""

    def __init__(self) -> None:
        self._gate = asyncio.Barrier(CALLS)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Hold at the barrier, then echo. Every waiter resumes in the same loop iteration."""
        async with asyncio.timeout(GATE_TIMEOUT):
            await self._gate.wait()
        return _echo(request)


def _keys() -> list[str]:
    return [f"idem-{index:03d}" for index in range(CALLS)]


def _assert_no_cross_talk(keys: list[str], received: list[str]) -> None:
    for key, got in zip(keys, received, strict=True):
        assert got == key, f"{key} received the response for {got!r}: concurrent calls observed each other"


def test_the_sync_client_is_safe_across_threads():
    client = Mailkube(api_key="mk_test", http_client=httpx.Client(transport=_EchoTransport()))
    keys = _keys()

    def send(key: str) -> str:
        return client.emails.send(**MINIMAL, idempotency_key=key).id

    with ThreadPoolExecutor(max_workers=CALLS) as pool:
        received = list(pool.map(send, keys))

    _assert_no_cross_talk(keys, received)


def test_the_async_client_is_safe_across_tasks():
    keys = _keys()

    async def scenario() -> list[str]:
        client = AsyncMailkube(
            api_key="mk_test",
            http_client=httpx.AsyncClient(transport=_AsyncEchoTransport()),
        )
        results = await asyncio.gather(*(client.emails.send(**MINIMAL, idempotency_key=key) for key in keys))
        return [email.id for email in results]

    _assert_no_cross_talk(keys, asyncio.run(scenario()))
