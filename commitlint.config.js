// Conventional Commits ruleset shared by the pre-commit hook and CI.
// Only `feat:`, `fix:`, and `perf:` trigger a release on `main`.
module.exports = {
  extends: ["@commitlint/config-conventional"],
};
