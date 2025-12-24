#!/usr/bin/env python3
import argparse
import csv
import os
import subprocess
import shutil
import fnmatch
import re

from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError


EXPLICIT_TAG = "EXPLICIT"
MPAA_TAG = "©rat"
UNKNOWN_VALUE = "Unknown"


def _normalize_text(value):
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\u2019", "'")
    s = s.replace("\u2018", "'")
    s = s.replace("\u201c", '"')
    s = s.replace("\u201d", '"')
    s = " ".join(s.strip().lower().split())
    return s


def _override_field_matches(rule_val, actual_val):
    if rule_val == "*":
        return True
    if any(ch in rule_val for ch in ["*", "?", "["]):
        return fnmatch.fnmatchcase(actual_val, rule_val)
    return rule_val == actual_val


def _load_explicit_overrides(repo_root):
    overrides_file = os.path.join(repo_root, "log", "explicit_overrides.csv")
    overrides = []
    if not os.path.exists(overrides_file):
        return overrides

    try:
        with open(overrides_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            order = 0
            for row in reader:
                if not row:
                    continue
                if row[0].strip().startswith("#"):
                    continue
                if row[0].strip().lower() in {"artist", "#artist"}:
                    continue
                if len(row) < 4:
                    continue

                artist, album, title, explicit_val = (x.strip() for x in row[:4])
                if not artist or not album or not title or not explicit_val:
                    continue

                val = explicit_val.strip().lower()
                if val in {"yes", "y", "true", "1", "explicit"}:
                    val_out = "Yes"
                elif val in {"no", "n", "false", "0", "clean", "notexplicit"}:
                    val_out = "No"
                else:
                    val_out = UNKNOWN_VALUE

                overrides.append(
                    {
                        "artist": artist if artist == "*" else _normalize_text(artist),
                        "album": album if album == "*" else _normalize_text(album),
                        "title": title if title == "*" else _normalize_text(title),
                        "value": val_out,
                        "order": order,
                    }
                )
                order += 1
    except Exception:
        return []

    return overrides


def _resolve_override(overrides, artist_norm, album_norm, title_norm):
    best = None
    best_score = (-1, -1)
    for rule in overrides or []:
        ra = rule.get("artist")
        rb = rule.get("album")
        rt = rule.get("title")

        if not _override_field_matches(ra, artist_norm):
            continue
        if not _override_field_matches(rb, album_norm):
            continue
        if not _override_field_matches(rt, title_norm):
            continue

        spec = 0
        if ra != "*":
            spec += 1
        if rb != "*":
            spec += 1
        if rt != "*":
            spec += 1

        score = (spec, int(rule.get("order") or 0))
        if score > best_score:
            best_score = score
            best = rule

    if best is None:
        return None
    return best.get("value")


def _infer_music_identity_from_path(audio_path, src_root):
    try:
        rel = os.path.relpath(audio_path, src_root).replace(os.sep, "/")
    except Exception:
        rel = os.path.basename(audio_path)

    parts = [p for p in rel.split("/") if p and p != "."]
    artist = parts[0] if len(parts) >= 3 else ""
    album = parts[1] if len(parts) >= 3 else ""
    filename = parts[-1] if parts else os.path.basename(audio_path)
    title = filename.rsplit(".", 1)[0]
    m = re.match(r"^\s*\d+\s*-\s*(.*)$", title)
    if m:
        title = m.group(1)
    return _normalize_text(artist), _normalize_text(album), _normalize_text(title)


def _read_music_identity(audio_path, src_root=None):
    artist = ""
    album = ""
    title = ""

    if audio_path.lower().endswith(".flac"):
        try:
            audio = FLAC(audio_path)
            artist = (audio.get("artist") or [""])[0]
            album = (audio.get("album") or [""])[0]
            title = (audio.get("title") or [""])[0]
        except Exception:
            artist = ""
            album = ""
            title = ""
    else:
        try:
            audio = MP3(audio_path)
            if audio.tags:
                a = audio.tags.get("TPE1")
                b = audio.tags.get("TALB")
                t = audio.tags.get("TIT2")
                if a is not None and getattr(a, "text", None):
                    artist = a.text[0]
                if b is not None and getattr(b, "text", None):
                    album = b.text[0]
                if t is not None and getattr(t, "text", None):
                    title = t.text[0]
        except ID3NoHeaderError:
            artist = ""
            album = ""
            title = ""
        except Exception:
            artist = ""
            album = ""
            title = ""

    if not title:
        title = os.path.basename(audio_path).rsplit(".", 1)[0]

    artist_norm = _normalize_text(artist)
    album_norm = _normalize_text(album)
    title_norm = _normalize_text(title)

    if src_root and (not artist_norm or not album_norm):
        p_artist, p_album, p_title = _infer_music_identity_from_path(audio_path, src_root)
        if not artist_norm:
            artist_norm = p_artist
        if not album_norm:
            album_norm = p_album
        if not title_norm:
            title_norm = p_title

    return artist_norm, album_norm, title_norm

MPAA_ORDER = {
    "G": 0,
    "PG": 1,
    "PG-13": 2,
    "R": 3,
    "NC-17": 4,
}


def _rsync_supports_info_progress2():
    rsync_bin = _resolve_rsync_bin()
    try:
        p = subprocess.run(
            [rsync_bin, "--help"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return False

    out = (p.stdout or "") + "\n" + (p.stderr or "")
    return "--info" in out and "progress2" in out


def _resolve_rsync_bin():
    override = os.environ.get("RSYNC_BIN")
    if override:
        return override

    for candidate in ("/opt/homebrew/bin/rsync", "/usr/local/bin/rsync"):
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return shutil.which("rsync") or "rsync"


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


def _is_under_excluded_dir(rel_path, excluded_dirs):
    if not excluded_dirs:
        return False
    parts = rel_path.split("/")
    if len(parts) <= 1:
        return False
    prefix = ""
    for part in parts[:-1]:
        if prefix:
            prefix = prefix + part + "/"
        else:
            prefix = part + "/"
        if prefix in excluded_dirs:
            return True
    return False


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
    parser.add_argument("--scan-only", action="store_true", help="Scan and write exclude/keep files, but do not run rsync")
    parser.add_argument("--keep-file", default=None, help="Write included (kept) relative file paths to this file")

    args = parser.parse_args()

    src = os.path.abspath(args.src)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_exclude_file = os.path.join(repo_root, "log", "sync_exclude.txt")
    exclude_file = args.exclude_file or default_exclude_file

    overrides = []
    if args.media == "music" and args.exclude_explicit:
        overrides = _load_explicit_overrides(repo_root)

    total_flacs = 0
    excluded_yes = 0
    excluded_unknown = 0
    excluded_mpaa = 0
    excluded_unrated = 0
    errors = 0
    override_yes_excluded = 0
    override_no_included = 0

    patterns = []
    excluded_files = set()
    excluded_dirs = set()
    
    # Track directories that have included files
    dirs_with_included_files = set()

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

                override_val = None
                if overrides:
                    artist_norm, album_norm, title_norm = _read_music_identity(fullpath, src)
                    override_val = _resolve_override(overrides, artist_norm, album_norm, title_norm)

                effective = override_val if override_val is not None else tag

                if override_val == "Yes":
                    override_yes_excluded += 1
                elif override_val == "No":
                    override_no_included += 1

                if effective == "Yes" and args.exclude_explicit:
                    exclude = True
                    excluded_yes += 1
                elif effective == UNKNOWN_VALUE and args.exclude_unknown:
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

            rel = os.path.relpath(fullpath, src).replace(os.sep, "/")
            if exclude:
                patterns.append("/" + _escape_rsync_pattern(rel))
                excluded_files.add(rel)
            else:
                dirs_with_included_files.add(root)

        if args.max_flacs and total_flacs >= args.max_flacs:
            break

    # Add exclude patterns for empty directories
    all_dirs = set()
    dirs_with_files = set()
    
    # First pass: collect all directories and those with files
    for root, dirs, files in os.walk(src):
        all_dirs.add(root)
        for file in files:
            if args.media == "music":
                if file.lower().endswith((".flac", ".mp3")):
                    dirs_with_files.add(root)
            else:
                if file.lower().endswith((".mp4",)):
                    dirs_with_files.add(root)
    
    # Exclude empty directories (those without any media files)
    empty_dirs = all_dirs - dirs_with_files
    for empty_dir in sorted(empty_dirs, reverse=True):  # Process deepest first
        rel = os.path.relpath(empty_dir, src).replace(os.sep, "/")
        if rel != ".":  # Don't exclude the root source directory
            patterns.append("/" + _escape_rsync_pattern(rel) + "/")
            excluded_dirs.add(rel + "/")

    _write_exclude_file(exclude_file, patterns)

    if args.keep_file:
        kept_files = set()
        for root, _dirs, files in os.walk(src):
            for name in files:
                fullpath = os.path.join(root, name)
                rel = os.path.relpath(fullpath, src).replace(os.sep, "/")
                if rel in excluded_files:
                    continue
                if _is_under_excluded_dir(rel, excluded_dirs):
                    continue
                kept_files.add(rel)

        os.makedirs(os.path.dirname(os.path.abspath(args.keep_file)), exist_ok=True)
        with open(args.keep_file, "w", encoding="utf-8", newline="\n") as f:
            for p in sorted(kept_files):
                f.write(p)
                f.write("\n")

    rsync_bin = _resolve_rsync_bin()
    cmd = [
        rsync_bin,
        "-a",
        "--human-readable",
        "--stats",
        "--progress",
        "--exclude-from",
        exclude_file,
    ]

    if _rsync_supports_info_progress2():
        cmd.append("--info=progress2")
    if args.dry_run:
        cmd.append("--dry-run")
    
    # Build source-aware delete patterns if delete is enabled
    delete_patterns = []
    if not args.no_delete and ":" in args.dest:  # Remote sync with delete
        # Create include patterns for all directories in source
        source_dirs = set()
        for root, dirs, files in os.walk(src):
            rel_dir = os.path.relpath(root, src).replace(os.sep, "/")
            if rel_dir != ".":
                source_dirs.add(rel_dir)
        
        # Add include patterns for source directories
        for source_dir in sorted(source_dirs):
            delete_patterns.append(f"+ /{source_dir}/")
        
        # Include all files in source directories
        delete_patterns.append("+ */")
        delete_patterns.append("+ *")
        
        # Exclude everything else (other library folders)
        delete_patterns.append("- *")
        
        # Write delete patterns to a separate file
        delete_exclude_file = exclude_file.replace('.txt', '_delete.txt')
        _write_exclude_file(delete_exclude_file, delete_patterns)
        
        # Use --delete --exclude-from=delete_patterns_file
        cmd.extend(["--delete", "--exclude-from", delete_exclude_file])
    elif not args.no_delete:
        # Local sync or no remote - use regular delete
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
        if args.exclude_explicit:
            print(f"Overrides matched Yes: {override_yes_excluded}")
            print(f"Overrides matched No: {override_no_included}")
        print(f"Tag read errors treated as Unknown: {errors}")
    else:
        print(f"Scanned files: {total_flacs}")
        print(f"Excluded MPAA above {max_mpaa}: {excluded_mpaa} (max-mpaa={args.max_mpaa})")
        print(f"Excluded NR/Unrated: {excluded_unrated} (exclude-unrated={args.exclude_unrated})")
        print(f"Excluded Unknown/missing rating: {excluded_unknown} (exclude-unknown={args.exclude_unknown})")
        print(f"Tag read errors treated as Unknown: {errors}")
    print(f"Exclude file: {exclude_file} ({len(patterns)} lines)")

    # Try direct subprocess call without shell - let Python handle argument escaping
    if args.print_command:
        print("Command:")
        print(" ".join(f'"{arg}"' for arg in cmd))
        return 0

    if args.scan_only:
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
