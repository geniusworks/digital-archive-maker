#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import acoustid
import musicbrainzngs
from mutagen import File

# ===== CONFIG =====
TARGET_DIR = os.getenv("LIBRARY_ROOT", "/Volumes/Data/Media/Library") + "/Music"
ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY", "")
musicbrainzngs.set_useragent("FixTrackScript", "1.0", "testing@example.com")


# ---- UTILS -----
def sanitize(name: str) -> str:
    return "".join(c for c in name if c not in '/\\:*?"<>|').strip()


def clean_filename(name: str) -> str:
    name = re.sub(r"^\d+[-. ]*", "", name)
    name = re.sub(r"[_]+$", "", name)
    return name.strip()


def parse_from_filename(filename: str):
    name, _ = os.path.splitext(os.path.basename(filename))
    m = re.match(r"(?P<artist>.+?) - (?P<title>.+)", name)
    if m:
        return (
            sanitize(m.group("artist")),
            "Unknown Album",
            sanitize(m.group("title")),
        )
    m = re.match(
        r"(?P<artist>.+?) - (?P<album>.+?) - (?P<track>\d+) - (?P<title>.+)",
        name,
    )
    if m:
        return (
            sanitize(m.group("artist")),
            sanitize(m.group("album")),
            sanitize(m.group("title")),
        )
    m = re.match(r"(?P<track>\d+) - (?P<artist>.+?) - (?P<title>.+)", name)
    if m:
        return (
            sanitize(m.group("artist")),
            "Unknown Album",
            sanitize(m.group("title")),
        )
    return "Unknown Artist", "Unknown Album", sanitize(name)


def lookup_metadata(file_path):
    if not ACOUSTID_API_KEY:
        print(
            "Warning: ACOUSTID_API_KEY not set; skipping AcoustID lookup.",
            file=sys.stderr,
        )
        return None
    try:
        results = acoustid.match(ACOUSTID_API_KEY, file_path)
        for score, recording_id, title_guess, artist_guess in results:
            if score > 0.8 and recording_id:
                try:
                    rec = musicbrainzngs.get_recording_by_id(
                        recording_id, includes=["artists", "releases"]
                    )
                    artist_name = rec["recording"]["artist-credit"][0]["artist"]["name"]
                    album_name = (
                        rec["recording"]["release-list"][0]["title"]
                        if rec["recording"]["release-list"]
                        else "Unknown Album"
                    )
                    track_title = rec["recording"]["title"]
                    return artist_name, album_name, track_title, None
                except Exception:
                    continue
    except Exception:
        pass
    return None


# ---- MAIN FUNCTION -----
def fix_track(src_path: str, dest_root: str, skip_metadata=False) -> str:
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")
    print(f"Processing: {src}")

    artist = album = title = None
    track_num = None

    if not skip_metadata:
        audio = File(src)
        if audio and audio.tags:
            try:
                artist = sanitize(str(audio.tags.get("artist", ["Unknown Artist"])[0]))
                album = sanitize(str(audio.tags.get("album", ["Unknown Album"])[0]))
                title = sanitize(str(audio.tags.get("title", [src.stem])[0]))
                track_num = audio.tags.get("tracknumber", [None])[0]
                if isinstance(track_num, str) and "/" in track_num:
                    track_num = track_num.split("/")[0]
                if track_num:
                    track_num = track_num.zfill(2)
                print(f"Metadata found: Artist={artist}, Album={album}, Title={title}")
            except Exception as e:
                print(f"Metadata parsing error: {e}")
                artist = album = title = None

    # AcoustID lookup (even if metadata skipped)
    if not artist or not album or not title or artist == "Unknown Artist":
        result = lookup_metadata(str(src)) if not skip_metadata else None
        if result:
            artist, album, title, track_num = result
            print(f"AcoustID lookup success: Artist={artist}, Album={album}, Title={title}")
        else:
            print("AcoustID lookup failed.")

    # fallback to filename parsing
    if not artist or not album or not title:
        artist, album, title = parse_from_filename(clean_filename(src.stem))
        print(f"Using filename fallback: Artist={artist}, Album={album}, Title={title}")

    artist = sanitize(artist)
    album = sanitize(album)
    title = sanitize(title)
    ext = src.suffix.lower()
    filename = f"{track_num + ' - ' if track_num else ''}{title}{ext}"

    dest_dir = Path(dest_root) / artist / album
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    shutil.copy2(src, dest_path)
    print(f"Copied to: {dest_path}")
    return str(dest_path)


# ---- CLI -----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize a single track")
    parser.add_argument("source_file", help="Path to the audio file")
    parser.add_argument("--target", help="Target root directory", default=TARGET_DIR)
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip reading embedded metadata",
    )
    args = parser.parse_args()

    try:
        dest = fix_track(args.source_file, args.target, skip_metadata=args.no_metadata)
        print(f"Copied to: {dest}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
