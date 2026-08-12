# Release & Publishing

Load this when touching `release.yml`, `[tool.semantic_release]`, versioning, or PyPI publishing.

## The contract

1. **Conventional Commits drive the version.** On push to `main`, `python-semantic-release` reads the
   commit history since the last tag: `fix:` → patch, `feat:` → minor, `feat!:`/`BREAKING CHANGE:` → major.
   `perf:` also releases. Anything else (`chore`, `docs`, `ci`, `refactor`, `test`) does **not** release.
2. **It creates the tag `vX.Y.Z` and the GitHub Release, and writes nothing else.** No commit, no
   `CHANGELOG.md`, no version bump in the tree. `major_on_zero = false`, so `0.x` stays in `0.x` on
   `feat:`. See "Why nothing is committed back to `main`".
3. **The tag IS the version.** `project.version` is `dynamic`; `hatch-vcs` resolves the tag at build
   time and writes it into the distribution metadata, and `mailkube.__version__` — which is also the
   `User-Agent` every request carries — reads it back from that metadata. The runtime version equals
   the released version by construction. There is **no version literal anywhere in the tree**: do not
   add one, and do not add `version_toml` or `version_variables`. A hand-maintained (or separately
   rewritten) literal is how this package spent 1.0.0 through 1.2.0 reporting itself as
   `mailkube-python/0.1.0`.
4. **Publishing is OIDC-only.** The `publish` job builds with `uv build` and uploads via
   `pypa/gh-action-pypi-publish` using GitHub's OIDC token — **no PyPI token is stored anywhere**.

## Why nothing is committed back to `main`

`main` is covered by a ruleset requiring a pull request and the `test` / `dry` / `docs` checks. A
`chore(release):` commit pushed straight to `main` by the workflow violates it, and the obvious fix
does not exist: **`github-actions[bot]` cannot be added to a ruleset bypass list.** Bypass is
available to admins, the maintain/write role, teams, GitHub Apps and Dependabot, and the built-in
Actions identity is none of those. Making the commit work would mean introducing a separate identity
— a GitHub App or a deploy key — purely to write a version number that the tag already carries.

So `release.yml` passes `commit: false`, `changelog: false` and `build: false` to the action, and
`[tool.semantic_release]` declares no version location at all. The release writes one tag and one
GitHub Release. The generated release notes are the changelog.

**`fetch-depth: 0` is mandatory on every checkout that builds or installs the package** — the `test`
job in `ci.yml` and the `publish` job here. A shallow clone carries no tags, so `hatch-vcs` resolves
no version and the package silently builds as an unrelated `0.1.devN`. On the publish path that
means uploading a wrong version to PyPI, which cannot be undone.

Verified: a clean checkout at `v1.4.0` builds `mailkube-1.4.0` in both the sdist and the wheel.
`[tool.hatch.build.hooks.vcs]` bakes the resolved version into the sdist, which matters because
`uv build` builds the wheel *from the sdist*, where no `.git` directory exists.

## Required GitHub / PyPI setup (one-time, per repo)

- GitHub **environments** `release` and `pypi` must exist (Settings → Environments), with protection rules.
- A **PyPI Trusted Publisher** must be registered for this project pointing at:
  org = this GitHub org, repo = this repo, workflow = `release.yml`, environment = `pypi`.
  For a brand-new package name, use PyPI's **pending publisher** flow (the project need not exist yet).

## Do not

- Do not add a static `project.version`, a `__version__` literal, `version_toml`, or
  `version_variables`. The git tag is the only source of truth.
- Do not re-enable `commit`/`changelog` on the release action, and do not drop `fetch-depth: 0` from
  the `test` or `publish` checkouts. Both failures are silent and land on PyPI.
- Do not add a `password:`/token to the publish step — that defeats OIDC and reintroduces a secret.
- Do not gate `release.yml` on anything weaker than the full `ci.yml` (`test` + `dry` + `docs`).
