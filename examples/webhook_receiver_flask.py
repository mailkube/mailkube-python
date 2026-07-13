"""Receive and verify Mailkube webhooks in a Flask app.

    MAILKUBE_WEBHOOK_SECRET=... flask --app examples/webhook_receiver_flask run
"""

import os

from flask import Flask, request

from mailkube import SignatureVerificationError, UnknownEvent, verify

app = Flask(__name__)
SECRET = os.environ["MAILKUBE_WEBHOOK_SECRET"]


@app.post("/webhooks/mailkube")
def receive():
    """Verify the signature over the raw body, then dispatch on the event type."""
    try:
        event = verify(request.get_data(), request.headers, SECRET)
    except SignatureVerificationError:
        return {"error": "invalid signature"}, 400

    if isinstance(event, UnknownEvent):
        # A newer event type than this SDK version knows about — still usable.
        print("unknown event:", event.type, event.data)
    else:
        print("event:", event.type)

    return {"ok": True}, 200
