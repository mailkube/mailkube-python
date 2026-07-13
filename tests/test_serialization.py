"""The request-body serializer: renames, header split, bytes attachments, omission."""

from __future__ import annotations

import base64

from mailkube._base_client import BaseClient


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
