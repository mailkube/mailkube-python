"""Attach a file by passing raw bytes — the SDK base64-encodes it for you.

    MAILKUBE_API_KEY=mk_... python examples/send_with_attachments.py
"""

from pathlib import Path

from mailkube import Mailkube

pdf_bytes = Path("invoice.pdf").read_bytes()

with Mailkube() as client:
    email = client.emails.send(
        from_="Acme <hello@yourdomain.com>",
        to="customer@example.com",
        subject="Your invoice",
        html="<p>Your invoice is attached.</p>",
        attachments=[
            {
                "filename": "invoice.pdf",
                "content": pdf_bytes,  # raw bytes, or a base64 string
                "content_type": "application/pdf",
            }
        ],
    )
    print("sent:", email.id)
