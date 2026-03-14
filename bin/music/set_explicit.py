#!/usr/bin/env python3
"""
Set EXPLICIT tag for FLAC files.

Usage:
    python3 set_explicit.py <path> <value> [--album]
    path: path to FLAC file or album directory
    value: Yes, No, or Unknown
    --album: apply to all FLAC files in directory
"""

import argparse
import subprocess
import sys
from pathlib import Path


def require_command(cmd: str) -> None:
    """Check if a required command is available."""
    result = subprocess.run(["which", cmd], capture_output=True, text=True)
    if result.returncode != 0:
        print(
            f"Error: Required command '{cmd}' not found. Please install it.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_explicit_tag(flac_file: Path) -> str:
    """Get current EXPLICIT tag value from FLAC file."""
    try:
        result = subprocess.run(
            ["metaflac", "--show-tag=EXPLICIT", str(flac_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        # Extract value from output like "EXPLICIT=Yes"
        for line in result.stdout.strip().split("\n"):
            if line.startswith("EXPLICIT="):
                return line.split("=", 1)[1]
        return "None"
    except subprocess.CalledProcessError:
        return "None"


def set_explicit_tag(flac_file: Path, value: str) -> str:
    """Set EXPLICIT tag for a FLAC file."""
    old_value = get_explicit_tag(flac_file)

    try:
        subprocess.run(
            ["metaflac", "--set-tag=EXPLICIT=" + value, str(flac_file)],
            capture_output=True,
            check=True,
        )
        return old_value
    except subprocess.CalledProcessError as e:
        print(f"Error setting tag for {flac_file}: {e}", file=sys.stderr)
        raise


def process_album(album_dir: Path, value: str) -> int:
    """Process all FLAC files in an album directory."""
    if not album_dir.is_dir():
        print(f"Error: {album_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Setting EXPLICIT={value} for all FLAC files in: {album_dir}")

    flac_files = list(album_dir.glob("*.flac"))
    count = 0

    for flac_file in flac_files:
        old_value = set_explicit_tag(flac_file, value)
        print(f"  {flac_file.name}: {old_value} → {value}")
        count += 1

    print(f"Updated {count} files")
    return count


def process_single_file(flac_file: Path, value: str) -> None:
    """Process a single FLAC file."""
    if not flac_file.is_file() or flac_file.suffix.lower() != ".flac":
        print(
            f"Error: {flac_file} is not a FLAC file (use --album for directories)",
            file=sys.stderr,
        )
        sys.exit(1)

    old_value = set_explicit_tag(flac_file, value)
    print(f"{flac_file.name}: {old_value} → {value}")


def main():
    parser = argparse.ArgumentParser(
        description="Set EXPLICIT tag for FLAC files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s song.flac Yes
  %(prog)s /path/to/album No --album
  %(prog)s /path/to/album Unknown --album
        """,
    )
    parser.add_argument("path", help="Path to FLAC file or album directory")
    parser.add_argument("value", choices=["Yes", "No", "Unknown"], help="EXPLICIT tag value")
    parser.add_argument(
        "--album",
        action="store_true",
        help="Apply to all FLAC files in directory",
    )
    args = parser.parse_args()

    # Check for metaflac
    require_command("metaflac")

    path = Path(args.path)

    if args.album:
        process_album(path, args.value)
    else:
        process_single_file(path, args.value)


if __name__ == "__main__":
    main()
