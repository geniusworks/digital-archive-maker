#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from pathlib import Path


TRACKS = [
    ("👁 No", "00:00"),
    ("Alphabet St.", "05:46"),
    ("Glam Slam", "11:25"),
    ("Anna Stesia", "16:33"),
    ("Dance On", "21:31"),
    ("Lovesexy", "25:15"),
    ("When 2 R in Love", "31:04"),
    ("I Wish U Heaven", "35:02"),
    ("Positivity", "37:53"),
]


def sanitize_filename(title: str) -> str:
    # Replace forbidden characters only; keep spaces + unicode (including emoji).
    return re.sub(r"[\\/:*?\"<>|]", "_", title)


def require_command(cmd: str) -> None:
    res = subprocess.run(["which", cmd], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Missing required command: {cmd}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Split Lovesexy.flac (one-file album) into track files using fixed timestamps")
    parser.add_argument("input", nargs="?", default="Lovesexy.flac")
    parser.add_argument("--out", default="Lovesexy_Split")
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists() or not inp.is_file():
        print(f"Error: input file '{inp}' not found.", file=sys.stderr)
        return 1

    require_command("ffmpeg")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (title, start) in enumerate(TRACKS):
        tracknum = f"{i + 1:02d}"
        safe_title = sanitize_filename(title)
        outfile = out_dir / f"{tracknum} - {safe_title}.flac"

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            start,
        ]

        if i < len(TRACKS) - 1:
            next_start = TRACKS[i + 1][1]
            cmd += ["-to", next_start]

        cmd += ["-i", str(inp), "-c", "copy", str(outfile)]

        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"Failed to split track {tracknum}: {title}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
