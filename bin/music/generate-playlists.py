#!/usr/bin/env python3
"""
Generate .m3u8 playlist files for albums that don't have them yet.

Scans music directories and creates simple M3U playlists for any album folder
containing audio files but missing a playlist file.
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def sanitize_filename(name):
    """Sanitize a string for use as a filename."""
    # Remove invalid characters and replace with safe alternatives
    sanitized = re.sub(r'[<>:"/\\|?*]', "", name)
    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(" .")
    # Ensure it's not empty
    return sanitized if sanitized else "Unknown"


def get_album_name(directory):
    """Extract album name from audio file metadata or fallback to directory name."""
    if not MUTAGEN_AVAILABLE:
        # Fallback to directory name if mutagen not available
        return sanitize_filename(os.path.basename(directory))

    audio_extensions = {".flac", ".mp3", ".m4a", ".wav", ".aac", ".ogg"}

    for name in os.listdir(directory):
        if Path(name).suffix.lower() in audio_extensions:
            filepath = os.path.join(directory, name)
            try:
                if name.lower().endswith(".flac"):
                    audio = FLAC(filepath)
                    album = audio.get("ALBUM")
                    if album:
                        return sanitize_filename(str(album[0]))
                elif name.lower().endswith(".mp3"):
                    audio = MP3(filepath)
                    if audio.tags:
                        album = audio.tags.get("TALB") or audio.tags.get("ALBUM")
                        if album:
                            return sanitize_filename(str(album[0]))
            except Exception:
                continue

    # Fallback to directory name
    return sanitize_filename(os.path.basename(directory))


def find_audio_files(directory):
    """Find all audio files in a directory, sorted naturally."""
    audio_extensions = {".flac", ".mp3", ".m4a", ".wav", ".aac", ".ogg"}

    audio_files = []
    for name in os.listdir(directory):
        if Path(name).suffix.lower() in audio_extensions:
            audio_files.append(name)

    # Natural sort (handle track numbers properly)
    def natural_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]

    return sorted(audio_files, key=natural_key)


def generate_playlist(directory, dry_run=False):
    """Generate a playlist for the given directory using album-specific naming."""
    audio_files = find_audio_files(directory)

    if not audio_files:
        return False  # No audio files found

    # Get album name from metadata or directory name
    album_name = get_album_name(directory)
    playlist_filename = f"{album_name}.m3u8"
    playlist_path = os.path.join(directory, playlist_filename)

    if os.path.exists(playlist_path):
        return False  # Playlist already exists

    if dry_run:
        print(f"Would create: {playlist_path} ({len(audio_files)} tracks)")
        for audio_file in audio_files:
            print(f"  {audio_file}")
        return True

    # Create the playlist
    with open(playlist_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        for audio_file in audio_files:
            f.write(f"{audio_file}\n")

    print(f"Created: {playlist_path} ({len(audio_files)} tracks)")
    return True


def scan_directory(root_dir, dry_run=False):
    """Scan for albums missing playlists and generate them."""
    created_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(root_dir):
        # Skip if this looks like a root-level directory (no subdirectories)
        if not dirs and not any(
            Path(f).suffix.lower() in {".flac", ".mp3", ".m4a", ".wav", ".aac", ".ogg"}
            for f in files
        ):
            continue

        # Check if this directory has audio files
        audio_files = [
            f
            for f in files
            if Path(f).suffix.lower() in {".flac", ".mp3", ".m4a", ".wav", ".aac", ".ogg"}
        ]

        if not audio_files:
            continue  # No audio files in this directory

        # Generate playlist (will check if already exists)
        if generate_playlist(root, dry_run):
            created_count += 1
        else:
            skipped_count += 1

    return created_count, skipped_count


def main():
    parser = argparse.ArgumentParser(description="Generate .m3u8 playlists for albums missing them")
    parser.add_argument("directory", help="Root music directory to scan")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating files",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found: {args.directory}")
        return 1

    print(f"Scanning: {args.directory}")
    print("Playlist naming: Album-specific (based on metadata or folder name)")

    if not MUTAGEN_AVAILABLE:
        print("Warning: mutagen not available - using directory names for playlists")

    if args.dry_run:
        print("DRY RUN - No files will be created")

    created_count, skipped_count = scan_directory(args.directory, args.dry_run)

    print("\nSummary:")
    print(f"  Playlists created: {created_count}")
    print(f"  Already existed: {skipped_count}")

    if args.dry_run and created_count > 0:
        print(f"\nRun without --dry-run to create {created_count} playlist(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
