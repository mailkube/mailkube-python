#!/usr/bin/env bash
# Fail if any .rules/*.md file is not indexed in CLAUDE.md.
#
# The rule index in CLAUDE.md drives progressive disclosure; an unindexed rule is invisible.
# Runs against the current working directory (used both by generated repos and the meta-repo).
set -euo pipefail

rules_dir=".rules"
index_file="CLAUDE.md"

if [[ ! -d "$rules_dir" ]]; then
  echo "No $rules_dir/ directory — nothing to check."
  exit 0
fi

if [[ ! -f "$index_file" ]]; then
  echo "ERROR: $index_file not found, cannot verify the rule index." >&2
  exit 1
fi

missing=0
for rule in "$rules_dir"/*.md; do
  [[ -e "$rule" ]] || continue
  name="$(basename "$rule")"
  # Accept either the bare filename or the `.rules/<name>` path in the index table.
  if ! grep -qF "$name" "$index_file"; then
    echo "ERROR: $rule is not indexed in $index_file (add a row to the Rule Index table)." >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "Rule index OK: all $rules_dir/*.md files are indexed in $index_file."
