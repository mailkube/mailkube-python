"""Send an email with the asynchronous client, and thread a reply onto it.

MAILKUBE_API_KEY=mk_... python examples/async_send.py
"""

import asyncio
import os

from mailkube import AsyncMailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")


async def main() -> None:
    """Send a first message, then a reply threaded onto its Message-ID."""
    async with AsyncMailkube() as client:
        first = await client.emails.send(
            from_=SENDER,
            to=RECIPIENT,
            subject="Ticket #4821 opened",
            html="<p>We're on it.</p>",
        )
        print("first:", first.id, first.message_id)

        reply = await client.emails.send(
            from_=SENDER,
            to=RECIPIENT,
            subject="Re: Ticket #4821 opened",
            html="<p>Here's an update.</p>",
            headers={
                "In-Reply-To": first.message_id or "",
                "References": first.message_id or "",
            },
        )
        print("reply:", reply.id)


asyncio.run(main())
