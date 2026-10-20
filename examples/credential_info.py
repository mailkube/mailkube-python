"""Describe the API key this client authenticates with, without sending anything.

Prints the key's domain, organization, allowlist, plan and send-quota usage, never the key
itself. Run with your API key in the environment:

    MAILKUBE_API_KEY=mk_... python examples/credential_info.py

The key is checked exactly as a send checks it, so this is also how to verify a key before
using it: a key that cannot send raises AuthenticationError (``invalid_api_key``). The call
counts as a use of the key, and plan figures can be up to 30 seconds old.
"""

import sys

from mailkube import AuthenticationError, Mailkube

with Mailkube() as client:  # reads MAILKUBE_API_KEY from the environment
    try:
        key = client.credential.info()
    except AuthenticationError as exc:
        sys.exit(f"this key cannot send: {exc.error_name}")

    print(f"key {key.key_id} ({key.name}) sends for {key.domain.name}")
    print(f"organization {key.organization.name} ({key.organization.alias})")
    print("allowed from", ", ".join(key.allowed_source_ips) or "any address")

    # A plan without a daily limit lists the monthly quota only; an absent quota is no limit.
    if key.plan is None:
        print("no subscription")
    else:
        print(f"plan {key.plan.name} ({key.plan.status})")
        for quota in key.plan.quotas:
            print(f"  {quota.name}: {quota.used} of {quota.limit} recipients in {quota.period}")
