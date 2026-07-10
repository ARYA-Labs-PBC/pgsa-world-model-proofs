#!/usr/bin/env bash
# Register the ARYA custom merge driver so `.gitattributes  merge=arya-manifest` takes effect.
# Custom merge drivers CANNOT live in .gitattributes alone — they need a git config entry.
# Default scope: repo-local. Pass --global to install for every repo on this machine (agent boxes/CI).
set -euo pipefail
SCOPE="--local"; DRV="$(cd "$(dirname "$0")" && pwd)/arya-merge-manifest.py"
if [ "${1:-}" = "--global" ]; then
  SCOPE="--global"; DEST="$HOME/.config/arya/git/arya-merge-manifest.py"
  mkdir -p "$(dirname "$DEST")"; cp "$DRV" "$DEST"; DRV="$DEST"
fi
git config $SCOPE merge.arya-manifest.name "ARYA structured-manifest merge (max-semver + additive union, conservative)"
git config $SCOPE merge.arya-manifest.driver "python3 '$DRV' %O %A %B %L %P"
echo "installed arya-manifest merge driver ($SCOPE) -> $DRV"
