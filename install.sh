#!/usr/bin/env bash
# Install mod2mov.
#
#   ./install.sh             # pipx if available, else a symlink
#   ./install.sh --bundled   # also install a static ffmpeg into the venv
#   ./install.sh --link      # just symlink the script
#   ./install.sh --link ~/bin
#
# ffmpeg is not installed by this script -- see the README. Install it first:
#   brew install ffmpeg

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
    --bundled) mode="bundled" ;;
    -h|--help) sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) target="$arg"; mode="link" ;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }
on_path() { case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac; }

symlink_install() {
  local dest="$1"
  if [ -z "$dest" ]; then
    for d in "$HOME/.local/bin" "$HOME/bin" /opt/homebrew/bin /usr/local/bin; do
      if [ -d "$d" ] && [ -w "$d" ] && on_path "$d"; then dest="$d"; break; fi
    done
    [ -z "$dest" ] && dest="$HOME/.local/bin"
  fi
  mkdir -p "$dest"
  if [ ! -w "$dest" ]; then
    echo "error: $dest is not writable. Re-run with sudo, or pass a directory:" >&2
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
}

if [ "$mode" = "link" ]; then
  symlink_install "$target"
elif have pipx; then
  if [ "$mode" = "bundled" ]; then
    pipx install --force "$here[bundled]"
  else
    pipx install --force "$here"
  fi
  echo
  echo "installed: $(command -v mod2mov 2>/dev/null || echo "run 'pipx ensurepath' and restart your shell")"
else
  echo "pipx not found -- installing as a symlink instead."
  echo "(for an isolated install: brew install pipx)"
  echo
  symlink_install ""
fi

if ! have ffmpeg && [ "$mode" != "bundled" ]; then
  echo
  echo "warning: ffmpeg not found. mod2mov needs it:"
  echo "  brew install ffmpeg"
fi
