"""Send from a saved template instead of raw HTML/text.

    MAILKUBE_API_KEY=mk_... python examples/send_with_template.py
"""

from mailkube import Mailkube

with Mailkube() as client:
    email = client.emails.send(
        from_="Acme <hello@yourdomain.com>",
        to="customer@example.com",
        subject="Welcome to Acme",
        template_id="3f6c2e1a-8b4d-4c2e-9a1f-2b3c4d5e6f70",
        template_version="latest",
        variables={"first_name": "Sam"},
    )
    print("sent:", email.id)
