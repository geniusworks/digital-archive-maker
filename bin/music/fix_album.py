#!/usr/bin/env python3
"""
Normalize and complete an album folder structure.

Usage:
    python3 fix_album.py /path/to/Artist/Album

This script:
1. Looks up the album on MusicBrainz
2. Verifies file count matches track count
3. Renames FLAC files to "NN - Title.flac" format
4. Creates an M3U8 playlist
5. Runs metadata and cover art fix scripts
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import List


def require_command(cmd: str) -> None:
    """Check if a required command is available."""
    result = subprocess.run(["which", cmd], capture_output=True, text=True)
    if result.returncode != 0:
        print(
            f"Error: Required command '{cmd}' not found. Please install it.",
            file=sys.stderr,
        )
        sys.exit(1)


def url_encode(text: str) -> str:
    """URL-encode text for use in URLs."""
    return urllib.parse.quote(text, safe="")


def query_musicbrainz(artist: str, album: str) -> dict:
    """Query MusicBrainz for release information."""
    q_artist = url_encode(artist)
    q_album = url_encode(album)

    print(f"Searching MusicBrainz for {artist} - {album}...")

    # Query for releases
    mb_url = f"https://musicbrainz.org/ws/2/release/?query=artist:{q_artist}%20release:{q_album}&fmt=json&limit=1"
    try:
        result = subprocess.run(["curl", "-s", mb_url], capture_output=True, text=True, check=True)
        releases = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error querying MusicBrainz: {e}", file=sys.stderr)
        sys.exit(1)

    if not releases.get("releases"):
        print("No matching release found.")
        sys.exit(1)

    release = releases["releases"][0]
    release_id = release["id"]

    # Get tracklist
    tracklist_url = f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json"
    try:
        result = subprocess.run(
            ["curl", "-s", tracklist_url],
            capture_output=True,
            text=True,
            check=True,
        )
        tracklist = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONError) as e:
        print(f"Error getting tracklist: {e}", file=sys.stderr)
        sys.exit(1)

    return {"release_id": release_id, "tracklist": tracklist}


def get_track_titles(tracklist: dict) -> List[str]:
    """Extract track titles from MusicBrainz tracklist."""
    titles = []
    for medium in tracklist.get("media", []):
        for track in medium.get("tracks", []):
            title = track.get("title", "")
            if title:
                titles.append(title)
    return titles


def clean_filename(title: str) -> str:
    """Clean title for use in filename."""
    # Replace forward slashes with underscores and remove non-alphanumeric except spaces and hyphens
    return title.replace("/", "_").replace("-", " - ").strip().replace("  -  ", " - ")


def rename_files_and_create_playlist(titles: List[str], album_path: Path) -> Path:
    """Rename FLAC files and create M3U8 playlist."""
    flac_files = sorted(album_path.glob("*.flac"))

    if len(flac_files) != len(titles):
        print(f"File count ({len(flac_files)}) does not match track count ({len(titles)}).")
        sys.exit(1)

    album_name = album_path.name
    playlist_file = album_path / f"{album_name}.m3u8"

    # Create M3U8 file
    with open(playlist_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for i, (flac_file, title) in enumerate(zip(flac_files, titles)):
            num = f"{i + 1:02d}"
            clean_title = clean_filename(title)
            new_name = f"{num} - {clean_title}.flac"

            if flac_file.name != new_name:
                new_path = flac_file.parent / new_name
                flac_file.rename(new_path)
                print(f"Renamed: {flac_file.name} -> {new_name}")
                flac_file = new_path

            f.write(f"{flac_file.name}\n")

    print(f"Playlist created: {playlist_file}")
    return playlist_file


def clean_old_playlists(album_path: Path) -> None:
    """Remove old/placeholder playlist files."""
    old_files = ["Unknown Album.m3u", "Unknown Album.m3u8"]
    for old_file in old_files:
        old_path = album_path / old_file
        if old_path.exists():
            old_path.unlink()
            print(f"Removed stale playlist: {old_file}")


def run_script(script_path: Path, album_path: str, *args: List[str]) -> None:
    """Run a helper script."""
    if not script_path.exists():
        print(
            f"Warning: Script {script_path} not found, skipping.",
            file=sys.stderr,
        )
        return

    cmd = [str(script_path), album_path] + list(args)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path.name}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Normalize and complete an album folder structure")
    parser.add_argument("album_path", help="Path to the album folder")
    args = parser.parse_args()

    album_path = Path(args.album_path)

    if not album_path.exists() or not album_path.is_dir():
        print(f"Error: {album_path} is not a valid directory")
        sys.exit(1)

    # Extract artist and album name from folder path
    artist_name = album_path.parent.name
    album_name = album_path.name

    print(f"Processing album: {artist_name} - {album_name}")

    # Query MusicBrainz
    mb_data = query_musicbrainz(artist_name, album_name)
    titles = get_track_titles(mb_data["tracklist"])

    # Change to album directory
    original_dir = Path.cwd()
    try:
        os.chdir(album_path)

        # Rename files and create playlist
        playlist_file = rename_files_and_create_playlist(titles, album_path)

        # Clean up old playlists
        clean_old_playlists(album_path)

    finally:
        os.chdir(original_dir)

    # Get script directory (parent of music/ directory)
    script_dir = Path(__file__).parent.parent.parent

    # Run metadata fix script
    print("Running metadata fix script...")
    run_script(script_dir / "music" / "fix_metadata.py", str(album_path), "--fix")

    # Run cover art fix script
    print("Running cover art fix script...")
    run_script(script_dir / "music" / "fix_album_covers.py", str(album_path))

    print("Album processing complete!")


if __name__ == "__main__":
    main()
