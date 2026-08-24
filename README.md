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

### Install options

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
mod2mov SOURCE [DEST] [options]
mod2mov help            # full option reference
```

`SOURCE` is a folder of `.MOD` files or a single `.MOD` file. `DEST` is
optional. Running `mod2mov` with no arguments prints the help.

### Output layout

Files are **always** named `<YYYY-MM-DD>-vid-<NNN>.mov`, numbered within their
own day, and grouped into **one folder per day**:

```
Aug 18, 2026/
  2026-08-18-vid-001.mov
  2026-08-18-vid-002.mov
Aug 23, 2026/
  2026-08-23-vid-001.mov
  ...
  2026-08-23-vid-104.mov
```

The date comes from each source file's timestamp, which for a camcorder is the
moment the clip finished recording. Numbering restarts each day and is padded
to three digits, so **alphabetical order always equals chronological order** —
inside a day folder, and also if you later tip every file into one folder.

Pass `--flat` to skip the day folders and write straight into `DEST`. The
filenames are unchanged, so they still sort correctly:

```
2026-08-18-vid-001.mov
2026-08-23-vid-104.mov
```

### Where the output goes

`DEST` is independent of the layout — it only says where the tree starts.

| You run | Output |
|---------|--------|
| `mod2mov ~/Downloads/videos1` | `~/Downloads/videos1_mov/Aug 23, 2026/2026-08-23-vid-001.mov` |
| `mod2mov ~/Downloads/videos1 ~/Movies/holiday` | `~/Movies/holiday/Aug 23, 2026/2026-08-23-vid-001.mov` |
| `mod2mov ~/Downloads/videos1 ~/Movies/holiday --flat` | `~/Movies/holiday/2026-08-23-vid-001.mov` |
| `mod2mov ~/Downloads/videos1/MOV001.MOD` | a day folder beside the source file |

Omit `DEST` and a folder converts into a sibling `<name>_mov` folder; a single
file converts beside itself.

### Examples

```sh
# the common case -- day folders, 25p
mod2mov ~/Downloads/videos1 ~/Movies/holiday

# see the full rename plan without encoding anything
mod2mov ~/Downloads/videos1 ~/Movies/holiday --dry-run

# everything in one folder, full motion smoothness, with a rename record
mod2mov ~/Downloads/videos1 ~/Movies/holiday --flat --mode b --manifest holiday.csv

# a second card folder, into a destination that already has clips from that day
mod2mov /Volumes/CARD/SD_VIDEO/PRG002 ~/Movies/holiday
```

That last one matters: numbering **continues past whatever the target day
folder already holds**, so a card split across `PRG001` and `PRG002` appends
(`...-vid-062.mov` onward) instead of colliding. The flip side is that
re-running over the same sources appends duplicates rather than skipping —
use `--dry-run` first if you are unsure what a folder already contains.


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

Every flag, with its default:

| Flag | Default | What it does |
|------|---------|--------------|
| `SOURCE` | — | Folder of `.MOD` files, or one `.MOD` file. Required. |
| `DEST` | see above | Where the output tree starts. Optional. |
| `-m`, `--mode {a,b,c}` | `a` | Deinterlacing mode — see above. |
| `-f`, `--flat` | off | Write every file straight into `DEST` instead of grouping into a folder per day. Filenames are unchanged. |
| `--folder-format FMT` | `%b %d, %Y` | `strftime` format for the day folders, e.g. `Aug 23, 2026`. Use `%Y-%m-%d` for `2026-08-23`. Ignored with `--flat`. |
| `--crf N` | `18` | x264 quality. Lower is better; 18 is near-transparent, 23 is ffmpeg's default, 28 is visibly lossy. |
| `--preset NAME` | `slow` | x264 speed/efficiency tradeoff (`ultrafast` … `veryslow`). Slower means a smaller file at the same quality. |
| `--audio-bitrate RATE` | `192k` | AAC bitrate. |
| `--ext EXT` | `MOD` | Source extension to match. Repeatable: `--ext MPG --ext TOD`. |
| `--no-preserve-dates` | off | Don't copy source timestamps onto the output. The day folders still come from the source date. |
| `--overwrite` | off | Replace existing output files instead of aborting. |
| `--manifest CSV` | — | Write a source-to-output mapping, with each output's timestamp. |
| `--ffmpeg PATH` | auto | Use a specific ffmpeg binary. Also settable as `$MOD2MOV_FFMPEG`. |
| `-n`, `--dry-run` | off | Print the full rename plan and exit without encoding. |
| `-h`, `--help`, `help` | — | Print the full reference. Also shown when run with no arguments. |


## Notes on correctness

- **Ordering** is by modification time, with filename as tiebreaker. Camcorder
  hex numbering already sorts correctly, but sorting by time also survives a
  card whose counter has wrapped.
- **Numbering continues** past whatever a day folder already holds, so a card
  split across `PRG001`/`PRG002` appends rather than colliding. The flip side:
  re-running over the same sources appends duplicates instead of skipping.
- **Three-digit padding** because a single day can hold more than 99 clips, and
  `vid-100` would otherwise sort before `vid-11`.
- **Aspect ratio** is carried through by ffmpeg. PAL SD stores 720×576 with a
  16:15 pixel aspect that displays as 4:3; losing that flag stretches the image.
- **Name collisions** are resolved before any encoding starts, and existing
  outputs abort the run unless you pass `--overwrite`.
- **Truncated encodes** are caught by comparing source and output duration after
  each file; a mismatch over 0.5s prints a warning.
- **In-place conversion is refused** rather than letting ffmpeg read and write
  the same path.
- **AppleDouble sidecars are skipped.** macOS writes `._MOV001.MOD` files onto
  FAT32 cards; they carry a video extension but hold 4KB of resource-fork
  metadata, and would otherwise take a slot in the numbering.
- **Sources are never modified**, only read.
- **Failures don't stop the run.** Remaining files still convert, the failed
  names are listed at the end, and the exit code is non-zero.

## License

MIT — see [LICENSE](LICENSE).

ffmpeg is a separate work with its own terms, and this repo contains no ffmpeg
binaries. The default install uses whatever ffmpeg you installed yourself, so
no ffmpeg licensing follows from using this tool. The optional `--bundled`
install pulls a GPL ffmpeg build from PyPI — fine for personal use, but worth
knowing if you ever embed mod2mov in a proprietary product.
