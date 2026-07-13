# Release & Publishing

Load this when touching `release.yml`, `[tool.semantic_release]`, versioning, or PyPI publishing.

## The contract

1. **Conventional Commits drive the version.** On push to `main`, `python-semantic-release` reads the
   commit history since the last tag: `fix:` → patch, `feat:` → minor, `feat!:`/`BREAKING CHANGE:` → major.
   `perf:` also releases. Anything else (`chore`, `docs`, `ci`, `refactor`, `test`) does **not** release.
2. **It bumps `project.version` in `pyproject.toml`**, regenerates `CHANGELOG.md`, commits, tags `vX.Y.Z`,
   and creates a GitHub Release. `major_on_zero = false`, so `0.x` stays in `0.x` on `feat:`.
3. **Publishing is OIDC-only.** The `publish` job builds with `uv build` and uploads via
   `pypa/gh-action-pypi-publish` using GitHub's OIDC token — **no PyPI token is stored anywhere**.

## Required GitHub / PyPI setup (one-time, per repo)

- GitHub **environments** `release` and `pypi` must exist (Settings → Environments), with protection rules.
- A **PyPI Trusted Publisher** must be registered for this project pointing at:
  org = this GitHub org, repo = this repo, workflow = `release.yml`, environment = `pypi`.
  For a brand-new package name, use PyPI's **pending publisher** flow (the project need not exist yet).

## Do not

- Do not hand-edit `project.version` or `CHANGELOG.md` — semantic-release owns them.
- Do not add a `password:`/token to the publish step — that defeats OIDC and reintroduces a secret.
- Do not gate `release.yml` on anything weaker than the full `ci.yml` (`test` + `dry` + `docs`).
