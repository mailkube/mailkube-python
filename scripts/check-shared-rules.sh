#!/usr/bin/env bash
# Fail if a shared rule file in this repo has drifted from its canonical copy in repo-template.
#
# Some `.rules/` files are not written here. They are synced from `repo-template` so that every
# mailkube SDK and integration describes one API the same way. `repo-template`'s own CI keeps its
# templates in step with `common/`, but nothing keeps an ALREADY-GENERATED repo in step after the
# canonical file changes — and that gap is not hypothetical: the Python SDK ran for a release
# cycle against a constitution two sections out of date, and nobody noticed.
#
# This script closes it. It ships in `common/`, so every template and every repo generated from
# one inherits it with no per-repo wiring.
#
# Usage:  ./scripts/check-shared-rules.sh
#
# Environment:
#   SHARED_RULES_REPO   canonical repo, default mailkube/repo-template
#   SHARED_RULES_REF    ref to compare against, default main
#   GITHUB_TOKEN        required only when the canonical repo is private
set -euo pipefail

repo="${SHARED_RULES_REPO:-mailkube/repo-template}"
ref="${SHARED_RULES_REF:-main}"

# local path : canonical path within the repo-template checkout.
# A file absent locally is skipped, which is how one script serves both template kinds:
# SDK repos have no INTEGRATION_CONTRACT.md and integrations have both.
shared_rules=(
  ".rules/SDK_CONTRACT.md:common/.rules/SDK_CONTRACT.md"
  ".rules/INTEGRATION_CONTRACT.md:common-integration/.rules/INTEGRATION_CONTRACT.md"
)

fetch() {
  local path="$1" dest="$2"
  local url="https://api.github.com/repos/${repo}/contents/${path}?ref=${ref}"
  # Built as one always-non-empty array: expanding an EMPTY array under `set -u` is an error on
  # bash 3.2, which is what macOS ships, and it would fail this check open.
  local -a args=(
    --fail --silent --show-error --location
    -H "Accept: application/vnd.github.raw"
    -H "X-GitHub-Api-Version: 2022-11-28"
  )
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    args+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
  fi
  # The API contents endpoint (rather than raw.githubusercontent) so a token works when the
  # canonical repo is private.
  curl "${args[@]}" "$url" --output "$dest"
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

checked=0
drifted=0

for entry in "${shared_rules[@]}"; do
  local_path="${entry%%:*}"
  canonical_path="${entry#*:}"

  [[ -f "$local_path" ]] || continue
  checked=$((checked + 1))

  dest="$tmp/$(basename "$local_path")"
  if ! fetch "$canonical_path" "$dest"; then
    echo "ERROR: could not fetch ${canonical_path} from ${repo}@${ref}." >&2
    echo "       If ${repo} is private, expose a token as GITHUB_TOKEN for this job." >&2
    exit 1
  fi

  if ! diff -u "$dest" "$local_path" >"$tmp/diff" 2>&1; then
    drifted=$((drifted + 1))
    echo "ERROR: $local_path has drifted from ${repo}@${ref}:${canonical_path}" >&2
    echo "--- canonical" >&2
    echo "+++ this repo" >&2
    sed -n '3,$p' "$tmp/diff" >&2
    echo >&2
  fi
done

if [[ "$checked" -eq 0 ]]; then
  echo "No shared rule files present — nothing to check."
  exit 0
fi

if [[ "$drifted" -ne 0 ]]; then
  cat >&2 <<EOF

${drifted} shared rule file(s) are out of date.

These files are NOT edited here. To fix:
  1. If the canonical version is correct, copy it over the local one and commit.
  2. If YOUR version has the change that should win, open a PR against ${repo}
     editing the file under common/ (or common-integration/), then run 'make sync' there.
     Never edit a synced copy in place: the next sync silently reverts it.
EOF
  exit 1
fi

echo "Shared rules OK: ${checked} file(s) match ${repo}@${ref}."
