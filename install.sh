#!/usr/bin/env bash
# Install mod2mov.
#
#   ./install.sh              # pipx if available (bundles ffmpeg), else symlink
#   ./install.sh --link       # always symlink; uses your system ffmpeg
#   ./install.sh --link ~/bin # symlink into a specific directory
#
# The pipx route installs the imageio-ffmpeg dependency, which ships a static
# ffmpeg binary -- so the tool works even with no system ffmpeg. A symlink is
# lighter and tracks `git pull`, but needs ffmpeg installed separately.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/mod2mov.py"
[ -f "$src" ] || { echo "error: mod2mov.py not found next to this script" >&2; exit 1; }
chmod +x "$src"

mode="auto"
target=""
for arg in "$@"; do
  case "$arg" in
    --link) mode="link" ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) target="$arg" ;;
  esac
done
[ -n "$target" ] && mode="link"

on_path() { case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac; }

if [ "$mode" = "auto" ] && command -v pipx >/dev/null 2>&1; then
  echo "installing with pipx (bundles ffmpeg)..."
  pipx install --force "$here"
  echo
  echo "installed: $(command -v mod2mov 2>/dev/null || echo "run 'pipx ensurepath' and restart your shell")"
  exit 0
fi

if [ "$mode" = "auto" ]; then
  echo "pipx not found -- falling back to a symlink."
  echo "For a self-contained install that bundles ffmpeg: brew install pipx && ./install.sh"
  echo
fi

if [ -n "$target" ]; then
  dest="$target"
  mkdir -p "$dest"
else
  dest=""
  for d in "$HOME/.local/bin" "$HOME/bin" /opt/homebrew/bin /usr/local/bin; do
    if [ -d "$d" ] && [ -w "$d" ] && on_path "$d"; then dest="$d"; break; fi
  done
  if [ -z "$dest" ]; then dest="$HOME/.local/bin"; mkdir -p "$dest"; fi
fi

if [ ! -w "$dest" ]; then
  echo "error: $dest is not writable. Re-run with sudo, or pass a different directory:" >&2
  echo "  ./install.sh --link \$HOME/.local/bin" >&2
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
  echo "         (or use the pipx install above, which bundles it)"
fi
