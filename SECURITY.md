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
[**"Report a vulnerability"**](https://github.com/mailkube/mailkube-python/security/advisories/new)
flow (Security → Advisories). This opens a private advisory visible only to the
maintainers.

When reporting, please include:

- a description of the issue and its impact,
- steps to reproduce (a minimal proof of concept if possible),
- the affected version/commit, and
- any suggested remediation.

For a vulnerability in the mailkube platform rather than in this repository, or if you
would rather not use GitHub, email security@mailkube.com. The full policy, including the
safe harbour for good-faith research, is published at https://mailkube.com/security/.

### What to expect

- **Acknowledgement** of every report we receive. We do not publish a response time, and
  we would rather say that than promise one we cannot always keep.
- **Triage and a severity assessment**, shared with you.
- We will keep you updated on remediation progress and coordinate a disclosure
  timeline with you. Credit is given to reporters who wish to be named.

This project is software placed on the EU market, so Regulation (EU) 2024/2847, the Cyber
Resilience Act, applies to it. We are ready for the Article 14 reporting obligations that
apply from 11 September 2026, and the remaining manufacturer obligations take effect on
11 December 2027. This is not a claim of compliance with that Regulation today.

## Handling secrets

Never commit credentials, API keys, or tokens to this repository. Local secrets belong in a
git-ignored `.env` and must never be baked into published packages or container images.
