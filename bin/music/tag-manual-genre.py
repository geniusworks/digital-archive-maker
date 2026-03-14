#!/usr/bin/env python3
"""Manual genre tagging for FLAC files.

This script allows manual genre assignment to FLAC files with validation
against the curated whitelist from update-genre-mb.py.

Usage:
    python3 bin/music/tag-manual-genre.py /path/to/file.flac --genre "jazz"
    python3 bin/music/tag-manual-genre.py /path/to/album --genre "rock" --recursive
    python3 bin/music/tag-manual-genre.py /path/to/music --genre "christmas" --recursive --dry-run
"""

import argparse
import sys
from pathlib import Path
from mutagen.flac import FLAC

# Import the same whitelist and validation functions from update-genre-mb.py
sys.path.append(str(Path(__file__).parent))
try:
    # Import the module using importlib to handle hyphenated filename
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "update_genre_mb", Path(__file__).parent / "update-genre-mb.py"
    )
    update_genre_mb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(update_genre_mb)

    # Get the functions and whitelist we need
    GENRE_WHITELIST = update_genre_mb.GENRE_WHITELIST
    _is_valid_genre = update_genre_mb._is_valid_genre
    _transform_genre = update_genre_mb._transform_genre
    write_flac_tags = update_genre_mb.write_flac_tags
    read_flac_tags = update_genre_mb.read_flac_tags
except Exception as e:
    print(f"Error importing from update-genre-mb.py: {e}")
    print("Make sure update-genre-mb.py exists and is accessible")
    sys.exit(1)


def validate_genre(genre: str) -> tuple[bool, str]:
    """Validate and transform a genre against the whitelist."""
    if not genre or not genre.strip():
        return False, "Empty genre"

    # Apply transformations first
    transformed = _transform_genre(genre.strip())

    # Check if valid
    if _is_valid_genre(transformed):
        return True, transformed
    else:
        return False, transformed


def process_file(
    flac_path: Path,
    genre: str,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> str:
    """Process a single FLAC file."""
    # Read current tags
    current_tags = read_flac_tags(flac_path)
    current_genre = current_tags.get("genre", "")

    # Validate genre
    is_valid, final_genre = validate_genre(genre)
    if not is_valid:
        print(f"  ❌ Invalid genre '{final_genre}' for {flac_path.name}")
        return "invalid"

    # Check if we need to update
    if current_genre == final_genre:
        if verbose:
            print(f"  ⏭️  Skipping {flac_path.name} (already has genre: {final_genre})")
        return "skipped"

    # Skip existing genre unless force
    if current_genre and not force:
        if verbose:
            print(f"  ⏭️  Skipping {flac_path.name} (existing genre: {current_genre})")
        return "skipped"

    # Show what we're doing
    if current_genre:
        if verbose:
            print(f"  🔄 Updating {flac_path.name}: {current_genre} → {final_genre}")
        else:
            print(f"  🔄 {flac_path.name}: {current_genre} → {final_genre}")
    else:
        if verbose:
            print(f"  ✅ Setting {flac_path.name}: {final_genre}")
        else:
            print(f"  ✅ {flac_path.name}: {final_genre}")

    # Dry run mode
    if dry_run:
        print(f"    [DRY RUN] Would set genre to '{final_genre}'")
        return "updated"

    # Actually write the tag
    new_tags = {"GENRE": final_genre}
    if write_flac_tags(flac_path, new_tags):
        return "updated"
    else:
        print(f"    ❌ Failed to update genre")
        return "failed"


def list_genres():
    """List all valid genres from the whitelist."""
    print("Valid genres (whitelist):")
    print("=" * 40)
    for genre in sorted(GENRE_WHITELIST):
        print(f"  {genre}")
    print(f"\nTotal: {len(GENRE_WHITELIST)} genres")


def main():
    parser = argparse.ArgumentParser(description="Manual genre tagging for FLAC files")
    parser.add_argument("path", help="FLAC file or folder to process")
    parser.add_argument("--genre", required=True, help="Genre to assign (must be in whitelist)")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--force", action="store_true", help="Overwrite existing genre tags")
    parser.add_argument(
        "--list-genres",
        action="store_true",
        help="List all valid genres and exit",
    )

    args = parser.parse_args()

    # List genres and exit
    if args.list_genres:
        list_genres()
        return

    # Validate the genre first
    is_valid, final_genre = validate_genre(args.genre)
    if not is_valid:
        print(f"❌ Invalid genre: '{final_genre}'")
        print(f"Use --list-genres to see all valid genres")
        sys.exit(1)

    # Check path exists
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"❌ Path does not exist: {path}")
        sys.exit(1)

    # Find FLAC files
    if path.is_file():
        if path.suffix.lower() != ".flac":
            print(f"❌ Not a FLAC file: {path}")
            sys.exit(1)
        flac_files = [path]
    elif path.is_dir():
        if args.recursive:
            flac_files = list(path.rglob("*.flac"))
        else:
            flac_files = list(path.glob("*.flac"))
    else:
        print(f"❌ Path is neither file nor directory: {path}")
        sys.exit(1)

    if not flac_files:
        print(f"❌ No FLAC files found in: {path}")
        sys.exit(1)

    print(f"🎵 Manual genre tagging: {final_genre}")
    print(f"📁 Processing {len(flac_files)} FLAC files...")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    if args.force:
        print("💪 FORCE MODE - Will overwrite existing genres")

    # Process files
    results = {"updated": 0, "skipped": 0, "invalid": 0, "failed": 0}

    for flac_file in sorted(flac_files):
        result = process_file(
            flac_file,
            args.genre,
            force=args.force,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        results[result] += 1

    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  ✅ Updated: {results['updated']}")
    print(f"  ⏭️  Skipped: {results['skipped']}")
    print(f"  ❌ Invalid: {results['invalid']}")
    print(f"  💥 Failed: {results['failed']}")
    print(f"  📊 Total: {len(flac_files)}")

    if args.dry_run:
        print("\n🔍 This was a dry run - no files were modified")
    elif results["updated"] > 0:
        print(f"\n✅ Successfully tagged {results['updated']} files with genre: {final_genre}")


if __name__ == "__main__":
    main()
