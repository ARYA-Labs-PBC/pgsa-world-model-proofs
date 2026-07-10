#!/usr/bin/env python3
"""ARYA structured-manifest merge driver — "union, but smarter".

Git invokes:  arya-merge-manifest.py %O %A %B %L %P
  %O = ancestor (base)   %A = ours (ALSO the output file)   %B = theirs
  %L = conflict-marker length   %P = real pathname
Exit 0 => fully resolved (git accepts %A). Non-zero => conflicts remain (git leaves markers for a human).

Strategy (CONSERVATIVE — never silently drops code):
 1. Run the normal 3-way merge (`git merge-file`). If it merges cleanly, done.
 2. For each REMAINING conflict hunk, auto-resolve ONLY when confident:
      a. version-field collision (`version = "x"` / `"version": "x"`)  -> keep MAX semver
      b. purely-additive hunk (base side empty; both sides only ADD distinct lines) -> union (dedup, order-stable)
    Any other hunk is left conflicted (human decides).
 3. If no markers remain after step 2 -> write result, exit 0; else write (with markers), exit 1.

This handles the classes plain `union` breaks: concurrent version bumps (v0.9.5 vs v0.9.6),
crate/dep/member additions, __init__ export appends — across pyproject.toml, Cargo.toml, package.json, etc.
"""
import re
import subprocess
import sys

_VER_RE = re.compile(r"""^\s*(?:version\s*=\s*|["']version["']\s*:\s*)["']([0-9]+(?:\.[0-9]+)*[^"']*)["']\s*,?\s*$""")


def _semver_key(v):
    parts = re.split(r"[.\-+]", v)
    key = []
    for p in parts:
        key.append((0, int(p)) if p.isdigit() else (1, p))  # numeric sorts before/according to str
    return key


def _resolve_version_lines(lines):
    """If every non-blank line is a version field, return [max-semver line]; else None."""
    vers = []
    for ln in lines:
        m = _VER_RE.match(ln)
        if not m:
            if ln.strip() == "":
                continue
            return None
        vers.append((m.group(1), ln))
    if not vers:
        return None
    best = max(vers, key=lambda t: _semver_key(t[0]))
    return [best[1]]


def _resolve_additive(base_lines, ours, theirs):
    """If base side is empty (pure additions on both sides), union ours+theirs (stable, deduped)."""
    if [l for l in base_lines if l.strip()]:
        return None  # base had content -> this is a modification, not a pure add
    seen, out = set(), []
    for ln in ours + theirs:
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
    return out


def main():
    ancestor, ours, theirs, marker_len, path = (sys.argv[1], sys.argv[2], sys.argv[3],
                                                sys.argv[4] if len(sys.argv) > 4 else "7",
                                                sys.argv[5] if len(sys.argv) > 5 else "manifest")
    ml = int(marker_len) if str(marker_len).isdigit() else 7
    # 1. standard 3-way merge to a marked buffer
    # --diff3 emits the '||||||| base' section, which the additive-detector needs to tell a pure
    # ADD (empty base) from a MODIFICATION (non-empty base) — without it every conflict looks additive.
    r = subprocess.run(["git", "merge-file", "-p", "--diff3", f"--marker-size={ml}",
                        "-L", "ours", "-L", "base", "-L", "theirs", ours, ancestor, theirs],
                       capture_output=True, text=True)
    if r.returncode == 0:
        with open(ours, "w") as f:
            f.write(r.stdout)
        return 0  # clean merge

    merged = r.stdout.splitlines(keepends=True)
    lt, mid, gt = "<" * ml, "=" * ml, ">" * ml
    out, i, unresolved = [], 0, False
    while i < len(merged):
        line = merged[i]
        if line.startswith(lt):
            ours_b, base_b, theirs_b, sect = [], [], [], "ours"
            i += 1
            while i < len(merged) and not merged[i].startswith(gt):
                m = merged[i]
                if m.startswith(mid):
                    sect = "theirs"
                elif m.startswith("|" * ml):
                    sect = "base"
                else:
                    (ours_b if sect == "ours" else base_b if sect == "base" else theirs_b).append(m)
                i += 1
            i += 1  # consume the '>>>>>>>' line
            res = _resolve_version_lines(ours_b + theirs_b)
            if res is None:
                res = _resolve_additive(base_b, ours_b, theirs_b)
            if res is not None:
                out.extend(res)
            else:
                unresolved = True
                out.append(line)
                out.extend(ours_b)
                out.append((mid + "\n"))
                out.extend(theirs_b)
                out.append((gt + "\n"))
        else:
            out.append(line)
            i += 1
    with open(ours, "w") as f:
        f.write("".join(out))
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
