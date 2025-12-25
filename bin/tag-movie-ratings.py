#!/usr/bin/env python3
"""
Movie MPAA Rating Tagger

Tags .mp4 movie files with MPAA ratings using TMDb API and manual overrides.
Similar to tag-explicit-mb.py but for movies.

Usage:
    python3 bin/tag-movie-ratings.py "/path/to/movies"
    python3 bin/tag-movie-ratings.py "/path/to/movies" --dry-run
    python3 bin/tag-movie-ratings.py "/path/to/movies" --verbose
"""

import argparse
import csv
import json
import os
import re
import signal
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# Constants
RATING_TAG = "©rat"  # Copyright Rating field for MPAA ratings
_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _REPO_ROOT / "log"
MOVIE_CACHE_FILE = _LOG_DIR / "movie_rating_cache.json"
MOVIE_OVERRIDES_FILE = _LOG_DIR / "movie_rating_overrides.csv"
SHOWS_CACHE_FILE = _LOG_DIR / "shows_rating_cache.json"
SHOWS_OVERRIDES_FILE = _LOG_DIR / "shows_rating_overrides.csv"
UNKNOWN_VALUE = "Unknown"
VALID_RATINGS = {"G", "PG", "PG-13", "R", "NC-17", "NR", "Unrated"}

# Global settings
DRY_RUN = False
VERBOSE = False
PRINT_RATING_TO_CONSOLE = True
MAX_RATING_CONSOLE_LINES = 1000

OMDB_RATE_LIMITED = False
OMDB_RATE_LIMITED_DATE = None
INTERRUPT_REQUESTED = False


def _sigint_handler(signum, frame):
    global INTERRUPT_REQUESTED
    if INTERRUPT_REQUESTED:
        raise KeyboardInterrupt
    INTERRUPT_REQUESTED = True


def normalize_title(title):
    """Normalize movie title for API lookup"""
    # Remove common suffixes and normalize
    title = re.sub(r'\s*\(\d{4}\).*$', '', title)  # Remove year and everything after
    title = re.sub(r'\s*:\s.*$', '', title)  # Remove subtitle after colon
    title = title.strip()
    return title


def _format_display_title(title, year):
    """Format title for console display, avoiding double year"""
    if re.search(r'\s*\(\d{4}\)\s*$', title):
        return title
    elif year:
        return f"{title} ({year})"
    else:
        return title


def extract_year_from_path(file_path):
    """Extract year from folder name or filename"""
    path = Path(file_path)
    
    # Check folder name first
    folder_match = re.search(r'\((\d{4})\)', path.parent.name)
    if folder_match:
        return int(folder_match.group(1))
    
    # Check filename
    file_match = re.search(r'\((\d{4})\)', path.stem)
    if file_match:
        return int(file_match.group(1))
    
    return None


def read_rating_from_file(file_path):
    """Read existing MPAA rating from MP4 file"""
    try:
        from mutagen.mp4 import MP4
        audio = MP4(file_path)
        return audio, audio.get(RATING_TAG, [None])[0]
    except ImportError:
        raise RuntimeError("mutagen is required (pip install mutagen)")
    except Exception as e:
        if VERBOSE:
            print(f"Error reading {file_path}: {e}")
        return None, None


def write_rating_to_file(file_path, rating, audio=None):
    """Write MPAA rating to MP4 file"""
    if DRY_RUN:
        print(f"DRY RUN: Would write {RATING_TAG}={rating} to {file_path}")
        return True
    
    try:
        if audio is None:
            from mutagen.mp4 import MP4
            audio = MP4(file_path)
        audio[RATING_TAG] = [rating]
        audio.save()
        return True
    except ImportError:
        print("Error: mutagen is required (pip install mutagen)")
        return False
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")
        return False


def _ensure_log_dir_exists():
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def load_overrides(overrides_file: Path):
    """Load manual rating overrides from CSV"""
    overrides = {}

    _ensure_log_dir_exists()
    if not overrides_file.exists():
        return overrides
    
    with open(overrides_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get('title') or '').strip()
            rating = (row.get('rating') or '').strip()
            if not title or not rating:
                continue
            key = f"{normalize_title(title)}"
            overrides[key] = rating
    
    return overrides


def load_cache(cache_file: Path):
    """Load rating cache"""
    _ensure_log_dir_exists()
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}


def save_cache(cache, cache_file: Path):
    """Save rating cache"""
    _ensure_log_dir_exists()
    if OMDB_RATE_LIMITED and OMDB_RATE_LIMITED_DATE:
        meta = cache.get("__meta__")
        if not isinstance(meta, dict):
            meta = {}
        meta["omdb_rate_limited_date"] = OMDB_RATE_LIMITED_DATE
        cache["__meta__"] = meta

    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(cache_file.parent),
            prefix=cache_file.name + ".",
            suffix=".tmp",
        ) as tf:
            tmp_name = tf.name
            json.dump(cache, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
        os.replace(tmp_name, cache_file)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _tmdb_get_json(path, query):
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise RuntimeError("TMDB_API_KEY environment variable not set")

    query = dict(query or {})
    query["api_key"] = api_key
    url = f"https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(query)}"

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _omdb_get_json(query):
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        raise RuntimeError("OMDB_API_KEY environment variable not set")

    query = dict(query or {})
    query["apikey"] = api_key
    url = f"https://www.omdbapi.com/?{urllib.parse.urlencode(query)}"

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def get_omdb_rating(title, year=None):
    """Get MPAA rating from OMDb API"""
    try:
        query = {"t": normalize_title(title)}
        if year:
            query["y"] = str(year)
        
        data = _omdb_get_json(query)
        
        if data.get("Response") != "True":
            if VERBOSE:
                err = data.get("Error") or "OMDb response was not True"
                print(f"OMDb lookup failed for {title} ({year}): {err}")

            err = (data.get("Error") or "").lower()
            if "limit" in err or "request limit" in err or "daily" in err:
                global OMDB_RATE_LIMITED, OMDB_RATE_LIMITED_DATE
                OMDB_RATE_LIMITED = True
                OMDB_RATE_LIMITED_DATE = date.today().isoformat()
            return None
        
        rated = (data.get("Rated") or "").strip()
        if rated in VALID_RATINGS:
            return rated

        rated_upper = rated.upper()
        legacy_map = {
            "APPROVED": "NR",
            "PASSED": "NR",
            "NOT RATED": "NR",
            "N/A": "NR",
            "UNRATED": "Unrated",
        }

        mapped = legacy_map.get(rated_upper)
        if mapped in VALID_RATINGS:
            return mapped
        
        return None
        
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as e:
        if VERBOSE:
            print(f"OMDb API error for {title}: {e}")
        return None


def get_movie_rating(title, year=None):
    """Get MPAA rating from TMDb or OMDb API"""
    start_time = time.time()
    
    # Try TMDb first if API key is available
    if os.getenv("TMDB_API_KEY"):
        rating = get_tmdb_rating(title, year)
        if rating:
            elapsed = time.time() - start_time
            if VERBOSE and elapsed > 2.0:
                print(f"Slow TMDb lookup ({elapsed:.1f}s): {title} ({year})")
            return rating
    
    # Fall back to OMDb if API key is available
    if os.getenv("OMDB_API_KEY") and not OMDB_RATE_LIMITED:
        rating = get_omdb_rating(title, year)
        elapsed = time.time() - start_time
        if VERBOSE and elapsed > 2.0:
            print(f"Slow OMDb lookup ({elapsed:.1f}s): {title} ({year})")
        return rating

    if VERBOSE:
        if OMDB_RATE_LIMITED:
            print(f"OMDb is rate-limited for today; skipping API lookup for {title} ({year})")
        else:
            print(f"No TMDB_API_KEY or OMDB_API_KEY set; skipping API lookup for {title} ({year})")
    return None


def get_tmdb_rating(title, year=None):
    """Get MPAA rating from TMDb API"""
    try:
        search_query = {
            "query": normalize_title(title),
            "include_adult": "false",
            "language": "en-US",
        }
        if year:
            search_query["year"] = str(year)

        search_data = _tmdb_get_json("/search/movie", search_query)
        search_results = search_data.get("results") or []

        if not search_results:
            return None

        # Find best match by year if provided; else first result.
        best = search_results[0]
        if year:
            for r in search_results:
                rd = r.get("release_date") or ""
                if rd.startswith(f"{year}-"):
                    best = r
                    break

        movie_id = best.get("id")
        if not movie_id:
            return None

        release_dates = _tmdb_get_json(f"/movie/{movie_id}/release_dates", {"language": "en-US"})
        for country in release_dates.get("results") or []:
            if country.get("iso_3166_1") != "US":
                continue

            for rel in country.get("release_dates") or []:
                cert = (rel.get("certification") or "").strip()
                if cert in VALID_RATINGS:
                    return cert

        return None

    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as e:
        if VERBOSE:
            print(f"TMDb API error for {title}: {e}")
        return None


def find_movie_files(root_path):
    """Find all .mp4 movie files in directory or return single file if it's an MP4"""
    root = Path(root_path)
    
    # If it's a single MP4 file, return just that file
    if root.is_file() and root.suffix.lower() == ".mp4":
        # Skip sample files and extras
        if "sample" in root.name.lower() or "extra" in root.name.lower():
            return []
        return [root]
    
    # Otherwise scan directory recursively
    movie_files = []
    for file_path in root.rglob("*.mp4"):
        # Skip sample files and extras
        if "sample" in file_path.name.lower() or "extra" in file_path.name.lower():
            continue
        movie_files.append(file_path)
    
    return sorted(movie_files)


def main():
    parser = argparse.ArgumentParser(description="Tag MP4 movie files with MPAA ratings")
    parser.add_argument("root", nargs="?", default=".", 
                       help="Root directory to scan for MP4 files")
    parser.add_argument(
        "--media",
        choices=["movies", "shows"],
        default="movies",
        help="Which library is being tagged (controls which overrides/cache files are used)",
    )
    parser.add_argument("--dry-run", action="store_true", 
                       help="Don't write tags, just report what would be done")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--max-files", type=int, default=0,
                       help="Maximum number of files to process (0 = no limit)")
    
    args = parser.parse_args()
    
    global DRY_RUN, VERBOSE
    DRY_RUN = args.dry_run
    VERBOSE = args.verbose

    previous_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _sigint_handler)
    
    try:
        from dotenv import load_dotenv
        load_dotenv(_REPO_ROOT / ".env")
    except ImportError:
        pass
    
    # API keys are optional, but at least one is required for automatic lookups.
    if os.getenv("TMDB_API_KEY"):
        print("Using TMDb API (with OMDb fallback if OMDB_API_KEY is set)")
    elif os.getenv("OMDB_API_KEY"):
        print("Using OMDb API")
    else:
        print("No TMDB_API_KEY or OMDB_API_KEY set; API lookups disabled (override/cache/existing tags only)")
    
    if args.media == "movies":
        overrides_file = MOVIE_OVERRIDES_FILE
        cache_file = MOVIE_CACHE_FILE
    else:
        overrides_file = SHOWS_OVERRIDES_FILE
        cache_file = SHOWS_CACHE_FILE

    # Load data
    overrides = load_overrides(overrides_file)
    cache = load_cache(cache_file)

    global OMDB_RATE_LIMITED, OMDB_RATE_LIMITED_DATE
    meta = cache.get("__meta__")
    if isinstance(meta, dict):
        limited_date = meta.get("omdb_rate_limited_date")
        today = date.today().isoformat()
        if limited_date == today:
            OMDB_RATE_LIMITED = True
            OMDB_RATE_LIMITED_DATE = limited_date

    # Find movie files
    movie_files = find_movie_files(args.root)
    
    if args.max_files > 0:
        movie_files = movie_files[:args.max_files]
    
    print(f"Processing {len(movie_files)} movie files...")
    
    stats = {}
    rating_console_lines = 0
    processed_count = 0
    try:
        for i, file_path in enumerate(movie_files, 1):
            if INTERRUPT_REQUESTED:
                print("\nInterrupt requested; stopping after current progress.")
                break

            # Update progress on same line, but move to next line before printing rating info
            if PRINT_RATING_TO_CONSOLE:
                print(f"Processing: {i}/{len(movie_files)}")
            else:
                print(f"\rProcessing: {i}/{len(movie_files)}", end="", flush=True)
         
            # Extract title from filename
            title = file_path.stem
            year = extract_year_from_path(file_path)
            title_norm = normalize_title(title)
        
            # Check cache/overrides
            cache_key = f"{title_norm}_{year}" if year else title_norm
            cached_rating = cache.get(cache_key)
            override_rating = overrides.get(title_norm)

            existing_rating = None
            audio = None
        
            # Determine rating
            new_rating = None
            source = "Unknown"
        
            if override_rating:
                new_rating = override_rating
                source = "Override"
            elif cached_rating:
                new_rating = cached_rating
                source = "Cache"
            else:
                audio, existing_rating = read_rating_from_file(file_path)
                if existing_rating and existing_rating in VALID_RATINGS:
                    new_rating = existing_rating
                    source = "Existing"
                else:
                    # Query movie rating (TMDb or OMDb)
                    new_rating = get_movie_rating(title, year)
                    if new_rating:
                        source = "API"
                        cache[cache_key] = new_rating
                    else:
                        new_rating = UNKNOWN_VALUE
                        source = "Unknown"
        
            # For overrides/cache, we need to read the file to check existing rating
            if override_rating or cached_rating:
                if audio is None:
                    audio, existing_rating = read_rating_from_file(file_path)

            should_write = (
                new_rating in VALID_RATINGS and
                new_rating != existing_rating
            )
            
            if should_write:
                success = write_rating_to_file(file_path, new_rating, audio=audio)
                if success:
                    cache[cache_key] = new_rating
        
            # Print rating info
            if PRINT_RATING_TO_CONSOLE:
                if new_rating in VALID_RATINGS:
                    if rating_console_lines < MAX_RATING_CONSOLE_LINES:
                        print(f"RATING={new_rating}: {_format_display_title(title, year)} ({source})")
                        rating_console_lines += 1
                elif VERBOSE and new_rating == UNKNOWN_VALUE:
                    if rating_console_lines < MAX_RATING_CONSOLE_LINES:
                        print(f"UNKNOWN: {_format_display_title(title, year)} ({source})")
                        rating_console_lines += 1

            stats[new_rating] = stats.get(new_rating, 0) + 1

            processed_count += 1
    finally:
        save_cache(cache, cache_file)
        signal.signal(signal.SIGINT, previous_sigint_handler)
     
    # Print summary
    print(f"\n\nProcessed: {processed_count} files")
    print("Ratings:", ", ".join(f"{k}={v}" for k, v in sorted(stats.items())))

if __name__ == "__main__":
    main()
