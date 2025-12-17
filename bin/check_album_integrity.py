#!/usr/bin/env python3
"""Check album folders for basic integrity.

Validates:
1. `cover.jpg` exists and is exactly 1000x1000 pixels.
2. Track listings in `*.m3u8` playlists match `.flac` files present in the folder.
3. `_cover.jpg` does not exist alongside `cover.jpg`.

By default the script scans the CDs directory under `RIPS_ROOT` (default `/Volumes/Data/Media/Rips/CDs`).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

DEFAULT_RIPS_ROOT = "/Volumes/Data/Media/Rips"


@dataclass
class AlbumReport:
    path: Path
    issues: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check album folders for cover art and playlist integrity.")
    parser.add_argument(
        "root",
        nargs="?",
        help="Root directory containing album folders (default: RIPS_ROOT/CDs)",
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
    parser.set_defaults(require_cover=True)
    return parser.parse_args(argv)


def get_default_root() -> Path:
    rips_root = os.environ.get("RIPS_ROOT", DEFAULT_RIPS_ROOT)
    return Path(rips_root) / "CDs"


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
            print(f"Warning: album path is not a directory: {album_path}", file=sys.stderr)
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


def collect_album_dirs(root: Path, explicit: Optional[List[str]], max_depth: Optional[int]) -> List[Path]:
    if explicit:
        return collect_explicit_albums(root, explicit)

    albums = list(iter_album_dirs(root, max_depth))
    albums.sort()
    return albums


def check_cover(album: Path) -> Optional[str]:
    cover = album / "cover.jpg"
    if not cover.exists():
        return "cover.jpg is missing"

    width_height = get_image_size(cover)
    if width_height is None:
        return "Unable to determine size of cover.jpg"

    if width_height != (1000, 1000):
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


def check_album(album: Path, require_cover: bool = True) -> AlbumReport:
    report = AlbumReport(path=album)

    if not has_flac_files(album):
        # Skip directories without FLAC files.
        return report

    if require_cover:
        cover_issue = check_cover(album)
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
        report = check_album(album, require_cover=args.require_cover)
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
