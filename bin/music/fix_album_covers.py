#!/usr/bin/env python3
"""
Fetch missing cover art for albums using MusicBrainz and Cover Art Archive.

Usage:
    python3 fix_album_covers.py [/path/to/album/or/library]
    Examples:
        python3 fix_album_covers.py /Volumes/Data/Media/Library/CDs       # full scan
        python3 fix_album_covers.py /Volumes/Data/Media/Library/CDs/U2/The Joshua Tree  # specific album
    Defaults to current directory if no argument is given.
"""

import argparse
import os
import sys
import subprocess
import urllib.parse
import json
import tempfile
from pathlib import Path
from typing import Optional


def require_command(cmd: str) -> None:
    """Check if a required command is available."""
    result = subprocess.run(['which', cmd], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: Required command '{cmd}' not installed. Please install it.", file=sys.stderr)
        sys.exit(1)


def url_encode(text: str) -> str:
    """URL-encode text for use in URLs."""
    return urllib.parse.quote(text, safe='')


def process_album_dir(album_dir: Path) -> None:
    """Process a single album directory for missing cover art."""
    if (album_dir / "cover.jpg").exists():
        print(f"✔ Already has cover: {album_dir}")
        return
    
    album_name = album_dir.name
    artist_name = album_dir.parent.name
    
    # Skip invalid album names
    if artist_name in ("Unknown", "Untitled") or album_name in ("Unknown", "Untitled"):
        print(f"✘ Skipping invalid: {artist_name} - {album_name}")
        return
    
    print(f"→ Searching cover for: {artist_name} - {album_name}")
    
    # URL-encode for query
    q_artist = url_encode(artist_name)
    q_album = url_encode(album_name)
    
    # Query MusicBrainz
    mb_url = f"https://musicbrainz.org/ws/2/release/?query=artist:{q_artist}%20release:{q_album}&fmt=json&limit=1"
    try:
        result = subprocess.run(['curl', '-s', mb_url], capture_output=True, text=True, check=True)
        release_json = result.stdout
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"  ✘ Error querying MusicBrainz: {e}")
        return
    
    releases = json.loads(release_json).get('releases') or []
    release_id = releases[0].get('id', '') if releases else ''
    
    if not release_id:
        print("  ✘ No MusicBrainz release found.")
        return
    
    # Cover Art Archive URL
    cover_url = f"https://coverartarchive.org/release/{release_id}/front.jpg"
    target_path = album_dir / "cover.jpg"
    
    # Download to a temp file first. Use delete=False so we can move the file.
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_name = tmp_file.name

        # Download the cover
        dl = subprocess.run(
            ['curl', '-sSL', '--fail', '-o', tmp_name, cover_url],
            capture_output=True,
            text=True,
        )
        if dl.returncode != 0:
            print("  ✘ Cover not found on Cover Art Archive.")
            return

        # Check if it's a valid JPEG (best-effort)
        file_cmd = subprocess.run(['file', '--mime-type', tmp_name], capture_output=True, text=True)
        if 'jpeg' not in (file_cmd.stdout or '').lower():
            print("  ✘ Downloaded file is not a valid JPEG")
            return

        # Resize with ImageMagick if available
        magick_check = subprocess.run(['which', 'magick'], capture_output=True, text=True)
        if magick_check.returncode == 0:
            subprocess.run(
                ['magick', tmp_name, '-resize', '1000x1000>', tmp_name],
                capture_output=True,
                text=True,
            )

        os.replace(tmp_name, target_path)
        tmp_name = None
        print(f"  ✔ Downloaded cover: {target_path}")
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def scan_library(search_path: Path) -> None:
    """Scan library recursively for albums missing cover art."""
    # If this directory itself looks like an album dir (contains FLACs), process directly.
    if any(search_path.glob('*.flac')):
        process_album_dir(search_path)
        return

    # Otherwise, treat it as a library root / higher-level folder.
    else:
        # It's a library root or higher-level folder — scan recursively for album dirs missing cover.jpg
        print(f"📂 Scanning for albums missing cover.jpg under: {search_path}")
        found_any = False
        
        for album_dir in search_path.rglob('*/'):
            if album_dir.is_dir():
                # Check if directory contains FLAC files
                if list(album_dir.glob('*.flac')):
                    # Check if cover.jpg is missing
                    if not (album_dir / 'cover.jpg').exists():
                        found_any = True
                        process_album_dir(album_dir)
        
        if not found_any:
            print("✔ No album folders missing cover.jpg found.")


def main():
    parser = argparse.ArgumentParser(description="Fetch missing cover art for albums")
    parser.add_argument("search_path", nargs="?", help="Path to album or library root directory")
    args = parser.parse_args()
    
    search_path = Path(args.search_path) if args.search_path else Path('.')
    
    if not search_path.exists():
        print(f"Error: '{search_path}' is not a valid directory")
        sys.exit(1)
    
    if search_path.is_dir():
        scan_library(search_path)
    else:
        print(f"Error: '{search_path}' is not a directory")


if __name__ == "__main__":
    main()
