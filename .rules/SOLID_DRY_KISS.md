# Engineering Standards: SOLID · DRY · KISS · Coverage · Docs

These are **enforced by CI** — a PR that violates them cannot merge. This file tells you the exact
thresholds and how to satisfy each gate locally *before* pushing.

## The five pillars

| Pillar | Rule | Enforced by |
|---|---|---|
| **Coverage** | ≥ 90% **line and branch** | `pytest --cov-branch --cov-fail-under=90` (the `test` CI job) |
| **DRY** | ≤ 1% duplicated code | `jscpd` (the `dry` CI job) |
| **KISS** | cyclomatic complexity ≤ 10 per unit | ruff `C901` (the `test` CI job) |
| **Documentation** | every public module/class/function has a docstring | ruff `D` / google convention |
| **SOLID** | see below — approximated by lint + review | ruff `PL`/`SIM`/`ARG`/`B` + PR checklist |

## Run the gates locally

```bash
uv run ruff check .            # lint incl. C901 (complexity), D (docstrings), PL/SIM/ARG (SOLID smells)
uv run ruff format --check .   # formatting
uv run mypy src                # strict types
uv run pytest                  # tests + 90% line+branch coverage gate
npx --yes jscpd@4 --config .jscpd.json .   # duplication (DRY) gate
./scripts/check-rule-index.sh  # every .rules/*.md indexed in CLAUDE.md
```

`uv run pre-commit run --all-files` runs the ruff + jscpd + commitlint hooks in one shot.

## SOLID, concretely (paradigm-neutral guidance)

SOLID is not a single lint rule; keep these in mind and confirm them in the PR checklist:

- **S**ingle responsibility — a function/class does one thing; if you need "and" to describe it, split it.
- **O**pen/closed — extend via new functions/subclasses/strategies, not by editing stable call sites.
- **L**iskov — subtypes honor their base's contract (types, exceptions, invariants).
- **I**nterface segregation — small, focused protocols; unused parameters (ruff `ARG`) are a smell.
- **D**ependency inversion — depend on an abstraction/`Protocol` at I/O and network boundaries, inject it.

## Requesting a waiver

If a threshold is genuinely wrong for a specific line, add a **scoped, commented** ignore
(e.g. `# noqa: C901  # parser dispatch, intentionally flat`) and call it out in the PR. Blanket
config relaxations (lowering `fail_under`, disabling a rule globally) require maintainer sign-off.
