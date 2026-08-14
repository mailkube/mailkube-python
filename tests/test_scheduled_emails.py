"""Scheduled-email resource: request shaping, response mapping, and error surfacing."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from conftest import BASE_URL, SCHEDULED_EMAIL, capturing_handler, json_handler, make_client, page
from mailkube import (
    ErrorName,
    InvalidRequestError,
    MailkubeConnectionError,
    MailkubeError,
    NotFoundError,
    RateLimitError,
)

EMAIL_ID = SCHEDULED_EMAIL["id"]


def test_list_sends_no_query_when_unfiltered():
    captured = {}
    result = make_client(capturing_handler(200, page([SCHEDULED_EMAIL]), captured)).scheduled_emails.list()

    assert captured["method"] == "GET"
    assert captured["url"] == f"{BASE_URL}scheduled-emails"
    assert captured["params"] == {}
    assert captured["body"] is None
    assert result.pagination.current_page == 1
    assert result.pagination.total_count == 1
    assert result.has_more is False


def test_list_serializes_every_filter_shape():
    captured = {}
    make_client(capturing_handler(200, page([]), captured)).scheduled_emails.list(
        status=["scheduled", "canceled"],
        batch_id="campaign-x",
        scheduled_at_gte=datetime(2026, 8, 1, 7, 0, tzinfo=UTC),
        scheduled_at_lte="2026-08-31T07:00:00Z",
        page=2,
    )

    assert captured["params"] == {
        "status": "scheduled,canceled",
        "batch_id": "campaign-x",
        "scheduled_at_gte": "2026-08-01T07:00:00+00:00",
        "scheduled_at_lte": "2026-08-31T07:00:00Z",
        "page": "2",
    }


def test_list_accepts_a_bare_status_string():
    captured = {}
    make_client(capturing_handler(200, page([]), captured)).scheduled_emails.list(status="scheduled")

    assert captured["params"] == {"status": "scheduled"}


def test_list_maps_the_scheduled_email_object():
    item = make_client(json_handler(200, page([SCHEDULED_EMAIL]))).scheduled_emails.list().data[0]

    assert item.id == EMAIL_ID
    assert item.object == "scheduled_email"
    assert item.status == "scheduled"
    assert item.scheduled_at == "2026-08-20T07:00:00Z"
    assert item.batch_id == "campaign-x"
    assert item.recipients == "a@b.com +1"
    assert item.topic == "newsletter"
    assert item.tags == [{"name": "campaign", "value": "spring24"}]


def test_list_tolerates_a_field_this_release_does_not_know():
    payload = page([{**SCHEDULED_EMAIL, "some_future_field": "surprise"}])

    assert make_client(json_handler(200, payload)).scheduled_emails.list().data[0].id == EMAIL_ID


def test_get_targets_the_item_route():
    captured = {}
    result = make_client(capturing_handler(200, SCHEDULED_EMAIL, captured)).scheduled_emails.get(EMAIL_ID)

    assert captured["method"] == "GET"
    assert captured["url"] == f"{BASE_URL}scheduled-emails/{EMAIL_ID}"
    assert result.id == EMAIL_ID


def test_get_escapes_an_id_that_would_retarget_the_request():
    captured = {}
    make_client(capturing_handler(200, SCHEDULED_EMAIL, captured)).scheduled_emails.get("../batches/x?page=9")

    assert captured["raw_path"] == "/mta/v1/scheduled-emails/..%2Fbatches%2Fx%3Fpage%3D9"
    assert captured["params"] == {}


def test_update_sends_only_the_new_due_time():
    captured = {}
    make_client(capturing_handler(200, SCHEDULED_EMAIL, captured)).scheduled_emails.update(
        EMAIL_ID, scheduled_at=datetime(2026, 8, 21, 7, 0, tzinfo=UTC)
    )

    assert captured["method"] == "PATCH"
    assert captured["body"] == {"scheduled_at": "2026-08-21T07:00:00+00:00"}


def test_update_can_move_the_email_into_a_batch():
    captured = {}
    make_client(capturing_handler(200, SCHEDULED_EMAIL, captured)).scheduled_emails.update(
        EMAIL_ID, scheduled_at="2026-08-21T07:00:00Z", batch_id="campaign-y"
    )

    assert captured["body"] == {"scheduled_at": "2026-08-21T07:00:00Z", "batch_id": "campaign-y"}


def test_cancel_deletes_and_reports_the_new_status():
    captured = {}
    payload = {"id": EMAIL_ID, "object": "scheduled_email", "status": "canceled"}
    result = make_client(capturing_handler(200, payload, captured)).scheduled_emails.cancel(EMAIL_ID)

    assert captured["method"] == "DELETE"
    assert captured["url"] == f"{BASE_URL}scheduled-emails/{EMAIL_ID}"
    assert (result.id, result.status) == (EMAIL_ID, "canceled")


def test_batches_update_targets_the_batch_route_without_a_body_batch_id():
    captured = {}
    payload = {
        "object": "scheduled_email.batch",
        "batch_id": "campaign-x",
        "rescheduled_count": 2,
        "scheduled_at": "2026-08-21T07:00:00Z",
    }
    result = make_client(capturing_handler(200, payload, captured)).scheduled_emails.batches.update(
        "campaign-x", scheduled_at="2026-08-21T07:00:00Z"
    )

    assert captured["method"] == "PATCH"
    assert captured["url"] == f"{BASE_URL}scheduled-emails/batches/campaign-x"
    assert captured["body"] == {"scheduled_at": "2026-08-21T07:00:00Z"}
    assert result.rescheduled_count == 2


def test_batches_cancel_reports_the_affected_count():
    captured = {}
    payload = {"object": "scheduled_email.batch", "batch_id": "campaign-x", "canceled_count": 3}
    result = make_client(capturing_handler(200, payload, captured)).scheduled_emails.batches.cancel("campaign-x")

    assert captured["method"] == "DELETE"
    assert captured["url"] == f"{BASE_URL}scheduled-emails/batches/campaign-x"
    assert result.canceled_count == 3


def test_an_unknown_batch_is_a_no_op_not_an_error():
    payload = {"object": "scheduled_email.batch", "batch_id": "nope", "canceled_count": 0}

    assert make_client(json_handler(200, payload)).scheduled_emails.batches.cancel("nope").canceled_count == 0


@pytest.mark.parametrize(
    ("status", "name", "exc"),
    [
        (404, ErrorName.SCHEDULED_EMAIL_NOT_FOUND, NotFoundError),
        (422, ErrorName.SCHEDULED_EMAIL_NOT_PENDING, InvalidRequestError),
        (422, ErrorName.VALIDATION_ERROR, InvalidRequestError),
    ],
)
def test_error_envelope_surfaces_as_the_mapped_exception(status, name, exc):
    payload = {"name": str(name), "message": "boom", "statusCode": status}

    with pytest.raises(exc) as excinfo:
        make_client(json_handler(status, payload)).scheduled_emails.get(EMAIL_ID)

    assert excinfo.value.error_name == name
    assert excinfo.value.status_code == status


def test_rate_limit_carries_retry_after_and_the_request_id():
    payload = {"name": "rate_limit_exceeded", "message": "slow down", "statusCode": 429}
    headers = {"Retry-After": "7", "X-Request-Id": "req_9"}

    with pytest.raises(RateLimitError) as excinfo:
        make_client(json_handler(429, payload, headers)).scheduled_emails.list()

    assert excinfo.value.retry_after == 7
    assert excinfo.value.request_id == "req_9"


@pytest.mark.parametrize("payload", [[], "nope", None, 123, True])
def test_a_non_object_success_body_is_reported_clearly(payload):
    with pytest.raises(MailkubeError, match="Expected a JSON object"):
        make_client(json_handler(200, payload)).scheduled_emails.get(EMAIL_ID)


def test_a_transport_failure_becomes_a_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(MailkubeConnectionError):
        make_client(handler).scheduled_emails.list()
