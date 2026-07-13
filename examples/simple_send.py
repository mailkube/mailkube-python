"""Send a single email with the synchronous client.

Run with your API key in the environment:

    MAILKUBE_API_KEY=mk_... python examples/simple_send.py
"""

from mailkube import Mailkube

with Mailkube() as client:  # reads MAILKUBE_API_KEY from the environment
    email = client.emails.send(
        from_="Acme <hello@yourdomain.com>",
        to="customer@example.com",
        subject="Hello world",
        html="<p>It works!</p>",
    )
    print("sent:", email.id)
    print("message_id:", email.message_id)
