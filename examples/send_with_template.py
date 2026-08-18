"""Send from a saved template instead of raw HTML/text.

    MAILKUBE_API_KEY=mk_... python examples/send_with_template.py <template-uuid>

The template must exist on the sending domain and be published — a draft or deleted one is a
`template_not_found`. `template_id` is mutually exclusive with `html`/`text`: the server renders
the stored content and substitutes `variables` into it.
"""

import os
import sys

from mailkube import Mailkube

# The verified sender this account may send from, and where to send it. Override per
# environment; the fallbacks are placeholders and will be rejected until you set your own.
SENDER = os.environ.get("MAILKUBE_FROM", "Acme <hello@yourdomain.com>")
RECIPIENT = os.environ.get("MAILKUBE_TO", "customer@example.com")
TEMPLATE_ID = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MAILKUBE_TEMPLATE_ID")

if not TEMPLATE_ID:
    raise SystemExit("usage: python examples/send_with_template.py <template-uuid>")

with Mailkube() as client:
    email = client.emails.send(
        from_=SENDER,
        to=RECIPIENT,
        subject="Welcome to Acme",
        template_id=TEMPLATE_ID,
        # "latest" tracks the newest version; pin a number to freeze the content you tested.
        template_version="latest",
        variables={"first_name": "Sam"},
    )
    print("sent:", email.id)
