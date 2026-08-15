"""Tag a send with name/value pairs the server records on the sending-log.

    MAILKUBE_API_KEY=mk_... python examples/send_with_tags.py
"""

import os
from mailkube import Mailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

with Mailkube() as client:
    email = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
        subject="Welcome aboard",
        html="<p>Glad you're here.</p>",
        tags=[
            {"name": "campaign", "value": "spring24"},
            {"name": "plan", "value": "pro"},
        ],
    )
    print("sent:", email.id)
