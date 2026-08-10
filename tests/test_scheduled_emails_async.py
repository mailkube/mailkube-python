"""Async scheduled-email resource: the sync contract, honored through ``await``."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from conftest import BASE_URL, SCHEDULED_EMAIL, capturing_handler, json_handler, make_async_client, page
from mailkube import MailkubeConnectionError, NotFoundError

EMAIL_ID = SCHEDULED_EMAIL["id"]
BATCH_CANCEL = {"object": "scheduled_email.batch", "batch_id": "campaign-x", "canceled_count": 3}
BATCH_UPDATE = {
    "object": "scheduled_email.batch",
    "batch_id": "campaign-x",
    "rescheduled_count": 2,
    "scheduled_at": "2026-08-21T07:00:00Z",
}


def _run(handler, call):
    async def run():
        async with make_async_client(handler) as client:
            return await call(client)

    return asyncio.run(run())


def test_async_list_shapes_the_query_and_maps_the_page():
    captured = {}
    result = _run(
        capturing_handler(200, page([SCHEDULED_EMAIL]), captured),
        lambda client: client.scheduled_emails.list(status="scheduled"),
    )

    assert captured["method"] == "GET"
    assert captured["params"] == {"status": "scheduled"}
    assert result.data[0].id == EMAIL_ID


def test_async_get_targets_the_item_route():
    captured = {}
    result = _run(
        capturing_handler(200, SCHEDULED_EMAIL, captured),
        lambda client: client.scheduled_emails.get(EMAIL_ID),
    )

    assert captured["url"] == f"{BASE_URL}scheduled-emails/{EMAIL_ID}"
    assert result.status == "scheduled"


def test_async_update_sends_the_new_due_time():
    captured = {}
    _run(
        capturing_handler(200, SCHEDULED_EMAIL, captured),
        lambda client: client.scheduled_emails.update(EMAIL_ID, scheduled_at="2026-08-21T07:00:00Z"),
    )

    assert captured["method"] == "PATCH"
    assert captured["body"] == {"scheduled_at": "2026-08-21T07:00:00Z"}


def test_async_cancel_reports_the_new_status():
    payload = {"id": EMAIL_ID, "object": "scheduled_email", "status": "canceled"}
    result = _run(json_handler(200, payload), lambda client: client.scheduled_emails.cancel(EMAIL_ID))

    assert result.status == "canceled"


def test_async_batches_update_targets_the_batch_route():
    captured = {}
    result = _run(
        capturing_handler(200, BATCH_UPDATE, captured),
        lambda client: client.scheduled_emails.batches.update("campaign-x", scheduled_at="2026-08-21T07:00:00Z"),
    )

    assert captured["url"] == f"{BASE_URL}scheduled-emails/batches/campaign-x"
    assert result.rescheduled_count == 2


def test_async_batches_cancel_reports_the_affected_count():
    result = _run(json_handler(200, BATCH_CANCEL), lambda client: client.scheduled_emails.batches.cancel("campaign-x"))

    assert result.canceled_count == 3


def test_async_iter_all_walks_every_page():
    listing = f"{BASE_URL}scheduled-emails"
    pages = {
        listing: page([{**SCHEDULED_EMAIL, "id": "id-1"}], f"{listing}?page=2"),
        f"{listing}?page=2": page([{**SCHEDULED_EMAIL, "id": "id-2"}]),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[str(request.url)])

    async def collect(client):
        return [item.id async for item in client.scheduled_emails.iter_all()]

    assert _run(handler, collect) == ["id-1", "id-2"]


def test_async_error_envelope_surfaces_as_the_mapped_exception():
    payload = {"name": "scheduled_email_not_found", "message": "nope", "statusCode": 404}

    with pytest.raises(NotFoundError):
        _run(json_handler(404, payload), lambda client: client.scheduled_emails.get(EMAIL_ID))


def test_async_transport_failure_becomes_a_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(MailkubeConnectionError):
        _run(handler, lambda client: client.scheduled_emails.list())
