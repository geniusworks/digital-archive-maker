#!/usr/bin/env python3
"""
Utility to create IMDb ID-based overrides for movies.
This helps resolve "same title, wrong movie" issues by using IMDb ID as the definitive key.
"""

import argparse
import json
import sys
from pathlib import Path


def load_overrides(overrides_file):
    """Load existing overrides file"""
    if overrides_file.exists():
        with open(overrides_file, "r") as f:
            return json.load(f)
    return {}


def save_overrides(overrides_file, overrides):
    """Save overrides file with pretty formatting"""
    with open(overrides_file, "w") as f:
        json.dump(overrides, f, indent=2, sort_keys=True)


def read_imdb_id_from_mp4(file_path):
    """Read IMDb ID from MP4 file metadata"""
    try:
        from mutagen.mp4 import MP4

        audio = MP4(file_path)
        imdb_id = audio.get("----:com.apple.iTunes:imdb_id", [None])[0]
        return imdb_id
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def add_imdb_override(overrides_file, movie_file, rating, imdb_id=None):
    """Add IMDb ID-based override for a movie"""
    overrides = load_overrides(overrides_file)

    # Read IMDb ID from file if not provided
    if not imdb_id:
        imdb_id = read_imdb_id_from_mp4(movie_file)
        if not imdb_id:
            print(f"No IMDb ID found in {movie_file}")
            print("Please provide --imdb-id or ensure the movie has IMDb ID metadata")
            return False

    # Ensure imdb_id_based section exists
    if "imdb_id_based" not in overrides:
        overrides["imdb_id_based"] = {}

    # Add the override
    overrides["imdb_id_based"][imdb_id] = rating
    save_overrides(overrides_file, overrides)

    print(f"Added override: IMDb ID {imdb_id} = {rating}")
    return True


def list_imdb_ids(directory):
    """List all movies with their IMDb IDs"""
    print(f"Scanning {directory} for movies with IMDb IDs...")

    for mp4_file in Path(directory).rglob("*.mp4"):
        imdb_id = read_imdb_id_from_mp4(mp4_file)
        if imdb_id:
            print(f"{mp4_file.relative_to(directory)}: {imdb_id}")


def main():
    parser = argparse.ArgumentParser(description="Manage IMDb ID-based rating overrides")
    parser.add_argument(
        "--overrides",
        default="config/movie_rating_overrides.json",
        help="Path to overrides file",
    )
    parser.add_argument("--list", action="store_true", help="List movies with IMDb IDs")
    parser.add_argument("--add", help="Add override for this movie file")
    parser.add_argument("--rating", help="Rating for the override (G, PG, PG-13, R, NC-17)")
    parser.add_argument("--imdb-id", help="IMDb ID (if not in file metadata)")
    parser.add_argument("--directory", help="Directory to scan for --list")

    args = parser.parse_args()

    if args.list:
        if not args.directory:
            parser.error("--directory required for --list")
        list_imdb_ids(args.directory)

    elif args.add:
        if not args.rating:
            parser.error("--rating required for --add")
        if args.rating not in ["G", "PG", "PG-13", "R", "NC-17"]:
            parser.error("Invalid rating. Use: G, PG, PG-13, R, NC-17")

        success = add_imdb_override(Path(args.overrides), Path(args.add), args.rating, args.imdb_id)
        if not success:
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
