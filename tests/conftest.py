"""Shared test helpers: build clients backed by an httpx MockTransport (no network)."""

from __future__ import annotations

import json
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


BASE_URL = "https://api.mailkube.com/mta/v1/"

SCHEDULED_EMAIL = {
    "id": "11111111-1111-1111-1111-111111111111",
    "message_id": "<11111111-1111-1111-1111-111111111111@msg.mailkube.com>",
    "object": "scheduled_email",
    "status": "scheduled",
    "scheduled_at": "2026-08-20T07:00:00Z",
    "created_at": "2026-08-10T07:00:00Z",
    "batch_id": "campaign-x",
    "subject": "Hi",
    "recipients": "a@b.com +1",
    "topic": "newsletter",
    "tags": [{"name": "campaign", "value": "spring24"}],
}


def json_handler(status: int, payload: object, headers: dict[str, str] | None = None) -> Handler:
    """A handler answering every request with the same status + JSON body."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload, headers=headers)

    return handler


def capturing_handler(status: int, payload: object, captured: dict) -> Handler:
    """A handler recording the request it received into ``captured``."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        # raw_path is what goes on the wire; url.path is a decoded convenience view.
        captured["raw_path"] = request.url.raw_path.decode()
        captured["params"] = dict(request.url.params)
        captured["body"] = json.loads(request.content) if request.content else None
        return httpx.Response(status, json=payload)

    return handler


def page(data: list[dict], next_url: str | None = None, current_page: int = 1) -> dict:
    """A list-page payload, omitting `steps.next` at the end of the range like the API does."""
    steps = {} if next_url is None else {"next": next_url}
    return {
        "pagination": {"steps": steps, "total_count": len(data), "current_page": current_page},
        "data": data,
    }
