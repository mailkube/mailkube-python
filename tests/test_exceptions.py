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
from mailkube._exceptions import raise_for_response


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
