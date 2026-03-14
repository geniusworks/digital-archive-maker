#!/usr/bin/env python3
"""Check album folders for basic integrity.

Validates:
1. `cover.jpg` exists and is exactly 1000x1000 pixels.
2. Track listings in `*.m3u8` playlists match `.flac` files present in the folder.
3. `_cover.jpg` does not exist alongside `cover.jpg`.

By default the script scans the CDs directory under LIBRARY_ROOT.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

DEFAULT_LIBRARY_ROOT = os.getenv("LIBRARY_ROOT") or "/Library"


@dataclass
class AlbumReport:
    path: Path
    issues: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check album folders for cover art and playlist integrity."
    )
    parser.add_argument(
        "root",
        nargs="?",
        help="Root directory containing album folders (default: LIBRARY_ROOT/CDs)",
    )
    parser.add_argument(
        "--albums",
        nargs="*",
        help="Specific album folders to check (absolute or relative to root)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum directory depth relative to root to scan (default: unlimited)",
    )
    parser.add_argument(
        "--require-cover",
        action="store_true",
        help="Fail when cover.jpg is missing (default behaviour)",
    )
    parser.add_argument(
        "--show-ok",
        action="store_true",
        help="Display OK results (default: only failures are printed)",
    )
    parser.add_argument(
        "--fix-covers",
        action="store_true",
        help="Resize cover.jpg images that are not 1000x1000 pixels (within 5% tolerance)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes (use with --fix-covers)",
    )
    parser.add_argument(
        "--get-covers",
        action="store_true",
        help="Download missing or undersized cover.jpg images as _cover.jpg",
    )
    parser.add_argument(
        "--size-tolerance",
        type=float,
        default=5.0,
        help="Size tolerance percentage for auto-fixing covers (default: 5%%)",
    )
    parser.set_defaults(require_cover=True)
    return parser.parse_args(argv)


def get_default_root() -> Path:
    library_root = os.environ.get("LIBRARY_ROOT", DEFAULT_LIBRARY_ROOT)
    return Path(library_root) / "CDs"


def collect_explicit_albums(root: Path, entries: List[str]) -> List[Path]:
    dirs: List[Path] = []
    for entry in entries:
        album_path = Path(entry)
        if not album_path.is_absolute():
            album_path = (root / album_path).resolve()
        if not album_path.exists():
            print(f"Warning: album path not found: {album_path}", file=sys.stderr)
            continue
        if not album_path.is_dir():
            print(
                f"Warning: album path is not a directory: {album_path}",
                file=sys.stderr,
            )
            continue
        dirs.append(album_path)
    return sorted(set(dirs))


def iter_album_dirs(root: Path, max_depth: Optional[int]) -> Iterator[Path]:
    if not root.exists():
        print(f"Error: root directory not found: {root}", file=sys.stderr)
        return iter(())

    root_depth = len(root.resolve().parts)

    def within_depth(path: Path) -> bool:
        if max_depth is None:
            return True
        return len(path.parts) - root_depth <= max_depth

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if not within_depth(current.relative_to(root) if current != root else Path(".")):
            dirnames[:] = []
            continue
        # Skip the root itself unless it contains FLAC files directly.
        if current == root and not any(fn.lower().endswith(".flac") for fn in filenames):
            continue
        yield current


def collect_album_dirs(
    root: Path, explicit: Optional[List[str]], max_depth: Optional[int]
) -> List[Path]:
    if explicit:
        return collect_explicit_albums(root, explicit)

    albums = list(iter_album_dirs(root, max_depth))
    albums.sort()
    return albums


def download_cover_image(album: Path, dry_run: bool = False) -> bool:
    """Download album cover from Cover Art Archive and save as _cover.jpg."""
    try:
        import urllib.parse

        import requests
        from mutagen.flac import FLAC
    except ImportError as e:
        print(f"  Error: Missing required library: {e}")
        print("  Install with: pip install requests mutagen")
        return False

    # Get first FLAC file to extract metadata
    flac_files = list(album.glob("*.flac"))
    if not flac_files:
        print(f"  Error: No FLAC files found in {album}")
        return False

    try:
        audio = FLAC(flac_files[0])
        artist = audio.get("artist", [""])[0]
        album_name = audio.get("album", [""])[0]

        if not artist or not album_name:
            print(f"  Error: Missing artist or album metadata in {flac_files[0].name}")
            return False
    except Exception as e:
        print(f"  Error: Failed to read metadata from {flac_files[0].name}: {e}")
        return False

    if dry_run:
        print(f"  Would download cover for: {artist} - {album_name}")
        return True

    # Search MusicBrainz for release ID (like fix_album_covers.sh)
    try:
        # URL-encode artist and album names
        q_artist = urllib.parse.quote(artist)
        q_album = urllib.parse.quote(album_name)

        # Query MusicBrainz API
        mb_url = (
            f"https://musicbrainz.org/ws/2/release/?query=artist:{q_artist}"
            f"%20release:{q_album}&fmt=json&limit=1"
        )

        response = requests.get(mb_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data.get("releases") or len(data["releases"]) == 0:
            print(f"  Error: No MusicBrainz release found for {artist} - {album_name}")
            return False

        release_id = data["releases"][0]["id"]

    except Exception as e:
        print(f"  Error: Failed to query MusicBrainz for {artist} - {album_name}: {e}")
        return False

    # Download from Cover Art Archive (like fix_album_covers.sh)
    try:
        cover_url = f"https://coverartarchive.org/release/{release_id}/front.jpg"

        # Download to temp file first
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
            tmp_path = tmpfile.name

        try:
            response = requests.get(cover_url, timeout=30)
            response.raise_for_status()

            with open(tmp_path, "wb") as f:
                f.write(response.content)

            # Verify it's a valid JPEG
            try:
                from PIL import Image

                with Image.open(tmp_path) as img:
                    img.verify()
            except Exception:
                print(f"  Error: Downloaded file is not a valid image for {artist} - {album_name}")
                os.unlink(tmp_path)
                return False

            # Resize if larger than 1000x1000 (like fix_album_covers.sh)
            try:
                from PIL import Image

                with Image.open(tmp_path) as img:
                    if img.width > 1000 or img.height > 1000:
                        img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                        img.save(tmp_path, "JPEG", quality=95)
            except ImportError:
                # Pillow not available, skip resizing
                pass
            except Exception as e:
                print(f"  Warning: Failed to resize image for {artist} - {album_name}: {e}")

            # Move to final location
            cover_path = album / "_cover.jpg"
            os.rename(tmp_path, cover_path)

            print(f"  Downloaded: {artist} - {album_name} -> _cover.jpg")
            return True

        except Exception as e:
            print(f"  Error: Failed to download cover for {artist} - {album_name}: {e}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False

    except Exception as e:
        print(f"  Error: Failed to download cover for {artist} - {album_name}: {e}")
        return False


def resize_cover_image(cover_path: Path, dry_run: bool = False) -> bool:
    """Resize cover image to exactly 1000x1000 pixels using ImageMagick or Pillow."""
    target_size = (1000, 1000)

    if dry_run:
        width_height = get_image_size(cover_path)
        if width_height:
            print(
                f"  Would fix: {cover_path.name} (resize from {width_height[0]}x"
                f"{width_height[1]} to 1000x1000)"
            )
        else:
            print(f"  Would fix: {cover_path.name} (resize to 1000x1000)")
        return True

    # Try ImageMagick first (better quality)
    magick_cmds = [
        [
            "magick",
            "convert",
            str(cover_path),
            "-resize",
            f"{target_size[0]}x{target_size[1]}!",
            str(cover_path),
        ],
        [
            "convert",
            "-resize",
            f"{target_size[0]}x{target_size[1]}!",
            str(cover_path),
            str(cover_path),
        ],
    ]

    for cmd in magick_cmds:
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"  Fixed: {cover_path.name} (resized to 1000x1000)")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    # Fall back to Pillow
    try:
        from PIL import Image

        with Image.open(cover_path) as img:
            resized = img.resize(target_size, Image.Resampling.LANCZOS)
            resized.save(cover_path, quality=95)
            print(f"  Fixed: {cover_path.name} (resized to 1000x1000)")
            return True
    except Exception as e:
        print(f"  Error: Failed to resize {cover_path.name}: {e}")
        return False


def check_cover(
    album: Path,
    fix_covers: bool = False,
    dry_run: bool = False,
    size_tolerance: float = 5.0,
    get_covers: bool = False,
) -> Optional[str]:
    cover = album / "cover.jpg"
    temp_cover = album / "_cover.jpg"

    if not cover.exists():
        if get_covers:
            # Skip if _cover.jpg already exists
            if temp_cover.exists():
                if dry_run:
                    print("  Would skip: _cover.jpg already exists")
                return None
            if download_cover_image(album, dry_run=dry_run):
                return None  # Downloaded or would be downloaded successfully
            else:
                return "Failed to download cover.jpg"
        else:
            return "cover.jpg is missing"

    width_height = get_image_size(cover)
    if width_height is None:
        return "Unable to determine size of cover.jpg"

    if width_height != (1000, 1000):
        if fix_covers:
            w, h = width_height

            # Case 1: Near 1000x1000 (within size tolerance) - resize to exact 1000x1000
            tolerance_low = 1000 * (1 - size_tolerance / 100)
            tolerance_high = 1000 * (1 + size_tolerance / 100)

            if tolerance_low <= w <= tolerance_high and tolerance_low <= h <= tolerance_high:
                if resize_cover_image(cover, dry_run=dry_run):
                    return None  # Fixed or would be fixed successfully
                else:
                    return f"Failed to resize cover.jpg from {width_height[0]}x{width_height[1]}"

            # Case 2: Both dimensions larger than 1000 and within 5% aspect ratio of each other
            elif w > 1000 and h > 1000:
                aspect_ratio = w / h
                aspect_diff = abs(aspect_ratio - 1.0) * 100  # Percentage difference from square

                if aspect_diff <= size_tolerance:
                    if resize_cover_image(cover, dry_run=dry_run):
                        return None  # Fixed or would be fixed successfully
                    else:
                        return (
                            f"Failed to resize cover.jpg from {width_height[0]}x{width_height[1]}"
                        )
                else:
                    if dry_run:
                        print(
                            f"  Would skip: {cover.name} (aspect ratio {aspect_ratio:.3f} outside "
                            f"{size_tolerance}% tolerance)"
                        )
                    return (
                    f"cover.jpg is {width_height[0]}x{width_height[1]} (aspect ratio {aspect_ratio:.3f} "
                    f"outside {size_tolerance}% tolerance)"
                )
            else:
                # Case 3: Undersized or other covers - skip resizing
                if dry_run:
                    print(
                        f"  Would skip: {cover.name} (size {width_height[0]}x"
                        f"{width_height[1]} outside tolerance)"
                    )
                return f"cover.jpg is {width_height[0]}x{width_height[1]} (expected 1000x1000, outside tolerance)"
        elif get_covers:
            # Handle get_covers when fix_covers is False
            w, h = width_height

            # Check if cover is too small for --fix-covers to handle
            tolerance_low = 1000 * (1 - size_tolerance / 100)
            tolerance_high = 1000 * (1 + size_tolerance / 100)

            # Download if cover is undersized (not within tolerance and not both >1000)
            is_undersized = not (
                tolerance_low <= w <= tolerance_high and tolerance_low <= h <= tolerance_high
            ) and not (w > 1000 and h > 1000)

            if is_undersized:
                # Skip if _cover.jpg already exists
                if temp_cover.exists():
                    if dry_run:
                        print("  Would skip: _cover.jpg already exists")
                    return None
                if download_cover_image(album, dry_run=dry_run):
                    return None  # Downloaded or would be downloaded successfully
                else:
                    return (
                        f"Failed to download better cover for {width_height[0]}x{width_height[1]}"
                    )
            else:
                # Cover is within --fix-covers range, so don't download
                return None
        else:
            return f"cover.jpg is {width_height[0]}x{width_height[1]} (expected 1000x1000)"

    extra_cover = album / "_cover.jpg"
    if extra_cover.exists():
        return "Found _cover.jpg (should be removed after renaming)"
    return None


def get_image_size(path: Path) -> Optional[Tuple[int, int]]:
    # Try ImageMagick (magick identify)
    identify_cmds = [
        ["magick", "identify", "-format", "%wx%h", str(path)],
        ["identify", "-format", "%wx%h", str(path)],
    ]
    for cmd in identify_cmds:
        try:
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            continue
        except subprocess.CalledProcessError:
            continue
        else:
            output = completed.stdout.strip()
            if "x" in output:
                w_str, h_str = output.split("x", 1)
                if w_str.isdigit() and h_str.isdigit():
                    return int(w_str), int(h_str)
    # Fall back to Pillow if available
    try:
        from PIL import Image  # type: ignore
    except ModuleNotFoundError:
        return None

    try:
        with Image.open(path) as img:
            return img.width, img.height
    except Exception:
        return None


def read_m3u_playlist(m3u_path: Path) -> List[Path]:
    tracks: List[Path] = []
    try:
        with m3u_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                tracks.append((m3u_path.parent / line).resolve())
    except UnicodeDecodeError:
        with m3u_path.open("r", encoding="latin-1") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                tracks.append((m3u_path.parent / line).resolve())
    return tracks


def check_playlist(album: Path) -> Optional[str]:
    playlists = sorted(album.glob("*.m3u8"))
    if not playlists:
        playlists = sorted(album.glob("*.m3u"))
        if not playlists:
            return "No .m3u8 (or legacy .m3u) playlist found"

    issues: List[str] = []
    flac_files = sorted(p.resolve() for p in album.glob("*.flac"))
    flac_set = set(flac_files)

    for m3u in playlists:
        playlist_tracks = read_m3u_playlist(m3u)
        playlist_set = set(playlist_tracks)

        missing_files = [p for p in playlist_tracks if not p.exists()]
        extra_tracks = [p for p in playlist_tracks if p.suffix.lower() != ".flac"]
        unlisted_flacs = flac_set - playlist_set
        missing_in_playlist = playlist_set - flac_set

        if missing_files:
            issues.append(
                f"{m3u.name}: referenced files missing: "
                + ", ".join(str(p.relative_to(album)) for p in missing_files)
            )
        if extra_tracks:
            issues.append(
                f"{m3u.name}: contains non-FLAC entries: "
                + ", ".join(str(p.relative_to(album)) for p in extra_tracks)
            )
        if missing_in_playlist:
            issues.append(
                f"{m3u.name}: entries not matching FLACs: "
                + ", ".join(str(p.relative_to(album)) for p in missing_in_playlist)
            )
        if unlisted_flacs:
            issues.append(
                f"{m3u.name}: FLAC files missing from playlist: "
                + ", ".join(str(p.relative_to(album)) for p in unlisted_flacs)
            )

    if issues:
        return " | ".join(issues)
    return None


def has_flac_files(album: Path) -> bool:
    return any(album.glob("*.flac"))


def check_album(
    album: Path,
    require_cover: bool = True,
    fix_covers: bool = False,
    dry_run: bool = False,
    size_tolerance: float = 5.0,
    get_covers: bool = False,
) -> AlbumReport:
    report = AlbumReport(path=album)

    if not has_flac_files(album):
        # Skip directories without FLAC files.
        return report

    if require_cover:
        cover_issue = check_cover(
            album,
            fix_covers=fix_covers,
            dry_run=dry_run,
            size_tolerance=size_tolerance,
            get_covers=get_covers,
        )
        if cover_issue:
            report.issues.append(cover_issue)

    playlist_issue = check_playlist(album)
    if playlist_issue:
        report.issues.append(playlist_issue)

    return report


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    root = Path(args.root).resolve() if args.root else get_default_root()
    albums = collect_album_dirs(root, args.albums, args.max_depth)
    if not albums:
        print("No album directories to check.")
        return 1

    total = 0
    failures = 0
    for album in albums:
        report = check_album(
            album,
            require_cover=args.require_cover,
            fix_covers=args.fix_covers,
            dry_run=args.dry_run,
            size_tolerance=args.size_tolerance,
            get_covers=args.get_covers,
        )
        if not has_flac_files(album):
            continue
        total += 1
        if report.ok:
            if args.show_ok:
                print(f"[OK] {album}")
        else:
            failures += 1
            print(f"[FAIL] {album}")
            for issue in report.issues:
                print(f"  - {issue}")

    if total == 0:
        print("No album folders with FLAC files found.")
        return 1

    print(f"\nChecked {total} album folders. Failures: {failures}.")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
