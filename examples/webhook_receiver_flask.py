"""Receive and verify Mailkube webhooks in a Flask app.

MAILKUBE_WEBHOOK_SECRET=... flask --app examples/webhook_receiver_flask run
"""

import os

from flask import Flask, request

from mailkube import SignatureVerificationError, UnknownEvent, verify

app = Flask(__name__)
SECRET = os.environ["MAILKUBE_WEBHOOK_SECRET"]


@app.get("/webhooks/mailkube")
def register() -> tuple[str | dict[str, str], int]:
    """Answer Mailkube's one-time endpoint-registration challenge.

    When you create (or re-point the URL of) a webhook endpoint, Mailkube probes it
    with ``GET ...?hub.mode=subscribe&hub.challenge=<token>`` and only persists the
    endpoint if the response body echoes that token verbatim. Skip this and
    registration is rejected, so no events are ever delivered — signature
    verification below is necessary but not sufficient on its own.
    """
    if request.args.get("hub.mode") == "subscribe":
        return request.args.get("hub.challenge", ""), 200
    return {"error": "unexpected GET"}, 400


@app.post("/webhooks/mailkube")
def receive() -> tuple[dict[str, str | bool], int]:
    """Verify the signature over the raw body, then dispatch on the event type."""
    try:
        event = verify(request.get_data(), dict(request.headers), SECRET)
    except SignatureVerificationError:
        return {"error": "invalid signature"}, 400

    if isinstance(event, UnknownEvent):
        # A newer event type than this SDK version knows about — still usable.
        print("unknown event:", event.type, event.data)
    else:
        print("event:", event.type)

    return {"ok": True}, 200
