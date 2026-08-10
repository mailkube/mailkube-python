"""Pagination: the page object, and the auto-paging iterator that follows the API's links."""

from __future__ import annotations

import httpx
import pytest

from conftest import BASE_URL, SCHEDULED_EMAIL, json_handler, make_client, page
from mailkube import MailkubeError


def _item(index: int) -> dict:
    return {**SCHEDULED_EMAIL, "id": f"id-{index}"}


def _paged_handler(pages: dict[str, dict]):
    """Answer each page URL with its payload, keyed by the request's full URL."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[str(request.url)])

    return handler


def test_has_more_reflects_whether_the_server_offered_a_next_link():
    listing = f"{BASE_URL}scheduled-emails"
    with_next = make_client(json_handler(200, page([_item(1)], f"{listing}?page=2"))).scheduled_emails.list()
    without = make_client(json_handler(200, page([_item(1)]))).scheduled_emails.list()

    assert with_next.has_more is True
    assert with_next.pagination.steps.next == f"{listing}?page=2"
    assert without.has_more is False
    assert without.pagination.steps.previous is None


def test_iter_all_walks_every_page_by_following_the_next_links():
    listing = f"{BASE_URL}scheduled-emails"
    pages = {
        listing: page([_item(1)], f"{listing}?page=2", current_page=1),
        f"{listing}?page=2": page([_item(2)], f"{listing}?page=3", current_page=2),
        f"{listing}?page=3": page([_item(3)], current_page=3),
    }

    found = list(make_client(_paged_handler(pages)).scheduled_emails.iter_all())

    assert [item.id for item in found] == ["id-1", "id-2", "id-3"]


def test_iter_all_forwards_the_filters_to_the_first_page():
    listing = f"{BASE_URL}scheduled-emails"
    pages = {f"{listing}?status=scheduled": page([_item(1)])}

    found = list(make_client(_paged_handler(pages)).scheduled_emails.iter_all(status="scheduled"))

    assert [item.id for item in found] == ["id-1"]


def test_iter_all_stops_on_a_single_page():
    found = list(make_client(json_handler(200, page([_item(1)]))).scheduled_emails.iter_all())

    assert len(found) == 1


def test_iter_all_yields_nothing_when_there_are_no_matches():
    assert list(make_client(json_handler(200, page([]))).scheduled_emails.iter_all()) == []


def test_a_next_link_on_a_foreign_origin_is_refused_not_followed():
    """A credentialed request must never be redirected off the configured API origin."""
    payload = page([_item(1)], "https://evil.example/mta/v1/scheduled-emails?page=2")

    with pytest.raises(MailkubeError, match="not on the configured API origin"):
        list(make_client(json_handler(200, payload)).scheduled_emails.iter_all())
