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
- `ffmpeg` on your `PATH` (`brew install ffmpeg`)

## Install

```sh
git clone git@github.com:armanarutiunov/mod2mov.git
cd mod2mov
chmod +x mod2mov
ln -s "$PWD/mod2mov" /usr/local/bin/mod2mov   # optional
```

## Usage

```sh
mod2mov SOURCE_DIR DEST_DIR [--mode a|b|c]
```

```sh
# the common case
mod2mov ~/Downloads/videos1 ~/Movies/holiday

# see what it would do first
mod2mov ~/Downloads/videos1 ~/Movies/holiday --dry-run

# keep full motion smoothness, and record what was renamed to what
mod2mov ~/Downloads/videos1 ~/Movies/holiday --mode b --manifest holiday.csv
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
| `-p`, `--prefix` | `video_` | Output filename prefix |
| `-d`, `--digits` | `3` | Zero-padded digits in the sequence |
| `-s`, `--start` | `1` | First sequence number |
| `--crf` | `18` | x264 quality; lower is better, 18 is near-transparent |
| `--preset` | `slow` | x264 speed/efficiency tradeoff |
| `--audio-bitrate` | `192k` | AAC bitrate |
| `--ext` | `MOD` | Source extension to match; repeatable |
| `--no-preserve-dates` | off | Don't copy source timestamps onto the output |
| `--overwrite` | off | Replace existing output files |
| `--manifest CSV` | — | Write a source-to-output mapping |
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
- **Failures don't stop the run.** Remaining files still convert, the failed
  names are listed at the end, and the exit code is non-zero.

## License

MIT
