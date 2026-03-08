#!/usr/bin/env python3
"""
Standardize music video filenames to consistent format: {artist} - {title}.mp4
Processes all files in /Volumes/Data/Media/Library/Videos/Music and its subdirectories.
"""

import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from mutagen.mp3 import MP3 as MP3File
from mutagen.mp3 import HeaderNotFoundError
from mutagen.mp4 import MP4, MP4StreamInfoError

# Load environment variables
load_dotenv()

# Configuration
MUSIC_VIDEOS_ROOT = Path("/Volumes/Data/Media/Library/Videos/Music")
VERBOSE = True
DRY_RUN = False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    # Replace multiple spaces with single space
    filename = re.sub(r"\s+", " ", filename)
    # Strip leading/trailing spaces and dots
    filename = filename.strip(" .")
    return filename


def extract_metadata_from_file(file_path: Path) -> tuple[str, str] | None:
    """Extract artist and title from file metadata."""
    try:
        if file_path.suffix.lower() == ".mp4":
            mp4 = MP4(file_path)
            # Try different tag keys
            title = None
            artist = None

            # Title tags
            for title_key in ["\xa9nam", "TITLE", "title"]:
                if title_key in mp4 and mp4[title_key]:
                    title = str(mp4[title_key][0])
                    break

            # Artist tags
            for artist_key in ["\xa9ART", "ARTIST", "artist"]:
                if artist_key in mp4 and mp4[artist_key]:
                    artist = str(mp4[artist_key][0])
                    break

            if title and artist:
                return artist, title

        elif file_path.suffix.lower() == ".mp3":
            mp3 = MP3File(file_path)
            title = None
            artist = None

            # Title tags
            if hasattr(mp3, "tags") and mp3.tags:
                for title_key in ["TIT2", "TITLE", "Title"]:
                    if title_key in mp3.tags:
                        title = str(mp3.tags[title_key].text[0])
                        break

                # Artist tags
                for artist_key in ["TPE1", "ARTIST", "Artist"]:
                    if artist_key in mp3.tags:
                        artist = str(mp3.tags[artist_key].text[0])
                        break

            if title and artist:
                return artist, title

    except (MP4StreamInfoError, HeaderNotFoundError, Exception) as e:
        if VERBOSE:
            print(f"  Could not read metadata: {e}")

    return None


def parse_artist_from_filename(file_path: Path) -> str:
    """Extract artist name from parent directory."""
    parent_dir = file_path.parent.name

    # Handle special cases
    if parent_dir == "Various":
        return "Various"

    # Clean up the artist name
    artist = parent_dir.strip()
    # Remove any trailing numbers or common suffixes
    artist = re.sub(r"\s*\d+$", "", artist)
    artist = re.sub(r"\s*\([^)]*\)$", "", artist)

    return artist


def parse_title_from_filename(filename: str) -> str:
    """Extract title from filename, removing common prefixes/suffixes."""
    # Remove file extension
    name = Path(filename).stem

    # Remove artist prefix if present (e.g., "Artist - Title")
    if " - " in name:
        name = " - ".join(name.split(" - ")[1:])

    # Remove common prefixes/suffixes
    prefixes_to_remove = [
        r"^Official Video\s*[-:]?\s*",
        r"^Official Audio\s*[-:]?\s*",
        r"^Lyric Video\s*[-:]?\s*",
        r"^Music Video\s*[-:]?\s*",
        r"^HD\s*[-:]?\s*",
        r"^\d+\.\s*",  # Track numbers
    ]

    suffixes_to_remove = [
        r"\s*\(Official Video\)$",
        r"\s*\(Official Audio\)$",
        r"\s*\(Lyric Video\)$",
        r"\s*\(Music Video\)$",
        r"\s*\(HD\)$",
        r"\s*\(\d{4}\)$",  # Year
        r"\s*\[.*?\]$",  # Bracketed info
        r"\s*\(.*?\)$",  # Parenthetical info
    ]

    for pattern in prefixes_to_remove:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    for pattern in suffixes_to_remove:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    return name.strip()


def process_file(file_path: Path) -> tuple[str, str]:
    """Process a single music video file."""
    print(f"\nProcessing: {file_path.relative_to(MUSIC_VIDEOS_ROOT)}")

    # Try to get metadata from file first
    metadata = extract_metadata_from_file(file_path)

    if metadata:
        artist, title = metadata
        print(f"  Found metadata: Artist='{artist}', Title='{title}'")
    else:
        # Fall back to directory/filename parsing
        artist = parse_artist_from_filename(file_path)
        title = parse_title_from_filename(file_path.name)
        print(f"  Using parsed: Artist='{artist}', Title='{title}'")

    # Generate standardized filename
    clean_artist = sanitize_filename(artist)
    clean_title = sanitize_filename(title)
    new_filename = f"{clean_artist} - {clean_title}{file_path.suffix}"
    new_path = file_path.parent / new_filename

    # Handle duplicates
    counter = 1
    while new_path.exists() and new_path != file_path:
        new_filename = f"{clean_artist} - {clean_title} ({counter}){file_path.suffix}"
        new_path = file_path.parent / new_filename
        counter += 1

    # Check if rename needed
    if new_path == file_path:
        print(f"  Already has correct format")
        return "unchanged", file_path

    print(f"  Would rename: {file_path.name} → {new_filename}")
    print(f"  Full path: {new_path.relative_to(MUSIC_VIDEOS_ROOT)}")

    if DRY_RUN:
        print(f"  [DRY RUN] Would rename file")
        return "changed", new_path

    # Perform rename
    try:
        file_path.rename(new_path)
        print(f"  Renamed successfully")
        return "changed", new_path
    except Exception as e:
        print(f"  Error renaming: {e}")
        return "error", file_path


def main():
    """Main processing function."""
    global DRY_RUN

    # Check for dry-run flag
    if "--dry-run" in sys.argv:
        DRY_RUN = True
        print("DRY RUN MODE - No files will be renamed")

    if not MUSIC_VIDEOS_ROOT.exists():
        print(f"Error: Music videos directory not found: {MUSIC_VIDEOS_ROOT}")
        sys.exit(1)

    print(f"Standardizing music video filenames in: {MUSIC_VIDEOS_ROOT}")
    print(f"Target format: {{artist}} - {{title}}.mp4")

    # Counters
    processed = 0
    changed = 0
    unchanged = 0
    errors = 0

    # Process all files recursively
    for file_path in MUSIC_VIDEOS_ROOT.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in [
            ".mp4",
            ".mp3",
        ]:
            status, result_path = process_file(file_path)
            processed += 1

            if status == "changed":
                changed += 1
            elif status == "unchanged":
                unchanged += 1
            elif status == "error":
                errors += 1

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {processed}")
    print(f"Files renamed: {changed}")
    print(f"Files already correct: {unchanged}")
    print(f"Errors: {errors}")

    if DRY_RUN:
        print(f"\nDRY RUN - No actual changes made")
    else:
        print(f"\nAll files now follow the format: {{artist}} - {{title}}.mp4")


if __name__ == "__main__":
    main()
