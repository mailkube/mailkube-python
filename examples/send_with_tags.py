"""Tag a send with name/value pairs the server records on the sending-log.

    MAILKUBE_API_KEY=mk_... python examples/send_with_tags.py
"""

from mailkube import Mailkube

with Mailkube() as client:
    email = client.emails.send(
        from_="Acme <hello@yourdomain.com>",
        to="customer@example.com",
        subject="Welcome aboard",
        html="<p>Glad you're here.</p>",
        tags=[
            {"name": "campaign", "value": "spring24"},
            {"name": "plan", "value": "pro"},
        ],
    )
    print("sent:", email.id)
