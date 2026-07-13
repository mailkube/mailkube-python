"""Send an email with the asynchronous client, and thread a reply onto it.

    MAILKUBE_API_KEY=mk_... python examples/async_send.py
"""

import asyncio

from mailkube import AsyncMailkube


async def main() -> None:
    """Send a first message, then a reply threaded onto its Message-ID."""
    async with AsyncMailkube() as client:
        first = await client.emails.send(
            from_="Acme <hello@yourdomain.com>",
            to="customer@example.com",
            subject="Ticket #4821 opened",
            html="<p>We're on it.</p>",
        )
        print("first:", first.id, first.message_id)

        reply = await client.emails.send(
            from_="Acme <hello@yourdomain.com>",
            to="customer@example.com",
            subject="Re: Ticket #4821 opened",
            html="<p>Here's an update.</p>",
            headers={
                "In-Reply-To": first.message_id or "",
                "References": first.message_id or "",
            },
        )
        print("reply:", reply.id)


asyncio.run(main())
