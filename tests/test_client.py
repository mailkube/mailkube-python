"""Sync client: request shaping, response mapping, errors, lifecycle."""

from __future__ import annotations

import json

import httpx
import pytest

from conftest import make_client, ok_handler
from mailkube import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InvalidRequestError,
    Mailkube,
    MailkubeConnectionError,
    MailkubeError,
    NotFoundError,
    RateLimitError,
    ServerError,
)


def test_send_success_shapes_request_and_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return ok_handler(request)

    client = make_client(handler)
    email = client.emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="<p>Hi</p>", idempotency_key="k1")

    assert email.id == "abc123"
    assert email.message_id == "<abc123@msg.mailkube.com>"
    assert email.request_id == "req_1"
    assert email.idempotent_replayed is False
    assert "req_1" in email.headers.values()

    assert captured["url"] == "https://api.mailkube.com/mta/v1/emails"
    assert captured["headers"]["authorization"] == "Bearer mk_test"
    assert captured["headers"]["user-agent"].startswith("mailkube-python/")
    assert captured["headers"]["idempotency-key"] == "k1"
    assert captured["body"]["from"] == "a@x.com"
    assert "from_" not in captured["body"]
    assert "idempotency_key" not in captured["body"]
    assert captured["body"]["to"] == "b@y.com"


def test_idempotent_replayed_true():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "x"}, headers={"Idempotent-Replayed": "true"})

    email = make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
    assert email.idempotent_replayed is True
    assert email.message_id is None
    assert email.request_id is None


@pytest.mark.parametrize(
    ("status", "name", "exc"),
    [
        (400, "missing_user_agent", BadRequestError),
        (403, "invalid_api_key", AuthenticationError),
        (404, "template_not_found", NotFoundError),
        (409, "invalid_idempotent_request", ConflictError),
        (422, "validation_error", InvalidRequestError),
        (429, "rate_limit_exceeded", RateLimitError),
        (500, "application_error", ServerError),
        (503, "application_error", ServerError),
        (418, "teapot", APIError),
    ],
)
def test_error_status_mapping(status, name, exc):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status, json={"name": name, "message": "boom", "statusCode": status}, headers={"Retry-After": "7"}
        )

    with pytest.raises(exc) as info:
        make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
    assert info.value.error_name == name
    assert info.value.status_code == status
    assert info.value.message == "boom"


def test_rate_limit_carries_retry_after():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"name": "rate_limit_exceeded", "message": "slow"},
            headers={"Retry-After": "12"},
        )

    with pytest.raises(RateLimitError) as info:
        make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
    assert info.value.retry_after == 12


def test_non_integer_retry_after_is_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"name": "rate_limit_exceeded", "message": "x"},
            headers={"Retry-After": "soon"},
        )

    with pytest.raises(RateLimitError) as info:
        make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
    assert info.value.retry_after is None


def test_transport_error_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(MailkubeConnectionError):
        make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")


@pytest.mark.parametrize("content", [b"", b"<html>oops</html>", b'{"no":"id"}'])
def test_bad_success_body_raises(content):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content)

    with pytest.raises(MailkubeError):
        make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")


def test_non_json_error_body_still_maps_by_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, content=b"<html>bad gateway</html>")

    with pytest.raises(ServerError) as info:
        make_client(handler).emails.send(from_="a@x.com", to="b@y.com", subject="Hi", html="x")
    assert info.value.error_name == ""


def test_injected_client_not_closed():
    http = httpx.Client(transport=httpx.MockTransport(ok_handler))
    client = Mailkube(api_key="mk_test", http_client=http)
    client.close()
    assert http.is_closed is False


def test_owned_client_closed_via_context_manager():
    with Mailkube(api_key="mk_x") as client:
        pass
    assert client._http.is_closed is True


def test_env_api_key_and_base_url(monkeypatch):
    monkeypatch.setenv("MAILKUBE_API_KEY", "mk_env")
    monkeypatch.setenv("MAILKUBE_BASE_URL", "https://custom.example/v9/")
    client = Mailkube()
    assert client._build_url("emails") == "https://custom.example/v9/emails"


def test_missing_api_key_errors(monkeypatch):
    monkeypatch.delenv("MAILKUBE_API_KEY", raising=False)
    with pytest.raises(MailkubeError):
        Mailkube()
