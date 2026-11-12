#!/usr/bin/env bash
# Symlink (or copy with --copy) every skill in this repo into ~/.claude/skills/.
# Alternative to installing the Claude Code plugin; don't do both.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DEST=${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
MODE=link
[ "${1:-}" = "--copy" ] && MODE=copy
mkdir -p "$DEST"
for d in "$HERE"/plugins/rubin-analysis/skills/*/; do
  name=$(basename "$d")
  target="$DEST/$name"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "skip $name: $target exists and is not a symlink" >&2
    continue
  fi
  rm -f "$target"
  if [ "$MODE" = copy ]; then cp -r "$d" "$target"; else ln -s "${d%/}" "$target"; fi
  echo "$MODE $name -> $target"
done
echo "done. For lsst-eups see https://github.com/lsst-dm/agent-skills"
