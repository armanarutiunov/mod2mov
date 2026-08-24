#!/usr/bin/env python3
"""Convert camcorder .MOD files to .mov, in shooting order, with dates preserved.

MOD files are MPEG-2 program streams written by standard-definition camcorders
(JVC Everio and friends). They are interlaced, use non-square pixels, and carry
AC-3 audio -- a combination modern players handle badly. This tool re-encodes
them to H.264/AAC in a .mov container and renames them into a readable sequence.
"""

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Deinterlacing modes. Camcorder MOD footage stores 50 fields per second woven
# into 25 frames; the two fields in a frame are 1/50s apart, so anything moving
# shows comb artifacts on a progressive display.
MODES = {
    "a": {
        "label": "deinterlace to 25p",
        "help": "one frame per frame -- clean, film-like motion, smallest files",
        # yadif=0 -> one output frame per input frame (drops half the fields)
        "vf": "yadif=0:-1:0",
        "extra": [],
    },
    "b": {
        "label": "deinterlace to 50p",
        "help": "one frame per field -- full motion smoothness, ~35% larger",
        # yadif=1 -> one output frame per field, doubling the frame rate
        "vf": "yadif=1:-1:0",
        "extra": [],
    },
    "c": {
        "label": "keep interlaced",
        "help": "preserve the original fields -- most faithful, but combs on players that don't deinterlace",
        "vf": None,
        # Encode fields as fields and tag the stream top-field-first.
        "extra": ["-flags", "+ilme+ildct", "-top", "1"],
    },
}


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_ffmpeg(explicit=None):
    """Locate an ffmpeg binary.

    A system install is preferred -- it is usually newer and the user chose it --
    with the copy bundled by the imageio-ffmpeg dependency as the fallback, so
    the tool works on a machine with no ffmpeg of its own.
    """
    if explicit:
        return explicit if Path(explicit).exists() else None
    for candidate in (os.environ.get("MOD2MOV_FFMPEG"), shutil.which("ffmpeg")):
        if candidate and Path(candidate).exists():
            return candidate
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")


def probe_duration(path, ffmpeg):
    """Return duration in seconds, or None if it can't be determined.

    Uses ffprobe when available. The bundled ffmpeg ships without ffprobe, so
    fall back to parsing the Duration line ffmpeg prints when asked to describe
    an input.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, timeout=60,
            )
            return float(out.stdout.strip())
        except (ValueError, subprocess.SubprocessError):
            pass
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)],
                             capture_output=True, text=True, timeout=60)
        match = DURATION_RE.search(out.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except subprocess.SubprocessError:
        pass
    return None


def find_sources(src_dir, extensions):
    """Collect source files in shooting order.

    Camcorders number files in hex (MOV009 -> MOV00A -> MOV00F -> MOV010), so
    name order usually already matches shooting order. Sorting by mtime first is
    more robust -- it survives a card whose counter has wrapped -- with the name
    as tiebreaker for clips written within the same second.
    """
    wanted = {e.lower().lstrip(".") for e in extensions}
    files = [
        p for p in src_dir.iterdir()
        if p.is_file()
        and p.suffix.lower().lstrip(".") in wanted
        # macOS writes AppleDouble sidecars ("._MOV001.MOD") onto FAT32 cards.
        # They carry a video extension but are 4KB of resource-fork metadata.
        and not p.name.startswith("._")
    ]
    return sorted(files, key=lambda p: (p.stat().st_mtime, p.name.lower()))


def build_command(src, dst, mode, args, ffmpeg):
    cmd = [ffmpeg, "-nostdin", "-loglevel", "error", "-y" if args.overwrite else "-n",
           "-i", str(src)]
    if MODES[mode]["vf"]:
        cmd += ["-vf", MODES[mode]["vf"]]
    cmd += ["-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p"]
    cmd += MODES[mode]["extra"]
    cmd += ["-c:a", "aac", "-b:a", args.audio_bitrate]
    cmd += ["-movflags", "+faststart", str(dst)]
    return cmd


def run():
    epilog = "modes:\n" + "".join(
        f"  {k}  {v['label']:<22} {v['help']}\n" for k, v in MODES.items()
    ) + """
examples:
  mod2mov ~/Downloads/videos1                    -> ~/Downloads/videos1_mov/
  mod2mov ~/Downloads/videos1 ~/Movies/holiday   -> the given folder
  mod2mov ~/Downloads/videos1/MOV001.MOD         -> MOV001.mov, beside the source
"""

    parser = argparse.ArgumentParser(
        prog="mod2mov",
        description="Convert camcorder .MOD files to .mov, renaming them in "
                    "shooting order and preserving their original dates.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path,
                        help="a directory of .MOD files, or a single .MOD file")
    parser.add_argument("dest", type=Path, nargs="?", default=None,
                        help="output directory; defaults to SOURCE_mov for a "
                             "directory, or the file's own folder for a single file")
    parser.add_argument("-m", "--mode", choices=sorted(MODES), default="a",
                        help="deinterlacing mode (default: a)")
    parser.add_argument("-p", "--prefix", default=None,
                        help="output filename prefix (default: video_; a single "
                             "input file keeps its own name unless this is set)")
    parser.add_argument("-d", "--digits", type=int, default=3,
                        help="zero-padded digits in the sequence (default: 3)")
    parser.add_argument("-s", "--start", type=int, default=1,
                        help="first sequence number (default: 1)")
    parser.add_argument("--crf", type=int, default=18,
                        help="x264 quality, lower is better (default: 18)")
    parser.add_argument("--preset", default="slow",
                        help="x264 speed/efficiency preset (default: slow)")
    parser.add_argument("--audio-bitrate", default="192k",
                        help="AAC bitrate (default: 192k)")
    parser.add_argument("--ext", action="append", default=None, metavar="EXT",
                        help="source extension to match, repeatable (default: MOD)")
    parser.add_argument("--no-preserve-dates", action="store_true",
                        help="do not copy source timestamps onto the output")
    parser.add_argument("--overwrite", action="store_true",
                        help="replace existing output files")
    parser.add_argument("--manifest", type=Path, metavar="CSV",
                        help="write a source-to-output mapping to this CSV file")
    parser.add_argument("--ffmpeg", metavar="PATH",
                        help="use a specific ffmpeg binary (also: MOD2MOV_FFMPEG)")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="list what would be converted, then exit")
    args = parser.parse_args()

    ffmpeg = resolve_ffmpeg(args.ffmpeg)
    if ffmpeg is None:
        die("no ffmpeg available. Either install it (brew install ffmpeg), or "
            "reinstall this tool with its bundled copy (pipx install mod2mov).")
    if args.digits < 1:
        die("--digits must be at least 1")

    source = args.source.expanduser()
    if source.is_dir():
        sources = find_sources(source, args.ext or ["MOD"])
        if not sources:
            die(f"no matching files in {source}")
        # Default output sits beside the source folder, named <folder>_mov.
        dest = args.dest or source.resolve().parent / f"{source.resolve().name}_mov"
        # A batch is renumbered; a lone file keeps its name unless asked otherwise.
        sequence = True
    elif source.is_file():
        sources = [source]
        dest = args.dest or source.resolve().parent
        sequence = args.prefix is not None
    else:
        die(f"source does not exist: {args.source}")

    dest = Path(dest).expanduser()
    prefix = args.prefix if args.prefix is not None else "video_"

    # Resolve names up front so a collision is caught before any encoding starts.
    jobs = []
    for i, src in enumerate(sources):
        if sequence:
            name = f"{prefix}{args.start + i:0{args.digits}d}.mov"
        else:
            name = f"{src.stem}.mov"
        jobs.append((src, dest / name))

    # Converting a file in place would have ffmpeg read and write the same path.
    for src, dst in jobs:
        if src.resolve() == dst.resolve():
            die(f"output would overwrite the source file: {src}")

    mode = MODES[args.mode]
    print(f"{len(jobs)} file(s), mode {args.mode} ({mode['label']})")
    print(f"  {source}  ->  {dest}\n")

    if args.dry_run:
        for src, dst in jobs:
            print(f"  {src.name}  ->  {dst.name}")
        return 0

    dest.mkdir(parents=True, exist_ok=True)

    existing = [dst for _, dst in jobs if dst.exists()]
    if existing and not args.overwrite:
        die(f"{len(existing)} output file(s) already exist, e.g. {existing[0].name}. "
            "Use --overwrite to replace them.")

    failures, done = [], []
    for i, (src, dst) in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] {src.name} -> {dst.name}", flush=True)
        result = subprocess.run(build_command(src, dst, args.mode, args, ffmpeg),
                                capture_output=True, text=True)
        if result.returncode != 0 or not dst.exists():
            detail = result.stderr.strip().splitlines()
            print(f"    FAILED: {detail[-1] if detail else 'ffmpeg error'}",
                  file=sys.stderr)
            failures.append(src.name)
            continue

        if not args.no_preserve_dates:
            st = src.stat()
            os.utime(dst, (st.st_atime, st.st_mtime))

        # A truncated encode is worse than a failed one -- it looks like success.
        src_dur, dst_dur = probe_duration(src, ffmpeg), probe_duration(dst, ffmpeg)
        if src_dur and dst_dur and abs(src_dur - dst_dur) > 0.5:
            print(f"    warning: duration mismatch "
                  f"({src_dur:.1f}s -> {dst_dur:.1f}s), output may be truncated",
                  file=sys.stderr)
        done.append((src, dst))

    if args.manifest:
        with open(args.manifest, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["source", "output", "modified"])
            for src, dst in done:
                writer.writerow([src.name, dst.name,
                                 f"{dst.stat().st_mtime:.0f}"])
        print(f"\nmanifest written to {args.manifest}")

    print(f"\ndone: {len(done)} converted, {len(failures)} failed")
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def main():
    """Entry point. Also used by the console script installed via pip/pipx."""
    try:
        return run()
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
