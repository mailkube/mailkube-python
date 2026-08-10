"""The ``emails`` resource — namespaced under ``client.emails``."""

from __future__ import annotations

from typing import Unpack

from .._resource import Resource
from .._transport import AsyncSendTransport, SendTransport
from ..types.params import SendEmailParams
from ..types.responses import Email


class EmailsResource(Resource[SendTransport]):
    """Synchronous ``client.emails`` namespace."""

    def send(self, **params: Unpack[SendEmailParams]) -> Email:
        """Send an email.

        Pass the fields of :class:`~mailkube.types.params.SendEmailParams` as keyword
        arguments — ``from_``, ``to``, and ``subject`` are required; supply ``html`` and/or
        ``text`` for a raw send, or ``template_id`` for a template. ``idempotency_key`` is
        sent as the ``Idempotency-Key`` header.

        Pass ``scheduled_at`` to schedule the send instead of delivering it now; the result
        then reports :attr:`~mailkube.types.responses.Email.is_scheduled` and the email can
        be managed through ``client.scheduled_emails``.

        Args:
            **params: The send parameters (see :class:`~mailkube.types.params.SendEmailParams`).

        Returns:
            The accepted-send :class:`~mailkube.types.responses.Email`.
        """
        return self._transport.send_email(params)


class AsyncEmailsResource(Resource[AsyncSendTransport]):
    """Asynchronous ``client.emails`` namespace."""

    async def send(self, **params: Unpack[SendEmailParams]) -> Email:
        """Send an email (async).

        See :meth:`EmailsResource.send` for the parameters.

        Args:
            **params: The send parameters (see :class:`~mailkube.types.params.SendEmailParams`).

        Returns:
            The accepted-send :class:`~mailkube.types.responses.Email`.
        """
        return await self._transport.send_email(params)
