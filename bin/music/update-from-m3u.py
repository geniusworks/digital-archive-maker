#!/usr/bin/env python3
"""
Update filenames and metadata from M3U8 playlists.

This script reads M3U8 playlist files and updates audio file filenames
and metadata tags based on the playlist information.

Usage:
    python3 bin/music/update-from-m3u.py /path/to/album.m3u8 --dry-run
    python3 bin/music/update-from-m3u.py /path/to/album/ --dry-run
    python3 bin/music/update-from-m3u.py /path/to/album.m3u8 --force
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from mutagen.flac import FLAC
    from mutagen.id3 import TALB, TIT2, TPE1, TRCK
    from mutagen.mp3 import MP3

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("Error: mutagen library not available. Install with: pip install mutagen")
    sys.exit(1)


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove invalid characters and replace with safe alternatives
    sanitized = re.sub(r'[<>:"/\\|?*]', "", name)
    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(" .")
    # Ensure it's not empty
    return sanitized if sanitized else "Unknown"


def parse_m3u8(
    m3u8_path: Path,
) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """Parse M3U8 file and return list of (filename, title, duration) tuples."""
    entries = []

    if not m3u8_path.exists():
        print(f"❌ M3U8 file not found: {m3u8_path}")
        return entries

    with open(m3u8_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_title = None
    current_duration = None

    for line in lines:
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            # Parse EXTINF lines for title and duration
            if line.startswith("#EXTINF:"):
                # Format: #EXTINF:duration,title
                match = re.match(r"#EXTINF:([^,]*),(.*)", line)
                if match:
                    duration_str, title = match.groups()
                    current_duration = duration_str.strip()
                    current_title = title.strip()
            continue

        # This is a filename line
        filename = line
        entries.append((filename, current_title, current_duration))
        current_title = None
        current_duration = None

    return entries


def find_audio_file(folder_path: Path, target_filename: str, entry_index: int) -> Optional[Path]:
    """Find an audio file in the folder that matches the target filename or position."""
    audio_extensions = [".flac", ".mp3", ".m4a", ".wav", ".aac", ".ogg"]

    # First try: exact match
    exact_path = folder_path / target_filename
    if exact_path.exists():
        return exact_path

    # Second try: different extensions with same base name
    base_name = Path(target_filename).stem
    for ext in audio_extensions:
        test_path = folder_path / (base_name + ext)
        if test_path.exists():
            return test_path

    # Third try: find files with similar names
    for audio_file in folder_path.iterdir():
        if audio_file.is_file() and audio_file.suffix.lower() in audio_extensions:
            if base_name.lower() in audio_file.stem.lower():
                return audio_file

    # Fourth try: use position-based matching for generic track names
    # This handles "Track 1.flac", "Track 2.flac", etc.
    all_audio_files = sorted(
        [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() in audio_extensions]
    )

    # Try to find by pattern "Track N" first
    track_pattern = f"Track {entry_index + 1}"
    for audio_file in all_audio_files:
        if audio_file.stem.lower() == track_pattern.lower():
            return audio_file

    # Fallback to position-based if no "Track N" pattern found
    if entry_index < len(all_audio_files):
        return all_audio_files[entry_index]

    return None


def extract_metadata_from_title(
    title: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Extract artist and title from playlist title string."""
    # Common patterns: "Artist - Title", "Title", etc.
    if " - " in title:
        parts = title.split(" - ", 1)
        if len(parts) == 2:
            artist, track_title = parts
            return artist.strip(), track_title.strip()

    # No artist found, return as title only
    return None, title.strip()


def update_flac_tags(
    file_path: Path,
    artist: Optional[str],
    title: Optional[str],
    album: Optional[str] = None,
    track_number: Optional[str] = None,
) -> bool:
    """Update FLAC file metadata."""
    try:
        audio = FLAC(file_path)

        if artist:
            audio["ARTIST"] = [artist]
        if title:
            audio["TITLE"] = [title]
        if album:
            audio["ALBUM"] = [album]
        if track_number:
            audio["TRACKNUMBER"] = [track_number]

        audio.save()
        return True
    except Exception as e:
        print(f"❌ Error updating FLAC tags for {file_path.name}: {e}")
        return False


def update_mp3_tags(
    file_path: Path,
    artist: Optional[str],
    title: Optional[str],
    album: Optional[str] = None,
    track_number: Optional[str] = None,
) -> bool:
    """Update MP3 file metadata."""
    try:
        audio = MP3(file_path)

        if artist:
            if "TPE1" in audio.tags:
                del audio.tags["TPE1"]
            audio.tags.add(TPE1(encoding=3, text=artist))

        if title:
            if "TIT2" in audio.tags:
                del audio.tags["TIT2"]
            audio.tags.add(TIT2(encoding=3, text=title))

        if album:
            if "TALB" in audio.tags:
                del audio.tags["TALB"]
            audio.tags.add(TALB(encoding=3, text=album))

        if track_number:
            if "TRCK" in audio.tags:
                del audio.tags["TRCK"]
            audio.tags.add(TRCK(encoding=3, text=track_number))

        audio.save()
        return True
    except Exception as e:
        print(f"❌ Error updating MP3 tags for {file_path.name}: {e}")
        return False


def update_audio_file(
    file_path: Path,
    new_filename: str,
    artist: Optional[str],
    title: Optional[str],
    album: Optional[str] = None,
    track_number: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """Update audio file filename and metadata."""
    # Update metadata first
    if file_path.suffix.lower() == ".flac":
        success = update_flac_tags(file_path, artist, title, album, track_number)
    elif file_path.suffix.lower() == ".mp3":
        success = update_mp3_tags(file_path, artist, title, album, track_number)
    else:
        print(f"⚠️  Unsupported format: {file_path.suffix}")
        success = False

    if not success:
        return False

    # Update filename if needed
    new_path = file_path.parent / new_filename
    if new_path != file_path:
        if dry_run:
            print(f"🔄 Would rename: {file_path.name} → {new_filename}")
        else:
            if new_path.exists():
                print(f"⚠️  Target file exists, skipping rename: {new_filename}")
                return False

            try:
                file_path.rename(new_path)
                print(f"✅ Renamed: {file_path.name} → {new_filename}")
            except Exception as e:
                print(f"❌ Error renaming {file_path.name}: {e}")
                return False

    return True


def process_m3u8(m3u8_path: Path, dry_run: bool = False, force: bool = False) -> int:
    """Process M3U8 file and update audio files."""
    entries = parse_m3u8(m3u8_path)
    folder_path = m3u8_path.parent

    if not entries:
        print(f"❌ No entries found in M3U8 file: {m3u8_path}")
        return 0

    # Extract album name from folder or M3U8 filename
    album_name = m3u8_path.stem
    if album_name.endswith(".m3u8"):
        album_name = album_name[:-5]

    print(f"📋 Processing M3U8: {m3u8_path.name}")
    print(f"📁 Folder: {folder_path}")
    print(f"🎵 Album: {album_name}")
    print(f"📝 Entries: {len(entries)}")

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")

    updated_count = 0

    for i, (filename, title, duration) in enumerate(entries, 1):
        print(f"\n🎵 Entry {i}/{len(entries)}")
        print(f"📄 Playlist filename: {filename}")
        if title:
            print(f"🎼 Title: {title}")
        if duration:
            print(f"⏱️  Duration: {duration}")

        # Find the actual audio file (using position-based matching)
        audio_file = find_audio_file(folder_path, filename, i - 1)
        if not audio_file:
            print(f"❌ Audio file not found: {filename}")
            continue

        print(f"🎵 Found: {audio_file.name}")

        # Extract metadata from title
        artist, track_title = extract_metadata_from_title(title) if title else (None, None)

        # Extract filename from M3U8 entry (already has track number)
        m3u8_filename = filename
        m3u8_path = Path(m3u8_filename)

        # Use the M3U8 filename directly (it already has the correct format)
        new_filename = f"{m3u8_path.stem}{audio_file.suffix}"

        # Extract track number and title from M3U8 filename for metadata
        filename_pattern = re.match(r"^(\d{1,2})\s*-\s*(.+)", m3u8_path.stem)
        if filename_pattern:
            track_num = filename_pattern.group(1).zfill(2)  # Ensure 2-digit format
            m3u8_full_title = filename_pattern.group(2)

            # Parse artist and title from the M3U8 filename part
            m3u8_artist, m3u8_track_title = extract_metadata_from_title(m3u8_full_title)

            # Use M3U8 artist if found, otherwise keep original from EXTINF
            if m3u8_artist:
                artist = m3u8_artist
            # Use M3U8 title if found, otherwise keep original from EXTINF
            if m3u8_track_title:
                track_title = m3u8_track_title
        else:
            track_num = f"{i:02d}"
            m3u8_full_title = m3u8_path.stem

        # Fallback: if no artist found, use folder structure
        if not artist:
            # Get artist from parent folder name
            parent_folder = folder_path.parent.name  # e.g., "Various" or "The Beatles"
            artist = parent_folder

        # Fallback: if no title found, use filename without track number
        if not track_title:
            if filename_pattern:
                track_title = filename_pattern.group(2)  # Use whatever was after track number
            else:
                track_title = m3u8_path.stem  # Use full filename

        print(f"🔄 New filename: {new_filename}")
        if artist:
            print(f"🎤 Artist: {artist}")
        if track_title:
            print(f"🎵 Title: {track_title}")

        # Check if file already has correct metadata
        if not force and not dry_run:
            # Quick check - skip if already has title and matches
            try:
                if audio_file.suffix.lower() == ".flac":
                    audio = FLAC(audio_file)
                    current_title = audio.get("TITLE", [""])[0]
                    current_artist = audio.get("ARTIST", [""])[0]
                elif audio_file.suffix.lower() == ".mp3":
                    audio = MP3(audio_file)
                    current_title = str(audio.tags.get("TIT2", [""])[0]) if audio.tags else ""
                    current_artist = str(audio.tags.get("TPE1", [""])[0]) if audio.tags else ""
                else:
                    current_title = ""
                    current_artist = ""

                if (
                    current_title == track_title
                    and (not artist or current_artist == artist)
                    and audio_file.name == new_filename
                ):
                    print("⏭️  Skipping (already correct)")
                    continue
            except Exception:
                pass  # Fall through to update if there's an error reading tags

        # Update the file
        if update_audio_file(
            audio_file,
            new_filename,
            artist,
            track_title,
            album_name,
            track_num,
            dry_run,
        ):
            updated_count += 1

    return updated_count


def find_m3u8_in_folder(folder_path: Path) -> Optional[Path]:
    """Find M3U8 file in a folder."""
    m3u8_files = list(folder_path.glob("*.m3u8"))
    if not m3u8_files:
        return None

    # Prefer the one with the same name as the folder
    folder_name_m3u = folder_path / (folder_path.name + ".m3u8")
    if folder_name_m3u in m3u8_files:
        return folder_name_m3u

    # Return the first one found
    return m3u8_files[0]


def main():
    parser = argparse.ArgumentParser(
        description="Update filenames and metadata from M3U8 playlists"
    )
    parser.add_argument("path", help="Path to M3U8 file or folder containing M3U8")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force updates even if metadata appears correct",
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)

    # Determine if path is M3U8 file or folder
    if path.is_file() and path.suffix.lower() == ".m3u8":
        m3u8_files = [path]
    elif path.is_dir():
        m3u8_file = find_m3u8_in_folder(path)
        if not m3u8_file:
            print(f"❌ No M3U8 file found in folder: {path}")
            sys.exit(1)
        m3u8_files = [m3u8_file]
    else:
        print(f"❌ Path must be an M3U8 file or folder: {path}")
        sys.exit(1)

    total_updated = 0
    for m3u8_file in m3u8_files:
        updated = process_m3u8(m3u8_file, args.dry_run, args.force)
        total_updated += updated

    print("\n📊 Summary:")
    if args.dry_run:
        print(f"🔍 Would update {total_updated} files")
    else:
        print(f"✅ Updated {total_updated} files")

    if args.dry_run:
        print("💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    sys.exit(main())
