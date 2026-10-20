"""Async ``credential`` namespace: the sync contract, honored through ``await``."""

from __future__ import annotations

import asyncio

import pytest

from conftest import API_KEY, BASE_URL, capturing_handler, json_handler, make_async_client
from mailkube import AuthenticationError


def _run(handler, call):
    async def run():
        async with make_async_client(handler) as client:
            return await call(client)

    return asyncio.run(run())


def test_async_info_gets_the_calling_keys_description():
    captured = {}
    key = _run(capturing_handler(200, API_KEY, captured), lambda client: client.credential.info())

    assert captured["method"] == "GET"
    assert captured["url"] == f"{BASE_URL}api-keys/me"
    assert captured["body"] is None
    assert key.domain.name == "example.com"


def test_async_info_reads_a_null_plan_as_no_plan():
    key = _run(json_handler(200, {**API_KEY, "plan": None}), lambda client: client.credential.info())

    assert key.plan is None


def test_async_info_raises_an_authentication_error_for_a_refused_key():
    body = {"name": "invalid_api_key", "message": "API key is invalid"}
    with pytest.raises(AuthenticationError):
        _run(json_handler(403, body), lambda client: client.credential.info())
