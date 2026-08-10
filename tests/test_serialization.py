"""The request-body serializer: renames, header split, bytes attachments, omission."""

from __future__ import annotations

import base64
from datetime import UTC, datetime

from mailkube._base_client import BaseClient
from mailkube._serialization import query_value, to_iso


def _build(**params):
    return BaseClient._build_send_body(params)


def test_from_rename_and_omission():
    spec = _build(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
    assert spec.json["from"] == "a@x.com"
    assert "from_" not in spec.json
    assert spec.json == {"from": "a@x.com", "to": "b@y.com", "subject": "Hi", "html": "x"}
    assert spec.path == "emails"
    assert spec.headers == {}


def test_idempotency_key_becomes_header():
    spec = _build(from_="a@x.com", to="b@y.com", subject="Hi", html="x", idempotency_key="k9")
    assert spec.headers == {"Idempotency-Key": "k9"}
    assert "idempotency_key" not in spec.json


def test_bytes_attachment_is_base64_encoded():
    spec = _build(
        from_="a@x.com",
        to="b@y.com",
        subject="Hi",
        html="x",
        attachments=[{"filename": "a.txt", "content": b"DATA"}],
    )
    attachment = spec.json["attachments"][0]
    assert attachment["content"] == base64.b64encode(b"DATA").decode("ascii")
    assert base64.b64decode(attachment["content"]) == b"DATA"


def test_str_attachment_passthrough():
    spec = _build(
        from_="a@x.com",
        to="b@y.com",
        subject="Hi",
        html="x",
        attachments=[{"filename": "a.txt", "content": "YWJj"}],
    )
    assert spec.json["attachments"][0]["content"] == "YWJj"


def test_recipient_list_passthrough():
    spec = _build(from_="a@x.com", to=["b@y.com", "c@z.com"], subject="Hi", html="x")
    assert spec.json["to"] == ["b@y.com", "c@z.com"]


def test_tags_passthrough():
    tags = [{"name": "campaign", "value": "spring24"}, {"name": "plan", "value": "pro"}]
    spec = _build(from_="a@x.com", to="b@y.com", subject="Hi", html="x", tags=tags)
    assert spec.json["tags"] == tags


def test_scheduled_at_datetime_is_rendered_as_iso():
    spec = _build(
        from_="a@x.com",
        to="b@y.com",
        subject="Hi",
        html="x",
        scheduled_at=datetime(2026, 8, 20, 7, 0, tzinfo=UTC),
        batch_id="campaign-x",
    )
    assert spec.json["scheduled_at"] == "2026-08-20T07:00:00+00:00"
    assert spec.json["batch_id"] == "campaign-x"


def test_scheduled_at_string_passes_through_untouched():
    spec = _build(from_="a@x.com", to="b@y.com", subject="Hi", html="x", scheduled_at="2026-08-20T07:00:00Z")
    assert spec.json["scheduled_at"] == "2026-08-20T07:00:00Z"


def test_to_iso_renders_datetimes_and_passes_other_values_through():
    assert to_iso(datetime(2026, 8, 20, 7, 0, tzinfo=UTC)) == "2026-08-20T07:00:00+00:00"
    assert to_iso("2026-08-20T07:00:00Z") == "2026-08-20T07:00:00Z"
    assert to_iso(2) == "2"


def test_query_value_joins_lists_and_renders_scalars():
    assert query_value(["scheduled", "canceled"]) == "scheduled,canceled"
    assert query_value([datetime(2026, 8, 20, 7, 0, tzinfo=UTC)]) == "2026-08-20T07:00:00+00:00"
    assert query_value("scheduled") == "scheduled"
    assert query_value(3) == "3"
