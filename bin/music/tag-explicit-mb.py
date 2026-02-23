#!/usr/bin/env python3
import argparse
import csv
import json
import logging
import os
import re
import sys
import time
import fnmatch
from pathlib import Path

from dotenv import load_dotenv
import musicbrainzngs
import requests
from rapidfuzz import fuzz, process
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError
from tqdm import tqdm

# Load .env from repo root
_repo_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_repo_root / ".env")

# --- Configuration ---
DEFAULT_ROOT = "/Volumes/Data/Media/Library/CDs"  # default library root
USER_AGENT = ("JellyfinTagger", "1.0", "youremail@example.com")
RATE_LIMIT = 1.0  # seconds between MusicBrainz API requests
ITUNES_RATE_LIMIT = 0.25
ITUNES_COUNTRY = "US"
SPOTIFY_RATE_LIMIT = 0.1
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
SPOTIFY_ENABLED = bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(REPO_ROOT, "log")
EXPLICIT_DIR = os.path.join(LOG_DIR, "explicit")
os.makedirs(EXPLICIT_DIR, exist_ok=True)

LOG_FILE = os.path.join(EXPLICIT_DIR, "explicit_tagging_run.log")  # What was processed this run
CACHE_FILE = os.path.join(REPO_ROOT, "cache", "explicit_tagging_cache.json")
LEGACY_CACHE_FILE = os.path.join(REPO_ROOT, "explicit_tagging_cache.json")
ERROR_LOG_FILE = os.path.join(EXPLICIT_DIR, "explicit_tagging_errors.log")
EXPLICIT_PLAYLIST_FILE = os.path.join(EXPLICIT_DIR, "explicit_tracks_current.csv")
M3U_PLAYLIST_FILE = None  # Set conditionally below

os.makedirs(LOG_DIR, exist_ok=True)

OVERRIDES_FILE = os.path.join(REPO_ROOT, "config", "explicit_overrides.csv")
AGGRESSIVE_ALBUM_EXPLICIT = True
ITUNES_CLEANED_COUNTS_AS_EXPLICIT = True
PRINT_EXPLICIT_TO_CONSOLE = True
MAX_EXPLICIT_CONSOLE_LINES = 200
MAX_TRACKS = int(os.environ.get("EXPLICIT_MAX_TRACKS", "0") or 0)
DRY_RUN = str(os.environ.get("EXPLICIT_DRY_RUN", "0") or "0").strip().lower() in {"1", "true", "yes", "y"}
ONLY_UNKNOWN = str(os.environ.get("EXPLICIT_ONLY_UNKNOWN", "0") or "0").strip().lower() in {"1", "true", "yes", "y"}
INPUT_LOG_FILE = str(os.environ.get("EXPLICIT_INPUT_LOG", "") or "").strip() or None
ITUNES_TRACK_FALLBACK = str(os.environ.get("EXPLICIT_ITUNES_TRACK_FALLBACK", "") or "").strip().lower() in {"1", "true", "yes", "y"}
SPOTIFY_FALLBACK = str(os.environ.get("EXPLICIT_SPOTIFY_FALLBACK", "1") or "1").strip().lower() in {"1", "true", "yes", "y"}
SKIP_CACHED = str(os.environ.get("EXPLICIT_SKIP_CACHED", "1") or "1").strip().lower() in {"1", "true", "yes", "y"}

EXPLICIT_TAG = "EXPLICIT"
UNKNOWN_VALUE = "Unknown"

# Initialize MusicBrainz client
musicbrainzngs.set_useragent(*USER_AGENT)

logger = logging.getLogger("tag_explicit_mb")
logger.setLevel(logging.INFO)
_handler = logging.FileHandler(ERROR_LOG_FILE, mode="w", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_handler)

def _load_explicit_overrides(repo_root):
    """Load explicit overrides from CSV file - copied from sync-library.py"""
    overrides_file = os.path.join(repo_root, "config", "explicit_overrides.csv")
    overrides = []
    if not os.path.exists(overrides_file):
        return overrides

    try:
        with open(overrides_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            order = 0
            for row in reader:
                if not row:
                    continue
                if row[0].strip().startswith("#"):
                    continue
                if row[0].strip().lower() in {"artist", "#artist"}:
                    continue
                if len(row) < 4:
                    continue

                artist, album, title, explicit_val = (x.strip() for x in row[:4])
                if not artist or not album or not title or not explicit_val:
                    continue

                val = explicit_val.strip().lower()
                if val in {"yes", "y", "true", "1", "explicit"}:
                    val_out = "Yes"
                elif val in {"no", "n", "false", "0", "clean", "notexplicit"}:
                    val_out = "No"
                else:
                    val_out = UNKNOWN_VALUE

                artist_norm = artist if artist == "*" else _normalize_override_pattern(artist)
                album_norm = album if album == "*" else _normalize_override_pattern(album)
                title_norm = title if title == "*" else _normalize_override_pattern(title)

                overrides.append({
                    "artist": artist_norm,
                    "album": album_norm,
                    "title": title_norm,
                    "value": val_out,
                    "order": order,
                })
                order += 1
    except Exception:
        return []
    
    return overrides


def _load_cache():
    try:
        cache_path = CACHE_FILE
        if not os.path.exists(cache_path) and os.path.exists(LEGACY_CACHE_FILE):
            cache_path = LEGACY_CACHE_FILE

        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"mb_albums": {}, "itunes_albums": {}, "itunes_tracks": {}, "spotify_tracks": {}}

            # Backward compatible with previous cache format where the whole
            # file was a mapping of album_key -> {release_id, tracks}
            if "mb_albums" in data or "itunes_albums" in data:
                return {
                    "mb_albums": data.get("mb_albums") or {},
                    "itunes_albums": data.get("itunes_albums") or {},
                    "itunes_tracks": data.get("itunes_tracks") or {},
                    "spotify_tracks": data.get("spotify_tracks") or {},
                }

            logger.info(
                "Ignoring legacy cache format (pre split mb_albums/itunes_albums). "
                "Delete %s if you want to silence this message.",
                CACHE_FILE,
            )
            return {"mb_albums": {}, "itunes_albums": {}, "itunes_tracks": {}, "spotify_tracks": {}}
    except FileNotFoundError:
        return {"mb_albums": {}, "itunes_albums": {}, "itunes_tracks": {}, "spotify_tracks": {}}
    except Exception:
        logger.exception("Failed to load cache file")
        return {"mb_albums": {}, "itunes_albums": {}, "itunes_tracks": {}, "spotify_tracks": {}}


def _save_cache(cache):
    tmp = f"{CACHE_FILE}.tmp"
    try:
        # Update cache timestamp before saving
        cache["cache_mtime"] = time.time()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, CACHE_FILE)
    except Exception:
        logger.exception("Failed to save cache file")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _album_key(artist, album):
    return f"{_normalize_title(artist)}\n{_normalize_title(album)}"


def _normalize_title(title):
    s = (title or "").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^\w]+", " ", s, flags=re.UNICODE)
    return " ".join(s.split())


def _normalize_override_pattern(value):
    s = (value or "").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^\w*]+", " ", s, flags=re.UNICODE)
    return " ".join(s.split())


def _override_field_matches(rule_val, actual_val):
    if rule_val == "*":
        return True
    if any(ch in rule_val for ch in ["*", "?", "["]):
        return fnmatch.fnmatchcase(actual_val, rule_val)
    return rule_val == actual_val


def _lookup_track_value(track_map, title_norm):
    if not track_map:
        return None
    if title_norm in track_map:
        return track_map[title_norm]
    match = process.extractOne(
        title_norm,
        track_map.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=85,
    )
    if not match:
        return None
    best_key = match[0]
    return track_map.get(best_key)

def _first_tag(audio, key):
    values = None
    try:
        values = audio.get(key)
    except Exception:
        values = None

    if not values:
        # MP3 uses ID3 frames; EXPLICIT is stored as TXXX:EXPLICIT.
        if key == EXPLICIT_TAG and getattr(audio, "tags", None):
            try:
                frame = audio.tags.get("TXXX:" + EXPLICIT_TAG)
                if frame is not None:
                    if hasattr(frame, "text") and frame.text:
                        return str(frame.text[0]).strip()
                    return str(frame).strip()
            except Exception:
                return None
        return None

    return str(values[0]).strip() if values[0] is not None else None


def _strip_trailing_year(name):
    # e.g. "Purple Rain (1984)" -> "Purple Rain"
    return re.sub(r"\s*\(\d{4}\)\s*$", "", (name or "").strip())


def _strip_trailing_disc(name):
    s = (name or "").strip()
    s = re.sub(r"\s*\(disc\s*[ivx0-9]+\)\s*$", "", s, flags=re.IGNORECASE)
    return s


def _normalize_album_for_search(album):
    return _strip_trailing_disc(_strip_trailing_year(album))


def _load_overrides():
    overrides = []
    overrides_mtime = None
    
    if os.path.exists(OVERRIDES_FILE):
        overrides_mtime = os.path.getmtime(OVERRIDES_FILE)
    
    if not os.path.exists(OVERRIDES_FILE):
        return overrides, overrides_mtime

    try:
        with open(OVERRIDES_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            order = 0
            for row in reader:
                if not row:
                    continue
                if row[0].strip().lower() in {"artist", "#artist", "#"}:
                    continue
                if len(row) < 4:
                    continue

                artist, album, title, explicit_val = (x.strip() for x in row[:4])
                if not artist or not album or not title or not explicit_val:
                    continue

                artist_norm = artist if artist == "*" else _normalize_override_pattern(artist)
                album_norm = album if album == "*" else _normalize_override_pattern(album)  # Don't strip years/discs for cache compatibility
                title_norm = title if title == "*" else _normalize_override_pattern(title)

                val = explicit_val.strip().lower()
                if val in {"yes", "y", "true", "1", "explicit"}:
                    val_out = "Yes"
                elif val in {"no", "n", "false", "0", "clean", "notexplicit"}:
                    val_out = "No"
                else:
                    val_out = UNKNOWN_VALUE

                overrides.append(
                    {
                        "artist": artist_norm,
                        "album": album_norm,
                        "title": title_norm,
                        "value": val_out,
                        "order": order,
                    }
                )
                order += 1
    except Exception:
        logger.exception("Failed to read overrides file: %s", OVERRIDES_FILE)

    return overrides, overrides_mtime


def _resolve_override(overrides, artist_norm, album_norm, title_norm):
    best = None
    best_score = (-1, -1)
    for rule in overrides or []:
        ra = rule.get("artist")
        rb = rule.get("album")
        rt = rule.get("title")

        if not _override_field_matches(ra, artist_norm):
            continue
        if not _override_field_matches(rb, album_norm):
            continue
        if not _override_field_matches(rt, title_norm):
            continue

        spec = 0
        if ra != "*":
            spec += 1
        if rb != "*":
            spec += 1
        if rt != "*":
            spec += 1

        score = (spec, int(rule.get("order") or 0))
        if score > best_score:
            best_score = score
            best = rule

    if best is None:
        return None
    return best.get("value")


def _write_explicit_tag(audio_path, audio, value):
    if DRY_RUN:
        return value

    # Check existing tag to avoid unnecessary writes
    if audio_path.lower().endswith(".flac"):
        existing = audio.get(EXPLICIT_TAG)
        if existing and isinstance(existing, (list, tuple)):
            try:
                existing0 = str(existing[0]).strip()
            except Exception:
                existing0 = None
            if existing0 == value and len(existing) == 1:
                return value
    else:  # MP3
        existing0 = None
        try:
            if getattr(audio, "tags", None):
                frame = audio.tags.get("TXXX:" + EXPLICIT_TAG)
                if frame is not None:
                    # Mutagen returns a TXXX frame; its .text is list[str]
                    if hasattr(frame, "text") and frame.text:
                        existing0 = str(frame.text[0]).strip()
                    else:
                        existing0 = str(frame).strip()
        except Exception:
            existing0 = None

        if existing0 == value:
            return value

    orig_mtime = os.path.getmtime(audio_path)
    
    # Write tag based on format
    if audio_path.lower().endswith(".flac"):
        audio[EXPLICIT_TAG] = [value]
    else:  # MP3 - need to create proper ID3 frame
        from mutagen.id3 import TXXX
        # Remove existing TXXX:EXPLICIT tag if present
        if getattr(audio, "tags", None) and ("TXXX:" + EXPLICIT_TAG) in audio.tags:
            del audio.tags["TXXX:" + EXPLICIT_TAG]
        # Add new TXXX:EXPLICIT tag
        audio.tags.add(TXXX(encoding=3, desc=EXPLICIT_TAG, text=value))
    
    audio.save()
    os.utime(audio_path, (orig_mtime, orig_mtime))
    return value

def _mb_call(callable_, *args, **kwargs):
    last_exc = None
    for attempt in range(3):
        try:
            result = callable_(*args, **kwargs)
            time.sleep(RATE_LIMIT)
            return result
        except Exception as exc:
            last_exc = exc
            time.sleep(RATE_LIMIT * (2 ** attempt))
    raise last_exc


def _fetch_album_track_map(artist, album):
    result = _mb_call(musicbrainzngs.search_releases, artist=artist, release=album, limit=1)
    release_list = result.get("release-list") or []
    if not release_list:
        return None

    release_id = release_list[0].get("id")
    if not release_id:
        return None

    release_result = _mb_call(
        musicbrainzngs.get_release_by_id,
        release_id,
        includes=["recordings"],
    )
    release = (release_result or {}).get("release") or {}

    tracks = {}
    for medium in release.get("medium-list", []) or []:
        for track in medium.get("track-list", []) or []:
            recording = track.get("recording") or {}
            title = recording.get("title") or track.get("title") or ""
            adult = recording["adult_content"] if "adult_content" in recording else None
            if title:
                tracks[_normalize_title(title)] = adult

    if not tracks:
        return None

    return {"release_id": release_id, "tracks": tracks}

def _http_call_json(url, params, *, rate_limit):
    last_exc = None
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            time.sleep(rate_limit)
            return data
        except Exception as exc:
            last_exc = exc
            time.sleep(rate_limit * (2 ** attempt))
    raise last_exc


def _fetch_itunes_album_track_map(artist, album):
    want_artist = _normalize_title(artist)
    want_album = _normalize_title(album)

    search = _http_call_json(
        "https://itunes.apple.com/search",
        {
            "term": album,
            "media": "music",
            "entity": "album",
            "attribute": "albumTerm",
            "limit": 50,
            "country": ITUNES_COUNTRY,
            "explicit": "Yes",
        },
        rate_limit=ITUNES_RATE_LIMIT,
    )
    results = (search or {}).get("results") or []
    if not results:
        return None

    best = None
    best_score = -1
    for r in results:
        a = _normalize_title(r.get("artistName", ""))
        artist_sim = fuzz.WRatio(want_artist, a)
        if artist_sim < 85:
            continue
        alb = _normalize_title(r.get("collectionName", ""))
        sim = fuzz.WRatio(want_album, alb)
        if sim < 80:
            continue
        score = sim + (artist_sim * 0.2)
        if r.get("collectionExplicitness") == "explicit":
            score += 3
        if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and r.get("collectionExplicitness") == "cleaned":
            score += 3
        if score > best_score:
            best_score = score
            best = r

    if best is None:
        term = f"{artist} {album}".strip()
        search = _http_call_json(
            "https://itunes.apple.com/search",
            {
                "term": term,
                "media": "music",
                "entity": "album",
                "limit": 50,
                "country": ITUNES_COUNTRY,
                "explicit": "Yes",
            },
            rate_limit=ITUNES_RATE_LIMIT,
        )
        results = (search or {}).get("results") or []
        for r in results:
            a = _normalize_title(r.get("artistName", ""))
            artist_sim = fuzz.WRatio(want_artist, a)
            if artist_sim < 85:
                continue
            alb = _normalize_title(r.get("collectionName", ""))
            sim = fuzz.WRatio(want_album, alb)
            if sim < 80:
                continue
            score = sim + (artist_sim * 0.2)
            if r.get("collectionExplicitness") == "explicit":
                score += 3
            if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and r.get("collectionExplicitness") == "cleaned":
                score += 3
            if score > best_score:
                best_score = score
                best = r

        if best is None:
            return None

    collection_id = (best or {}).get("collectionId")
    if not collection_id:
        return None

    lookup = _http_call_json(
        "https://itunes.apple.com/lookup",
        {"id": collection_id, "entity": "song", "country": ITUNES_COUNTRY},
        rate_limit=ITUNES_RATE_LIMIT,
    )
    tracks = {}
    for r in (lookup or {}).get("results") or []:
        if r.get("wrapperType") != "track":
            continue
        title = r.get("trackName")
        explicitness = r.get("trackExplicitness")
        if title and explicitness:
            tracks[_normalize_title(title)] = explicitness

    if not tracks:
        return None

    return {
        "collection_id": collection_id,
        "collection_explicitness": (best or {}).get("collectionExplicitness"),
        "collection_name": (best or {}).get("collectionName"),
        "tracks": tracks,
    }


def _fetch_itunes_collection_meta_by_id(collection_id):
    lookup = _http_call_json(
        "https://itunes.apple.com/lookup",
        {"id": collection_id, "country": ITUNES_COUNTRY},
        rate_limit=ITUNES_RATE_LIMIT,
    )
    results = (lookup or {}).get("results") or []
    if not results:
        return None
    return {
        "collection_explicitness": results[0].get("collectionExplicitness"),
        "collection_name": results[0].get("collectionName"),
    }


def _is_itunes_collection_match(want_album_norm, cached_collection_name):
    if not cached_collection_name:
        return True
    cached_norm = _normalize_title(cached_collection_name)
    return fuzz.WRatio(want_album_norm, cached_norm) >= 70


def _itunes_track_key(artist, album, title):
    return (
        f"{_normalize_title(artist)}\n{_normalize_title(_normalize_album_for_search(album))}\n{_normalize_title(title)}"
    )


def _fetch_itunes_track_search(artist, album, title):
    want_artist = _normalize_title(artist)
    want_album = _normalize_title(_normalize_album_for_search(album))
    want_title = _normalize_title(title)

    term = f"{artist} {title}".strip()
    search = _http_call_json(
        "https://itunes.apple.com/search",
        {
            "term": term,
            "media": "music",
            "entity": "song",
            "limit": 50,
            "country": ITUNES_COUNTRY,
            "explicit": "Yes",
        },
        rate_limit=ITUNES_RATE_LIMIT,
    )
    results = (search or {}).get("results") or []
    if not results:
        return None

    best = None
    best_score = -1
    best_album_sim = None
    for r in results:
        if r.get("wrapperType") != "track":
            continue

        a = _normalize_title(r.get("artistName", ""))
        artist_sim = fuzz.WRatio(want_artist, a)
        if artist_sim < 85:
            continue

        t = _normalize_title(r.get("trackName", ""))
        title_sim = fuzz.WRatio(want_title, t)
        if title_sim < 85:
            continue

        score = title_sim + (artist_sim * 0.15)
        alb = _normalize_title(r.get("collectionName", ""))
        album_sim = fuzz.WRatio(want_album, alb)
        if want_album and album_sim < 60:
            continue
        if album_sim >= 70:
            score += (album_sim * 0.1)

        if r.get("trackExplicitness") == "explicit":
            score += 3
        if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and r.get("trackExplicitness") == "cleaned":
            score += 3

        if score > best_score:
            best_score = score
            best = r
            best_album_sim = album_sim

    if best is None:
        return None

    return {
        "track_id": best.get("trackId"),
        "track_explicitness": best.get("trackExplicitness"),
        "collection_explicitness": best.get("collectionExplicitness"),
        "collection_name": best.get("collectionName"),
        "album_sim": best_album_sim,
    }


def _explicit_from_itunes(value):
    if value == "explicit":
        return True
    if value == "cleaned":
        if ITUNES_CLEANED_COUNTS_AS_EXPLICIT:
            return True
        return False
    return None


def _itunes_collection_is_explicit(collection_explicitness):
    if collection_explicitness == "explicit":
        return True
    if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and collection_explicitness == "cleaned":
        return True
    return False


def _explicit_from_mb(value):
    if value is True:
        return True
    return None


# --- Spotify API ---
_spotify_token = None
_spotify_token_expires = 0


def _get_spotify_token():
    global _spotify_token, _spotify_token_expires
    if _spotify_token and time.time() < _spotify_token_expires - 60:
        return _spotify_token

    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _spotify_token = data.get("access_token")
        _spotify_token_expires = time.time() + data.get("expires_in", 3600)
        return _spotify_token
    except Exception:
        logger.exception("Failed to get Spotify access token")
        return None


def _spotify_track_key(artist, album, title):
    return f"{_normalize_title(artist)}\n{_normalize_title(album)}\n{_normalize_title(title)}"


def _fetch_spotify_track_search(artist, album, title):
    token = _get_spotify_token()
    if not token:
        return None

    want_artist = _normalize_title(artist)
    want_album = _normalize_title(album)
    want_title = _normalize_title(title)

    query = f"artist:{artist} track:{title}"
    if album:
        query += f" album:{album}"

    try:
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            params={
                "q": query,
                "type": "track",
                "limit": 20,
                "market": "US",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        time.sleep(SPOTIFY_RATE_LIMIT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Spotify search failed: %s - %s - %s", artist, album, title)
        return None

    tracks = (data.get("tracks") or {}).get("items") or []
    if not tracks:
        return None

    best = None
    best_score = -1
    for t in tracks:
        artists = t.get("artists") or []
        artist_names = [a.get("name", "") for a in artists]
        artist_match = any(fuzz.WRatio(want_artist, _normalize_title(a)) >= 85 for a in artist_names)
        if not artist_match:
            continue

        track_name = _normalize_title(t.get("name", ""))
        title_sim = fuzz.WRatio(want_title, track_name)
        if title_sim < 85:
            continue

        score = title_sim
        album_obj = t.get("album") or {}
        album_name = _normalize_title(album_obj.get("name", ""))
        album_sim = fuzz.WRatio(want_album, album_name) if want_album else 100
        if want_album and album_sim < 60:
            continue
        if album_sim >= 70:
            score += (album_sim * 0.1)

        if t.get("explicit"):
            score += 5

        if score > best_score:
            best_score = score
            best = t

    if best is None:
        return None

    return {
        "track_id": best.get("id"),
        "explicit": best.get("explicit"),
        "track_name": best.get("name"),
        "album_name": (best.get("album") or {}).get("name"),
    }


# --- Parse command line arguments ---
parser = argparse.ArgumentParser(description="Tag FLAC files with explicit content information")
parser.add_argument("root", nargs="?", default=DEFAULT_ROOT, 
                    help="Root directory to scan for FLAC files (default: %(default)s)")
parser.add_argument("--dry-run", action="store_true", 
                    help="Don't write tags, just report what would be done")
parser.add_argument("--max-tracks", type=int, default=0,
                    help="Maximum number of tracks to process (0 = no limit)")
parser.add_argument("--generate-explicit-playlist", action="store_true",
                    help="Generate Explicit.m3u8 playlist file (disabled by default)")
parser.add_argument("--verbose", action="store_true",
                    help="Print all EXPLICIT=Yes tracks (including already-tagged ones) and increase output limit")

args = parser.parse_args()

ROOT = args.root
M3U_PLAYLIST_FILE = os.path.join(ROOT, "Explicit.m3u8") if args.generate_explicit_playlist else None
if args.max_tracks > 0:
    MAX_TRACKS = args.max_tracks
if args.dry_run:
    DRY_RUN = True

if args.verbose:
    PRINT_EXPLICIT_TO_CONSOLE = True
    MAX_EXPLICIT_CONSOLE_LINES = 1000

cache = _load_cache()
mb_cache = cache["mb_albums"]
itunes_cache = cache["itunes_albums"]
itunes_track_cache = cache.get("itunes_tracks") or {}
cache["itunes_tracks"] = itunes_track_cache
spotify_track_cache = cache.get("spotify_tracks") or {}
cache["spotify_tracks"] = spotify_track_cache

overrides, overrides_mtime = _load_overrides()

mb_album_runtime_cache = {}
itunes_album_runtime_cache = {}
spotify_track_runtime_cache = {}
itunes_track_runtime_cache = {}
explicit_playlist_entries = set()
stats = {
    "Yes": 0,
    "No": 0,
    "Unknown": 0,
}
source_counts = {}
explicit_console_lines = 0
explicit_console_suppressed = False

# --- Collect all FLAC files ---
all_flacs = []
if ONLY_UNKNOWN:
    source_log = INPUT_LOG_FILE or LOG_FILE
    if source_log and os.path.exists(source_log):
        try:
            with open(source_log, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if not row or len(row) < 5:
                        continue
                    path = row[0]
                    explicit_val = (row[4] or "").strip().lower()
                    if explicit_val not in {"", UNKNOWN_VALUE.lower()}:
                        continue
                    if not path or not path.lower().endswith((".flac", ".mp3")):
                        continue
                    if os.path.exists(path):
                        all_flacs.append(path)
        except Exception:
            logger.exception("Failed to read input log for second pass: %s", source_log)

if not all_flacs:
    for root, dirs, files in os.walk(ROOT):
        audio_files = [os.path.join(root, f) for f in files if f.lower().endswith((".flac", ".mp3"))]
        all_flacs.extend(audio_files)

if MAX_TRACKS > 0:
    all_flacs = all_flacs[:MAX_TRACKS]

# --- Process with progress bar ---
with open(LOG_FILE, "w", encoding="utf-8", newline="") as log:
    writer = csv.writer(log)
    writer.writerow(["File", "Artist", "Album", "Title", "Explicit", "Source"])

    for audio_path in tqdm(all_flacs, desc="Tagging audio files"):
        # Load audio file based on extension
        if audio_path.lower().endswith(".flac"):
            audio = FLAC(audio_path)
        else:  # MP3
            try:
                audio = MP3(audio_path)
            except ID3NoHeaderError:
                # MP3 has no ID3 tags, create empty ID3
                audio = MP3(audio_path)
                audio.add_tags()
        
        prev_explicit_tag = _first_tag(audio, EXPLICIT_TAG)

        if ONLY_UNKNOWN and prev_explicit_tag is not None and prev_explicit_tag.strip().lower() not in {UNKNOWN_VALUE.lower(), ""}:
            continue

        # Prefer tags over folder names to avoid issues like "Purple Rain (1984)"
        album = _first_tag(audio, "album") or os.path.basename(os.path.dirname(audio_path))
        artist = (
            _first_tag(audio, "albumartist")
            or _first_tag(audio, "artist")
            or os.path.basename(os.path.dirname(os.path.dirname(audio_path)))
        )
        
        # Handle case where artist directory contains tracks directly (no album subdirectory)
        if artist == "Music" and os.path.basename(os.path.dirname(audio_path)) != "Music":
            artist = os.path.basename(os.path.dirname(audio_path))
        title = _first_tag(audio, "title")
        if not title:
            title = os.path.basename(audio_path).rsplit(".", 1)[0]
            m = re.match(r"^\s*\d+\s*-\s*(.*)$", title)
            if m:
                title = m.group(1)

        album_search = _normalize_album_for_search(album)
        title_norm = _normalize_title(title)

        # --- SKIP_CACHED: skip if already processed (has tag or in cache) and no pending override ---
        if SKIP_CACHED:
            override_val = _resolve_override(overrides, _normalize_title(artist), _normalize_title(album_search), title_norm)
            if override_val is not None:
                # Override exists — check if tag already matches
                if override_val == prev_explicit_tag:
                    continue
                # Override doesn't match current tag — need to re-tag
            else:
                # No override — skip if already tagged Yes/No, but NOT Unknown (need to check Unknown against overrides)
                if prev_explicit_tag in {"Yes", "No"}:
                    continue
                # For Unknown tags, only process if overrides file changed since last cache write
                if prev_explicit_tag == UNKNOWN_VALUE:
                    cache_mtime = cache.get("cache_mtime", 0)
                    if overrides_mtime and cache_mtime and overrides_mtime <= cache_mtime:
                        continue
                # Check if we have cached data for this track (Spotify/iTunes track-level) - only skip if not Unknown
                if prev_explicit_tag != UNKNOWN_VALUE:
                    itunes_track_key = _itunes_track_key(artist, album_search, title)
                    spotify_key = _spotify_track_key(artist, album, title)  # Use original album for Spotify
                    if itunes_track_key in itunes_track_cache or spotify_key in spotify_track_cache:
                        continue

        source = UNKNOWN_VALUE

        explicit_status = None

        # --- Overrides (highest priority) ---
        override_val = _resolve_override(overrides, _normalize_title(artist), _normalize_title(album_search), title_norm)
        if override_val is not None:
            if override_val == "Yes":
                explicit_status = True
                source = "Override"
            elif override_val == "No":
                explicit_status = False
                source = "Override"
            elif override_val == UNKNOWN_VALUE:
                explicit_status = None
                source = "Override"

        # Initialize itunes_data to None for all paths
        itunes_data = None
        
        # For Unknown tracks, skip remote services and only use overrides
        if prev_explicit_tag == UNKNOWN_VALUE:
            # Skip iTunes, Spotify, MusicBrainz - just use override result or keep Unknown
            if explicit_status is None:
                source = UNKNOWN_VALUE
        else:
            # --- iTunes (primary) ---
            if explicit_status is None:
                itunes_key = _album_key(artist, album_search)
                itunes_data = itunes_album_runtime_cache.get(itunes_key)
                if itunes_data is None and itunes_key in itunes_album_runtime_cache:
                    itunes_data = None
                else:
                    if itunes_data is None:
                        itunes_data = itunes_cache.get(itunes_key)
                        if itunes_data is not None:
                            itunes_album_runtime_cache[itunes_key] = itunes_data

                    if itunes_data is None:
                        try:
                            itunes_data = _fetch_itunes_album_track_map(artist, album_search)
                        except Exception:
                            logger.exception("iTunes request failed: %s - %s", artist, album_search)
                            itunes_album_runtime_cache[itunes_key] = None
                        else:
                            if itunes_data is not None:
                                itunes_cache[itunes_key] = itunes_data
                                _save_cache(cache)
                                itunes_album_runtime_cache[itunes_key] = itunes_data
                            else:
                                itunes_album_runtime_cache[itunes_key] = None

        if itunes_data is not None:
            want_album_norm = _normalize_title(album_search)

            if not _is_itunes_collection_match(want_album_norm, itunes_data.get("collection_name")):
                itunes_cache.pop(itunes_key, None)
                itunes_album_runtime_cache.pop(itunes_key, None)
                _save_cache(cache)
                itunes_data = None

        if itunes_data is not None:
                if "collection_explicitness" not in itunes_data and itunes_data.get("collection_id"):
                    try:
                        meta = _fetch_itunes_collection_meta_by_id(itunes_data["collection_id"])
                        if meta:
                            if meta.get("collection_explicitness") is not None:
                                itunes_data["collection_explicitness"] = meta.get("collection_explicitness")
                            if meta.get("collection_name"):
                                itunes_data["collection_name"] = meta.get("collection_name")
                    except Exception:
                        logger.exception(
                            "Failed to fetch iTunes collectionExplicitness: %s (%s - %s)",
                            itunes_data.get("collection_id"),
                            artist,
                            album_search,
                        )
                    else:
                        itunes_cache[itunes_key] = itunes_data
                        _save_cache(cache)

                it_val = _lookup_track_value((itunes_data.get("tracks") or {}), title_norm)
                if it_val == "notExplicit":
                    it_track = None
                    it_album_explicit = False
                    source = "iTunesNotExplicit"
                else:
                    it_track = _explicit_from_itunes(it_val)
                    it_album_explicit = _itunes_collection_is_explicit(itunes_data.get("collection_explicitness"))

                if it_track is True:
                    explicit_status = True
                    if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and it_val == "cleaned":
                        source = "iTunesCleaned"
                    else:
                        source = "iTunesTrack"
                elif it_track is False:
                    if AGGRESSIVE_ALBUM_EXPLICIT and it_album_explicit and it_val != "cleaned":
                        explicit_status = True
                        if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and itunes_data.get("collection_explicitness") == "cleaned":
                            source = "iTunesAlbumCleaned"
                        else:
                            source = "iTunesAlbum"
                    else:
                        explicit_status = False
                        source = "iTunesTrack"
                else:
                    if AGGRESSIVE_ALBUM_EXPLICIT and it_album_explicit:
                        explicit_status = True
                        if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and itunes_data.get("collection_explicitness") == "cleaned":
                            source = "iTunesAlbumCleaned"
                        else:
                            source = "iTunesAlbum"

        # --- iTunes (track search fallback) ---
        if explicit_status is None and (ITUNES_TRACK_FALLBACK or ONLY_UNKNOWN):
            itunes_track_key = _itunes_track_key(artist, album_search, title)
            it_track_data = itunes_track_runtime_cache.get(itunes_track_key)
            if it_track_data is None and itunes_track_key in itunes_track_runtime_cache:
                it_track_data = None
            else:
                if it_track_data is None:
                    it_track_data = itunes_track_cache.get(itunes_track_key)
                    if it_track_data is not None:
                        itunes_track_runtime_cache[itunes_track_key] = it_track_data

                if it_track_data is None:
                    try:
                        it_track_data = _fetch_itunes_track_search(artist, album_search, title)
                    except Exception:
                        logger.exception("iTunes track search failed: %s - %s - %s", artist, album_search, title)
                        itunes_track_runtime_cache[itunes_track_key] = None
                    else:
                        if it_track_data is not None:
                            itunes_track_cache[itunes_track_key] = it_track_data
                            _save_cache(cache)
                            itunes_track_runtime_cache[itunes_track_key] = it_track_data
                        else:
                            # Negative cache: store empty dict to avoid re-querying
                            itunes_track_cache[itunes_track_key] = {}
                            _save_cache(cache)
                            itunes_track_runtime_cache[itunes_track_key] = {}

            if it_track_data is not None and it_track_data:
                it_val = it_track_data.get("track_explicitness")
                if it_val == "notExplicit":
                    it_track = None
                    source = "iTunesTrackSearchNotExplicit"
                else:
                    it_track = _explicit_from_itunes(it_val)

                if it_track is True:
                    explicit_status = True
                    if ITUNES_CLEANED_COUNTS_AS_EXPLICIT and it_val == "cleaned":
                        source = "iTunesTrackSearchCleaned"
                    else:
                        source = "iTunesTrackSearch"

        # --- Spotify (fallback) ---
        if explicit_status is None and SPOTIFY_ENABLED and SPOTIFY_FALLBACK:
            spotify_key = _spotify_track_key(artist, album_search, title)
            sp_data = spotify_track_runtime_cache.get(spotify_key)
            if sp_data is None and spotify_key in spotify_track_runtime_cache:
                sp_data = None
            else:
                if sp_data is None:
                    sp_data = spotify_track_cache.get(spotify_key)
                    if sp_data is not None:
                        spotify_track_runtime_cache[spotify_key] = sp_data

                if sp_data is None:
                    try:
                        sp_data = _fetch_spotify_track_search(artist, album_search, title)
                    except Exception:
                        logger.exception("Spotify search failed: %s - %s - %s", artist, album_search, title)
                        spotify_track_runtime_cache[spotify_key] = None
                    else:
                        if sp_data is not None:
                            spotify_track_cache[spotify_key] = sp_data
                            _save_cache(cache)
                            spotify_track_runtime_cache[spotify_key] = sp_data
                        else:
                            # Negative cache: store empty dict to avoid re-querying
                            spotify_track_cache[spotify_key] = {}
                            _save_cache(cache)
                            spotify_track_runtime_cache[spotify_key] = {}

            if sp_data is not None and sp_data:
                if sp_data.get("explicit") is True:
                    explicit_status = True
                    source = "Spotify"

        # --- MusicBrainz (fallback) ---
        if explicit_status is None:
            mb_key = _album_key(artist, album_search)
            mb_data = mb_album_runtime_cache.get(mb_key)
            if mb_data is None and mb_key in mb_album_runtime_cache:
                mb_data = None
            else:
                if mb_data is None:
                    mb_data = mb_cache.get(mb_key)
                    if mb_data is not None:
                        mb_album_runtime_cache[mb_key] = mb_data

                if mb_data is None:
                    try:
                        mb_data = _fetch_album_track_map(artist, album_search)
                    except Exception:
                        logger.exception("MusicBrainz request failed: %s - %s", artist, album_search)
                        mb_album_runtime_cache[mb_key] = None
                    else:
                        if mb_data is not None:
                            mb_cache[mb_key] = mb_data
                            _save_cache(cache)
                            mb_album_runtime_cache[mb_key] = mb_data
                        else:
                            mb_album_runtime_cache[mb_key] = None

            if mb_data is not None:
                mb_val = _lookup_track_value((mb_data.get("tracks") or {}), title_norm)
                explicit_status = _explicit_from_mb(mb_val)
                if explicit_status is not None:
                    source = "MusicBrainz"

        if explicit_status is True:
            tag_value = _write_explicit_tag(audio_path, audio, "Yes")
        elif explicit_status is False:
            tag_value = _write_explicit_tag(audio_path, audio, "No")
        else:
            tag_value = _write_explicit_tag(audio_path, audio, UNKNOWN_VALUE)
        
        # Force save the cache after each successful tag to ensure persistence
        if tag_value and (explicit_status is not None or source == "Override"):
            _save_cache(cache)

        stats[tag_value] = stats.get(tag_value, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1

        if PRINT_EXPLICIT_TO_CONSOLE and tag_value == "Yes":
            # In verbose mode, print all Yes tracks; otherwise only print newly-tagged ones
            if args.verbose or prev_explicit_tag != "Yes":
                if explicit_console_lines < MAX_EXPLICIT_CONSOLE_LINES:
                    tqdm.write(f"EXPLICIT=Yes: {artist} - {album} - {title} ({source})")
                    explicit_console_lines += 1
                elif not explicit_console_suppressed:
                    tqdm.write("Further EXPLICIT=Yes messages suppressed")
                    explicit_console_suppressed = True

        if tag_value == "Yes":
            explicit_playlist_entries.add(os.path.relpath(audio_path, ROOT))

        writer.writerow([audio_path, artist, album, title, tag_value, source])

# Build definitive list of ALL files with EXPLICIT=Yes tag (not just processed ones)
explicit_tracks = []
overrides = _load_explicit_overrides(REPO_ROOT)

for root, _dirs, files in os.walk(ROOT):
    for name in files:
        if not name.lower().endswith((".flac", ".mp3")):
            continue
        fullpath = os.path.join(root, name)
        try:
            if name.lower().endswith(".flac"):
                audio = FLAC(fullpath)
                tag_val = _first_tag(audio, EXPLICIT_TAG)
            else:  # MP3
                audio = MP3(fullpath)
                # For MP3, check TXXX:EXPLICIT tag
                tag_val = None
                if getattr(audio, "tags", None):
                    frame = audio.tags.get("TXXX:" + EXPLICIT_TAG)
                    if frame is not None:
                        if hasattr(frame, "text") and frame.text:
                            tag_val = str(frame.text[0]).strip()
                        else:
                            tag_val = str(frame).strip()
            
            # Extract metadata for override matching
            artist = _first_tag(audio, "ARTIST") or "Unknown Artist"
            album = _first_tag(audio, "ALBUM") or "Unknown Album"
            title = _first_tag(audio, "TITLE") or os.path.splitext(name)[0]
            
            # Check if this track should be explicit (either from tag or override)
            is_explicit = False
            source = "File Tag"
            
            # Check metadata tag first
            if tag_val == "Yes":
                is_explicit = True
                source = "File Tag"
            
            # Also check overrides (independent of metadata tag)
            album_search = _normalize_album_for_search(album)
            title_norm = _normalize_title(title)
            override_val = _resolve_override(overrides, _normalize_title(artist), _normalize_title(album_search), title_norm)
            if override_val == "Yes":
                is_explicit = True
                source = "Override"
            
            if is_explicit:
                explicit_tracks.append([fullpath, artist, album, title, "Yes", source])
        except Exception:
            pass

# Write definitive explicit tracks list (append mode to support multiple source directories)
with open(EXPLICIT_PLAYLIST_FILE, "a", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    # Only write header if file is empty
    if os.path.getsize(EXPLICIT_PLAYLIST_FILE) == 0:
        writer.writerow(["File", "Artist", "Album", "Title", "Explicit", "Source"])
    for track in sorted(explicit_tracks):
        writer.writerow(track)

print(f"Definitive explicit tracks list: {len(explicit_tracks)} tracks written to {EXPLICIT_PLAYLIST_FILE}")

# Build M3U playlist if enabled (legacy functionality)
if M3U_PLAYLIST_FILE:
    with open(M3U_PLAYLIST_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        for track in sorted(explicit_tracks):
            f.write(os.path.relpath(track[0], ROOT) + "\n")
    playlist_count = len(explicit_tracks)
else:
    playlist_count = 0

processed_count = stats.get('Yes', 0) + stats.get('No', 0) + stats.get('Unknown', 0)
print(f"Processed: {processed_count} tracks (skipped {len(all_flacs) - processed_count} already tagged)")
if args.verbose:
    print(f"Definitive explicit tracks: {len(explicit_tracks)} total EXPLICIT=Yes tracks")
    if args.generate_explicit_playlist:
        print(f"M3U playlist: {playlist_count} tracks written to Explicit.m3u8")
    else:
        print("M3U playlist: generation disabled (use --generate-explicit-playlist to enable)")
if processed_count > 0:
    if args.verbose:
        print(f"  This run: Yes={stats.get('Yes', 0)} No={stats.get('No', 0)} Unknown={stats.get('Unknown', 0)}")
        if source_counts:
            top_sources = sorted(source_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
            print("  Sources:", ", ".join(f"{k}={v}" for k, v in top_sources))