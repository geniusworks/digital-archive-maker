#!/usr/bin/env python3
import csv
import json
import logging
import os
import re
import time

import musicbrainzngs
import requests
from rapidfuzz import fuzz, process
from mutagen.flac import FLAC
from tqdm import tqdm

# --- Configuration ---
ROOT = "/Volumes/Data/Media/Rips/CDs"  # change to your library root
USER_AGENT = ("JellyfinTagger", "1.0", "youremail@example.com")
RATE_LIMIT = 1.0  # seconds between MusicBrainz API requests
ITUNES_RATE_LIMIT = 0.25
ITUNES_COUNTRY = "US"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(REPO_ROOT, "log")
LOG_FILE = os.path.join(LOG_DIR, "explicit_tagging.log")
CACHE_FILE = os.path.join(LOG_DIR, "explicit_tagging_cache.json")
LEGACY_CACHE_FILE = os.path.join(REPO_ROOT, "explicit_tagging_cache.json")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "explicit_tagging_errors.log")
EXPLICIT_PLAYLIST_FILE = os.path.join(ROOT, "Explicit.m3u8")

os.makedirs(LOG_DIR, exist_ok=True)

OVERRIDES_FILE = "explicit_overrides.csv"
AGGRESSIVE_ALBUM_EXPLICIT = True
ITUNES_CLEANED_COUNTS_AS_EXPLICIT = True
PRINT_EXPLICIT_TO_CONSOLE = True
MAX_EXPLICIT_CONSOLE_LINES = 200
MAX_TRACKS = int(os.environ.get("EXPLICIT_MAX_TRACKS", "0") or 0)
DRY_RUN = str(os.environ.get("EXPLICIT_DRY_RUN", "0") or "0").strip().lower() in {"1", "true", "yes", "y"}

EXPLICIT_TAG = "EXPLICIT"
UNKNOWN_VALUE = "Unknown"

# Initialize MusicBrainz client
musicbrainzngs.set_useragent(*USER_AGENT)

logger = logging.getLogger("tag_explicit_mb")
logger.setLevel(logging.INFO)
_handler = logging.FileHandler(ERROR_LOG_FILE, mode="w", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_handler)


def _load_cache():
    try:
        cache_path = CACHE_FILE
        if not os.path.exists(cache_path) and os.path.exists(LEGACY_CACHE_FILE):
            cache_path = LEGACY_CACHE_FILE

        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"mb_albums": {}, "itunes_albums": {}}

            # Backward compatible with previous cache format where the whole
            # file was a mapping of album_key -> {release_id, tracks}
            if "mb_albums" in data or "itunes_albums" in data:
                return {
                    "mb_albums": data.get("mb_albums") or {},
                    "itunes_albums": data.get("itunes_albums") or {},
                }

            logger.info(
                "Ignoring legacy cache format (pre split mb_albums/itunes_albums). "
                "Delete %s if you want to silence this message.",
                CACHE_FILE,
            )
            return {"mb_albums": {}, "itunes_albums": {}}
    except FileNotFoundError:
        return {"mb_albums": {}, "itunes_albums": {}}
    except Exception:
        logger.exception("Failed to load cache file")
        return {"mb_albums": {}, "itunes_albums": {}}


def _save_cache(cache):
    tmp = f"{CACHE_FILE}.tmp"
    try:
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
    values = audio.get(key)
    if not values:
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
    if not os.path.exists(OVERRIDES_FILE):
        return overrides

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

                artist_norm = artist if artist == "*" else _normalize_title(artist)
                album_norm = album if album == "*" else _normalize_title(_normalize_album_for_search(album))
                title_norm = title if title == "*" else _normalize_title(title)

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

    return overrides


def _resolve_override(overrides, artist_norm, album_norm, title_norm):
    best = None
    best_score = (-1, -1)
    for rule in overrides or []:
        ra = rule.get("artist")
        rb = rule.get("album")
        rt = rule.get("title")
        if ra not in {"*", artist_norm}:
            continue
        if rb not in {"*", album_norm}:
            continue
        if rt not in {"*", title_norm}:
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


def _write_explicit_tag(flac_path, audio, value):
    if DRY_RUN:
        return value

    existing = audio.get(EXPLICIT_TAG)
    if existing and isinstance(existing, (list, tuple)):
        try:
            existing0 = str(existing[0]).strip()
        except Exception:
            existing0 = None
        if existing0 == value and len(existing) == 1:
            return value

    orig_mtime = os.path.getmtime(flac_path)
    audio[EXPLICIT_TAG] = [value]
    audio.save()
    os.utime(flac_path, (orig_mtime, orig_mtime))
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
        if a != want_artist:
            continue
        alb = _normalize_title(r.get("collectionName", ""))
        sim = fuzz.WRatio(want_album, alb)
        if sim < 85:
            continue
        score = sim
        if r.get("collectionExplicitness") == "explicit":
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
            if a != want_artist:
                continue
            alb = _normalize_title(r.get("collectionName", ""))
            sim = fuzz.WRatio(want_album, alb)
            if sim < 85:
                continue
            score = sim
            if r.get("collectionExplicitness") == "explicit":
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


cache = _load_cache()
mb_cache = cache["mb_albums"]
itunes_cache = cache["itunes_albums"]

overrides = _load_overrides()

mb_album_runtime_cache = {}
itunes_album_runtime_cache = {}
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
for root, dirs, files in os.walk(ROOT):
    flacs = [os.path.join(root, f) for f in files if f.lower().endswith(".flac")]
    all_flacs.extend(flacs)

if MAX_TRACKS > 0:
    all_flacs = all_flacs[:MAX_TRACKS]

# --- Process with progress bar ---
with open(LOG_FILE, "w", encoding="utf-8", newline="") as log:
    writer = csv.writer(log)
    writer.writerow(["File", "Artist", "Album", "Title", "Explicit", "Source"])

    for flac_path in tqdm(all_flacs, desc="Tagging FLACs"):
        audio = FLAC(flac_path)
        prev_explicit_tag = _first_tag(audio, EXPLICIT_TAG)

        # Prefer tags over folder names to avoid issues like "Purple Rain (1984)"
        album = _first_tag(audio, "album") or os.path.basename(os.path.dirname(flac_path))
        artist = (
            _first_tag(audio, "albumartist")
            or _first_tag(audio, "artist")
            or os.path.basename(os.path.dirname(os.path.dirname(flac_path)))
        )
        title = _first_tag(audio, "title")
        if not title:
            title = os.path.basename(flac_path).rsplit(".", 1)[0]
            m = re.match(r"^\s*\d+\s*-\s*(.*)$", title)
            if m:
                title = m.group(1)

        album_search = _normalize_album_for_search(album)
        title_norm = _normalize_title(title)
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
            tag_value = _write_explicit_tag(flac_path, audio, "Yes")
        elif explicit_status is False:
            tag_value = _write_explicit_tag(flac_path, audio, "No")
        else:
            tag_value = _write_explicit_tag(flac_path, audio, UNKNOWN_VALUE)

        stats[tag_value] = stats.get(tag_value, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1

        if PRINT_EXPLICIT_TO_CONSOLE and tag_value == "Yes" and prev_explicit_tag != "Yes":
            if explicit_console_lines < MAX_EXPLICIT_CONSOLE_LINES:
                tqdm.write(f"EXPLICIT=Yes: {artist} - {album} - {title} ({source})")
                explicit_console_lines += 1
            elif not explicit_console_suppressed:
                tqdm.write("Further EXPLICIT=Yes messages suppressed")
                explicit_console_suppressed = True

        if tag_value == "Yes":
            explicit_playlist_entries.add(os.path.relpath(flac_path, ROOT))

        writer.writerow([flac_path, artist, album, title, tag_value, source])

with open(EXPLICIT_PLAYLIST_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("#EXTM3U\n")
    for relpath in sorted(explicit_playlist_entries):
        f.write(f"{relpath}\n")

print(
    "Summary: "
    f"Yes={stats.get('Yes', 0)} "
    f"No={stats.get('No', 0)} "
    f"Unknown={stats.get('Unknown', 0)}"
)
if source_counts:
    top_sources = sorted(source_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print("Top sources:")
    for k, v in top_sources:
        print(f"  {k}: {v}")