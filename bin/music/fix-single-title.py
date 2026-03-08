#!/usr/bin/env python3
"""
Fix a single track's title by removing track number from the beginning.
Usage: python3 fix-single-title.py /path/to/file.flac
"""

import re
import sys
from pathlib import Path

from mutagen.flac import FLAC


def fix_track_title(flac_path):
    """Remove track number from the beginning of a track's title."""
    path = Path(flac_path)

    if not path.exists():
        print(f"File not found: {flac_path}")
        return False

    if not path.suffix.lower() == ".flac":
        print(f"Not a FLAC file: {flac_path}")
        return False

    try:
        audio = FLAC(flac_path)
        current_title = audio.get("TITLE", [""])[0]

        # If no title exists, extract from filename
        if not current_title:
            filename_title = path.stem  # Remove extension
            # Remove track number from beginning
            current_title = re.sub(r"^\d+\s*[-.\s]*", "", filename_title).strip()
            print(f"No TITLE tag found, extracted from filename: {repr(current_title)}")

        if not current_title:
            print(f"Could not determine title for: {flac_path}")
            return False

        # Remove track number from beginning of title
        # Patterns: "13 - Title", "13 Title", "13. Title", etc.
        new_title = re.sub(r"^\d+\s*[-.\s]*", "", current_title).strip()

        if new_title == current_title:
            print(f"File: {path.name}")
            print(f"Current title: {repr(current_title)}")
            print("✓ Title already correct (no update needed)")
            return True

        print(f"File: {path.name}")
        print(f"Before: {repr(current_title)}")
        print(f"After:  {repr(new_title)}")

        # Update the title
        audio["TITLE"] = [new_title]
        audio.save()

        print("✓ Title updated successfully")
        return True

    except Exception as e:
        print(f"Error processing {flac_path}: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 fix-single-title.py /path/to/file.flac")
        sys.exit(1)

    fix_track_title(sys.argv[1])
