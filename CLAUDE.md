# Project Rules

`mailkube` is a public (Apache-2.0) mailkube SDK published to PyPI.
Load the relevant rule file from `.rules/` based on the task.

## Rule Index

> **Index every rule (required).** Every file in `.rules/` MUST have a row in the table below. When you
> add or rename a `.rules/` file, add or update its row in the **same change** — an unindexed rule is
> invisible, because this index is what drives progressive disclosure. The `docs` CI job (`scripts/check-rule-index.sh`)
> fails the build if `.rules/` and this index drift. This convention holds for every mailkube repo.

| Rule File | Load When |
|---|---|
| `.rules/SOLID_DRY_KISS.md` | Writing or changing any code — the enforced engineering standards (SOLID, DRY, KISS, coverage, docs) and how to run each gate locally. |
| `.rules/RELEASE.md` | Touching `release.yml`, `[tool.semantic_release]`, versioning, or the PyPI OIDC publish flow. |

## Key Conventions (always apply)

- **Tooling is `uv`**: `uv sync`, `uv run …`; deps in PEP 621 `[project]` + `[dependency-groups]`; `uv.lock` committed.
- **`src/` layout** — code lives in `src/mailkube/`; tests in `tests/`.
- **Ruff** for lint **and** format; **line length ≤ 120**; **mypy strict** on `src`.
- **Type-annotate** every function; `from __future__ import annotations` at the top of modules.
- **≥ 90% coverage, line + branch** — enforced by `--cov-fail-under=90`; never lower the gate to make a change pass.
- **Max cyclomatic complexity 10** (ruff `C901`) — split, don't waive.
- **Every public module/class/function has a docstring** (ruff `D`, google convention).
- **No duplication** — the `jscpd` gate blocks at > 1% duplicated code; extract shared logic.
- **Conventional Commits** for PR titles (squash-merged); only `feat:`/`fix:`/`perf:` cut a release.
- **No secrets in the repo** — local config lives in a git-ignored `.env`, excluded from the built package.
- **Keep `README` / `CHANGELOG` current** with user-visible changes (the changelog is generated on release).
