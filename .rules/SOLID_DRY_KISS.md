# Engineering Standards: SOLID · DRY · KISS · Coverage · Docs

These are **enforced by CI** — a PR that violates them cannot merge. This file tells you the exact
thresholds and how to satisfy each gate locally *before* pushing.

## The five pillars

| Pillar | Rule | Enforced by |
|---|---|---|
| **Coverage** | ≥ 90% **line and branch** | `pytest --cov-branch --cov-fail-under=90` (the `test` CI job) |
| **DRY** | ≤ 1% duplicated code | `jscpd` (the `dry` CI job) — `src/` at `minTokens: 50`, `examples/` at 100 |
| **Examples compile** | every `examples/*.py` is valid Python | `compileall` (the `examples` CI job) |
| **KISS** | cyclomatic complexity ≤ 10 per unit | ruff `C901` (the `test` CI job) |
| **Documentation** | every public module/class/function has a docstring | ruff `D` / google convention |
| **SOLID** | see below — approximated by lint + review | ruff `PL`/`SIM`/`ARG`/`B` + PR checklist |

## Run the gates locally

```bash
uv run ruff check .            # lint incl. C901 (complexity), D (docstrings), PL/SIM/ARG (SOLID smells)
uv run ruff format --check .   # formatting
uv run mypy                    # strict types (src + examples)
uv run pytest                  # tests + 90% line+branch coverage gate
npx --yes jscpd@4 --config .jscpd.json .   # duplication (DRY) gate
npx --yes jscpd@4 --config .jscpd.examples.json examples/   # the same gate over examples/
python -m compileall -q examples/            # every example compiles
./scripts/check-rule-index.sh  # every .rules/*.md indexed in AGENTS.md
```

`uv run pre-commit run --all-files` runs the ruff + jscpd + commitlint hooks in one shot.

**`examples/` is in scope for ruff and mypy.** It is runnable documentation, which is the reason,
not an exception to it: customers copy those files, and every defect the SDK certification run
surfaced lived there because no gate looked at it. Two carve-outs remain, each for a reason:

- **Duplication** is measured by a *separate* pass, `.jscpd.examples.json`, at `minTokens: 100`
  instead of 50. Every example repeats the same opening — import, read `MAILKUBE_FROM`, construct
  the client — and hoisting that into a shared helper would make each file unreadable on its own,
  which is the one thing an example must be. 100 clears that scaffolding (measured: the cliff is
  at 90) and still fails on a copy-pasted example.
- **Coverage** excludes them, because nothing in CI executes them: they need live credentials.

`flask` is in the dev group for the same reason: without it installed, mypy degrades
`examples/webhook_receiver_flask.py` to `Any` and stops checking it.

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
