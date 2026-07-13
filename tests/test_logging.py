"""Logging helpers: null by default, opt-in, secret redaction."""

from __future__ import annotations

import logging

from mailkube import enable_logging
from mailkube._logging import get_logger, logger, redact_headers


def test_get_logger_is_namespaced():
    assert get_logger("mailkube.sub").name == "mailkube.sub"


def test_null_handler_attached_by_default():
    assert any(isinstance(handler, logging.NullHandler) for handler in logger.handlers)


def test_enable_logging_sets_level_and_stream_handler():
    enable_logging("INFO")
    assert logging.getLogger("mailkube").level == logging.INFO
    assert any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)


def test_redact_headers_masks_secrets():
    redacted = redact_headers({"Authorization": "secret", "Idempotency-Key": "k", "X-Foo": "bar"})
    assert redacted["Authorization"] == "***"
    assert redacted["Idempotency-Key"] == "***"
    assert redacted["X-Foo"] == "bar"
