#!/usr/bin/env python3
"""
Scan and update metadata for music videos in Videos/Music folder.
Checks for missing metadata and updates it using filename-based lookups.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from mutagen.id3 import TIT2, TPE1
from mutagen.mp3 import MP3 as MP3File
from mutagen.mp3 import HeaderNotFoundError
from mutagen.mp4 import MP4, MP4StreamInfoError

# Load environment variables
load_dotenv()

# Configuration
MUSIC_VIDEOS_ROOT = Path("/Volumes/Data/Media/Library/Videos/Music")
VERBOSE = True
DRY_RUN = False
FORCE_UPDATE = False  # Set to True to overwrite existing metadata

# API keys (optional - for enhanced metadata lookup)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")


def parse_filename(filename: str) -> tuple[str, str] | None:
    """Parse artist and title from filename in format 'Artist - Title.mp4'."""
    if not filename or not isinstance(filename, str):
        return None

    # Remove file extension
    name = Path(filename).stem

    # Split on " - " (space dash space)
    if " - " in name:
        parts = name.split(" - ", 1)
        if len(parts) == 2:
            artist, title = parts
            # Clean up whitespace
            artist = artist.strip()
            title = title.strip()
            if artist and title:
                return artist, title

    return None


def extract_metadata_from_file(file_path: Path) -> dict:
    """Extract existing metadata from file."""
    metadata = {"artist": None, "title": None, "has_metadata": False}

    try:
        if file_path.suffix.lower() == ".mp4":
            mp4 = MP4(file_path)

            # Extract title
            for title_key in ["\xa9nam", "TITLE", "title"]:
                if title_key in mp4 and mp4[title_key]:
                    metadata["title"] = str(mp4[title_key][0])
                    break

            # Extract artist
            for artist_key in ["\xa9ART", "ARTIST", "artist"]:
                if artist_key in mp4 and mp4[artist_key]:
                    metadata["artist"] = str(mp4[artist_key][0])
                    break

        elif file_path.suffix.lower() == ".mp3":
            mp3 = MP3File(file_path)

            if "TIT2" in mp3:
                metadata["title"] = str(mp3["TIT2"])

            if "TPE1" in mp3:
                metadata["artist"] = str(mp3["TPE1"])

        # Check if we have both artist and title
        metadata["has_metadata"] = bool(metadata["artist"] and metadata["title"])

    except Exception as e:
        if VERBOSE:
            print(f"Error reading metadata from {file_path.name}: {e}")

    return metadata


def write_metadata_to_file(file_path: Path, artist: str, title: str) -> bool:
    """Write artist and title metadata to file."""
    try:
        if file_path.suffix.lower() == ".mp4":
            mp4 = MP4(file_path)

            # Write title
            if "\xa9nam" not in mp4 or FORCE_UPDATE:
                mp4["\xa9nam"] = [title]

            # Write artist
            if "\xa9ART" not in mp4 or FORCE_UPDATE:
                mp4["\xa9ART"] = [artist]

            mp4.save()
            return True

        elif file_path.suffix.lower() == ".mp3":
            mp3 = MP3File(file_path)

            # Write title
            if "TIT2" not in mp3 or FORCE_UPDATE:
                mp3["TIT2"] = TIT2(encoding=3, text=title)

            # Write artist
            if "TPE1" not in mp3 or FORCE_UPDATE:
                mp3["TPE1"] = TPE1(encoding=3, text=artist)

            mp3.save()
            return True

    except Exception as e:
        if VERBOSE:
            print(f"Error writing metadata to {file_path.name}: {e}")
        return False

    return False


def process_file(file_path: Path) -> dict:
    """Process a single file for metadata issues."""
    result = {
        "file": file_path,
        "action": "none",
        "parsed_artist": None,
        "parsed_title": None,
        "existing_artist": None,
        "existing_title": None,
    }

    # Get existing metadata
    existing = extract_metadata_from_file(file_path)
    result["existing_artist"] = existing["artist"]
    result["existing_title"] = existing["title"]

    # Parse filename
    parsed = parse_filename(file_path.name)
    if not parsed:
        result["action"] = "skip"  # Can't parse filename
        return result

    result["parsed_artist"], result["parsed_title"] = parsed

    # Check if metadata is missing or incomplete
    if not existing["has_metadata"] or FORCE_UPDATE:
        if DRY_RUN:
            result["action"] = "would_update"
        else:
            success = write_metadata_to_file(file_path, parsed[0], parsed[1])
            result["action"] = "updated" if success else "failed"
    else:
        result["action"] = "has_metadata"

    return result


def scan_music_videos():
    """Scan all music videos and update metadata where needed."""
    if not MUSIC_VIDEOS_ROOT.exists():
        print(f"Error: Music videos directory not found: {MUSIC_VIDEOS_ROOT}")
        return

    print(f"Scanning music videos in: {MUSIC_VIDEOS_ROOT}")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE UPDATE'}")
    if FORCE_UPDATE:
        print("Force update: Will overwrite existing metadata")
    print()

    # Find all video files
    video_files = []
    for ext in ["*.mp4", "*.MP4", "*.mp3", "*.MP3"]:
        video_files.extend(MUSIC_VIDEOS_ROOT.rglob(ext))

    print(f"Found {len(video_files)} video files")
    print()

    # Process files
    results = {
        "updated": 0,
        "would_update": 0,
        "has_metadata": 0,
        "skip": 0,
        "failed": 0,
        "total": len(video_files),
    }

    for file_path in sorted(video_files):
        result = process_file(file_path)
        action = result["action"]
        results[action] += 1

        if VERBOSE or action in ["updated", "would_update", "failed"]:
            status_icon = {
                "updated": "✅",
                "would_update": "🔄",
                "has_metadata": "✓",
                "skip": "⏭",
                "failed": "❌",
                "none": "?",
            }.get(action, "?")

            print(f"{status_icon} {file_path.name}")

            if action in ["updated", "would_update", "failed"]:
                print(f"   Parsed: {result['parsed_artist']} - {result['parsed_title']}")
                if result["existing_artist"] or result["existing_title"]:
                    print(f"   Existing: {result['existing_artist']} - {result['existing_title']}")

            if action == "failed":
                print(f"   ERROR: Failed to update metadata")
            elif action == "skip":
                print(f"   SKIP: Cannot parse filename format")

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY:")
    print(f"Total files: {results['total']}")
    print(f"Updated: {results['updated']}")
    if DRY_RUN:
        print(f"Would update: {results['would_update']}")
    print(f"Already had metadata: {results['has_metadata']}")
    print(f"Skipped (unparseable): {results['skip']}")
    print(f"Failed: {results['failed']}")
    print("=" * 60)


def main():
    """Main function."""
    global DRY_RUN, VERBOSE, FORCE_UPDATE

    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Scan and update music video metadata")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing metadata")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    parser.add_argument("--directory", help="Override default directory to scan")

    args = parser.parse_args()

    DRY_RUN = args.dry_run
    VERBOSE = not args.quiet
    FORCE_UPDATE = args.force

    if args.directory:
        global MUSIC_VIDEOS_ROOT
        MUSIC_VIDEOS_ROOT = Path(args.directory)

    scan_music_videos()


if __name__ == "__main__":
    main()
