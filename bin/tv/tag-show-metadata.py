#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from mutagen.mp4 import MP4, MP4FreeForm

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _REPO_ROOT / "log"
_CACHE_DIR = _REPO_ROOT / "cache"
_CACHE_FILE = _CACHE_DIR / "show_metadata_cache.json"


def _utcnow_isoz():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_env():
    try:
        from dotenv import load_dotenv

        load_dotenv(_REPO_ROOT / ".env")
    except ImportError:
        pass


def _load_show_overrides():
    """Load manual show overrides from JSON file."""
    overrides_file = _REPO_ROOT / "config" / "show_tmdb_overrides.json"
    if not overrides_file.exists():
        return {}

    try:
        with open(overrides_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("overrides", {})
    except Exception as e:
        if os.getenv("DEBUG"):
            print(f"Warning: Could not load show overrides: {e}")
        return {}


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


def _tmdb_get_json(path, query=None, timeout=20):
    read_token = os.getenv("TMDB_READ_ACCESS_TOKEN")
    api_key = os.getenv("TMDB_API_KEY")
    if not read_token and not api_key:
        return None

    url = f"https://api.themoviedb.org/3{path}"

    headers = {"Accept": "application/json"}
    params = dict(query or {})
    if read_token:
        headers["Authorization"] = f"Bearer {read_token}"
    else:
        params["api_key"] = api_key

    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def parse_show_folder(folder_name):
    m = re.match(r"^(.+?)\s*\((\d{4})\)\s*$", folder_name)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return folder_name.strip(), None


def _extract_year_from_text(text):
    if not text:
        return None
    m = re.search(r"\((\d{4})\)", text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _parse_jellyfin_episode_filename(filename):
    m = re.match(
        r"^(?P<show>.+?)\s+-\s+S(?P<season>\d{2})E(?P<episode>\d{2})\s+-\s+"
        r"(?P<title>.+)\.(?P<ext>mp4|m4v)$",
        filename,
        re.IGNORECASE,
    )
    if not m:
        return None
    return {
        "show": m.group("show").strip(),
        "season": int(m.group("season")),
        "episode": int(m.group("episode")),
        "title": m.group("title").strip(),
        "ext": m.group("ext").lower(),
    }


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


def _set_mp4_value(mp4, key, value, force=False):
    if value is None:
        return False
    if not force and not _is_missing_mp4_tag(mp4, key):
        return False
    existing = mp4.get(key)
    if existing == value:
        return False
    mp4[key] = value
    return True


def _set_freeform_text(mp4, freeform_key, value, force=False):
    if not value:
        return False
    if not force and not _is_missing_mp4_tag(mp4, freeform_key):
        return False
    existing = None
    try:
        v = mp4.get(freeform_key)
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, (bytes, bytearray)):
                existing = bytes(first).decode("utf-8", errors="replace")
            elif hasattr(first, "decode"):
                existing = first.decode("utf-8", errors="replace")
            else:
                existing = str(first)
    except Exception:
        existing = None

    if existing == value:
        return False
    mp4[freeform_key] = [MP4FreeForm(value.encode("utf-8"))]
    return True


def _would_set_mp4_value(mp4, key, value, force=False):
    if value is None:
        return False
    if not force and not _is_missing_mp4_tag(mp4, key):
        return False
    existing = mp4.get(key)
    return existing != value


def _would_set_freeform_text(mp4, freeform_key, value, force=False):
    if not value:
        return False
    if not force and not _is_missing_mp4_tag(mp4, freeform_key):
        return False
    existing = None
    try:
        v = mp4.get(freeform_key)
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, (bytes, bytearray)):
                existing = bytes(first).decode("utf-8", errors="replace")
            elif hasattr(first, "decode"):
                existing = first.decode("utf-8", errors="replace")
            else:
                existing = str(first)
    except Exception:
        existing = None

    return existing != value


def _plan_episode_tag_updates(mp4, show_title, show_year, season, episode, ep_data, force=False):
    planned = []

    # Always enforce ordering tags
    if _would_set_mp4_value(mp4, "tvsh", [show_title], force=True):
        planned.append("tvsh")
    if _would_set_mp4_value(mp4, "tvsn", [int(season)], force=True):
        planned.append("tvsn")
    if _would_set_mp4_value(mp4, "tves", [int(episode)], force=True):
        planned.append("tves")

    ep_name = None
    ep_overview = None
    ep_air_date = None
    if isinstance(ep_data, dict):
        ep_name = ep_data.get("name")
        ep_overview = ep_data.get("overview")
        ep_air_date = ep_data.get("air_date")

    if isinstance(ep_name, str) and ep_name.strip():
        ep_name = ep_name.strip()
        if _would_set_mp4_value(mp4, "tven", [ep_name], force=force):
            planned.append("tven")
        if _would_set_mp4_value(mp4, "\xa9nam", [ep_name], force=force):
            planned.append("\xa9nam")

    if isinstance(ep_overview, str) and ep_overview.strip():
        ep_overview = ep_overview.strip()
        if _would_set_mp4_value(mp4, "\xa9des", [ep_overview], force=force):
            planned.append("\xa9des")

    year_to_write = None
    if isinstance(ep_air_date, str) and len(ep_air_date) >= 4 and ep_air_date[:4].isdigit():
        year_to_write = ep_air_date[:4]
    elif show_year:
        year_to_write = str(show_year)

    if year_to_write and _would_set_mp4_value(mp4, "\xa9day", [year_to_write], force=force):
        planned.append("\xa9day")

    if isinstance(ep_data, dict) and isinstance(ep_data.get("id"), int):
        if _would_set_freeform_text(
            mp4,
            "----:com.apple.iTunes:tmdb_episode_id",
            str(ep_data["id"]),
            force=force,
        ):
            planned.append("tmdb_episode_id")

    return planned


def _infer_show_context(file_path):
    parsed = _parse_jellyfin_episode_filename(file_path.name)

    show_dir = file_path.parent
    if show_dir.name.lower().startswith("season ") or show_dir.name.lower() == "specials":
        show_dir = show_dir.parent

    show_title, show_year = parse_show_folder(show_dir.name)

    if parsed and parsed.get("show"):
        show_title = parsed["show"]

    if parsed and show_year is None:
        show_year = _extract_year_from_text(parsed.get("title"))

    return {
        "show_dir": show_dir,
        "show_title": show_title,
        "show_year": show_year,
        "parsed": parsed,
    }


def _cache_key_show(show_title, show_year):
    show_title = (show_title or "").strip().lower()
    return f"show:{show_title}:{show_year or ''}"


def _cache_key_episode(show_id, season, episode):
    return f"episode:{show_id}:S{int(season):02d}E{int(episode):02d}"


def _get_omdb_show_data(imdb_id, language="en-US"):
    """Fetch TV show data from OMDb using IMDb ID."""
    if not imdb_id:
        return None

    # Ensure IMDb ID starts with 'tt'
    if not imdb_id.startswith("tt"):
        imdb_id = f"tt{imdb_id}"

    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        print("Warning: OMDB_API_KEY not set, cannot use IMDb lookup")
        return None

    try:
        url = "http://www.omdbapi.com/"
        params = {"apikey": api_key, "i": imdb_id, "r": "json"}

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "True" and data.get("Type") in [
            "series",
            "movie",
        ]:
            return data
        else:
            if data.get("Error"):
                print(f"OMDb error: {data.get('Error')}")
            else:
                print("OMDb: Not found or not a series/movie")
            return None
    except Exception as e:
        print(f"OMDb lookup failed: {e}")
        return None


def _tmdb_find_show_id(cache, show_title, show_year=None, language="en-US", verbose=False):
    key = _cache_key_show(show_title, show_year)
    cached = cache.get(key)
    if isinstance(cached, dict) and isinstance(cached.get("show_id"), int):
        return cached["show_id"]
    if isinstance(cached, dict) and cached.get("not_found") is True:
        return None

    query = {
        "query": show_title,
        "page": 1,
        "include_adult": "false",
        "language": language,
    }
    if show_year:
        query["first_air_date_year"] = str(show_year)

    data = _tmdb_get_json("/search/tv", query)
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        cache[key] = {"not_found": True, "fetched_at": _utcnow_isoz()}
        return None

    best = results[0]
    if show_year:
        for r in results:
            fad = r.get("first_air_date") or ""
            if fad.startswith(f"{show_year}-"):
                best = r
                break

    show_id = best.get("id")
    if not isinstance(show_id, int):
        cache[key] = {"not_found": True, "fetched_at": _utcnow_isoz()}
        return None

    cache[key] = {
        "show_id": show_id,
        "name": best.get("name"),
        "first_air_date": best.get("first_air_date"),
        "fetched_at": _utcnow_isoz(),
    }

    if verbose:
        print(f"  TMDb show match: {best.get('name')} (id={show_id})")

    return show_id


def _tmdb_get_episode(cache, show_id, season, episode, language="en-US"):
    key = _cache_key_episode(show_id, season, episode)
    cached = cache.get(key)
    if isinstance(cached, dict) and cached.get("not_found"):
        return None
    if isinstance(cached, dict) and isinstance(cached.get("episode"), dict):
        return cached["episode"]

    try:
        ep = _tmdb_get_json(
            f"/tv/{show_id}/season/{int(season)}/episode/{int(episode)}",
            {"language": language},
        )
        if not ep:
            cache[key] = {"not_found": True, "fetched_at": _utcnow_isoz()}
            return None
    except Exception:
        cache[key] = {"not_found": True, "fetched_at": _utcnow_isoz()}
        return None

    cache[key] = {"episode": ep, "fetched_at": _utcnow_isoz()}
    return ep


def _write_episode_metadata(
    file_path,
    show_title,
    show_year,
    season,
    episode,
    ep_data,
    dry_run=False,
    force=False,
):
    if not MUTAGEN_AVAILABLE:
        print("  Warning: mutagen not available; skipping file")
        return False

    try:
        mp4 = MP4(file_path)
    except Exception as e:
        print(f"  Error: could not read MP4 tags: {e}")
        return False

    changed = False

    # Always enforce ordering tags based on filename (idempotent if already correct)
    changed = _set_mp4_value(mp4, "tvsh", [show_title], force=True) or changed
    changed = _set_mp4_value(mp4, "tvsn", [int(season)], force=True) or changed
    changed = _set_mp4_value(mp4, "tves", [int(episode)], force=True) or changed

    ep_name = None
    ep_overview = None
    ep_air_date = None
    if isinstance(ep_data, dict):
        ep_name = ep_data.get("name")
        ep_overview = ep_data.get("overview")
        ep_air_date = ep_data.get("air_date")

    if isinstance(ep_name, str) and ep_name.strip():
        changed = _set_mp4_value(mp4, "tven", [ep_name.strip()], force=force) or changed
        changed = _set_mp4_value(mp4, "\xa9nam", [ep_name.strip()], force=force) or changed

    if isinstance(ep_overview, str) and ep_overview.strip():
        changed = _set_mp4_value(mp4, "\xa9des", [ep_overview.strip()], force=force) or changed

    year_to_write = None
    if isinstance(ep_air_date, str) and len(ep_air_date) >= 4 and ep_air_date[:4].isdigit():
        year_to_write = ep_air_date[:4]
    elif show_year:
        year_to_write = str(show_year)

    if year_to_write:
        changed = _set_mp4_value(mp4, "\xa9day", [year_to_write], force=force) or changed

    if isinstance(ep_data, dict) and isinstance(ep_data.get("id"), int):
        changed = (
            _set_freeform_text(
                mp4,
                "----:com.apple.iTunes:tmdb_episode_id",
                str(ep_data["id"]),
                force=force,
            )
            or changed
        )

    if not changed:
        return False

    if dry_run:
        return True

    mp4.save()
    return True


def _find_video_files(paths, recursive=False):
    out = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix.lower() in (".mp4", ".m4v"):
            out.append(path)
        elif path.is_dir():
            if recursive:
                for f in path.rglob("*"):
                    if f.is_file() and f.suffix.lower() in (".mp4", ".m4v"):
                        out.append(f)
            else:
                for f in path.iterdir():
                    if f.is_file() and f.suffix.lower() in (".mp4", ".m4v"):
                        out.append(f)
    return sorted(set(out))


def main():
    _load_env()
    parser = argparse.ArgumentParser(description="Tag TV show episode MP4s with metadata from TMDb")
    parser.add_argument("paths", nargs="+", help="Episode file(s) or directory")
    parser.add_argument("--recursive", action="store_true", help="Recurse into directories")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing tags (default is fill-missing)",
    )
    parser.add_argument("--language", default="en-US", help="TMDb language (default: en-US)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--tmdb-id", type=int, help="Override TMDb show ID (skips search)")
    parser.add_argument(
        "--imdb-id",
        help="Override IMDb ID (e.g., 'tt1234567') - converts to TMDb ID",
    )
    args = parser.parse_args()

    files = _find_video_files(args.paths, recursive=args.recursive)
    if not files:
        print("No episode files found")
        return

    cache = _load_cache()
    overrides = _load_show_overrides()
    cache_dirty = False

    wrote = 0
    skipped = 0
    errors = 0

    printed_show_not_found = set()
    printed_episode_not_found = set()
    printed_show_match = set()

    for f in files:
        ctx = _infer_show_context(f)
        parsed = ctx.get("parsed")
        show_title = ctx.get("show_title")
        show_year = ctx.get("show_year")

        if not parsed:
            print(f"Skipping (unrecognized filename): {f}")
            skipped += 1
            continue

        season = parsed["season"]
        episode = parsed["episode"]
        local_title = parsed.get("title")

        if args.verbose:
            print(f"\nProcessing: {f}")
            print(f"  Show: {show_title} ({show_year})")
            print(f"  S{season:02d}E{episode:02d}")

        try:
            # Check for manual overrides first
            override_key = f"{show_title} ({show_year})" if show_year else show_title
            manual_override = overrides.get(override_key)

            if manual_override:
                # Use manual override
                if manual_override.get("imdb_id"):
                    # Use IMDb ID from override
                    omdb_data = _get_omdb_show_data(manual_override["imdb_id"], args.language)
                    if omdb_data is None:
                        print(
                            f"  Could not fetch IMDb data for {manual_override['imdb_id']} "
                            f"(from override)"
                        )
                        skipped += 1
                        continue

                    show_name = omdb_data.get("Title", "Unknown")
                    show_year_override = omdb_data.get("Year", "").split("–")[0]
                    if args.verbose:
                        print(
                            f"  IMDb show (override): {show_name} ({show_year_override}) "
                            f"[id={manual_override['imdb_id']}]"
                        )

                    episode_title = local_title or f"Episode {episode}"
                    if show_name and episode_title:
                        if ":" in show_name and "-" in episode_title:
                            episode_title = episode_title.replace("-", ":", 1)

                    ep_data = {
                        "name": episode_title,
                        "overview": "",
                        "air_date": "",
                        "episode_number": episode,
                        "season_number": season,
                        "imdb_id": manual_override["imdb_id"],
                    }
                    show_id = f"imdb_{manual_override['imdb_id']}"

                elif manual_override.get("tmdb_id"):
                    # Use TMDb ID from override
                    show_id = manual_override["tmdb_id"]
                    try:
                        show_info = _tmdb_get_json(f"/tv/{show_id}", {"language": args.language})
                        if show_info:
                            if args.verbose:
                                print(
                                    f"  TMDb show (override): {show_info.get('name')} "
                                    f"({show_info.get('first_air_date', 'unknown')}) [id={show_id}]"
                                )
                    except Exception:
                        if args.verbose:
                            print(f"  TMDb show (override): id={show_id}")

                    ep_data = _tmdb_get_episode(
                        cache, show_id, season, episode, language=args.language
                    )
                    cache_dirty = True
                    if not isinstance(ep_data, dict):
                        ep_nf_key = (int(show_id), int(season), int(episode))
                        if ep_nf_key not in printed_episode_not_found:
                            if local_title:
                                if args.verbose:
                                    print(
                                        f"  No TMDb episode match for S{season:02d}E{episode:02d} "
                                        f"({local_title})"
                                    )
                            else:
                                if args.verbose:
                                    print(
                                        f"  No TMDb episode match for S{season:02d}E{episode:02d}"
                                    )
                            printed_episode_not_found.add(ep_nf_key)
                        skipped += 1
                        continue
                else:
                    if args.verbose:
                        print(f"  Invalid override for {override_key}")
                    skipped += 1
                    continue

            # Use provided TMDb ID, convert IMDb ID, or search for it
            elif args.tmdb_id:
                show_id = args.tmdb_id
                if args.verbose:
                    print(f"  Using provided TMDb ID: {show_id}")
                # Get show info for display
                try:
                    show_info = _tmdb_get_json(f"/tv/{show_id}", {"language": args.language})
                    if show_info:
                        print(
                            f"  TMDb show: {show_info.get('name')} "
                            f"({show_info.get('first_air_date', 'unknown')}) [id={show_id}]"
                        )
                except Exception:
                    print(f"  TMDb show: id={show_id}")
            elif args.imdb_id:
                # Use IMDb ID via OMDb for show info
                omdb_data = _get_omdb_show_data(args.imdb_id, args.language)
                if omdb_data is None:
                    print(f"  Could not fetch IMDb data for {args.imdb_id}")
                    skipped += 1
                    continue

                if args.verbose:
                    print(f"  Using IMDb ID: {args.imdb_id}")

                # Display show info from OMDb
                show_name = omdb_data.get("Title", "Unknown")
                show_year = omdb_data.get("Year", "").split("–")[0]  # Take first year for range
                print(f"  IMDb show: {show_name} ({show_year}) [id={args.imdb_id}]")

                # For IMDb mode, we'll use filename-based episode info
                # OMDb doesn't have reliable episode data for TV series
                # But fix common filesystem character conversions
                episode_title = local_title or f"Episode {episode}"

                # Fix common filesystem character conversions
                # macOS converts ":" to "-" in filenames
                if show_name and episode_title:
                    # If show name contains ":", fix episode title to match
                    if ":" in show_name and "-" in episode_title:
                        # Replace first dash with colon to match show title format
                        episode_title = episode_title.replace("-", ":", 1)

                ep_data = {
                    "name": episode_title,
                    "overview": "",
                    "air_date": "",
                    "episode_number": episode,
                    "season_number": season,
                    "imdb_id": args.imdb_id,
                }
                show_id = f"imdb_{args.imdb_id}"  # Use special prefix for IMDb shows
            else:
                show_id = _tmdb_find_show_id(
                    cache,
                    show_title,
                    show_year,
                    language=args.language,
                    verbose=args.verbose,
                )
                if show_id is None:
                    show_nf_key = (show_title or "", show_year or "")
                    if show_nf_key not in printed_show_not_found:
                        if args.verbose:
                            print(f"  No TMDb show match for: {show_title} ({show_year})")
                        printed_show_not_found.add(show_nf_key)
                    skipped += 1
                    cache_dirty = True
                    continue

                show_match_key = (show_title or "", show_year or "")
                if show_match_key not in printed_show_match:
                    cached_show = cache.get(_cache_key_show(show_title, show_year))
                    if isinstance(cached_show, dict) and isinstance(
                        cached_show.get("show_id"), int
                    ):
                        matched_name = cached_show.get("name") or show_title
                        matched_date = cached_show.get("first_air_date")
                        if matched_date:
                            if args.verbose:
                                print(
                                    f"  TMDb show match: {show_title} ({show_year}) -> "
                                    f"{matched_name} ({matched_date}) [id={cached_show['show_id']}]"
                                )
                        else:
                            if args.verbose:
                                print(
                                    f"  TMDb show match: {show_title} ({show_year}) -> "
                                    f"{matched_name} [id={cached_show['show_id']}]"
                                )
                    else:
                        if args.verbose:
                            print(f"  TMDb show match: {show_title} ({show_year}) -> id={show_id}")
                    printed_show_match.add(show_match_key)

            # Get episode data (skip for IMDb shows since we created it above)
            if args.imdb_id or (manual_override and manual_override.get("imdb_id")):
                # ep_data already created above from filename/local title
                cache_dirty = True
                if args.verbose:
                    print("  Using filename-based episode data for IMDb show")
            else:
                ep_data = _tmdb_get_episode(cache, show_id, season, episode, language=args.language)
                cache_dirty = True
                if not isinstance(ep_data, dict):
                    ep_nf_key = (int(show_id), int(season), int(episode))
                    if ep_nf_key not in printed_episode_not_found:
                        if local_title:
                            if args.verbose:
                                print(
                                    f"  No TMDb episode match for S{season:02d}E{episode:02d} "
                                    f"({local_title})"
                                )
                        else:
                            if args.verbose:
                                print(f"  No TMDb episode match for S{season:02d}E{episode:02d}")
                        printed_episode_not_found.add(ep_nf_key)
                    skipped += 1
                    continue

            planned_updates = []
            try:
                if MUTAGEN_AVAILABLE:
                    mp4_existing = MP4(f)
                    planned_updates = _plan_episode_tag_updates(
                        mp4_existing,
                        show_title=show_title,
                        show_year=show_year,
                        season=season,
                        episode=episode,
                        ep_data=ep_data,
                        force=args.force,
                    )
            except Exception:
                planned_updates = []

            did = _write_episode_metadata(
                f,
                show_title=show_title,
                show_year=show_year,
                season=season,
                episode=episode,
                ep_data=ep_data,
                dry_run=args.dry_run,
                force=args.force,
            )

            if did:
                wrote += 1
                tmdb_ep_title = None
                if isinstance(ep_data.get("name"), str) and ep_data.get("name").strip():
                    tmdb_ep_title = ep_data.get("name").strip()
                if args.dry_run:
                    fields = ",".join(planned_updates) if planned_updates else "(unknown)"
                    if local_title and tmdb_ep_title and local_title != tmdb_ep_title:
                        print(
                            f"  [DRY RUN] S{season:02d}E{episode:02d}: {local_title} -> "
                            f"{tmdb_ep_title} [{fields}]"
                        )
                    elif local_title:
                        print(f"  [DRY RUN] S{season:02d}E{episode:02d}: {local_title} [{fields}]")
                    elif tmdb_ep_title:
                        print(
                            f"  [DRY RUN] S{season:02d}E{episode:02d}: {tmdb_ep_title} [{fields}]"
                        )
                    else:
                        print(f"  [DRY RUN] S{season:02d}E{episode:02d} [{fields}]")
                else:
                    print(f"  Updated tags: S{season:02d}E{episode:02d}")
            else:
                skipped += 1
                if args.verbose:
                    print(f"  No changes needed: S{season:02d}E{episode:02d}")

        except Exception as e:
            print(f"  Error: {e}")
            errors += 1

    if cache_dirty:
        _save_cache(cache)

    if args.dry_run:
        print(
            f"\nDry run completed. Would update: {wrote}. "
            f"Skipped/no-op: {skipped}. Errors: {errors}."
        )
    else:
        print(
            f"\nAll updates completed. Updated: {wrote}. "
            f"Skipped/no-op: {skipped}. Errors: {errors}."
        )


if __name__ == "__main__":
    sys.exit(main())
