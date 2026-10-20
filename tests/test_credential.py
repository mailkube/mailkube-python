"""The ``credential`` namespace: the calling API key describing itself."""

from __future__ import annotations

import pytest

from conftest import API_KEY, BASE_URL, MONTHLY_QUOTA, capturing_handler, json_handler, make_client
from mailkube import APIError, APIKey, AuthenticationError, ErrorName, MailkubeError, RateLimitError


def test_info_gets_the_calling_keys_description_with_no_body():
    captured = {}
    make_client(capturing_handler(200, API_KEY, captured)).credential.info()

    assert captured["method"] == "GET"
    assert captured["url"] == f"{BASE_URL}api-keys/me"
    assert captured["body"] is None


def test_info_sends_no_idempotency_key():
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return json_handler(200, API_KEY)(request)

    make_client(handler).credential.info()

    assert "idempotency-key" not in seen


def test_info_decodes_the_key_its_domain_organization_and_plan():
    key = make_client(json_handler(200, API_KEY)).credential.info()

    assert isinstance(key, APIKey)
    assert key.key_id == "k3v9x2m8q1w7r4t6y0p5s2a8"
    assert key.name == "production-backend"
    assert key.description is None
    assert key.created_at == "2026-09-02T08:14:03Z"
    assert key.last_auth_at == "2026-10-19T16:41:22Z"
    assert key.allowed_source_ips == ["203.0.113.0/24"]
    assert key.domain.name == "example.com"
    assert (key.organization.name, key.organization.alias) == ("Example Ltd", "example")
    assert key.plan is not None
    assert (key.plan.code, key.plan.name, key.plan.status) == (
        "00000000-0000-0000-0000-000000000003",
        "Momentum",
        "active",
    )
    daily = key.plan.quotas[0]
    assert (daily.name, daily.limit, daily.used, daily.remaining, daily.period) == (
        "emails_per_day",
        5000,
        120,
        4880,
        "2026-10-19",
    )


@pytest.mark.parametrize("payload", [{**API_KEY, "plan": None}, {k: v for k, v in API_KEY.items() if k != "plan"}])
def test_a_null_or_absent_plan_reads_as_no_plan(payload):
    assert make_client(json_handler(200, payload)).credential.info().plan is None


def test_a_monthly_only_plan_gets_no_synthesized_daily_quota():
    payload = {**API_KEY, "plan": {**API_KEY["plan"], "quotas": [MONTHLY_QUOTA]}}
    key = make_client(json_handler(200, payload)).credential.info()

    assert key.plan is not None
    assert [quota.name for quota in key.plan.quotas] == ["emails_per_month"]


def test_a_refused_key_raises_an_authentication_error():
    body = {"name": "invalid_api_key", "message": "API key is invalid"}
    with pytest.raises(AuthenticationError) as raised:
        make_client(json_handler(403, body)).credential.info()

    assert raised.value.error_name == ErrorName.INVALID_API_KEY


def test_a_rate_limit_carries_retry_after():
    body = {"name": "rate_limit_exceeded", "message": "slow down"}
    with pytest.raises(RateLimitError) as raised:
        make_client(json_handler(429, body, headers={"Retry-After": "59"})).credential.info()

    assert raised.value.retry_after == 59


def test_a_non_object_success_body_is_an_sdk_error():
    with pytest.raises(MailkubeError, match="Expected a JSON object"):
        make_client(json_handler(200, [])).credential.info()


def test_a_success_object_missing_a_required_field_is_an_sdk_error_not_a_validation_error():
    payload = {k: v for k, v in API_KEY.items() if k != "key_id"}
    with pytest.raises(MailkubeError, match="key_id") as raised:
        make_client(json_handler(200, payload)).credential.info()

    assert not isinstance(raised.value, APIError)
