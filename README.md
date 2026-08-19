# mod2mov

Convert camcorder `.MOD` files to `.mov`, renamed in shooting order with their
original dates preserved.

Standard-definition camcorders (JVC Everio and similar) write `.MOD` files:
MPEG-2 program streams that are interlaced, use non-square pixels, and carry
AC-3 audio. Modern players handle that combination badly — QuickTime shows comb
artifacts on motion, editors often import them stretched, and the hex filenames
(`MOV009` → `MOV00A` → `MOV010`) don't read as a sequence.

`mod2mov` re-encodes to H.264/AAC in a `.mov` container, deinterlaces the way
you choose, renumbers the files as `video_001.mov`, `video_002.mov`, … in
shooting order, and copies each source file's timestamp onto its output so
sorting by date still works.

## Requirements

- Python 3.8+
- ffmpeg

## Install

```sh
brew install ffmpeg

git clone https://github.com/armanarutiunov/mod2mov.git
cd mod2mov
./install.sh
```

On Linux, swap the first line for `sudo apt-get install ffmpeg` (or `dnf`,
`pacman` — whatever your distribution uses).

`install.sh` installs the tool with `pipx` when it's available, falling back to
a symlink otherwise. It doesn't touch ffmpeg — it only warns if it's missing.

### Options

```sh
./install.sh --link          # just symlink; skip pipx entirely
./install.sh --link ~/bin    # symlink into a specific directory
./install.sh --bundled       # install a static ffmpeg into the venv (see below)
```

`--link` symlinks `mod2mov.py` into the first writable directory on your `PATH`
(`~/.local/bin`, `~/bin`, `/opt/homebrew/bin`, `/usr/local/bin`), so no `sudo`
is needed and `git pull` updates the installed tool.

`--bundled` pulls in [`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/),
which ships a static ffmpeg binary (~47MB) inside the virtualenv. Use it when
installing a system ffmpeg isn't practical. It's a GPL build, and it ships
without `ffprobe` — the tool falls back to parsing ffmpeg's own output for its
duration checks, so nothing is lost.

### Which ffmpeg gets used

Resolved in this order, first hit wins:

1. `--ffmpeg /path/to/ffmpeg`
2. `$MOD2MOV_FFMPEG`
3. `ffmpeg` on your `PATH`
4. the bundled copy, if installed with `--bundled`

### Uninstall

```sh
pipx uninstall mod2mov      # if installed with pipx
rm "$(command -v mod2mov)"  # if symlinked
```

## Usage

```sh
mod2mov SOURCE [DEST] [--mode a|b|c]
```

`SOURCE` is either a folder of `.MOD` files or a single `.MOD` file. `DEST` is
optional — leave it off and the output goes somewhere sensible:

| You run | Output goes to | Named |
|---------|----------------|-------|
| `mod2mov ~/Downloads/videos1` | `~/Downloads/videos1_mov/` | `video_001.mov`, `video_002.mov`, … |
| `mod2mov ~/Downloads/videos1/MOV001.MOD` | `~/Downloads/videos1/` | `MOV001.mov` |

So a folder gets a sibling folder with a `_mov` suffix, and a single file lands
next to the original. A batch is renumbered in shooting order; a lone file keeps
its own name, since renaming it to `video_001.mov` would risk colliding with a
batch you converted earlier. Pass `--prefix` to force sequence naming on a
single file too.

```sh
# the common case
mod2mov ~/Downloads/videos1

# see what it would do first
mod2mov ~/Downloads/videos1 --dry-run

# somewhere specific, full motion smoothness, with a record of the renames
mod2mov ~/Downloads/videos1 ~/Movies/holiday --mode b --manifest holiday.csv

# continue the numbering from a second memory card
mod2mov ~/Downloads/card2 ~/Movies/holiday --start 32
```

## Deinterlacing modes

The source records 50 *fields* per second — half-images of alternating scan
lines — woven into 25 frames. The two fields in a frame are 1/50s apart, so
anything that moved between them appears twice in the same frame. On a CRT this
was invisible; on a modern display it shows as horizontal comb teeth.

| Mode | Output | What it does |
|------|--------|--------------|
| **a** *(default)* | 25fps progressive | Keeps one field per frame and interpolates the missing lines. Clean, film-like motion, smallest files. |
| **b** | 50fps progressive | Expands *every* field to a full frame. Keeps all the motion the camera captured — smooth and immediate. ~35% larger. |
| **c** | 25fps interlaced | Preserves the original fields. Most faithful to the source, but combs on any player that doesn't deinterlace. |

If you're unsure, run a single clip through all three and compare a shot with
camera movement in it. **a** and **b** differ in motion feel, not quality;
**c** is the archival choice, not the watching choice.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `-m`, `--mode` | `a` | Deinterlacing mode (see above) |
| `-p`, `--prefix` | `video_` | Output filename prefix; also forces sequence naming for a single input file |
| `-d`, `--digits` | `3` | Zero-padded digits in the sequence |
| `-s`, `--start` | `1` | First sequence number |
| `--crf` | `18` | x264 quality; lower is better, 18 is near-transparent |
| `--preset` | `slow` | x264 speed/efficiency tradeoff |
| `--audio-bitrate` | `192k` | AAC bitrate |
| `--ext` | `MOD` | Source extension to match; repeatable |
| `--no-preserve-dates` | off | Don't copy source timestamps onto the output |
| `--overwrite` | off | Replace existing output files |
| `--manifest CSV` | — | Write a source-to-output mapping |
| `--ffmpeg PATH` | auto | Use a specific ffmpeg binary (also `$MOD2MOV_FFMPEG`) |
| `-n`, `--dry-run` | off | List what would be converted, then exit |

## Notes on correctness

- **Ordering** is by modification time, with filename as tiebreaker. Camcorder
  hex numbering already sorts correctly, but sorting by time also survives a
  card whose counter has wrapped.
- **Aspect ratio** is carried through by ffmpeg. PAL SD stores 720×576 with a
  16:15 pixel aspect that displays as 4:3; losing that flag stretches the image.
- **Name collisions** are resolved before any encoding starts, and existing
  outputs abort the run unless you pass `--overwrite`.
- **Truncated encodes** are caught by comparing source and output duration after
  each file; a mismatch over 0.5s prints a warning.
- **In-place conversion is refused** rather than letting ffmpeg read and write
  the same path.
- **Failures don't stop the run.** Remaining files still convert, the failed
  names are listed at the end, and the exit code is non-zero.

## License

MIT — see [LICENSE](LICENSE).

ffmpeg is a separate work with its own terms, and this repo contains no ffmpeg
binaries. The default install uses whatever ffmpeg you installed yourself, so
no ffmpeg licensing follows from using this tool. The optional `--bundled`
install pulls a GPL ffmpeg build from PyPI — fine for personal use, but worth
knowing if you ever embed mod2mov in a proprietary product.
