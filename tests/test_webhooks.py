"""Webhook verification + parsing.

Signatures are recomputed independently here (mirroring api/webhook/services/sender.py),
never imported — the receiver and sender live on opposite sides of a trust boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from mailkube import (
    EmailBouncedEvent,
    EmailClickedEvent,
    EmailDeliveredEvent,
    SignatureVerificationError,
    UnknownEvent,
    parse_event,
    verify,
    verify_signature,
)
from mailkube.types.events import _event_discriminator

SECRET = "s" * 64
WEBHOOK_ID = "d1"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sign(body: bytes, *, webhook_id: str = WEBHOOK_ID, timestamp: str | None = None) -> dict[str, str]:
    ts = timestamp or _now_iso()
    signing_input = f"{webhook_id}.{ts}.".encode() + body
    digest = hmac.new(SECRET.encode(), signing_input, hashlib.sha256).hexdigest()
    return {"X-Webhook-Id": webhook_id, "X-Webhook-Ts": ts, "X-Webhook-Sig": f"sha256={digest}"}


def _msg_ctx() -> dict[str, object]:
    return {
        "email_id": "e1",
        "created_at": "2026-01-01T00:00:00Z",
        "domain": "acme.com",
        "subject": "Hi",
        "to": ["b@y.com"],
        "from": "a@x.com",
    }


def _event(event_type: str, data: dict[str, object]) -> bytes:
    return json.dumps({"type": event_type, "created_at": "2026-01-01T00:00:00Z", "data": data}).encode()


# --- Signature verification --------------------------------------------------------


def test_verify_signature_ok_returns_raw_body():
    body = _event("email.delivered", {**_msg_ctx(), "delivery": {"recipient": "b@y.com", "timestamp": "t"}})
    assert verify_signature(body, _sign(body), SECRET) == body


def test_verify_signature_accepts_str_payload():
    body = b'{"type":"x","created_at":"c","data":{}}'
    headers = _sign(body)
    assert verify_signature(body.decode(), headers, SECRET) == body


def test_verify_signature_without_prefix():
    body = b"{}"
    headers = _sign(body)
    headers["X-Webhook-Sig"] = headers["X-Webhook-Sig"].removeprefix("sha256=")
    assert verify_signature(body, headers, SECRET) == body


def test_tampered_body_rejected():
    body = b'{"a":1}'
    headers = _sign(body)
    with pytest.raises(SignatureVerificationError):
        verify_signature(b'{"a":2}', headers, SECRET)


def test_wrong_id_rejected():
    body = b"{}"
    headers = _sign(body)
    headers["X-Webhook-Id"] = "other"
    with pytest.raises(SignatureVerificationError):
        verify_signature(body, headers, SECRET)


def test_stale_timestamp_rejected():
    body = b"{}"
    old = (datetime.now(UTC) - timedelta(seconds=1000)).isoformat()
    with pytest.raises(SignatureVerificationError):
        verify_signature(body, _sign(body, timestamp=old), SECRET)


def test_naive_timestamp_treated_as_utc():
    body = b"{}"
    naive_ts = datetime.now(UTC).replace(tzinfo=None).isoformat()
    assert verify_signature(body, _sign(body, timestamp=naive_ts), SECRET) == body


def test_malformed_timestamp_rejected():
    body = b"{}"
    headers = _sign(body, timestamp="not-a-date")
    with pytest.raises(SignatureVerificationError):
        verify_signature(body, headers, SECRET)


@pytest.mark.parametrize("missing", ["X-Webhook-Id", "X-Webhook-Ts", "X-Webhook-Sig"])
def test_missing_header_rejected(missing):
    body = b"{}"
    headers = _sign(body)
    del headers[missing]
    with pytest.raises(SignatureVerificationError):
        verify_signature(body, headers, SECRET)


# --- Parsing + forward compatibility -----------------------------------------------

_DELIVERY = {"recipient": "b@y.com", "timestamp": "t"}
_FAILURE = {"recipient": "b@y.com", "timestamp": "t", "code": 550, "reason": "blocked"}
_OPEN = {"ipAddress": "1.2.3.4", "userAgent": "UA", "timestamp": "t"}

PAYLOADS = {
    "email.delivered": {**_msg_ctx(), "delivery": _DELIVERY},
    "email.bounced": {**_msg_ctx(), "bounce": _FAILURE},
    "email.delivery_delayed": {**_msg_ctx(), "delay": _FAILURE},
    "email.suppressed": {**_msg_ctx(), "suppression": {"recipients": ["b@y.com"], "timestamp": "t"}},
    "email.opened": {**_msg_ctx(), "open": _OPEN},
    "email.clicked": {**_msg_ctx(), "click": {**_OPEN, "link": "https://x/y"}},
    "domain.status": {
        "domain": "acme.com",
        "status": "active",
        "onboarding_state": "done",
        "previous": {"status": "on_hold", "onboarding_state": "pending"},
    },
    "webhook.status": {
        "endpoint_url": "https://x/hook",
        "is_active": True,
        "is_deleted": False,
        "disabled_reason": "none",
        "previous": {"is_active": False, "is_deleted": False, "disabled_reason": "user"},
    },
}


@pytest.mark.parametrize("event_type", list(PAYLOADS))
def test_parse_each_known_event(event_type):
    event = parse_event(_event(event_type, PAYLOADS[event_type]))
    assert event.type == event_type
    assert not isinstance(event, UnknownEvent)


def test_parse_delivered_fields():
    event = parse_event(_event("email.delivered", PAYLOADS["email.delivered"]))
    assert isinstance(event, EmailDeliveredEvent)
    assert event.data.from_ == "a@x.com"
    assert event.data.delivery.recipient == "b@y.com"


def test_parse_bounced_failure_fields():
    event = parse_event(_event("email.bounced", PAYLOADS["email.bounced"]))
    assert isinstance(event, EmailBouncedEvent)
    assert event.data.bounce.code == 550
    assert event.data.bounce.reason == "blocked"


def test_parse_clicked_camelcase_aliases():
    event = parse_event(_event("email.clicked", PAYLOADS["email.clicked"]))
    assert isinstance(event, EmailClickedEvent)
    assert event.data.click.ip_address == "1.2.3.4"
    assert event.data.click.user_agent == "UA"
    assert event.data.click.link == "https://x/y"


def test_unknown_event_type_falls_back():
    event = parse_event(_event("email.reopened", {"anything": 1}))
    assert isinstance(event, UnknownEvent)
    assert event.type == "email.reopened"
    assert event.data == {"anything": 1}


def test_extra_field_on_known_event_is_kept():
    payload = {**PAYLOADS["email.delivered"], "future_field": "kept"}
    event = parse_event(_event("email.delivered", payload))
    assert isinstance(event, EmailDeliveredEvent)


def test_verify_combinator_returns_typed_event():
    body = _event("email.delivered", PAYLOADS["email.delivered"])
    event = verify(body, _sign(body), SECRET)
    assert isinstance(event, EmailDeliveredEvent)


def test_discriminator_branches():
    assert _event_discriminator({"type": "email.delivered"}) == "email.delivered"
    assert _event_discriminator({"type": "nope"}) == "unknown"
    assert _event_discriminator({}) == "unknown"
    assert _event_discriminator(SimpleNamespace(type="domain.status")) == "domain.status"
    assert _event_discriminator(SimpleNamespace()) == "unknown"
