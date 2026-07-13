# Contributing to mailkube

Thanks for helping improve **mailkube**, a [mailkube](https://mailkube.com) SDK.
Contributions of all kinds are welcome: bug reports, fixes, docs, and features.

By contributing you agree that your contributions are licensed under the project's
[Apache License 2.0](LICENSE) (inbound = outbound). **No CLA and no sign-off are required.**
Please also read our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

Requires [uv](https://docs.astral.sh/uv/) (and Node.js for the `jscpd` duplication check).

```bash
git clone https://github.com/mailkube/mailkube
cd mailkube

uv sync                                              # create the env + install everything
uv run pre-commit install                            # ruff + format + jscpd hooks
uv run pre-commit install --hook-type commit-msg     # Conventional Commits hook
```

## Quality gates

Every change must pass the same checks CI runs (see [.rules/SOLID_DRY_KISS.md](.rules/SOLID_DRY_KISS.md)):

```bash
uv run ruff check .                          # lint incl. complexity (C901) + docstrings (D)
uv run ruff format --check .                 # formatting
uv run mypy src                              # strict types
uv run pytest                                # tests + 90% line+branch coverage gate
npx --yes jscpd@4 --config .jscpd.json .     # duplication (DRY) gate, blocks at > 1%
./scripts/check-rule-index.sh                # every .rules/*.md indexed in CLAUDE.md
```

`uv run pre-commit run --all-files` runs the lint/format/jscpd hooks in one shot.

## Commit & PR conventions

This project follows **[Conventional Commits](https://www.conventionalcommits.org/)**. A CI check
enforces the **PR title** (PRs are **squash-merged** using it), and it drives releases: only
`feat:`, `fix:`, and `perf:` cut a new version. See [.rules/RELEASE.md](.rules/RELEASE.md).

Suggested scopes: `client`, `models`, `ci`, `deps`, `docs`.

```
feat(client): add retry with exponential backoff
fix(models): correct optional field serialization
docs: document the pagination helper
```

## Reporting bugs / requesting features

Open an issue using the templates. For **security vulnerabilities**, do not open a public
issue — follow [SECURITY.md](SECURITY.md) instead.
