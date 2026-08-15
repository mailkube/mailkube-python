"""Send a single email with the synchronous client.

Run with your API key in the environment:

    MAILKUBE_API_KEY=mk_... python examples/simple_send.py
"""

import os
from mailkube import Mailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

with Mailkube() as client:  # reads MAILKUBE_API_KEY from the environment
    email = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
        subject="Hello world",
        html="<p>It works!</p>",
    )
    print("sent:", email.id)
    print("message_id:", email.message_id)
