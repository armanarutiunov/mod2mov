#!/usr/bin/env bash
# Symlink mod2mov into a directory on your PATH.
#
#   ./install.sh              # pick a sensible directory automatically
#   ./install.sh ~/bin        # install somewhere specific
#
# A symlink (rather than a copy) means `git pull` updates the installed tool.

set -euo pipefail

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/mod2mov"
[ -f "$src" ] || { echo "error: mod2mov not found next to this script" >&2; exit 1; }
chmod +x "$src"

on_path() { case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac; }

if [ $# -gt 0 ]; then
  dest="$1"
  mkdir -p "$dest"
else
  # Prefer a writable directory already on PATH, so no sudo and no shell edits.
  dest=""
  for d in "$HOME/.local/bin" "$HOME/bin" /opt/homebrew/bin /usr/local/bin; do
    if [ -d "$d" ] && [ -w "$d" ] && on_path "$d"; then dest="$d"; break; fi
  done
  if [ -z "$dest" ]; then
    dest="$HOME/.local/bin"
    mkdir -p "$dest"
  fi
fi

if [ ! -w "$dest" ]; then
  echo "error: $dest is not writable. Re-run with sudo, or pass a different directory:" >&2
  echo "  ./install.sh \$HOME/.local/bin" >&2
  exit 1
fi

ln -sf "$src" "$dest/mod2mov"
echo "installed: $dest/mod2mov -> $src"

if ! on_path "$dest"; then
  echo
  echo "warning: $dest is not on your PATH. Add this to your shell profile:"
  echo "  export PATH=\"$dest:\$PATH\""
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo
  echo "warning: ffmpeg not found. Install it with: brew install ffmpeg"
fi
