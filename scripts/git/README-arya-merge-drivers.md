# ARYA merge drivers

Auto-resolves the recurring, *safe* merge-conflict classes so concurrent PRs stop wedging on them.

- **`union`** (git built-in, no setup): purely accumulative/append-only files (`.gitignore`,
  `requirements*.txt`, `go.sum`, `CHANGELOG*.md`, `.claude/state/*.jsonl`).
- **`arya-manifest`** (custom driver, `scripts/git/arya-merge-manifest.py`): structured manifests
  (`pyproject.toml`, `package.json`, `**/Cargo.toml`). It resolves **version-field collisions by
  max-semver**, **unions purely-additive hunks** (deps/members/exports), and **conservatively leaves
  genuine logic conflicts for a human**. Lockfiles are intentionally NOT auto-merged (regenerate them).

## Activate the custom driver (once per clone, or once globally)
```
scripts/git/install-arya-merge-drivers.sh            # this repo only
scripts/git/install-arya-merge-drivers.sh --global   # every repo on this machine / CI runner
```
Built-in `union` needs no activation. Origin: the 2026-07-10 duplicate-lane merge-conflict incident.
