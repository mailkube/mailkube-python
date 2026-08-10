"""The ``scheduled_emails`` resource — namespaced under ``client.scheduled_emails``.

A send carrying ``scheduled_at`` is accepted but not delivered yet; until it is due it
lives in this collection, where it can be listed, inspected, rescheduled or canceled —
one at a time, or a whole ``batch_id`` at once via ``client.scheduled_emails.batches``.

The request builders are module-level functions rather than methods so the synchronous
and asynchronous namespaces share one definition of every URL, body and query string.
Only the ``await`` differs between the two classes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Unpack
from urllib.parse import quote

from .._resource import Resource
from .._serialization import query_value, to_iso
from .._transport import AsyncScheduledTransport, RequestSpec, ScheduledTransport
from ..types.params import (
    ScheduledEmailBatchUpdateParams,
    ScheduledEmailListParams,
    ScheduledEmailUpdateParams,
)
from ..types.responses import (
    CanceledScheduledEmail,
    ScheduledEmail,
    ScheduledEmailBatchCancel,
    ScheduledEmailBatchUpdate,
    ScheduledEmailPage,
)

_SCHEDULED_PATH = "scheduled-emails"
_BATCH_PATH = "scheduled-emails/batches"


def _item_path(base: str, identifier: str) -> str:
    """Return the path of one item, with the identifier escaped.

    Escaping is not cosmetic: an identifier carrying an encoded ``?`` or ``/`` would
    otherwise re-target the request at a different route.

    Args:
        base: The collection path.
        identifier: The item's id or batch label.

    Returns:
        The item path.
    """
    return f"{base}/{quote(identifier, safe='')}"


def _list_spec(params: ScheduledEmailListParams) -> RequestSpec:
    """Build the request listing scheduled emails."""
    query = {key: query_value(value) for key, value in params.items()}
    return RequestSpec(path=_SCHEDULED_PATH, method="GET", params=query)


def _next_page_spec(page: ScheduledEmailPage) -> RequestSpec | None:
    """Build the request for the page after ``page``, or ``None`` if there is none.

    The API issues absolute page links, which the client only follows when they are on its
    own origin — so a link cannot redirect a credentialed request elsewhere.
    """
    next_url = page.pagination.steps.next
    if next_url is None:
        return None
    return RequestSpec(path=next_url, method="GET")


def _get_spec(email_id: str) -> RequestSpec:
    """Build the request retrieving one scheduled email."""
    return RequestSpec(path=_item_path(_SCHEDULED_PATH, email_id), method="GET")


def _update_spec(email_id: str, params: ScheduledEmailUpdateParams) -> RequestSpec:
    """Build the request rescheduling one scheduled email."""
    body: dict[str, object] = {"scheduled_at": to_iso(params["scheduled_at"])}
    batch_id = params.get("batch_id")
    if batch_id is not None:
        body["batch_id"] = batch_id
    return RequestSpec(path=_item_path(_SCHEDULED_PATH, email_id), method="PATCH", json=body)


def _cancel_spec(email_id: str) -> RequestSpec:
    """Build the request canceling one scheduled email."""
    return RequestSpec(path=_item_path(_SCHEDULED_PATH, email_id), method="DELETE")


def _batch_update_spec(batch_id: str, params: ScheduledEmailBatchUpdateParams) -> RequestSpec:
    """Build the request rescheduling a whole batch."""
    body: dict[str, object] = {"scheduled_at": to_iso(params["scheduled_at"])}
    return RequestSpec(path=_item_path(_BATCH_PATH, batch_id), method="PATCH", json=body)


def _batch_cancel_spec(batch_id: str) -> RequestSpec:
    """Build the request canceling a whole batch."""
    return RequestSpec(path=_item_path(_BATCH_PATH, batch_id), method="DELETE")


class ScheduledEmailBatchesResource(Resource[ScheduledTransport]):
    """Synchronous ``client.scheduled_emails.batches`` namespace."""

    def update(self, batch_id: str, **params: Unpack[ScheduledEmailBatchUpdateParams]) -> ScheduledEmailBatchUpdate:
        """Reschedule every pending email in a batch.

        Args:
            batch_id: The batch label the sends were grouped under.
            **params: The new due time (see
                :class:`~mailkube.types.params.ScheduledEmailBatchUpdateParams`).

        Returns:
            The batch result, including how many emails were moved.
        """
        return self._transport.request(_batch_update_spec(batch_id, params), ScheduledEmailBatchUpdate)

    def cancel(self, batch_id: str) -> ScheduledEmailBatchCancel:
        """Cancel every pending email in a batch.

        An unknown batch is a no-op reporting ``canceled_count: 0``, not an error.

        Args:
            batch_id: The batch label the sends were grouped under.

        Returns:
            The batch result, including how many emails were canceled.
        """
        return self._transport.request(_batch_cancel_spec(batch_id), ScheduledEmailBatchCancel)


class AsyncScheduledEmailBatchesResource(Resource[AsyncScheduledTransport]):
    """Asynchronous ``client.scheduled_emails.batches`` namespace."""

    async def update(
        self, batch_id: str, **params: Unpack[ScheduledEmailBatchUpdateParams]
    ) -> ScheduledEmailBatchUpdate:
        """Reschedule every pending email in a batch (async).

        See :meth:`ScheduledEmailBatchesResource.update`.

        Args:
            batch_id: The batch label the sends were grouped under.
            **params: The new due time.

        Returns:
            The batch result, including how many emails were moved.
        """
        return await self._transport.request(_batch_update_spec(batch_id, params), ScheduledEmailBatchUpdate)

    async def cancel(self, batch_id: str) -> ScheduledEmailBatchCancel:
        """Cancel every pending email in a batch (async).

        See :meth:`ScheduledEmailBatchesResource.cancel`.

        Args:
            batch_id: The batch label the sends were grouped under.

        Returns:
            The batch result, including how many emails were canceled.
        """
        return await self._transport.request(_batch_cancel_spec(batch_id), ScheduledEmailBatchCancel)


class ScheduledEmailsResource(Resource[ScheduledTransport]):
    """Synchronous ``client.scheduled_emails`` namespace.

    Attributes:
        batches: The batch operations (``client.scheduled_emails.batches``).
    """

    def __init__(self, transport: ScheduledTransport) -> None:
        """Bind the resource and its batch sub-namespace to a transport.

        Args:
            transport: The client that performs the requests.
        """
        super().__init__(transport)
        self.batches = ScheduledEmailBatchesResource(transport)

    def list(self, **params: Unpack[ScheduledEmailListParams]) -> ScheduledEmailPage:
        """List one page of scheduled emails.

        Args:
            **params: The filters (see
                :class:`~mailkube.types.params.ScheduledEmailListParams`).

        Returns:
            One page: :attr:`~mailkube.types.responses.ScheduledEmailPage.data` plus the
            pagination metadata. Use :meth:`iter_all` to walk every page.
        """
        return self._transport.request(_list_spec(params), ScheduledEmailPage)

    def iter_all(self, **params: Unpack[ScheduledEmailListParams]) -> Iterator[ScheduledEmail]:
        """Iterate every scheduled email matching the filters, across all pages.

        Pages are fetched lazily by following the links the API returns, so abandoning the
        iterator early costs nothing.

        Args:
            **params: The filters, as for :meth:`list`. A ``page`` sets the starting page.

        Yields:
            Each scheduled email, page after page.
        """
        page = self.list(**params)
        while True:
            yield from page.data
            spec = _next_page_spec(page)
            if spec is None:
                return
            page = self._transport.request(spec, ScheduledEmailPage)

    def get(self, email_id: str) -> ScheduledEmail:
        """Retrieve one scheduled email.

        Args:
            email_id: The id returned by the scheduled-send acknowledgement.

        Returns:
            The scheduled email.
        """
        return self._transport.request(_get_spec(email_id), ScheduledEmail)

    def update(self, email_id: str, **params: Unpack[ScheduledEmailUpdateParams]) -> ScheduledEmail:
        """Reschedule one scheduled email.

        Args:
            email_id: The id returned by the scheduled-send acknowledgement.
            **params: The new due time, and optionally a batch to move it into (see
                :class:`~mailkube.types.params.ScheduledEmailUpdateParams`).

        Returns:
            The updated scheduled email.
        """
        return self._transport.request(_update_spec(email_id, params), ScheduledEmail)

    def cancel(self, email_id: str) -> CanceledScheduledEmail:
        """Cancel one scheduled email.

        Args:
            email_id: The id returned by the scheduled-send acknowledgement.

        Returns:
            The cancellation acknowledgement.
        """
        return self._transport.request(_cancel_spec(email_id), CanceledScheduledEmail)


class AsyncScheduledEmailsResource(Resource[AsyncScheduledTransport]):
    """Asynchronous ``client.scheduled_emails`` namespace.

    Attributes:
        batches: The batch operations (``client.scheduled_emails.batches``).
    """

    def __init__(self, transport: AsyncScheduledTransport) -> None:
        """Bind the resource and its batch sub-namespace to an async transport.

        Args:
            transport: The async client that performs the requests.
        """
        super().__init__(transport)
        self.batches = AsyncScheduledEmailBatchesResource(transport)

    async def list(self, **params: Unpack[ScheduledEmailListParams]) -> ScheduledEmailPage:
        """List one page of scheduled emails (async).

        See :meth:`ScheduledEmailsResource.list`.

        Args:
            **params: The filters.

        Returns:
            One page of scheduled emails.
        """
        return await self._transport.request(_list_spec(params), ScheduledEmailPage)

    async def iter_all(self, **params: Unpack[ScheduledEmailListParams]) -> AsyncIterator[ScheduledEmail]:
        """Iterate every matching scheduled email across all pages (async).

        See :meth:`ScheduledEmailsResource.iter_all`.

        Args:
            **params: The filters.

        Yields:
            Each scheduled email, page after page.
        """
        page = await self.list(**params)
        while True:
            for item in page.data:
                yield item
            spec = _next_page_spec(page)
            if spec is None:
                return
            page = await self._transport.request(spec, ScheduledEmailPage)

    async def get(self, email_id: str) -> ScheduledEmail:
        """Retrieve one scheduled email (async).

        See :meth:`ScheduledEmailsResource.get`.

        Args:
            email_id: The scheduled email's id.

        Returns:
            The scheduled email.
        """
        return await self._transport.request(_get_spec(email_id), ScheduledEmail)

    async def update(self, email_id: str, **params: Unpack[ScheduledEmailUpdateParams]) -> ScheduledEmail:
        """Reschedule one scheduled email (async).

        See :meth:`ScheduledEmailsResource.update`.

        Args:
            email_id: The scheduled email's id.
            **params: The new due time, and optionally a batch to move it into.

        Returns:
            The updated scheduled email.
        """
        return await self._transport.request(_update_spec(email_id, params), ScheduledEmail)

    async def cancel(self, email_id: str) -> CanceledScheduledEmail:
        """Cancel one scheduled email (async).

        See :meth:`ScheduledEmailsResource.cancel`.

        Args:
            email_id: The scheduled email's id.

        Returns:
            The cancellation acknowledgement.
        """
        return await self._transport.request(_cancel_spec(email_id), CanceledScheduledEmail)
