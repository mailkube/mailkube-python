<!--
PR titles MUST follow Conventional Commits (e.g. `fix(client): ...`) — it is CI-enforced and
becomes the squash-merge commit message. Only feat/fix/perf trigger a release.
-->

## What

<!-- Describe the change in 1–2 sentences. -->

## Why

<!-- The user-visible problem this solves, or the motivation. -->

## Quality checklist

- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run mypy src` passes
- [ ] `uv run pytest` passes (coverage ≥ 90% line + branch)
- [ ] `npx jscpd --config .jscpd.json .` clean (no new duplication)
- [ ] Docs updated (`README.md`) if user-visible

## Engineering standards (SOLID / DRY / KISS)

- [ ] Single-responsibility: new/changed units do one thing; no god-functions
- [ ] No duplication introduced; shared logic extracted (DRY)
- [ ] Public APIs documented (docstrings — doc-lint passes)
- [ ] Complexity within limit (no lint-complexity waivers added)
- [ ] Depends on abstractions/interfaces where a boundary is crossed (DIP)

## Notes

<!-- Optional: screenshots, follow-ups, breaking-change details. -->
