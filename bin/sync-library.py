#!/usr/bin/env python3
import argparse
import os
import subprocess

from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError


EXPLICIT_TAG = "EXPLICIT"
MPAA_TAG = "©rat"
UNKNOWN_VALUE = "Unknown"

MPAA_ORDER = {
    "G": 0,
    "PG": 1,
    "PG-13": 2,
    "R": 3,
    "NC-17": 4,
}


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


def _normalize_mpaa_value(raw):
    if raw is None:
        return UNKNOWN_VALUE
    v = str(raw).strip()
    if not v:
        return UNKNOWN_VALUE
    v_upper = v.upper()
    if v_upper in {"G", "PG", "PG-13", "R", "NC-17"}:
        return v_upper
    if v_upper in {"NR", "NOT RATED"}:
        return "NR"
    if v_upper in {"UNRATED"}:
        return "Unrated"
    return UNKNOWN_VALUE


def _read_mpaa_tag(video_path):
    video = MP4(video_path)
    values = video.get(MPAA_TAG)
    if not values:
        return UNKNOWN_VALUE
    return _normalize_mpaa_value(values[0])


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
    parser.add_argument("--src", required=True, help="Source root")
    parser.add_argument("--dest", required=True, help="Destination (path or rsync remote like user@host:/path)")
    parser.add_argument(
        "--media",
        choices=["music", "movies"],
        default="music",
        help="Media type to sync (default: music)",
    )
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
    parser.add_argument(
        "--max-mpaa",
        default=None,
        help="Exclude movies with MPAA rating above this value (G, PG, PG-13, R, NC-17)",
    )
    parser.add_argument(
        "--exclude-unrated",
        action="store_true",
        help="Exclude movies tagged NR or Unrated",
    )
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to rsync")
    parser.add_argument("--delete", action="store_true", help="(compat) Enable rsync --delete (default: enabled)")
    parser.add_argument("--no-delete", action="store_true", help="Skip cleanup of empty destination directories (default: enabled)")
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
    excluded_mpaa = 0
    excluded_unrated = 0
    errors = 0

    patterns = []

    max_mpaa = None
    if args.max_mpaa:
        max_mpaa = _normalize_mpaa_value(args.max_mpaa)
        if max_mpaa not in MPAA_ORDER:
            raise SystemExit(f"Invalid --max-mpaa: {args.max_mpaa}")

    for root, _dirs, files in os.walk(src):
        for name in files:
            if args.media == "music":
                if not name.lower().endswith((".flac", ".mp3")):
                    continue
            else:
                if not name.lower().endswith((".mp4",)):
                    continue

            fullpath = os.path.join(root, name)
            total_flacs += 1

            if args.max_flacs and total_flacs > args.max_flacs:
                break

            exclude = False
            if args.media == "music":
                try:
                    tag = _read_explicit_tag(fullpath)
                except Exception:
                    errors += 1
                    tag = UNKNOWN_VALUE

                if tag == "Yes" and args.exclude_explicit:
                    exclude = True
                    excluded_yes += 1
                elif tag == UNKNOWN_VALUE and args.exclude_unknown:
                    exclude = True
                    excluded_unknown += 1
            else:
                try:
                    rating = _read_mpaa_tag(fullpath)
                except Exception:
                    errors += 1
                    rating = UNKNOWN_VALUE

                if rating in {"NR", "Unrated"} and args.exclude_unrated:
                    exclude = True
                    excluded_unrated += 1
                elif rating == UNKNOWN_VALUE and args.exclude_unknown:
                    exclude = True
                    excluded_unknown += 1
                elif max_mpaa and rating in MPAA_ORDER and MPAA_ORDER[rating] > MPAA_ORDER[max_mpaa]:
                    exclude = True
                    excluded_mpaa += 1

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
    if not args.no_delete:
        cmd.append("--delete")
    if args.ssh:
        cmd.extend(["-e", args.ssh])

    src_arg = src.rstrip(os.sep) + os.sep
    dest_arg = args.dest
    if ":" not in dest_arg:
        dest_arg = os.path.abspath(dest_arg)
        dest_arg = dest_arg.rstrip(os.sep) + os.sep

    cmd.extend([src_arg, dest_arg])

    if args.media == "music":
        print(f"Scanned files: {total_flacs}")
        print(f"Excluded EXPLICIT=Yes: {excluded_yes} (exclude-explicit={args.exclude_explicit})")
        print(f"Excluded EXPLICIT=Unknown/missing: {excluded_unknown} (exclude-unknown={args.exclude_unknown})")
        print(f"Tag read errors treated as Unknown: {errors}")
    else:
        print(f"Scanned files: {total_flacs}")
        print(f"Excluded MPAA above {max_mpaa}: {excluded_mpaa} (max-mpaa={args.max_mpaa})")
        print(f"Excluded NR/Unrated: {excluded_unrated} (exclude-unrated={args.exclude_unrated})")
        print(f"Excluded Unknown/missing rating: {excluded_unknown} (exclude-unknown={args.exclude_unknown})")
        print(f"Tag read errors treated as Unknown: {errors}")
    print(f"Exclude file: {exclude_file} ({len(patterns)} lines)")

    if args.print_command:
        print("Command:")
        print(" ".join(cmd))
        return 0

    result = subprocess.call(cmd)
    
    # Post-process playlists on destination (only if not remote and not dry-run)
    if result == 0 and not args.dry_run and ":" not in args.dest:
        _fix_destination_playlists(args.dest, patterns)
    
    return result


def _fix_destination_playlists(dest_root, exclude_patterns):
    """Fix .m3u8 playlists on destination to replace missing tracks with (skipped) placeholders"""
    import re
    
    print("Fixing playlists on destination...")
    fixed_count = 0
    
    # Convert exclude patterns to a set of relative paths for quick lookup
    excluded_files = set()
    for pattern in exclude_patterns:
        if pattern.startswith("/") and not pattern.startswith("**"):
            # Convert rsync pattern to relative path
            rel_path = pattern[1:]  # Remove leading /
            excluded_files.add(rel_path)
    
    for root, dirs, files in os.walk(dest_root):
        for name in files:
            if not name.lower().endswith(".m3u8"):
                continue
            
            playlist_path = os.path.join(root, name)
            try:
                with open(playlist_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                new_lines = []
                track_num = 0
                changed = False
                
                for line in lines:
                    line = line.rstrip("\n")
                    
                    # Skip header and empty lines
                    if line.startswith("#EXTM3U") or not line.strip():
                        new_lines.append(line)
                        continue
                    
                    # Skip comment lines (already processed)
                    if line.startswith("#"):
                        new_lines.append(line)
                        continue
                    
                    track_num += 1
                    rel_path = os.path.relpath(os.path.join(root, line), dest_root).replace(os.sep, "/")
                    
                    # Check if file exists or was excluded
                    full_path = os.path.join(root, line)
                    if not os.path.exists(full_path) or rel_path in excluded_files:
                        # Replace with placeholder
                        new_lines.append(f"# Track {track_num} (skipped)")
                        changed = True
                    else:
                        new_lines.append(line)
                
                if changed:
                    with open(playlist_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write("\n".join(new_lines) + "\n")
                    fixed_count += 1
                    print(f"  Fixed: {os.path.relpath(playlist_path, dest_root)}")
            
            except Exception as e:
                print(f"  Error fixing {playlist_path}: {e}")
    
    if fixed_count > 0:
        print(f"Fixed {fixed_count} playlist files")
    else:
        print("No playlist fixes needed")


if __name__ == "__main__":
    raise SystemExit(main())
