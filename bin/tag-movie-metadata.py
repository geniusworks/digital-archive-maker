#!/usr/bin/env python3

import os
import sys
import json
import argparse
import re
import requests
from pathlib import Path
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp4 import MP4FreeForm
import base64
from datetime import datetime

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _REPO_ROOT / "log"
_CACHE_FILE = _LOG_DIR / "movie_metadata_cache.json"


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(_REPO_ROOT / ".env")
    except ImportError:
        pass


def _load_cache():
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _save_cache(cache):
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(_CACHE_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, _CACHE_FILE)
    except Exception:
        pass


def _normalize_cache_title(title):
    if not title:
        return ""
    t = str(title).strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return t.strip()


def _cache_key(imdb_id=None, tmdb_id=None, title=None, year=None):
    if imdb_id:
        return f"imdb:{imdb_id.strip()}"
    if tmdb_id:
        return f"tmdb:{str(tmdb_id).strip()}"
    t = _normalize_cache_title(title)
    y = str(year).strip() if year else ""
    if t and y:
        return f"title:{t}|year:{y}"
    if t:
        return f"title:{t}"
    return None

def find_imdb_id_from_file(file_path):
    """Try to extract IMDb ID from filename or existing tags."""
    # Check filename for IMDb ID pattern
    filename = os.path.basename(file_path)
    import re
    imdb_match = re.search(r'tt(\d+)', filename)
    if imdb_match:
        return f"tt{imdb_match.group(1)}"
    
    # Check existing tags for IMDb ID
    try:
        mp4 = MP4(file_path)
        # Check common IMDb ID tags
        for key in ['----:com.apple.iTunes:imdb', '----:com.apple.iTunes:IMDb', '----:com.apple.iTunes:imdb_id']:
            if key in mp4:
                return mp4[key][0].decode('utf-8')
    except:
        pass
    
    return None

def find_tmdb_id_from_file(file_path):
    """Try to extract TMDb ID from filename or existing tags."""
    filename = os.path.basename(file_path)
    import re
    tmdb_match = re.search(r'tmdb(\d+)', filename)
    if tmdb_match:
        return tmdb_match.group(1)
    
    # Check existing tags for TMDb ID
    try:
        mp4 = MP4(file_path)
        for key in ['----:com.apple.iTunes:tmdb', '----:com.apple.iTunes:TMDb', '----:com.apple.iTunes:tmdb_id']:
            if key in mp4:
                return mp4[key][0].decode('utf-8')
    except:
        pass
    
    return None

def get_tmdb_metadata(imdb_id=None, tmdb_id=None, title=None, year=None, verbose=False):
    """Fetch comprehensive metadata from TMDb."""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        if verbose:
            print("Warning: TMDB_API_KEY not set, skipping TMDb lookup")
        return None
 
    headers = {"Accept": "application/json"}
    
    # Try to find movie by IMDb ID first
    if imdb_id:
        try:
            url = f"https://api.themoviedb.org/3/find/{imdb_id}"
            params = {"api_key": api_key, "external_source": "imdb_id"}
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if data.get('movie_results'):
                tmdb_id = data['movie_results'][0]['id']
            else:
                print(f"No TMDb results found for IMDb ID: {imdb_id}")
                return None
        except Exception as e:
            print(f"TMDb IMDb lookup failed: {e}")
            return None
    
    # Search by title (and optional year) if no IDs
    if not tmdb_id and title:
        try:
            url = "https://api.themoviedb.org/3/search/movie"
            params = {
                "api_key": api_key,
                'query': title,
                'page': 1
            }
            if year:
                params['year'] = year
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                tmdb_id = data['results'][0]['id']
            else:
                print(f"No TMDb search results for: {title} ({year})")
                return None
        except Exception as e:
            print(f"TMDb search failed: {e}")
            return None
    
    if not tmdb_id:
        return None
    
    # Get full movie details
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {
            "api_key": api_key,
            'append_to_response': 'credits,videos,images,releases,keywords'
        }
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"TMDb details lookup failed: {e}")
        return None

def get_omdb_metadata(imdb_id=None, title=None, year=None, verbose=False):
    """Fetch metadata from OMDb as backup/supplement."""
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        if verbose:
            print("Warning: OMDB_API_KEY not set, skipping OMDb lookup")
        return None
    
    try:
        url = "http://www.omdbapi.com/"
        params = {'apikey': api_key, 'plot': 'full', 'r': 'json'}
        if imdb_id:
            params['i'] = imdb_id
        elif title:
            params['t'] = title
            if year:
                params['y'] = str(year)
        else:
            return None

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        else:
            print(f"OMDb error: {data.get('Error', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"OMDb lookup failed: {e}")
        return None


def _normalize_omdb_metadata(data):
    if not isinstance(data, dict):
        return None
    if data.get("Response") != "True":
        return None

    title = data.get("Title")
    year_str = data.get("Year")
    year_int = None
    if isinstance(year_str, str) and year_str[:4].isdigit():
        year_int = int(year_str[:4])

    genres = []
    if isinstance(data.get("Genre"), str) and data.get("Genre").strip():
        genres = [{"name": g.strip()} for g in data.get("Genre").split(",") if g.strip()]

    crew = []
    if isinstance(data.get("Director"), str) and data.get("Director").strip() and data.get("Director") != "N/A":
        for d in [p.strip() for p in data.get("Director").split(",") if p.strip()]:
            crew.append({"job": "Director", "name": d})
    if isinstance(data.get("Writer"), str) and data.get("Writer").strip() and data.get("Writer") != "N/A":
        for w in [p.strip() for p in data.get("Writer").split(",") if p.strip()]:
            crew.append({"job": "Writer", "name": w})

    cast = []
    if isinstance(data.get("Actors"), str) and data.get("Actors").strip() and data.get("Actors") != "N/A":
        for a in [p.strip() for p in data.get("Actors").split(",") if p.strip()]:
            cast.append({"name": a, "character": ""})

    releases = None
    rated = data.get("Rated")
    if isinstance(rated, str) and rated.strip() and rated != "N/A":
        releases = {"countries": [{"iso_3166_1": "US", "certification": rated}]}

    production_companies = []
    prod = data.get("Production")
    if isinstance(prod, str) and prod.strip() and prod != "N/A":
        production_companies = [{"name": prod.strip()}]

    runtime = None
    runtime_str = data.get("Runtime")
    if isinstance(runtime_str, str) and runtime_str.strip() and runtime_str != "N/A":
        m = re.search(r"(\d+)", runtime_str)
        if m:
            runtime = int(m.group(1))

    poster_url = data.get("Poster")
    if not isinstance(poster_url, str) or not poster_url.strip() or poster_url == "N/A":
        poster_url = None

    overview = data.get("Plot")
    if not isinstance(overview, str) or overview == "N/A":
        overview = None

    return {
        "title": title,
        "year": year_int,
        "overview": overview,
        "genres": genres,
        "credits": {"crew": crew, "cast": cast},
        "releases": releases,
        "production_companies": production_companies,
        "runtime": runtime,
        "imdb_id": data.get("imdbID"),
        "_poster_url": poster_url,
    }

def download_image(url, timeout=30):
    """Download image from URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Failed to download image from {url}: {e}")
        return None

def _is_missing_mp4_tag(mp4, key):
    try:
        if key not in mp4:
            return True
        value = mp4.get(key)
        if value is None:
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False
    except Exception:
        return True


def _extract_mp4_text(mp4, key):
    try:
        v = mp4.get(key)
        if v is None:
            return None
        if isinstance(v, list):
            if not v:
                return None
            if len(v) == 1:
                return v[0]
            return v
        return v
    except Exception:
        return None


def _set_mp4_text(mp4, key, value, force=False):
    if value is None:
        return False
    if not force and not _is_missing_mp4_tag(mp4, key):
        return False
    existing = _extract_mp4_text(mp4, key)
    if existing == value:
        return False
    mp4[key] = value
    return True


def _get_freeform_text(mp4, freeform_key):
    try:
        v = mp4.get(freeform_key)
        if not isinstance(v, list) or not v:
            return None
        first = v[0]
        if isinstance(first, (bytes, bytearray)):
            return bytes(first).decode("utf-8", errors="replace")
        if hasattr(first, "decode"):
            return first.decode("utf-8", errors="replace")
        return str(first)
    except Exception:
        return None


def _set_freeform_text(mp4, freeform_key, value, force=False):
    if not value:
        return False
    if not force and not _is_missing_mp4_tag(mp4, freeform_key):
        return False
    existing = _get_freeform_text(mp4, freeform_key)
    if existing == value:
        return False
    mp4[freeform_key] = [MP4FreeForm(value.encode("utf-8"))]
    return True


def _mp4_needs_metadata(file_path):
    try:
        mp4 = MP4(file_path)
    except Exception:
        return True

    keys = [
        "\xa9nam",
        "\xa9day",
        "\xa9des",
        "\xa9gen",
        "\xa9ART",
        "\xa9wrt",
        "\xa9act",
        "\xa9rat",
        "\xa9cpy",
        "covr",
        "----:com.apple.iTunes:imdb_id",
        "----:com.apple.iTunes:tmdb_id",
    ]
    return any(_is_missing_mp4_tag(mp4, k) for k in keys)


def write_metadata_to_file(file_path, metadata, dry_run=False, force=False):
    """Write comprehensive metadata to MP4 file."""
    if dry_run:
        print(f"DRY RUN: Would write metadata to {file_path}")
        return True

    try:
        if not isinstance(metadata, dict):
            return False

        mp4 = MP4(file_path)
        changed = False

        if metadata.get('title'):
            changed = _set_mp4_text(mp4, '\xa9nam', metadata.get('title'), force=force) or changed

        if metadata.get('year'):
            changed = _set_mp4_text(mp4, '\xa9day', str(metadata.get('year')), force=force) or changed
        elif isinstance(metadata.get('release_date'), str) and metadata.get('release_date'):
            changed = _set_mp4_text(mp4, '\xa9day', metadata['release_date'][:4], force=force) or changed

        if metadata.get('overview'):
            changed = _set_mp4_text(mp4, '\xa9des', metadata.get('overview'), force=force) or changed

        genres_list = metadata.get('genres') or []
        if genres_list:
            genres = [g.get('name') for g in genres_list if isinstance(g, dict) and g.get('name')]
            genres = [g for g in genres if g]
            if genres:
                changed = _set_mp4_text(mp4, '\xa9gen', ', '.join(genres), force=force) or changed

        credits = metadata.get('credits') or {}
        crew = credits.get('crew') or []
        if crew:
            directors = [c.get('name') for c in crew if isinstance(c, dict) and c.get('job') == 'Director' and c.get('name')]
            writers = [c.get('name') for c in crew if isinstance(c, dict) and c.get('job') in ['Writer', 'Screenplay'] and c.get('name')]

            if directors:
                changed = _set_mp4_text(mp4, '\xa9ART', ', '.join(directors), force=force) or changed
            if writers:
                changed = _set_mp4_text(mp4, '\xa9wrt', ', '.join(writers), force=force) or changed

        cast_list = credits.get('cast') or []
        if cast_list:
            cast = cast_list[:10]
            actors = []
            for c in cast:
                if not isinstance(c, dict):
                    continue
                name = c.get('name')
                character = c.get('character')
                if name and character:
                    actors.append(f"{name} as {character}")
                elif name:
                    actors.append(str(name))
            if actors:
                changed = _set_mp4_text(mp4, '\xa9act', '\n'.join(actors), force=force) or changed

        releases = metadata.get('releases') or {}
        countries = releases.get('countries') or []
        if countries:
            us_release = None
            for country in countries:
                if not isinstance(country, dict):
                    continue
                if country.get('iso_3166_1') == 'US':
                    us_release = country
                    break

            if us_release and us_release.get('certification'):
                changed = _set_mp4_text(mp4, '\xa9rat', us_release['certification'], force=force) or changed

        companies = metadata.get('production_companies') or []
        if companies:
            studios = [c.get('name') for c in companies if isinstance(c, dict) and c.get('name')]
            if studios:
                changed = _set_mp4_text(mp4, '\xa9cpy', studios[0], force=force) or changed

        freeform_data = {}
        if metadata.get('imdb_id'):
            freeform_data['imdb_id'] = metadata['imdb_id']
        if metadata.get('id'):
            freeform_data['tmdb_id'] = str(metadata['id'])
        if metadata.get('runtime'):
            freeform_data['runtime'] = str(metadata['runtime'])
        if metadata.get('budget'):
            freeform_data['budget'] = str(metadata['budget'])
        if metadata.get('revenue'):
            freeform_data['revenue'] = str(metadata['revenue'])

        keywords_container = metadata.get('keywords') or {}
        keywords_list = keywords_container.get('keywords') or []
        if keywords_list:
            keywords = [k.get('name') for k in keywords_list if isinstance(k, dict) and k.get('name')]
            keywords = [k for k in keywords if k]
            if keywords:
                freeform_data['keywords'] = ', '.join(keywords)

        for key, value in freeform_data.items():
            if value:
                freeform_key = f"----:com.apple.iTunes:{key}"
                changed = _set_freeform_text(mp4, freeform_key, value, force=force) or changed

        poster_url = None
        if metadata.get('poster_path'):
            poster_url = f"https://image.tmdb.org/t/p/original{metadata['poster_path']}"
        elif metadata.get('_poster_url'):
            poster_url = metadata.get('_poster_url')

        if poster_url and (force or _is_missing_mp4_tag(mp4, 'covr')):
            poster_data = download_image(poster_url)
            if poster_data:
                mp4['covr'] = [MP4Cover(poster_data, MP4Cover.FORMAT_JPEG)]
                changed = True

        if not changed:
            return False

        mp4.save()
        return True
    except Exception as e:
        print(f"Error writing metadata to {file_path}: {e}")
        return False

def parse_title_year_from_filename(file_path):
    """Extract title and year from filename."""
    filename = os.path.basename(file_path)
    import re
    
    # Look for (YYYY) pattern
    match = re.search(r'(.+?)\s*\((\d{4})\)', filename)
    if match:
        title = match.group(1).replace('.', ' ').strip()
        year = int(match.group(2))
        return title, year
    
    return None, None


def parse_title_year_from_path(file_path):
    title, year = parse_title_year_from_filename(file_path)
    if title:
        return title, year
    parent = os.path.basename(os.path.dirname(file_path))
    match_title, match_year = parse_title_year_from_filename(parent)
    if match_title:
        return match_title, match_year
    return None, None

def main():
    _load_env()
    cache = _load_cache()
    parser = argparse.ArgumentParser(description='Tag movie files with comprehensive metadata')
    parser.add_argument('paths', nargs='+', help='Movie file(s) or directory')
    parser.add_argument('--imdb-id', help='IMDb ID (tt#######)')
    parser.add_argument('--tmdb-id', help='TMDb ID')
    parser.add_argument('--title', help='Movie title (for search)')
    parser.add_argument('--year', type=int, help='Release year (for search)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without writing')
    parser.add_argument('--force', action='store_true', help='Overwrite existing tags/artwork (default is to only fill missing)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--recursive', action='store_true', help='Process directories recursively')
    
    args = parser.parse_args()
    
    # Find movie files
    movie_files = []
    for path in args.paths:
        if os.path.isfile(path):
            movie_files.append(path)
        elif os.path.isdir(path):
            if args.recursive:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.m4v')):
                            movie_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(path):
                    if file.lower().endswith(('.mp4', '.m4v')):
                        movie_files.append(os.path.join(path, file))
    
    if not movie_files:
        print("No movie files found")
        return
    
    print(f"Found {len(movie_files)} movie file(s)")
    
    cache_dirty = False
    for file_path in movie_files:
        print(f"\nProcessing: {file_path}")

        if not args.force and not _mp4_needs_metadata(file_path):
            if args.verbose:
                print("  Already has metadata; skipping")
            continue
        
        imdb_id = args.imdb_id or find_imdb_id_from_file(file_path)
        tmdb_id = args.tmdb_id or find_tmdb_id_from_file(file_path)
        title = args.title
        year = args.year

        if not title and not imdb_id and not tmdb_id:
            title, year = parse_title_year_from_path(file_path)
        
        if args.verbose:
            print(f"  IMDb ID: {imdb_id}")
            print(f"  TMDb ID: {tmdb_id}")
            print(f"  Title: {title}")
            print(f"  Year: {year}")
        
        if not any([imdb_id, tmdb_id, title]):
            print(f"  No identifiers found (no IDs and couldn't infer title/year); skipping")
            continue

        key = _cache_key(imdb_id=imdb_id, tmdb_id=tmdb_id, title=title, year=year)
        cached = cache.get(key) if key else None
        if isinstance(cached, dict) and cached.get("not_found") is True:
            if args.verbose:
                print("  Cached as not found; skipping")
            continue

        if isinstance(cached, dict) and isinstance(cached.get("metadata"), dict):
            metadata = cached.get("metadata")
        else:
            metadata = get_tmdb_metadata(imdb_id, tmdb_id, title, year, verbose=args.verbose)

            if not metadata:
                omdb = get_omdb_metadata(imdb_id=imdb_id, title=title, year=year, verbose=args.verbose)
                metadata = _normalize_omdb_metadata(omdb)

            if key:
                cache[key] = {
                    "fetched_at": datetime.utcnow().isoformat() + "Z",
                    "not_found": metadata is None,
                    "metadata": metadata,
                }
                cache_dirty = True
        
        if not metadata:
            print(f"  No metadata found for {file_path}")
            continue
        
        if args.verbose:
            title_out = metadata.get('title', 'Unknown')
            year_out = metadata.get('year')
            if not year_out and isinstance(metadata.get('release_date'), str):
                year_out = metadata.get('release_date', '')[:4]
            print(f"  Found: {title_out} ({year_out})")
            print(f"  Genres: {', '.join([g['name'] for g in metadata.get('genres', [])])}")
            overview = metadata.get('overview') or ''
            print(f"  Overview: {overview[:100]}...")
        
        # Write metadata
        wrote = write_metadata_to_file(file_path, metadata, args.dry_run, force=args.force)
        if args.dry_run:
            print(f"  [DRY RUN] Would write metadata to {file_path}")
        else:
            if wrote:
                print(f"  Wrote metadata to {file_path}")
            else:
                print(f"  No changes needed")

        if cache_dirty:
            _save_cache(cache)
            cache_dirty = False

if __name__ == '__main__':
    main()
