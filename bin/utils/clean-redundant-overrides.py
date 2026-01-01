#!/usr/bin/env python3
"""Remove movie rating overrides that are redundant.

Compares:
- log/movie_rating_overrides.json (manual overrides)
- log/movie_rating_cache.json (cached ratings)

If an override has the same title and rating as the cache, it is removed from the
overrides file.
"""

import argparse
import json
from pathlib import Path

OVERRIDES_FILE = Path("log/movie_rating_overrides.json")
CACHE_FILE = Path("log/movie_rating_cache.json")

def main():
    parser = argparse.ArgumentParser(
        description="Remove redundant entries from movie_rating_overrides.json (already present in movie_rating_cache.json)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without modifying the overrides file",
    )
    args = parser.parse_args()

    if not CACHE_FILE.exists():
        raise SystemExit(f"Cache file not found: {CACHE_FILE}")
    if not OVERRIDES_FILE.exists():
        raise SystemExit(f"Overrides file not found: {OVERRIDES_FILE}")

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
    with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
        overrides = json.load(f)

    if not isinstance(cache, dict):
        raise SystemExit(f"Cache file is not a JSON object: {CACHE_FILE}")
    if not isinstance(overrides, dict):
        raise SystemExit(f"Overrides file is not a JSON object: {OVERRIDES_FILE}")

    removed = {}
    kept = {}
    for title, rating in overrides.items():
        if title in cache and cache.get(title) == rating:
            removed[title] = rating
        else:
            kept[title] = rating

    if removed:
        print(f"{'[DRY RUN] Would remove' if args.dry_run else 'Removing'} {len(removed)} overrides already present in rating cache:")
        for title, rating in sorted(removed.items()):
            print(f"  - {title}: {rating}")

        if args.dry_run:
            print(f"[DRY RUN] Would keep {len(kept)} overrides.")
            return

        with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(kept, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        print(f"Wrote {len(kept)} overrides back to {OVERRIDES_FILE}")
    else:
        print("No overrides match rating cache; nothing to remove.")

if __name__ == "__main__":
    main()
