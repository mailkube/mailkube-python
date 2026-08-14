"""The raise_for_response status-to-exception mapping."""

from __future__ import annotations

import pytest

from mailkube import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from mailkube._exceptions import ErrorName, raise_for_response

# The public error reference, transcribed by hand. Deliberately a literal and not derived from
# ErrorName: comparing the enum to itself proves nothing, and comparing it to another repo's file
# would make this suite depend on a checkout that is not here. A dropped, added or misspelled
# member fails structurally against this list.
DOCUMENTED_ERROR_NAMES = [
    "invalid_api_key",
    "browser_not_allowed",
    "scheduling_not_included",
    "missing_user_agent",
    "invalid_idempotency_key",
    "invalid_request_body",
    "invalid_idempotent_request",
    "concurrent_idempotent_requests",
    "missing_required_field",
    "validation_error",
    "invalid_from_address",
    "from_domain_not_allowed",
    "invalid_attachment",
    "max_recipients_exceeded",
    "max_message_size_exceeded",
    "body_content_rejected",
    "link_reputation_blocked",
    "quota_exceeded",
    "topic_not_found",
    "topic_disabled",
    "missing_required_variable",
    "template_not_published",
    "template_not_found",
    "scheduled_email_not_found",
    "scheduled_email_not_pending",
    "method_not_allowed",
    "not_acceptable",
    "unsupported_media_type",
    "rate_limit_exceeded",
    "application_error",
]


def test_error_name_covers_the_documented_catalogue():
    """Every documented error name must be available as a constant, and no extra ones invented."""
    assert sorted(member.value for member in ErrorName) == sorted(DOCUMENTED_ERROR_NAMES)


@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (400, BadRequestError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, InvalidRequestError),
        (429, RateLimitError),
        (500, ServerError),
        (599, ServerError),
        (418, APIError),
    ],
)
def test_status_maps_to_exception(status, exc):
    with pytest.raises(exc) as info:
        raise_for_response(status, {"name": "n", "message": "m"}, None)
    assert type(info.value) is exc
    assert info.value.error_name == "n"
    assert info.value.message == "m"
    assert info.value.status_code == status


def test_non_dict_body_yields_empty_fields():
    with pytest.raises(ServerError) as info:
        raise_for_response(500, None, None)
    assert info.value.error_name == ""
    assert info.value.message == ""
    assert info.value.body is None


def test_retry_after_is_carried():
    with pytest.raises(RateLimitError) as info:
        raise_for_response(429, {"name": "rate_limit_exceeded"}, 30)
    assert info.value.retry_after == 30
