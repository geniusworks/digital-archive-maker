#!/usr/bin/env python3
"""
Fix missing track numbers in FLAC files.
Usage: python3 fix-track-numbers.py /path/to/album/directory
"""

import os
import re
import sys
from pathlib import Path

from mutagen.flac import FLAC


def extract_track_from_filename(filename):
    """Extract track number from filename patterns."""
    # Common patterns: "01 - Song.flac", "1 Song.flac", "Song - 01.flac", etc.
    patterns = [
        r"^(\d+)\s*[-_.]\s*",  # "01 - Song.flac"
        r"^(\d+)\s+",  # "1 Song.flac"
        r"\s*[-_.]\s*(\d+)\.",  # "Song - 01.flac"
        r"\s+(\d+)\s*-",  # "Song 01 - Title.flac"
        r"(\d+)$",  # "Song01.flac"
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1))
    return None


def fix_track_numbers(directory):
    """Fix track numbers for all FLAC files in directory."""
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"Directory not found: {directory}")
        return False

    flac_files = sorted([f for f in dir_path.glob("*.flac")])

    if not flac_files:
        print(f"No FLAC files found in {directory}")
        return False

    print(f"Found {len(flac_files)} FLAC files")

    updated = 0
    for i, flac_file in enumerate(flac_files, 1):
        try:
            audio = FLAC(flac_file)
            current_track = audio.get("tracknumber", [""])[0]

            # Skip if already has track number
            if current_track and current_track.strip():
                print(f"✓ {flac_file.name} - already has track {current_track}")
                continue

            # Try to extract from filename
            filename_track = extract_track_from_filename(flac_file.name)

            if filename_track:
                new_track = str(filename_track)
                print(f"→ {flac_file.name} - setting track {new_track} (from filename)")
                audio["tracknumber"] = [new_track]

                # Also set total if we know it
                if len(flac_files) > 1:
                    audio["tracktotal"] = [str(len(flac_files))]

                audio.save()
                updated += 1
            else:
                # Use sequential numbering as fallback
                new_track = str(i)
                print(f"? {flac_file.name} - setting track {new_track} (sequential)")
                audio["tracknumber"] = [new_track]

                if len(flac_files) > 1:
                    audio["tracktotal"] = [str(len(flac_files))]

                audio.save()
                updated += 1

        except Exception as e:
            print(f"✗ Error processing {flac_file.name}: {e}")

    print(f"\nUpdated {updated} files")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 fix-track-numbers.py /path/to/album/directory")
        sys.exit(1)

    fix_track_numbers(sys.argv[1])
