"""Shared test helpers: build clients backed by an httpx MockTransport (no network)."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from mailkube import AsyncMailkube, Mailkube

Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler, **kwargs) -> Mailkube:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return Mailkube(api_key="mk_test", http_client=http, **kwargs)


def make_async_client(handler: Handler, **kwargs) -> AsyncMailkube:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncMailkube(api_key="mk_test", http_client=http, **kwargs)


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"id": "abc123", "message_id": "<abc123@msg.mailkube.com>"},
        headers={"Idempotent-Replayed": "false", "X-Request-Id": "req_1"},
    )
