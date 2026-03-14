#!/usr/bin/env python3
"""
Music Video Filename and Metadata Normalizer

This script organizes music video files by:
1. Using the folder name as the artist
2. Extracting song titles from existing metadata or filenames
3. Looking up correct track information using MusicBrainz/AcoustID
4. Renaming files to consistent format: "Artist - Song Title.ext"
5. Updating MP4/M4V metadata with correct artist and song title

Usage:
    python3 bin/video/fix_music_videos.py /path/to/Music/Videos [--dry-run] [--force]
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

VERBOSE = False


def load_dotenv(repo_root: Path) -> None:
    """Load .env file if present."""
    env_path = repo_root / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except ImportError:
        # If python-dotenv not available, try simple parsing
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


def get_library_root() -> Path:
    """Get library root from environment or default."""
    # Try LIBRARY_ROOT from environment
    lib_root = os.getenv("LIBRARY_ROOT")
    if lib_root:
        return Path(lib_root)

    # Fallback to default
    return Path("/Volumes/Data/Media/Library")


try:
    import acoustid
    import musicbrainzngs
    from mutagen.mp4 import MP4, MP4FreeForm

    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    missing = str(e).split("required")[0].strip() if "required" in str(e) else str(e)
    print(f"Error: Missing dependencies - {missing}")
    print("Install with: pip install mutagen acoustid python-musicbrainzngs")
    sys.exit(1)


# Configure MusicBrainz
musicbrainzngs.set_useragent("MusicVideoFixer", "1.0", "https://example.com")

# AcoustID API key from environment
ACOUSTID_API_KEY = ""

# Log file for skipped files
LOG_DIR = Path(__file__).parent.parent.parent / "log"
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SKIPPED_LOG = CONFIG_DIR / "music_videos_skipped.csv"


def log_skipped_file(artist: str, file_path: Path, extracted_title: str, reason: str) -> None:
    """Log a file that was skipped for later review."""
    LOG_DIR.mkdir(exist_ok=True)

    # Write header if file doesn't exist
    file_exists = SKIPPED_LOG.exists()

    # Use absolute path since files may be outside repo
    file_str = str(file_path)
    safe_title = extracted_title or ""

    with open(SKIPPED_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(
                [
                    "timestamp",
                    "artist",
                    "file_path",
                    "extracted_title",
                    "reason",
                ]
            )

        writer.writerow([datetime.now().isoformat(), artist, file_str, safe_title, reason])


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in a filename."""
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Remove leading/trailing spaces
    return sanitized.strip()


def extract_title_from_metadata(file_path: Path) -> Optional[str]:
    """Extract song title from existing file metadata."""
    if file_path.suffix.lower() not in {".mp4", ".m4v"}:
        return None

    try:
        mp4 = MP4(str(file_path))

        # Try various metadata fields
        title = None
        if "©nam" in mp4:
            title = mp4["©nam"][0]
        elif "TITLE" in mp4:
            title = mp4["TITLE"][0]

        # Clean up title (remove artist name if present)
        if title:
            # Remove "Artist - " prefix if present
            title = re.sub(r"^.+?\s*-\s*", "", title)
            # Remove anything in brackets after title (e.g., [Official Video])
            title = re.sub(r"\s*\[.*?\]\s*$", "", title)
            # Remove anything in parentheses after title (e.g., (Official Video))
            title = re.sub(r"\s*\(.*?\)\s*$", "", title)
            title = title.strip()

        return title if title else None

    except Exception as e:
        if VERBOSE:
            print(f"  Metadata read error: {e}")
        return None


def extract_title_from_filename(file_path: Path, artist_name: str) -> Optional[str]:
    """Extract song title from filename."""
    filename = file_path.stem

    # Remove artist name if present at start
    title = re.sub(
        rf"^{re.escape(artist_name)}\s*[-–]\s*",
        "",
        filename,
        flags=re.IGNORECASE,
    )

    # Remove common suffixes
    title = re.sub(r"\s*(?:\(.*?\)|\[.*?\])$", "", title)  # Remove brackets
    title = re.sub(
        r"\s*(?:official\s+video|music\s+video|video|hd|4k|1080p|720p)\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    return title.strip() if title.strip() else filename


def lookup_music_video(file_path: Path, artist: str, title_hint: str) -> Optional[Tuple[str, str]]:
    """Lookup music video info using MusicBrainz search first, then AcoustID."""

    # Try MusicBrainz search first (more reliable for music videos)
    try:
        result = musicbrainzngs.search_recordings(recording=title_hint, artist=artist, limit=10)
        for rec in result.get("recording-list", []):
            if rec.get("artist-credit"):
                rec_artist = rec["artist-credit"][0]["artist"]["name"]
                # More permissive artist matching
                if (
                    rec_artist.lower() == artist.lower()
                    or artist.lower() in rec_artist.lower()
                    or rec_artist.lower() in artist.lower()
                ):
                    return rec_artist, rec["title"]
    except Exception as e:
        if VERBOSE:
            print(f"  MusicBrainz search failed: {e}")

    # Try AcoustID if available (less reliable for video)
    if ACOUSTID_API_KEY:
        try:
            results = acoustid.match(ACOUSTID_API_KEY, str(file_path))
            for score, recording_id, title_guess, artist_guess in results:
                if score > 0.5 and recording_id:  # Lower threshold for video
                    # More permissive artist matching
                    if (
                        artist_guess.lower() == artist.lower()
                        or artist.lower() in artist_guess.lower()
                        or artist_guess.lower() in artist.lower()
                    ):
                        try:
                            rec = musicbrainzngs.get_recording_by_id(
                                recording_id, includes=["artists"]
                            )
                            mb_title = rec["recording"]["title"]
                            mb_artist = rec["recording"]["artist-credit"][0]["artist"]["name"]
                            return mb_artist, mb_title
                        except Exception:
                            continue
        except Exception as e:
            if VERBOSE:
                print(f"  AcoustID lookup failed: {e}")

    return None


def update_video_metadata(
    file_path: Path, artist: str, title: str, dry_run: bool = False
) -> Tuple[bool, bool]:
    """Update MP4/M4V metadata with artist and title."""
    if file_path.suffix.lower() not in {".mp4", ".m4v"}:
        if VERBOSE:
            print(f"  Skipping metadata update for unsupported container: {file_path.suffix}")
        return True, False

    try:
        mp4 = MP4(str(file_path))

        # Update title
        if "nam" in mp4:
            current_title = mp4["nam"][0]
        else:
            current_title = ""

        # Update artist
        if "ART" in mp4:
            current_artist = mp4["ART"][0]
        else:
            current_artist = ""

        # Check if update needed
        needs_update = (current_title != title) or (current_artist != artist)
        if not needs_update:
            if VERBOSE:
                print("  Metadata already correct")
            return True, False

        if dry_run:
            print(
                f"  Would update metadata: '{current_artist}' -> '{artist}', '{current_title}' -> '{title}'"
            )
            return True, True

        # Set metadata
        mp4["nam"] = [title]  # Title
        mp4["ART"] = [artist]  # Artist

        # Also set standard tags for compatibility
        mp4["TITLE"] = [title]
        mp4["ARTIST"] = [artist]

        # Set media type to music video
        mp4["stik"] = [6]  # 6 = Music Video (iTunes/Apple standard)

        mp4.save()
        if VERBOSE:
            print(f"  Updated metadata: Artist='{artist}', Title='{title}'")

        return True, True

    except Exception as e:
        print(f"  Error updating metadata: {e}")
        return False, False


def process_video_file(
    file_path: Path,
    artist_name: str,
    dry_run: bool = False,
    force: bool = False,
    use_extracted: bool = False,
) -> str:
    """Process a single music video file."""
    print(f"\n Processing: {file_path.name}")
    print(f" Artist: {artist_name}")

    # Extract title from metadata first
    title = extract_title_from_metadata(file_path)
    if title:
        print(f" Title from metadata: {title}")

    # If no title from metadata, try filename
    if not title:
        title = extract_title_from_filename(file_path, artist_name)
        if title:
            print(f" Title from filename: {title}")

    # If still no title, use filename as last resort
    if not title:
        title = file_path.stem
        print(f" Title fallback: {title}")

    # Try to lookup correct info
    artist = artist_name  # Default to folder name
    title = title  # Default to extracted title

    lookup_result = lookup_music_video(file_path, artist_name, title)
    if lookup_result:
        lookup_artist, lookup_title = lookup_result
        print(f" Found: {lookup_artist} - {lookup_title}")

        # Use lookup result if it seems better
        if lookup_artist.lower() == artist_name.lower():
            artist = lookup_artist
            title = lookup_title
        else:
            print(" Artist mismatch, using folder name")
    else:
        print(" No reliable lookup found")
        print(" Extracted title was: '{}'".format(title))

        if use_extracted and title and title != file_path.stem:
            print(" Using extracted title (risky mode)")
            artist = artist_name
        else:
            print(" Skipping this file")
            log_skipped_file(artist_name, file_path, title, "No reliable lookup found")
            return "skipped"

    # Generate new filename
    new_filename = f"{sanitize_filename(artist)} - {sanitize_filename(title)}{file_path.suffix}"
    new_path = file_path.parent / new_filename

    rename_needed = new_path != file_path

    # Check if rename needed
    if rename_needed:
        if new_path.exists():
            print(f" Target file exists, skipping rename: {new_filename}")
        elif dry_run:
            print(f" Would rename: {file_path.name} → {new_filename}")
        else:
            try:
                file_path.rename(new_path)
                print(f" Renamed: {file_path.name} → {new_filename}")
                file_path = new_path
            except Exception as e:
                print(f" Rename failed: {e}")
                log_skipped_file(artist_name, file_path, title, f"Rename failed: {e}")
                return "skipped"

    # Update metadata
    ok, meta_changed = update_video_metadata(file_path, artist, title, dry_run)
    if not ok:
        log_skipped_file(artist_name, file_path, title, "Metadata update failed")
        return "skipped"

    if force:
        return "changed"

    if rename_needed or meta_changed:
        return "changed"

    return "unchanged"


def scan_music_videos(
    root_path: Path,
    dry_run: bool = False,
    force: bool = False,
    use_extracted: bool = False,
) -> Tuple[int, int, int]:
    """Scan music video directory and process all video files."""
    if not root_path.exists():
        print(f" Directory not found: {root_path}")
        return 0, 0, 0

    print(f" Scanning: {root_path}")

    changed = 0
    unchanged = 0
    skipped = 0

    # Scan artist folders
    for artist_folder in sorted(root_path.iterdir()):
        if not artist_folder.is_dir() or artist_folder.name.startswith("."):
            continue

        artist_name = artist_folder.name
        print(f"\n Artist: {artist_name}")

        # Find video files in artist folder
        video_files = []
        for ext in ["*.mp4", "*.m4v", "*.mkv", "*.avi", "*.mov"]:
            video_files.extend(artist_folder.glob(ext))

        if not video_files:
            print(" No video files found")
            continue

        for video_file in sorted(video_files):
            status = process_video_file(video_file, artist_name, dry_run, force, use_extracted)
            if status == "changed":
                changed += 1
            elif status == "unchanged":
                unchanged += 1
            else:
                skipped += 1

    return changed, unchanged, skipped


def main():
    parser = argparse.ArgumentParser(description="Normalize music video filenames and metadata")
    parser.add_argument(
        "root",
        nargs="?",
        help="Root music videos directory (defaults to LIBRARY_ROOT/Music Videos)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force updates even if metadata appears correct",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--use-extracted",
        action="store_true",
        help="Use cleaned extracted titles when lookup fails (risky)",
    )

    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    # Load environment and determine root path
    repo_root = Path(__file__).parent.parent.parent
    load_dotenv(repo_root)

    global ACOUSTID_API_KEY
    ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY", "")

    if args.root:
        root_path = Path(args.root)
    else:
        library_root = get_library_root()
        root_path = library_root / "Music Videos"
        if VERBOSE:
            print(f"Using default path: {root_path}")

    if not DEPS_AVAILABLE:
        sys.exit(1)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")

    changed, unchanged, skipped = scan_music_videos(
        root_path, args.dry_run, args.force, args.use_extracted
    )

    print("\n📊 Summary:")
    if args.dry_run:
        print(f"🔍 Would change {changed} files")
        print(f"✅ Already correct {unchanged} files")
        if skipped > 0:
            print(f"⚠️  Would skip {skipped} files")
    else:
        print(f"✅ Changed {changed} files")
        print(f"✅ Already correct {unchanged} files")
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} files - see log: {SKIPPED_LOG}")
            print("   Review skipped files for manual cleanup or to add overrides")

    if args.dry_run:
        print("💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
