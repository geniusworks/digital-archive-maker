#!/usr/bin/env python3
import argparse
import os
import subprocess

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError


EXPLICIT_TAG = "EXPLICIT"
UNKNOWN_VALUE = "Unknown"


def _normalize_explicit_value(raw):
    if raw is None:
        return UNKNOWN_VALUE
    v = str(raw).strip().lower()
    if v in {"yes", "y", "true", "1", "explicit"}:
        return "Yes"
    if v in {"no", "n", "false", "0", "clean", "notexplicit"}:
        return "No"
    if v in {"unknown", "", "none", "null"}:
        return UNKNOWN_VALUE
    return UNKNOWN_VALUE


def _read_explicit_tag(audio_path):
    # Load audio file based on extension
    if audio_path.lower().endswith(".flac"):
        audio = FLAC(audio_path)
    else:  # MP3
        try:
            audio = MP3(audio_path)
        except ID3NoHeaderError:
            return UNKNOWN_VALUE
    
    # Try different tag names for different formats
    if audio_path.lower().endswith(".flac"):
        values = audio.get(EXPLICIT_TAG) or audio.get(EXPLICIT_TAG.lower())
    else:  # MP3 - use ID3 tag names
        values = audio.get("TXXX:" + EXPLICIT_TAG) or audio.get("EXPLICIT")
    
    if not values:
        return UNKNOWN_VALUE
    return _normalize_explicit_value(values[0])


def _escape_rsync_pattern(path):
    out = []
    for ch in path:
        if ch in "\\[]*?":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _write_exclude_file(exclude_file, patterns):
    os.makedirs(os.path.dirname(exclude_file), exist_ok=True)
    with open(exclude_file, "w", encoding="utf-8", newline="\n") as f:
        for p in patterns:
            f.write(p)
            f.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Source music root (the folder that contains Artist/Album/...)")
    parser.add_argument("--dest", required=True, help="Destination (path or rsync remote like user@host:/path)")
    parser.add_argument(
        "--exclude-explicit",
        action="store_true",
        help="Exclude tracks tagged EXPLICIT=Yes",
    )
    parser.add_argument(
        "--exclude-unknown",
        action="store_true",
        help="Exclude tracks tagged EXPLICIT=Unknown or missing EXPLICIT tag",
    )
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to rsync")
    parser.add_argument("--delete", action="store_true", help="Pass --delete to rsync")
    parser.add_argument("--ssh", default=None, help="Rsync remote shell, e.g. 'ssh -p 2222'")
    parser.add_argument("--exclude-file", default=None, help="Write rsync excludes to this file")
    parser.add_argument("--max-flacs", type=int, default=0, help="Only scan first N FLACs (debug)")
    parser.add_argument("--print-command", action="store_true", help="Print rsync command and exit")

    args = parser.parse_args()

    src = os.path.abspath(args.src)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_exclude_file = os.path.join(repo_root, "log", "sync_exclude.txt")
    exclude_file = args.exclude_file or default_exclude_file

    total_flacs = 0
    excluded_yes = 0
    excluded_unknown = 0
    errors = 0

    patterns = []

    for root, _dirs, files in os.walk(src):
        for name in files:
            if not name.lower().endswith((".flac", ".mp3")):
                continue

            fullpath = os.path.join(root, name)
            total_flacs += 1

            if args.max_flacs and total_flacs > args.max_flacs:
                break

            try:
                tag = _read_explicit_tag(fullpath)
            except Exception:
                errors += 1
                tag = UNKNOWN_VALUE

            exclude = False
            if tag == "Yes" and args.exclude_explicit:
                exclude = True
                excluded_yes += 1
            elif tag == UNKNOWN_VALUE and args.exclude_unknown:
                exclude = True
                excluded_unknown += 1

            if exclude:
                rel = os.path.relpath(fullpath, src).replace(os.sep, "/")
                patterns.append("/" + _escape_rsync_pattern(rel))

        if args.max_flacs and total_flacs >= args.max_flacs:
            break

    _write_exclude_file(exclude_file, patterns)

    cmd = [
        "rsync",
        "-a",
        "--human-readable",
        "--stats",
        "--progress",
        "--exclude-from",
        exclude_file,
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.delete:
        cmd.append("--delete")
    if args.ssh:
        cmd.extend(["-e", args.ssh])

    src_arg = src.rstrip(os.sep) + os.sep
    dest_arg = args.dest
    if ":" not in dest_arg:
        dest_arg = os.path.abspath(dest_arg)
        dest_arg = dest_arg.rstrip(os.sep) + os.sep

    cmd.extend([src_arg, dest_arg])

    print(f"Scanned FLACs: {total_flacs}")
    print(f"Excluded EXPLICIT=Yes: {excluded_yes} (exclude-explicit={args.exclude_explicit})")
    print(f"Excluded EXPLICIT=Unknown/missing: {excluded_unknown} (exclude-unknown={args.exclude_unknown})")
    print(f"FLAC read errors treated as Unknown: {errors}")
    print(f"Exclude file: {exclude_file} ({len(patterns)} lines)")

    if args.print_command:
        print("Command:")
        print(" ".join(cmd))
        return 0

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
