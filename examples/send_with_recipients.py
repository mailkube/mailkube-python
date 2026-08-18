"""Every recipient field and custom headers on one message.

    MAILKUBE_API_KEY=mk_... python examples/send_with_recipients.py

``to``, ``cc``, ``bcc`` and ``reply_to`` each take a single address or a list. The account limit is
50 recipients per message, counted across to + cc + bcc.

Custom headers carry your own metadata. The API caps them at 20 per message, header names match
``[A-Za-z0-9-]`` up to 64 characters, and no value may contain CR or LF.
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
        to=[RECIPIENT],
        cc=RECIPIENT,
        bcc=[RECIPIENT],
        # Replies go somewhere other than the sending address.
        reply_to="support@yourdomain.com",
        subject="Every recipient field at once",
        html="<p>to, cc, bcc and reply-to on a single message.</p>",
        text="to, cc, bcc and reply-to on a single message.",
        headers={
            "X-Campaign-Id": "recipients-demo",
            "X-Customer-Tier": "gold",
        },
    )
    print("sent:", email.id)
