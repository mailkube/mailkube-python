# Security Policy

## Supported versions

`mailkube` follows [Semantic Versioning](https://semver.org/). Security
fixes are released for the **latest published major version**. Older majors are supported only
while explicitly noted in the release notes.

| Version    | Supported          |
| ---------- | ------------------ |
| latest major | :white_check_mark: |
| older majors | :x:                |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report vulnerabilities privately through GitHub's
[**"Report a vulnerability"**](https://github.com/mailkube/mailkube/security/advisories/new)
flow (Security → Advisories). This opens a private advisory visible only to the
maintainers.

When reporting, please include:

- a description of the issue and its impact,
- steps to reproduce (a minimal proof of concept if possible),
- the affected version/commit, and
- any suggested remediation.

### What to expect

- **Acknowledgement** within 3 business days.
- **Triage and severity assessment** within 7 business days.
- We will keep you updated on remediation progress and coordinate a disclosure
  timeline with you. Credit is given to reporters who wish to be named.

## Handling secrets

Never commit credentials, API keys, or tokens to this repository. Local secrets belong in a
git-ignored `.env` and must never be baked into published packages or container images.
