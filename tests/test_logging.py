"""Logging helpers: null by default, opt-in, secret redaction."""

from __future__ import annotations

import importlib
import logging

import pytest

import mailkube._logging
from conftest import make_client, ok_handler
from mailkube import enable_logging
from mailkube._logging import get_logger, logger, redact_headers

MESSAGE = {
    "from_": "sender@example.com",
    "to": "recipient@example.com",
    "subject": "Your Q3 invoice",
    "html": "<p>Please find the invoice attached.</p>",
}


def test_get_logger_is_namespaced():
    assert get_logger("mailkube.sub").name == "mailkube.sub"


def test_null_handler_attached_by_default():
    assert any(isinstance(handler, logging.NullHandler) for handler in logger.handlers)


def test_enable_logging_sets_level_and_stream_handler():
    enable_logging("INFO")
    assert logging.getLogger("mailkube").level == logging.INFO
    assert any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        ("WARNING", logging.WARNING),
        ("warning", logging.WARNING),
        # MAILKUBE_LOG is applied at import time, so an unparseable value must degrade rather than
        # raise: an environment variable that makes `import mailkube` fail is not a usable switch.
        ("1", logging.DEBUG),
        ("true", logging.DEBUG),
    ],
)
def test_the_env_var_is_a_level_not_a_switch(monkeypatch, env_value, expected):
    """MAILKUBE_LOG=WARNING must suppress debug records, not merely turn logging on."""
    previous = logger.level
    monkeypatch.setenv("MAILKUBE_LOG", env_value)
    try:
        importlib.reload(mailkube._logging)
        assert logging.getLogger("mailkube").level == expected
        assert logger.isEnabledFor(logging.DEBUG) is (expected == logging.DEBUG)
    finally:
        logger.setLevel(previous)


@pytest.mark.parametrize("header", ["authorization", "AUTHORIZATION", "Idempotency-Key", "idempotency-key"])
def test_redact_headers_masks_secrets_whatever_the_casing(header):
    assert redact_headers({header: "secret", "X-Foo": "bar"}) == {header: "***", "X-Foo": "bar"}


def test_requests_and_responses_are_logged_with_the_request_id(caplog):
    with caplog.at_level(logging.DEBUG, logger="mailkube"):
        make_client(ok_handler).emails.send(**MESSAGE, idempotency_key="idem_secret")

    records = " ".join(record.getMessage() for record in caplog.records)
    assert "request POST https://api.mailkube.com/mta/v1/emails" in records
    assert "status=200" in records
    assert "request_id=req_1" in records


def test_no_secret_or_personal_data_reaches_a_log_record(caplog):
    """A debug flag must not turn the SDK into a PII or credential exfiltration path."""
    with caplog.at_level(logging.DEBUG, logger="mailkube"):
        make_client(ok_handler).emails.send(**MESSAGE, idempotency_key="idem_secret")

    records = " ".join(record.getMessage() for record in caplog.records)
    assert "***" in records, "the redaction helper was not applied to the logged headers"
    for secret in ("mk_test", "idem_secret", MESSAGE["to"], MESSAGE["subject"], MESSAGE["html"]):
        assert secret not in records
