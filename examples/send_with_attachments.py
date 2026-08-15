"""Attach a file by passing raw bytes — the SDK base64-encodes it for you.

    MAILKUBE_API_KEY=mk_... python examples/send_with_attachments.py [path/to/file.pdf]

With no argument the example builds a tiny valid PDF in memory, so it runs without you having to
find a file first. Pass a path to attach a real one.
"""

import os
import sys
from pathlib import Path

from mailkube import Mailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")

# The smallest thing a PDF reader will still open, so the example has something real to attach.
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 50]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

pdf_bytes = Path(sys.argv[1]).read_bytes() if len(sys.argv) > 1 else MINIMAL_PDF

with Mailkube() as client:
    email = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
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
