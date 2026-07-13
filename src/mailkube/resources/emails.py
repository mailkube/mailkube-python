"""The ``emails`` resource — namespaced under ``client.emails``."""

from __future__ import annotations

from typing import Unpack

from .._transport import AsyncSendTransport, SendTransport
from ..types.params import SendEmailParams
from ..types.responses import Email


class EmailsResource:
    """Synchronous ``client.emails`` namespace."""

    def __init__(self, transport: SendTransport) -> None:
        """Bind the resource to a transport.

        Args:
            transport: The client that performs the send.
        """
        self._transport = transport

    def send(self, **params: Unpack[SendEmailParams]) -> Email:
        """Send an email.

        Pass the fields of :class:`~mailkube.types.params.SendEmailParams` as keyword
        arguments — ``from_``, ``to``, and ``subject`` are required; supply ``html`` and/or
        ``text`` for a raw send, or ``template_id`` for a template. ``idempotency_key`` is
        sent as the ``Idempotency-Key`` header.

        Args:
            **params: The send parameters (see :class:`~mailkube.types.params.SendEmailParams`).

        Returns:
            The accepted-send :class:`~mailkube.types.responses.Email`.
        """
        return self._transport.send_email(params)


class AsyncEmailsResource:
    """Asynchronous ``client.emails`` namespace."""

    def __init__(self, transport: AsyncSendTransport) -> None:
        """Bind the resource to an async transport.

        Args:
            transport: The async client that performs the send.
        """
        self._transport = transport

    async def send(self, **params: Unpack[SendEmailParams]) -> Email:
        """Send an email (async).

        See :meth:`EmailsResource.send` for the parameters.

        Args:
            **params: The send parameters (see :class:`~mailkube.types.params.SendEmailParams`).

        Returns:
            The accepted-send :class:`~mailkube.types.responses.Email`.
        """
        return await self._transport.send_email(params)
