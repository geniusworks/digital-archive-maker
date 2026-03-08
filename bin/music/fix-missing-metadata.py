#!/usr/bin/env python3
"""
Fix missing metadata in music files using MusicBrainz.

This script identifies files with missing or incomplete metadata and uses
MusicBrainz to populate authoritative data. Falls back to directory structure
when MusicBrainz data is unavailable.

Usage:
    python3 fix-missing-metadata.py --scan /path/to/music/library
    python3 fix-missing-metadata.py --fix /path/to/music/library
    python3 fix-missing-metadata.py --scan /path/to/music/library --dry-run
    python3 fix-missing-metadata.py --scan /path/to/music/library --no-musicbrainz
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Support multiple audio formats
try:
    import musicbrainzngs
    import requests
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3NoHeaderError
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4

    SUPPORTED_FORMATS = True
except ImportError as e:
    print(f"Error: Missing dependencies - {e}")
    print("Install with: pip install mutagen musicbrainzngs requests")
    sys.exit(1)

# MusicBrainz configuration
USER_AGENT = ("MetadataFixer", "1.0", "youremail@example.com")
RATE_LIMIT = 1.0  # seconds between MusicBrainz API requests
musicbrainzngs.set_useragent(*USER_AGENT)


def has_track_number_prefix(title: str) -> bool:
    """Check if title starts with a track number pattern (not just any number)."""
    if not title:
        return False  # We'll handle missing titles separately

    # More restrictive patterns that specifically indicate track numbers
    # These patterns require separators that clearly indicate track numbering
    patterns = [
        r"^\d{1,2}\s*[-._]\s*",  # "01 - Title", "1. Title", "01_Title" (requires dash/dot/underscore)
        r"^\d{2}\s*[-._]\s*",  # "12 - Title" (exactly 2 digits + separator)
        r"^\d{1,2}\s*-\s*",  # "01 - Title" (dash separator only)
    ]

    return any(re.match(pattern, title.strip()) for pattern in patterns)


def needs_title_from_filename(title: str) -> bool:
    """Check if file needs title extracted from filename (missing or empty title)."""
    return not title or not title.strip()


def extract_metadata_from_path(file_path: Path) -> Dict[str, str]:
    """Extract artist and album from directory structure."""
    metadata = {}

    # Parent folder = album name
    if file_path.parent.name:
        metadata["album"] = file_path.parent.name

    # Grandparent folder = artist name
    if file_path.parent.parent.name:
        metadata["artist"] = file_path.parent.parent.name

    return metadata


def mb_call(func, *args, **kwargs):
    """Wrapper for MusicBrainz API calls with rate limiting."""
    try:
        result = func(*args, **kwargs)
        time.sleep(RATE_LIMIT)
        return result
    except Exception as e:
        print(f"MusicBrainz API error: {e}")
        return None


def fetch_musicbrainz_metadata(artist: str, album: str, title: str) -> Dict:
    """Fetch metadata from MusicBrainz using artist, album, and title."""
    metadata = {}

    # Try to find the release first
    result = mb_call(musicbrainzngs.search_releases, artist=artist, release=album, limit=1)

    if not result:
        # Fallback: search by artist and title
        result = mb_call(
            musicbrainzngs.search_recordings,
            artist=artist,
            query=title,
            limit=1,
        )

    release_list = result.get("release-list", []) if result else []
    if not release_list:
        return metadata

    release_id = release_list[0].get("id")
    if not release_id:
        return metadata

    # Get detailed release info
    release_result = mb_call(
        musicbrainzngs.get_release_by_id,
        release_id,
        includes=["recordings", "artist-credits"],
    )

    if not release_result:
        return metadata

    release = release_result.get("release", {})

    # Extract basic metadata
    metadata["album"] = release.get("title", album)
    metadata["artist"] = release.get("artist-credit-phrase", artist)

    # Extract track information
    tracks = []
    for medium in release.get("medium-list", []):
        for track in medium.get("track-list", []):
            track_info = {
                "number": track.get("number", ""),
                "title": track.get("recording", {}).get("title", track.get("title", "")),
                "duration": track.get("recording", {}).get("length", 0),
            }
            tracks.append(track_info)

    metadata["tracks"] = tracks

    # Try to find the specific track by title
    for track in tracks:
        if title.lower() in track["title"].lower() or track["title"].lower() in title.lower():
            metadata["track_number"] = track["number"]
            metadata["title"] = track["title"]
            break

    return metadata


def load_cache(cache_file: Path) -> Dict:
    """Load MusicBrainz cache."""
    try:
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cache(cache: Dict, cache_file: Path):
    """Save MusicBrainz cache."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")


def extract_title_from_filename(filename: str) -> str:
    """Extract clean title from filename by removing track number and extension."""
    # Remove extension
    name = Path(filename).stem

    # Remove track number patterns
    cleaned = re.sub(r"^\d+\s*[-.\s]+", "", name.strip())
    cleaned = re.sub(r"^\d+\s+", "", cleaned)
    cleaned = re.sub(r"^\d+\s*[-_.]+", "", cleaned)

    return cleaned.strip()


def remove_track_number_prefix(title: str) -> str:
    """Remove track number from the beginning of title."""
    if not title:
        return title

    # Remove track number patterns
    cleaned = re.sub(r"^\d+\s*[-.\s]+", "", title.strip())
    cleaned = re.sub(r"^\d+\s+", "", cleaned)
    cleaned = re.sub(r"^\d+\s*[-_.]+", "", cleaned)

    return cleaned.strip()


def get_audio_metadata(file_path: Path) -> Dict[str, str]:
    """Extract metadata from various audio formats."""
    metadata = {}

    try:
        if file_path.suffix.lower() == ".flac":
            audio = FLAC(file_path)
            metadata["title"] = audio.get("TITLE", [""])[0]
            metadata["artist"] = audio.get("ARTIST", [""])[0]
            metadata["album"] = audio.get("ALBUM", [""])[0]
            metadata["tracknumber"] = audio.get("TRACKNUMBER", [""])[0]

        elif file_path.suffix.lower() == ".mp3":
            audio = MP3(file_path)
            metadata["title"] = str(audio.get("TIT2", [""])[0]) if "TIT2" in audio else ""
            metadata["artist"] = str(audio.get("TPE1", [""])[0]) if "TPE1" in audio else ""
            metadata["album"] = str(audio.get("TALB", [""])[0]) if "TALB" in audio else ""
            metadata["tracknumber"] = str(audio.get("TRCK", [""])[0]) if "TRCK" in audio else ""

        elif file_path.suffix.lower() in {".mp4", ".m4a"}:
            audio = MP4(file_path)
            metadata["title"] = audio.get("\xa9nam", [""])[0]
            metadata["artist"] = audio.get("\xa9ART", [""])[0]
            metadata["album"] = audio.get("\xa9alb", [""])[0]
            metadata["tracknumber"] = audio.get("trkn", [""])[0] if "trkn" in audio else ""
            # MP4 track numbers are often "track/total", extract just track
            if metadata["tracknumber"]:
                metadata["tracknumber"] = str(metadata["tracknumber"]).split("/")[0]

        return metadata

    except Exception as e:
        print(f"Error reading {file_path.name}: {e}")
        return {}


def update_audio_metadata(
    file_path: Path,
    new_title: str,
    artist: str = None,
    album: str = None,
    track_number: str = None,
) -> bool:
    """Update title, artist, album, and track number metadata for various audio formats."""
    try:
        if file_path.suffix.lower() == ".flac":
            audio = FLAC(file_path)
            audio["TITLE"] = [new_title]
            if artist:
                audio["ARTIST"] = [artist]
            if album:
                audio["ALBUM"] = [album]
            if track_number:
                audio["TRACKNUMBER"] = [track_number]
            audio.save()

        elif file_path.suffix.lower() == ".mp3":
            audio = MP3(file_path)
            if "TIT2" in audio:
                audio["TIT2"].text = new_title
            else:
                from mutagen.id3 import TIT2

                audio["TIT2"] = TIT2(encoding=3, text=new_title)

            if artist:
                if "TPE1" in audio:
                    audio["TPE1"].text = artist
                else:
                    from mutagen.id3 import TPE1

                    audio["TPE1"] = TPE1(encoding=3, text=artist)

            if album:
                if "TALB" in audio:
                    audio["TALB"].text = album
                else:
                    from mutagen.id3 import TALB

                    audio["TALB"] = TALB(encoding=3, text=album)

            if track_number:
                if "TRCK" in audio:
                    audio["TRCK"].text = track_number
                else:
                    from mutagen.id3 import TRCK

                    audio["TRCK"] = TRCK(encoding=3, text=track_number)

            audio.save()

        elif file_path.suffix.lower() in {".mp4", ".m4a"}:
            audio = MP4(file_path)
            audio["\xa9nam"] = [new_title]
            if artist:
                audio["\xa9ART"] = [artist]
            if album:
                audio["\xa9alb"] = [album]
            if track_number:
                audio["trkn"] = [(int(track_number), 0)]  # (track, total)
            audio.save()

        return True

    except Exception as e:
        print(f"Error updating {file_path.name}: {e}")
        return False


def scan_directory(
    directory: Path, recursive: bool = True
) -> List[Tuple[Path, Dict[str, str], str]]:
    """Scan directory for audio files and return those with missing metadata.

    Returns list of (file_path, metadata, issue_type) tuples where issue_type is:
    - 'missing_title': Title is missing/empty
    - 'missing_artist': Artist is missing/empty
    - 'missing_album': Album is missing/empty
    """
    files_with_issues = []

    pattern = "**/*" if recursive else "*"
    audio_extensions = {".flac", ".mp3", ".mp4", ".m4a"}

    for file_path in directory.glob(pattern):
        if not file_path.is_file() or file_path.suffix.lower() not in audio_extensions:
            continue

        metadata = get_audio_metadata(file_path)
        if not metadata:
            continue

        title = metadata.get("title", "")
        artist = metadata.get("artist", "")
        album = metadata.get("album", "")

        # Focus only on missing metadata
        if needs_title_from_filename(title):
            files_with_issues.append((file_path, metadata, "missing_title"))
        elif not artist or not artist.strip():
            files_with_issues.append((file_path, metadata, "missing_artist"))
        elif not album or not album.strip():
            files_with_issues.append((file_path, metadata, "missing_album"))

    return files_with_issues


def main():
    parser = argparse.ArgumentParser(
        description="Fix missing metadata in music files using MusicBrainz"
    )
    parser.add_argument("directory", help="Directory to scan/fix")
    parser.add_argument("--scan", action="store_true", help="Only scan, don't fix (default)")
    parser.add_argument("--fix", action="store_true", help="Fix detected issues")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Scan recursively (default)",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Don't scan recursively",
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument(
        "--no-musicbrainz",
        action="store_true",
        help="Disable MusicBrainz lookup (use directory structure only)",
    )
    parser.add_argument(
        "--cache-dir",
        help="Cache directory for MusicBrainz data",
        default="log",
    )

    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    # Default to scan mode unless --fix is specified
    scan_mode = not args.fix

    if args.dry_run:
        scan_mode = True  # Dry run implies scan mode

    # Initialize cache (always enabled)
    use_musicbrainz = not args.no_musicbrainz
    cache = {}
    cache_file = Path(args.cache_dir) / "metadata_fix_cache.json"
    cache = load_cache(cache_file)

    if use_musicbrainz:
        print(f"🌐 MusicBrainz integration enabled")
    else:
        print(f"📁 Using directory structure only (MusicBrainz disabled)")
    print(f"📁 Cache: {cache_file}")

    print(f"Scanning: {directory}")
    print(f"Recursive: {args.recursive}")
    print(f"Mode: {'DRY RUN' if args.dry_run else ('SCAN' if scan_mode else 'FIX')}")
    print()

    # Find files with missing metadata
    problematic_files = scan_directory(directory, args.recursive)

    if not problematic_files:
        print("✅ No files found with missing metadata")
        return

    print(f"Found {len(problematic_files)} files with missing metadata:")
    print()

    for file_path, metadata, issue_type in problematic_files:
        current_title = metadata.get("title", "")
        current_artist = metadata.get("artist", "")
        current_album = metadata.get("album", "")

        # Get metadata from directory structure
        path_metadata = extract_metadata_from_path(file_path)

        # Get MusicBrainz metadata if enabled
        mb_metadata = {}
        if use_musicbrainz:
            artist = current_artist or path_metadata.get("artist", "")
            album = current_album or path_metadata.get("album", "")
            title = current_title or extract_title_from_filename(file_path.name)

            if artist and album and title:
                cache_key = f"{artist}|{album}|{title}"
                if cache_key in cache:
                    mb_metadata = cache[cache_key]
                else:
                    mb_metadata = fetch_musicbrainz_metadata(artist, album, title)
                    if mb_metadata:
                        cache[cache_key] = mb_metadata
                        save_cache(cache, cache_file)

        if issue_type == "missing_title":
            cleaned_title = extract_title_from_filename(file_path.name)
            issue_desc = "Missing title"
        elif issue_type == "missing_artist":
            cleaned_title = current_title or extract_title_from_filename(file_path.name)
            issue_desc = "Missing artist"
        elif issue_type == "missing_album":
            cleaned_title = current_title or extract_title_from_filename(file_path.name)
            issue_desc = "Missing album"
        else:
            continue

        # Use MusicBrainz data if available, otherwise fallback to path data
        final_artist = mb_metadata.get("artist", path_metadata.get("artist", current_artist))
        final_album = mb_metadata.get("album", path_metadata.get("album", current_album))
        final_title = mb_metadata.get("title", cleaned_title)
        track_number = mb_metadata.get("track_number", metadata.get("tracknumber", ""))

        print(f"📁 {file_path.relative_to(directory)} [{issue_desc}]")
        print(f"   Artist: {repr(current_artist)} → {repr(final_artist)}")
        print(f"   Album:  {repr(current_album)} → {repr(final_album)}")
        print(f"   Track:  {repr(track_number)}")
        print(f"   Title:  {repr(current_title)} → {repr(final_title)}")

        if mb_metadata:
            print(f"   🌐 MusicBrainz data available")
        print()

    if scan_mode or args.dry_run:
        if args.dry_run:
            print("🔍 DRY RUN - No changes made")
        else:
            print("🔍 SCAN ONLY - Use --fix to apply changes")
        return

    # Fix mode
    print("🔧 Fixing files...")
    fixed_count = 0
    failed_count = 0

    for file_path, metadata, issue_type in problematic_files:
        current_title = metadata.get("title", "")
        current_artist = metadata.get("artist", "")
        current_album = metadata.get("album", "")

        # Get metadata from directory structure
        path_metadata = extract_metadata_from_path(file_path)

        # Get MusicBrainz metadata if enabled
        mb_metadata = {}
        if use_musicbrainz:
            artist = current_artist or path_metadata.get("artist", "")
            album = current_album or path_metadata.get("album", "")
            title = current_title or extract_title_from_filename(file_path.name)

            if artist and album and title:
                cache_key = f"{artist}|{album}|{title}"
                if cache_key in cache:
                    mb_metadata = cache[cache_key]
                else:
                    mb_metadata = fetch_musicbrainz_metadata(artist, album, title)
                    if mb_metadata:
                        cache[cache_key] = mb_metadata
                        save_cache(cache, cache_file)

        if issue_type == "missing_title":
            cleaned_title = extract_title_from_filename(file_path.name)
        elif issue_type == "missing_artist":
            cleaned_title = current_title or extract_title_from_filename(file_path.name)
        elif issue_type == "missing_album":
            cleaned_title = current_title or extract_title_from_filename(file_path.name)
        else:
            continue

        # Use MusicBrainz data if available, otherwise fallback to path data
        final_artist = mb_metadata.get("artist", path_metadata.get("artist", current_artist))
        final_album = mb_metadata.get("album", path_metadata.get("album", current_album))
        final_title = mb_metadata.get("title", cleaned_title)
        final_track_number = mb_metadata.get("track_number", metadata.get("tracknumber", ""))

        # Check if anything needs to be updated
        needs_update = (
            final_title != current_title
            or final_artist != current_artist
            or final_album != current_album
            or (final_track_number and final_track_number != metadata.get("tracknumber", ""))
        )

        if not needs_update:
            if args.verbose:
                print(f"⏭️  Skipping {file_path.name} (no change needed)")
            continue

        success = update_audio_metadata(
            file_path,
            final_title,
            final_artist,
            final_album,
            final_track_number,
        )
        if success:
            fixed_count += 1
            status = "✅"
        else:
            failed_count += 1
            status = "❌"

        if args.verbose or not success:
            print(f"{status} {file_path.relative_to(directory)}")
            changes = []
            if final_title != current_title:
                changes.append(f"Title: {repr(current_title)} → {repr(final_title)}")
            if final_artist != current_artist:
                changes.append(f"Artist: {repr(current_artist)} → {repr(final_artist)}")
            if final_album != current_album:
                changes.append(f"Album: {repr(current_album)} → {repr(final_album)}")
            if final_track_number and final_track_number != metadata.get("tracknumber", ""):
                changes.append(
                    f"Track: {repr(metadata.get('tracknumber', ''))} → {repr(final_track_number)}"
                )
            print(f"   {', '.join(changes)}")

    print()
    print(f"Summary:")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(problematic_files)}")


if __name__ == "__main__":
    main()
