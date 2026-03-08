#!/usr/bin/env python3
"""Fix completely unknown album rips by renaming folders, files, and updating all metadata.

This script handles albums that were ripped without MusicBrainz data, resulting in:
- Unknown artist/album folders
- Generic track names (Track 01, Track 02, etc.)
- Missing or incorrect FLAC tags
- Outdated .m3u8 playlists

Usage:
    python3 bin/fix-unknown-album.py /path/to/unknown/album "Correct Artist" "Correct Album"
    python3 bin/fix-unknown-album.py /path/to/unknown/album "Correct Artist" "Correct Album" --dry-run
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mutagen.flac import FLAC


def normalize_tag_value(value: str) -> str:
    """Normalize a tag value by trimming and cleaning."""
    if not value:
        return ""
    return str(value).strip()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem compatibility."""
    # Remove characters that are problematic in filenames
    invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    # Remove leading/trailing spaces and dots
    filename = filename.strip(" .")
    # Ensure it's not empty
    return filename if filename else "unknown"


def read_flac_tags(flac_path: Path) -> Dict[str, str]:
    """Read tags from a FLAC file."""
    try:
        audio = FLAC(flac_path)
        tags = {}
        for key, value in audio.items():
            if isinstance(value, list) and value:
                tags[key.lower()] = str(value[0])
            else:
                tags[key.lower()] = str(value)
        return tags
    except Exception as e:
        print(f"Error reading tags from {flac_path}: {e}")
        return {}


def write_flac_tags(flac_path: Path, tags: Dict[str, str]) -> bool:
    """Write tags to a FLAC file."""
    try:
        audio = FLAC(flac_path)
        for key, value in tags.items():
            audio[key] = value
        audio.save()
        return True
    except Exception as e:
        print(f"Error writing tags to {flac_path}: {e}")
        return False


def parse_m3u8(m3u8_path: Path) -> List[Tuple[str, str]]:
    """Parse .m3u8 file and return list of (filename, title) tuples."""
    tracks = []

    try:
        with open(m3u8_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"):
                    continue

                # Extract title from filename
                filename = line
                title = os.path.splitext(os.path.basename(line))[0]
                # Remove track number if present (e.g., "01 - Title" -> "Title")
                title = re.sub(r"^\d+\s*-\s*", "", title)

                if filename and title:
                    tracks.append((filename, normalize_tag_value(title)))

    except Exception as e:
        print(f"Error parsing {m3u8_path}: {e}")
        return []

    return tracks


def write_m3u8(m3u8_path: Path, tracks: List[Tuple[str, str]]) -> bool:
    """Write updated .m3u8 file."""
    try:
        with open(m3u8_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for filename, title in tracks:
                f.write(f"{filename}\n")
        return True
    except Exception as e:
        print(f"Error writing {m3u8_path}: {e}")
        return False


def get_track_titles_from_musicbrainz(artist: str, album: str) -> Optional[List[str]]:
    """Try to get track titles from MusicBrainz."""
    try:
        import musicbrainzngs

        musicbrainzngs.set_useragent("fix-unknown-album", "1.0", "https://yourdomain.example")

        # Search for the release
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=1)
        if not result.get("release-list"):
            return None

        release = result["release-list"][0]
        release_id = release["id"]

        # Get release details with tracklist
        release_info = musicbrainzngs.get_release_by_id(release_id, includes=["recordings"])
        release_group = release_info["release"]

        track_titles = []
        for medium in release_group.get("medium-list", []):
            for track in medium.get("track-list", []):
                title = track.get("recording", {}).get("title", "")
                if title:
                    track_titles.append(title)

        return track_titles if track_titles else None

    except ImportError:
        print("MusicBrainz library not available, will use generic track titles")
        return None
    except Exception as e:
        print(f"Error fetching from MusicBrainz: {e}")
        return None


def fix_unknown_album(
    album_path: Path,
    correct_artist: str,
    correct_album: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Fix unknown album by renaming folders, files, and updating metadata."""

    album_path = album_path.resolve()
    if not album_path.exists():
        print(f"Error: Path {album_path} does not exist")
        return False

    print(f"Processing: {album_path}")
    print(f"Target: {correct_artist} / {correct_album}")

    # Find FLAC files
    flac_files = sorted([f for f in album_path.glob("*.flac")])
    if not flac_files:
        print("No FLAC files found")
        return False

    print(f"Found {len(flac_files)} FLAC files")

    # Try to get track titles from .m3u8 file first
    m3u8_files = list(album_path.glob("*.m3u8"))
    track_titles = None

    if m3u8_files:
        m3u8_file = m3u8_files[0]
        if verbose:
            print(f"Found .m3u8 file: {m3u8_file.name}")
        m3u8_tracks = parse_m3u8(m3u8_file)
        if m3u8_tracks:
            # Extract titles from .m3u8 tracks
            track_titles = [title for filename, title in m3u8_tracks]
            if verbose:
                print(f"Using {len(track_titles)} track titles from .m3u8 file")

    # If no .m3u8 titles, try MusicBrainz
    if not track_titles:
        track_titles = get_track_titles_from_musicbrainz(correct_artist, correct_album)
        if track_titles and verbose:
            print(f"Using {len(track_titles)} track titles from MusicBrainz")

    # If still no titles, use generic ones
    if not track_titles:
        print("Using generic track titles")
        track_titles = [f"Track {i+1:02d}" for i in range(len(flac_files))]

    if len(track_titles) != len(flac_files):
        print(
            f"Warning: MusicBrainz has {len(track_titles)} tracks but found {len(flac_files)} files"
        )
        # Adjust to match file count
        if len(track_titles) < len(flac_files):
            track_titles.extend(
                [f"Track {i+1:02d}" for i in range(len(track_titles), len(flac_files))]
            )
        else:
            track_titles = track_titles[: len(flac_files)]

    # Step 1: Rename FLAC files
    new_flac_files = []
    for i, flac_file in enumerate(flac_files):
        track_num = i + 1
        title = track_titles[i]
        new_filename = f"{track_num:02d} - {sanitize_filename(title)}.flac"
        new_flac_path = album_path / new_filename

        if verbose:
            print(f"  {flac_file.name} -> {new_filename}")

        if flac_file != new_flac_path:
            if dry_run:
                print(f"    [DRY RUN] Would rename: {flac_file.name} -> {new_filename}")
            else:
                try:
                    shutil.move(flac_file, new_flac_path)
                    print(f"    Renamed: {flac_file.name} -> {new_filename}")
                except Exception as e:
                    print(f"    Error renaming {flac_file}: {e}")
                    return False

        new_flac_files.append((new_flac_path, title))

    # Step 2: Update FLAC tags
    for i, (flac_path, title) in enumerate(new_flac_files):
        # In dry run, read from original file since new file doesn't exist yet
        if dry_run:
            original_flac_file = flac_files[i]
            current_tags = read_flac_tags(original_flac_file)
        else:
            current_tags = read_flac_tags(flac_path)

        new_tags = {
            "artist": correct_artist,
            "album": correct_album,
            "title": title,
            "tracknumber": f"{i+1:02d}",
        }

        # Check if tags need updating
        needs_update = any(current_tags.get(key, "") != value for key, value in new_tags.items())

        if needs_update:
            if verbose:
                print(f"  Updating tags for {flac_path.name}")
                print(f"    ARTIST: '{current_tags.get('artist', '')}' -> '{correct_artist}'")
                print(f"    ALBUM: '{current_tags.get('album', '')}' -> '{correct_album}'")
                print(f"    TITLE: '{current_tags.get('title', '')}' -> '{title}'")

            if dry_run:
                print(f"    [DRY RUN] Would update tags")
            else:
                if write_flac_tags(flac_path, new_tags):
                    print(f"    Updated tags: {flac_path.name}")
                else:
                    print(f"    Failed to update tags: {flac_path.name}")

    # Step 3: Update .m3u8 playlist
    m3u8_files = list(album_path.glob("*.m3u8"))
    if m3u8_files:
        m3u8_path = m3u8_files[0]  # Use the first .m3u8 file found
        # Create new track list
        new_tracks = [(flac_path.name, title) for flac_path, title in new_flac_files]

        if dry_run:
            print(f"  [DRY RUN] Would update {m3u8_path.name}")
        else:
            if write_m3u8(m3u8_path, new_tracks):
                print(f"  Updated playlist: {m3u8_path.name}")
            else:
                print(f"  Failed to update playlist: {m3u8_path.name}")
    else:
        print(f"  No .m3u8 playlist found")

    # Step 4: Rename album folder (if needed)
    current_album_name = album_path.name
    new_album_name = sanitize_filename(correct_album)

    if current_album_name != new_album_name:
        new_album_path = album_path.parent / new_album_name
        if dry_run:
            print(f"  [DRY RUN] Would rename folder: {current_album_name} -> {new_album_name}")
        else:
            try:
                album_path.rename(new_album_path)
                print(f"  Renamed folder: {current_album_name} -> {new_album_name}")
            except Exception as e:
                print(f"  Error renaming folder: {e}")
                return False

    print(f"Successfully fixed album: {correct_artist} / {correct_album}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fix completely unknown album rips by renaming folders, files, and updating metadata"
    )
    parser.add_argument("album_path", type=Path, help="Path to unknown album folder")
    parser.add_argument("artist", help="Correct artist name")
    parser.add_argument("album", help="Correct album name")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    success = fix_unknown_album(
        args.album_path,
        args.artist,
        args.album,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
