"""Async client: mirror the sync behavior via asyncio.run (no pytest-asyncio needed)."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from conftest import make_async_client, ok_handler
from mailkube import AsyncMailkube, InvalidRequestError, MailkubeConnectionError


def test_async_send_success():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return ok_handler(request)

    async def run() -> str:
        async with make_async_client(handler) as client:
            email = await client.emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
            return email.id

    assert asyncio.run(run()) == "abc123"
    assert captured["url"] == "https://api.mailkube.com/mta/v1/emails"
    assert captured["body"]["from"] == "a@x.com"


def test_async_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"name": "validation_error", "message": "bad"})

    async def run() -> None:
        async with make_async_client(handler) as client:
            await client.emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")

    with pytest.raises(InvalidRequestError):
        asyncio.run(run())


def test_async_transport_error_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    async def run() -> None:
        async with make_async_client(handler) as client:
            await client.emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")

    with pytest.raises(MailkubeConnectionError):
        asyncio.run(run())


def test_async_owned_client_closed():
    client = AsyncMailkube(api_key="mk_x")

    async def run() -> bool:
        await client.aclose()
        return client._http.is_closed

    assert asyncio.run(run()) is True


def test_async_injected_client_not_closed():
    http = httpx.AsyncClient(transport=httpx.MockTransport(ok_handler))
    client = AsyncMailkube(api_key="mk_test", http_client=http)

    async def run() -> bool:
        await client.aclose()
        return http.is_closed

    assert asyncio.run(run()) is False
