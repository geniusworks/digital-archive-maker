#!/usr/bin/env python3
"""Repair missing FLAC tags using .m3u8 playlist and folder structure.

This script repairs missing artist, album, and title tags in FLAC files by:
1. Extracting artist/album from folder structure
2. Extracting track titles from .m3u8 playlist files
3. Writing the tags to FLAC files that have missing/unknown tags

Usage:
    python3 bin/music/repair-flac-tags.py /path/to/album/folder
    python3 bin/music/repair-flac-tags.py /path/to/album/folder --dry-run
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mutagen.flac import FLAC


def normalize_tag_value(value: str) -> str:
    """Normalize a tag value by trimming and cleaning."""
    if not value:
        return ""
    return str(value).strip()


def parse_m3u8(m3u8_path: Path) -> List[Tuple[str, str]]:
    """Parse .m3u8 file and return list of (filename, title) tuples.

    Returns:
        List of tuples where first element is filename and second is title
    """
    tracks = []

    try:
        with open(m3u8_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Extract title from filename if not explicitly in playlist
                # Format is usually: "##:Artist - Album - Title.flac" or just "Title.flac"
                if line.startswith("##:"):
                    # Extended M3U format with metadata
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        metadata = parts[2]
                        # Try to extract title from metadata
                        if " - " in metadata:
                            # Assume format: Artist - Album - Title
                            title = metadata.split(" - ")[-1].strip()
                        else:
                            title = metadata.strip()
                        filename = parts[1] if len(parts) > 1 else ""
                    else:
                        title = line[2:].strip()
                        filename = ""
                else:
                    # Simple filename - this is the full filename with extension
                    filename = line
                    # Extract title from filename by removing track number and extension
                    title = os.path.splitext(os.path.basename(line))[0]
                    # Remove track number if present (e.g., "01 - Title" -> "Title")
                    title = re.sub(r"^\d+\s*-\s*", "", title)

                # Clean up title
                title = normalize_tag_value(title)
                filename = normalize_tag_value(filename)

                if title and filename:
                    tracks.append((filename, title))

    except Exception as e:
        print(f"Error parsing {m3u8_path}: {e}")
        return []

    return tracks


def extract_artist_album_from_path(album_path: Path) -> Tuple[str, str]:
    """Extract artist and album names from folder path.

    Assumes path structure: .../Artist/Album/
    """
    if album_path.name == "CDs":
        # If pointed to CDs root, we can't extract artist/album
        return "", ""

    # Get album name from current folder
    album = normalize_tag_value(album_path.name)

    # Get artist from parent folder
    artist = normalize_tag_value(album_path.parent.name) if album_path.parent.name != "CDs" else ""

    return artist, album


def find_flac_files(album_path: Path) -> List[Path]:
    """Find all FLAC files in the album directory."""
    flac_files = []
    for flac_path in album_path.glob("*.flac"):
        flac_files.append(flac_path)
    return sorted(flac_files)


def read_flac_tags(flac_path: Path) -> Dict[str, str]:
    """Read tags from a FLAC file."""
    try:
        audio = FLAC(flac_path)
        tags = {}
        tags["artist"] = normalize_tag_value(audio.get("ARTIST", [""])[0])
        tags["album"] = normalize_tag_value(audio.get("ALBUM", [""])[0])
        tags["title"] = normalize_tag_value(audio.get("TITLE", [""])[0])
        tags["tracknumber"] = normalize_tag_value(audio.get("TRACKNUMBER", [""])[0])
        return tags
    except Exception as e:
        print(f"Error reading tags from {flac_path}: {e}")
        return {}


def write_flac_tags(flac_path: Path, tags: Dict[str, str]) -> bool:
    """Write tags to a FLAC file."""
    try:
        audio = FLAC(flac_path)

        # Write all provided tags
        if tags.get("artist"):
            audio["ARTIST"] = tags["artist"]
            print(f"  Fixed ARTIST: {tags['artist']}")

        if tags.get("album"):
            audio["ALBUM"] = tags["album"]
            print(f"  Fixed ALBUM: {tags['album']}")

        if tags.get("title"):
            audio["TITLE"] = tags["title"]
            print(f"  Fixed TITLE: {tags['title']}")

        if tags.get("tracknumber"):
            audio["TRACKNUMBER"] = tags["tracknumber"]
            print(f"  Fixed TRACKNUMBER: {tags['tracknumber']}")

        audio.save()
        return True

    except Exception as e:
        print(f"Error writing tags to {flac_path}: {e}")
        return False


def match_flac_to_track(
    flac_path: Path, tracks: List[Tuple[str, str]]
) -> Optional[Tuple[str, str]]:
    """Match a FLAC file to a track entry from the playlist."""
    flac_name = flac_path.name

    # Try exact filename match first
    for filename, title in tracks:
        if filename == flac_name:
            return filename, title

    # Try basename match (without path)
    for filename, title in tracks:
        if os.path.basename(filename) == flac_name:
            return filename, title

    # Try to match by track number
    flac_track_match = re.match(r"^(\d+)", flac_name)
    if flac_track_match:
        flac_track_num = flac_track_match.group(1)
        for filename, title in tracks:
            playlist_track_match = re.match(r"^(\d+)", filename)
            if playlist_track_match and playlist_track_match.group(1) == flac_track_num:
                return filename, title

    # Try to match by extracting title from filename
    flac_title = os.path.splitext(flac_name)[0]
    flac_title = re.sub(r"^\d+\s*-\s*", "", flac_title)  # Remove track number

    for filename, title in tracks:
        playlist_title = os.path.splitext(os.path.basename(filename))[0]
        playlist_title = re.sub(r"^\d+\s*-\s*", "", playlist_title)

        if playlist_title.lower() == flac_title.lower():
            return filename, title

    return None


def repair_album_tags(album_path: Path, dry_run: bool = False) -> int:
    """Repair tags for all FLAC files in an album.

    Returns:
        Number of files that would be/are repaired
    """
    print(f"\nProcessing album: {album_path}")

    # Find playlist files
    m3u8_files = list(album_path.glob("*.m3u8"))
    if not m3u8_files:
        print("  No .m3u8 playlist found, skipping...")
        return 0

    # Use the first .m3u8 file found
    m3u8_file = m3u8_files[0]
    print(f"  Using playlist: {m3u8_file.name}")

    # Parse playlist
    tracks = parse_m3u8(m3u8_file)
    if not tracks:
        print("  No tracks found in playlist, skipping...")
        return 0

    print(f"  Found {len(tracks)} tracks in playlist")

    # Extract artist and album from path
    artist, album = extract_artist_album_from_path(album_path)
    print(f"  Artist from path: {artist or '(unknown)'}")
    print(f"  Album from path: {album or '(unknown)'}")

    # Find FLAC files
    flac_files = find_flac_files(album_path)
    print(f"  Found {len(flac_files)} FLAC files")

    repaired_count = 0

    for flac_path in flac_files:
        print(f"\n  Checking: {flac_path.name}")

        # Read current tags
        current_tags = read_flac_tags(flac_path)
        print(
            f"    Current: ARTIST='{current_tags.get('artist', '')}' "
            f"ALBUM='{current_tags.get('album', '')}' "
            f"TITLE='{current_tags.get('title', '')}'"
        )

        # Match to playlist track first to get expected title
        track_match = match_flac_to_track(flac_path, tracks)
        if not track_match:
            print("    Could not match to playlist track, skipping...")
            continue

        filename, expected_title = track_match

        # Check if tags differ from expected values
        needs_repair = False
        differences = {}

        # Check artist tag
        if artist and current_tags.get("artist", "") != artist:
            needs_repair = True
            differences["artist"] = (current_tags.get("artist", ""), artist)

        # Check album tag
        if album and current_tags.get("album", "") != album:
            needs_repair = True
            differences["album"] = (current_tags.get("album", ""), album)

        # Check title tag
        if expected_title and current_tags.get("title", "") != expected_title:
            needs_repair = True
            differences["title"] = (
                current_tags.get("title", ""),
                expected_title,
            )

        # Check track number (extract from filename)
        track_match_num = re.match(r"^(\d+)", flac_path.name)
        expected_track = track_match_num.group(1) if track_match_num else ""
        if expected_track and current_tags.get("tracknumber", "") != expected_track:
            needs_repair = True
            differences["tracknumber"] = (
                current_tags.get("tracknumber", ""),
                expected_track,
            )

        if not needs_repair:
            print("    Tags match expected values, skipping...")
            continue

        # Prepare new tags based on differences
        new_tags = {}
        for field, (current, expected) in differences.items():
            if expected:  # Only include if we have an expected value
                new_tags[field] = expected

        print(f"    Differences found: {differences}")
        print(f"    Repairing with: {new_tags}")

        if not new_tags:
            print("    No new information available, skipping...")
            continue

        if dry_run:
            print("    [DRY RUN] Would repair tags")
            repaired_count += 1
        else:
            if write_flac_tags(flac_path, new_tags):
                print("    Tags repaired successfully")
                repaired_count += 1
            else:
                print("    Failed to repair tags")

    return repaired_count


def main():
    parser = argparse.ArgumentParser(
        description="Repair missing FLAC tags using .m3u8 playlist and folder structure"
    )
    parser.add_argument(
        "album_path",
        help="Path to album folder containing FLAC files and .m3u8 playlist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be repaired without making changes",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    album_path = Path(args.album_path).resolve()

    if not album_path.exists():
        print(f"Error: Path does not exist: {album_path}")
        sys.exit(1)

    if not album_path.is_dir():
        print(f"Error: Path is not a directory: {album_path}")
        sys.exit(1)

    # Check for FLAC files
    flac_files = find_flac_files(album_path)
    if not flac_files:
        print(f"No FLAC files found in {album_path}")
        sys.exit(0)

    print("=" * 60)
    print("FLAC Tag Repair")
    print("=" * 60)
    print(f"Album: {album_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'REPAIR'}")

    total_repaired = repair_album_tags(album_path, args.dry_run)

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"Would repair {total_repaired} files")
    else:
        print(f"Repaired {total_repaired} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
