"""Webhook verification + parsing.

Signatures are recomputed independently here (mirroring the scheme in .rules/SDK_CONTRACT.md),
never imported — the receiver and sender live on opposite sides of a trust boundary. That
independence is what makes ``_sign`` a usable oracle for the shipped ``sign`` below.
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
    EmailFailedEvent,
    EmailOpenedEvent,
    EmailScheduledEvent,
    EmailSentEvent,
    SignatureVerificationError,
    UnknownEvent,
    parse_event,
    sign,
    verify,
    verify_signature,
)
from mailkube.types.events import _KNOWN_TAGS, _event_discriminator

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
        "tags": [{"name": "campaign", "value": "welcome"}],
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


# The three below tie the shipped ``sign`` to the independent ``_sign`` oracle, from both
# directions: the value it produces, and the verifier's acceptance of what it produced.


def test_sign_matches_an_independently_computed_signature():
    body = b"{}"
    stamp = "2026-01-01T00:00:00+00:00"
    expected = _sign(body, timestamp=stamp)["X-Webhook-Sig"]

    assert sign(WEBHOOK_ID, stamp, body, SECRET) == expected


def test_the_verifier_accepts_what_sign_produces():
    body = b'{"type":"email.sent"}'
    stamp = _now_iso()
    headers = {
        "X-Webhook-Id": WEBHOOK_ID,
        "X-Webhook-Ts": stamp,
        "X-Webhook-Sig": sign(WEBHOOK_ID, stamp, body, SECRET),
    }

    assert verify_signature(body, headers, SECRET) == body


def test_sign_accepts_a_str_payload_as_utf8():
    body = '{"subject":"héllo"}'.encode()
    stamp = "2026-01-01T00:00:00+00:00"

    assert sign(WEBHOOK_ID, stamp, body.decode(), SECRET) == sign(WEBHOOK_ID, stamp, body, SECRET)


# --- Parsing + forward compatibility -----------------------------------------------

_DELIVERY = {"recipient": "b@y.com", "timestamp": "t"}
_FAILURE = {"recipient": "b@y.com", "timestamp": "t", "code": 550, "reason": "blocked"}
_OPEN = {"ipAddress": "1.2.3.4", "userAgent": "UA", "timestamp": "t"}

PAYLOADS = {
    "email.sent": {**_msg_ctx(), "sent": _DELIVERY},
    "email.delivered": {**_msg_ctx(), "delivery": _DELIVERY},
    "email.scheduled": {**_msg_ctx(), "scheduled": {"scheduled_at": "t", "batch_id": "b1"}},
    "email.failed": {**_msg_ctx(), "failed": {"reason": "mta_unreachable", "timestamp": "t"}},
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


def test_catalogue_matches_the_union():
    # Pins the tags derived from WebhookEvent. A dropped or misspelled union arm degrades that
    # event to UnknownEvent at runtime, which nothing else here would notice.
    expected = {
        "email.sent",
        "email.delivered",
        "email.scheduled",
        "email.failed",
        "email.bounced",
        "email.delivery_delayed",
        "email.suppressed",
        "email.opened",
        "email.clicked",
        "domain.status",
        "webhook.status",
    }
    assert expected == _KNOWN_TAGS


def test_every_known_event_has_a_parse_payload():
    assert set(PAYLOADS) == _KNOWN_TAGS


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


def test_parse_sent_reuses_the_delivery_block():
    event = parse_event(_event("email.sent", PAYLOADS["email.sent"]))
    assert isinstance(event, EmailSentEvent)
    assert event.data.sent.recipient == "b@y.com"
    assert event.data.sent.timestamp == "t"


def test_parse_scheduled_fields():
    event = parse_event(_event("email.scheduled", PAYLOADS["email.scheduled"]))
    assert isinstance(event, EmailScheduledEvent)
    assert event.data.scheduled.scheduled_at == "t"
    assert event.data.scheduled.batch_id == "b1"


def test_parse_scheduled_null_batch_id():
    payload = {**_msg_ctx(), "scheduled": {"scheduled_at": "t", "batch_id": None}}
    event = parse_event(_event("email.scheduled", payload))
    assert isinstance(event, EmailScheduledEvent)
    assert event.data.scheduled.batch_id is None


def test_parse_failed_fields():
    event = parse_event(_event("email.failed", PAYLOADS["email.failed"]))
    assert isinstance(event, EmailFailedEvent)
    assert event.data.failed.reason == "mta_unreachable"
    assert event.data.failed.timestamp == "t"


def test_parse_failed_accepts_an_unpublished_reason():
    payload = {**_msg_ctx(), "failed": {"reason": "some_future_reason", "timestamp": "t"}}
    event = parse_event(_event("email.failed", payload))
    assert isinstance(event, EmailFailedEvent)
    assert event.data.failed.reason == "some_future_reason"


def test_parse_message_tags():
    event = parse_event(_event("email.delivered", PAYLOADS["email.delivered"]))
    assert event.data.tags == [{"name": "campaign", "value": "welcome"}]


def test_tags_default_to_empty_when_absent():
    payload = {k: v for k, v in PAYLOADS["email.delivered"].items() if k != "tags"}
    event = parse_event(_event("email.delivered", payload))
    assert event.data.tags == []


def test_unknown_key_inside_a_tag_is_kept():
    # Tag is a TypedDict, which pydantic would normally prune; it inherits the parent model's
    # extra="allow". Locking that here because the leniency policy depends on it.
    payload = {**_msg_ctx(), "tags": [{"name": "c", "value": "w", "future": "kept"}], "delivery": _DELIVERY}
    event = parse_event(_event("email.delivered", payload))
    assert event.data.tags == [{"name": "c", "value": "w", "future": "kept"}]
    assert event.model_dump(by_alias=True)["data"]["tags"][0]["future"] == "kept"


def test_null_message_context_fields_parse():
    # The server resolves these through the sending transaction, which a per-recipient event
    # can briefly outlive; all four then arrive as null.
    payload = {
        **PAYLOADS["email.delivered"],
        "domain": None,
        "subject": None,
        "to": None,
        "from": None,
    }
    event = parse_event(_event("email.delivered", payload))
    assert isinstance(event, EmailDeliveredEvent)
    assert (event.data.domain, event.data.subject, event.data.to, event.data.from_) == (None, None, None, None)


def test_parse_clicked_camelcase_aliases():
    event = parse_event(_event("email.clicked", PAYLOADS["email.clicked"]))
    assert isinstance(event, EmailClickedEvent)
    assert event.data.click.ip_address == "1.2.3.4"
    assert event.data.click.user_agent == "UA"
    assert event.data.click.link == "https://x/y"


def test_engagement_parses_without_ip_or_user_agent():
    """A current server omits both keys, and an already-released client must not raise.

    Asserting the keys are *absent* from the payload rather than empty is what makes this
    meaningful: a required field would raise here, which is how the SDK stood before.
    """
    opened = parse_event(_event("email.opened", {**_msg_ctx(), "open": {"timestamp": "t"}}))
    assert isinstance(opened, EmailOpenedEvent)
    assert opened.data.open.ip_address is None
    assert opened.data.open.user_agent is None
    assert opened.data.open.timestamp == "t"

    clicked = parse_event(_event("email.clicked", {**_msg_ctx(), "click": {"timestamp": "t", "link": "https://x/y"}}))
    assert isinstance(clicked, EmailClickedEvent)
    assert clicked.data.click.ip_address is None
    assert clicked.data.click.link == "https://x/y"


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
