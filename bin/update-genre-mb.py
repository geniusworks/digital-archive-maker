#!/usr/bin/env python3
"""Update genre metadata for FLAC files using MusicBrainz.

This script updates genre tags for FLAC files by:
1. Checking if genre tag already exists (skips if present)
2. Fetching genre information from MusicBrainz
3. Writing genre tags to FLAC files
4. Supporting dry-run mode and verbose output

Usage:
    python3 bin/update-genre-mb.py /path/to/music/folder
    python3 bin/update-genre-mb.py /path/to/music/folder --dry-run
    python3 bin/update-genre-mb.py /path/to/music/folder --recursive
"""

import argparse
import json
import os
import signal
import ssl
import sys
import time
import urllib.error
from pathlib import Path
from mutagen.flac import FLAC
from typing import Dict, List, Optional, Set

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = None

ACTIVE_TQDM = False


def _log(msg: str) -> None:
    if HAS_TQDM and ACTIVE_TQDM and tqdm is not None:
        try:
            tqdm.write(msg)
            return
        except Exception:
            pass
    print(msg)

# Global flag for graceful shutdown
SHUTDOWN_REQUESTED = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True
    print("\n\nInterrupt received. Finishing current file and saving cache...")
    print("Use Ctrl+C again to force exit.")

# Set up signal handler
signal.signal(signal.SIGINT, signal_handler)

# Global cache for genre lookups to avoid repeated API calls
GENRE_CACHE: Dict[str, str] = {}
CACHE_FILE = Path.home() / ".cache" / "genre_cache.json"

def load_cache():
    """Load genre cache from disk."""
    global GENRE_CACHE
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                GENRE_CACHE = json.load(f)
            print(f"Loaded {len(GENRE_CACHE)} cached genre entries")
    except Exception as e:
        print(f"Warning: Could not load cache: {e}")
        GENRE_CACHE = {}

def save_cache():
    """Save genre cache to disk."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(GENRE_CACHE, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")

def normalize_tag_value(value: str) -> str:
    """Normalize a tag value by trimming and cleaning."""
    if not value:
        return ""
    return str(value).strip()


def _cache_key_artist_album(artist: str, album: str) -> str:
    a = normalize_tag_value(artist).lower()
    b = normalize_tag_value(album).lower()
    return f"artist={a}||album={b}"


def _cache_key_artist(artist: str) -> str:
    a = normalize_tag_value(artist).lower()
    return f"artist={a}"

def retry_musicbrainz_call(func, *args, max_retries=3, base_delay=1):
    """Retry MusicBrainz API calls with exponential backoff for network errors."""
    for attempt in range(max_retries):
        try:
            return func(*args)
        except (ssl.SSLError, urllib.error.URLError, OSError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                _log(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
                _log(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            else:
                _log(f"Failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            # Non-network errors, don't retry
            raise

def get_genre_from_musicbrainz(artist: str, album: str, title: str = "") -> Optional[str]:
    """Try to get genre information from MusicBrainz."""
    try:
        import musicbrainzngs
        musicbrainzngs.set_useragent("update-genre-mb", "1.0", "https://yourdomain.example")
        
        # Cache by artist+album so we don't re-query per-track.
        # Also cache negative results (empty string) to avoid repeated failed lookups.
        cache_key_album = _cache_key_artist_album(artist, album)
        cache_key_artist = _cache_key_artist(artist)

        cached = GENRE_CACHE.get(cache_key_album)
        if cached is not None:
            return cached or None

        # If no album tag or album lookup not yet cached, allow artist-level cache.
        if not normalize_tag_value(album):
            cached_artist = GENRE_CACHE.get(cache_key_artist)
            if cached_artist is not None:
                return cached_artist or None
        
        # Try release group lookup first (more reliable for genres)
        def search_release_groups():
            return musicbrainzngs.search_release_groups(artist=artist, release=album, limit=1)
        
        result = retry_musicbrainz_call(search_release_groups)
        if result.get('release-group-list'):
            release_group = result['release-group-list'][0]
            release_group_id = release_group['id']
            
            # Get release group details with tags
            try:
                def get_release_group():
                    return musicbrainzngs.get_release_group_by_id(release_group_id, includes=['tags'])
                
                rg_info = retry_musicbrainz_call(get_release_group)
                tags = rg_info.get('release-group', {}).get('tag-list', [])
                
                # Extract genre tags (filter out non-genre tags)
                genre_tags = []
                non_genre_tags = {
                    'seen live', 'favorite', 'owned', 'wants', 'recommendations',
                    'beautiful', 'amazing', 'awesome', 'best', 'classic', 'great',
                    'love', 'liked', 'disliked', 'overrated', 'underrated',
                    # Decade/era tags (not real genres)
                    '90s', '80s', '70s', '60s', '50s', '2000s', '2010s', '2020s',
                    '1990s', '1980s', '1970s', '1960s', '1950s',
                    # Quality/subjective tags
                    'catchy', 'danceable', 'melodic', 'energetic', 'chill',
                    'relaxing', 'upbeat', 'mellow', 'dark', 'happy', 'sad'
                }
                
                # Priority genres (prefer these over decade tags)
                priority_genres = {
                    'rock', 'pop', 'jazz', 'classical', 'electronic', 'hip hop',
                    'rap', 'r&b', 'soul', 'funk', 'reggae', 'country', 'folk',
                    'blues', 'metal', 'punk', 'alternative', 'indie', 'ambient',
                    'techno', 'house', 'trance', 'dubstep', 'drum and bass',
                    'new wave', 'post-punk', 'grunge', 'shoegaze', 'emo',
                    'ska', 'punk rock', 'hard rock', 'progressive rock',
                    'synthpop', 'new romantic', 'gothic rock', 'indie rock'
                }
                
                for tag in tags:
                    tag_name = normalize_tag_value(tag.get('name', ''))
                    if tag_name and tag_name.lower() not in non_genre_tags:
                        genre_tags.append(tag_name)
                
                if genre_tags:
                    # Prioritize real genres over decade/era tags
                    priority_matches = [g for g in genre_tags if g.lower() in priority_genres]
                    if priority_matches:
                        genre = priority_matches[0]  # Use first priority genre found
                    else:
                        # Fall back to first available genre (but not decades)
                        genre = sorted(genre_tags, key=lambda x: x.lower())[0]

                    # Cache the successful lookup
                    GENRE_CACHE[cache_key_album] = genre
                    # Also populate an artist-level cache if not already present.
                    if GENRE_CACHE.get(cache_key_artist) is None:
                        GENRE_CACHE[cache_key_artist] = genre
                    return genre
                    
            except Exception:
                pass
        
        # Fallback to artist lookup
        try:
            def search_artists():
                return musicbrainzngs.search_artists(artist=artist, limit=1)
            
            artist_result = retry_musicbrainz_call(search_artists)
            if artist_result.get('artist-list'):
                artist_info = artist_result['artist-list'][0]
                artist_id = artist_info['id']
                
                def get_artist():
                    return musicbrainzngs.get_artist_by_id(artist_id, includes=['tags'])
                
                artist_info = retry_musicbrainz_call(get_artist)
                tags = artist_info.get('artist', {}).get('tag-list', [])
                
                genre_tags = []
                non_genre_tags = {
                    'seen live', 'favorite', 'owned', 'wants', 'recommendations',
                    'beautiful', 'amazing', 'awesome', 'best', 'classic', 'great',
                    'love', 'liked', 'disliked', 'overrated', 'underrated',
                    # Decade/era tags (not real genres)
                    '90s', '80s', '70s', '60s', '50s', '2000s', '2010s', '2020s',
                    '1990s', '1980s', '1970s', '1960s', '1950s',
                    # Quality/subjective tags
                    'catchy', 'danceable', 'melodic', 'energetic', 'chill',
                    'relaxing', 'upbeat', 'mellow', 'dark', 'happy', 'sad'
                }
                
                # Priority genres (prefer these over decade tags)
                priority_genres = {
                    'rock', 'pop', 'jazz', 'classical', 'electronic', 'hip hop',
                    'rap', 'r&b', 'soul', 'funk', 'reggae', 'country', 'folk',
                    'blues', 'metal', 'punk', 'alternative', 'indie', 'ambient',
                    'techno', 'house', 'trance', 'dubstep', 'drum and bass',
                    'new wave', 'post-punk', 'grunge', 'shoegaze', 'emo',
                    'ska', 'punk rock', 'hard rock', 'progressive rock',
                    'synthpop', 'new romantic', 'gothic rock', 'indie rock'
                }
                
                for tag in tags:
                    tag_name = normalize_tag_value(tag.get('name', ''))
                    if tag_name and tag_name.lower() not in non_genre_tags:
                        genre_tags.append(tag_name)
                
                if genre_tags:
                    # Prioritize real genres over decade/era tags
                    priority_matches = [g for g in genre_tags if g.lower() in priority_genres]
                    if priority_matches:
                        genre = priority_matches[0]  # Use first priority genre found
                    else:
                        # Fall back to first available genre (but not decades)
                        genre = sorted(genre_tags, key=lambda x: x.lower())[0]

                    # Cache the successful lookup
                    GENRE_CACHE[cache_key_album] = genre
                    GENRE_CACHE[cache_key_artist] = genre
                    return genre
                    
        except Exception:
            pass
        
        # Cache the miss to avoid repeated lookups.
        # Only cache the artist-level miss when we don't have album context.
        GENRE_CACHE[cache_key_album] = ""
        if not normalize_tag_value(album):
            GENRE_CACHE[cache_key_artist] = ""
        return None
        
    except ImportError:
        print("MusicBrainz library not available, install with: pip install musicbrainzngs")
        return None
    except Exception as e:
        print(f"Error fetching genre from MusicBrainz for {artist} - {album}: {e}")
        return None

def read_flac_tags(flac_path: Path) -> Dict[str, str]:
    """Read tags from a FLAC file."""
    try:
        audio = FLAC(flac_path)
        tags = {}
        for key in audio.keys():
            if audio[key]:
                tags[key.lower()] = str(audio[key][0])
        return tags
    except Exception as e:
        print(f"Error reading tags from {flac_path}: {e}")
        return {}

def write_flac_tags(flac_path: Path, tags: Dict[str, str]) -> bool:
    """Write tags to a FLAC file."""
    try:
        audio = FLAC(flac_path)
        for key, value in tags.items():
            if value:
                audio[key] = [value]
        audio.save()
        return True
    except Exception as e:
        print(f"Error writing tags to {flac_path}: {e}")
        return False

def update_file_genre(flac_path: Path, dry_run: bool = False, verbose: bool = False, force: bool = False) -> bool:
    """Update genre for a single FLAC file."""
    # Read current tags
    current_tags = read_flac_tags(flac_path)
    
    # Skip if genre already exists (unless force mode)
    if not force and 'genre' in current_tags and current_tags['genre']:
        if verbose:
            print(f"  Skipping {flac_path.name} (already has genre: {current_tags['genre']})")
        return "skipped"
    
    # Show current genre if force mode
    if force and 'genre' in current_tags and current_tags['genre']:
        if verbose:
            print(f"  Force updating {flac_path.name} (current: {current_tags['genre']})")
    elif verbose:
        print(f"  Processing {flac_path.name}")
    
    # Get metadata for lookup
    artist = current_tags.get('artist', '')
    album = current_tags.get('album', '')
    title = current_tags.get('title', '')
    
    if not artist:
        if verbose:
            print(f"  Skipping {flac_path.name} (no artist tag)")
        return "skipped"
    
    # Get genre from MusicBrainz
    genre = get_genre_from_musicbrainz(artist, album, title)
    
    if not genre:
        if verbose:
            print(f"  No genre found for {artist} - {album}")
        return "unresolved"
    
    # Update tags
    new_tags = {'GENRE': genre}
    
    if verbose or force:
        current_genre = current_tags.get('genre', '')
        if current_genre:
            print(f"  Updating {flac_path.name}: {artist} - {album}")
            print(f"    {current_genre} -> {genre}")
        else:
            print(f"  Setting {flac_path.name}: {artist} - {album} -> {genre}")
    
    if dry_run:
        print(f"    [DRY RUN] Would set genre to '{genre}'")
        return "updated"
    else:
        if write_flac_tags(flac_path, new_tags):
            return "updated"
        else:
            print(f"    Failed to update genre")
            return False

def update_genres_in_folder(folder_path: Path, recursive: bool = False, 
                           dry_run: bool = False, verbose: bool = False, force: bool = False) -> int:
    """Update genres for FLAC files in a folder."""
    global SHUTDOWN_REQUESTED
    global ACTIVE_TQDM
    updated_count = 0
    skipped_count = 0
    unresolved_count = 0
    
    if recursive:
        flac_files = list(folder_path.rglob("*.flac"))
    else:
        flac_files = list(folder_path.glob("*.flac"))
    
    if not flac_files:
        print(f"No FLAC files found in {folder_path}")
        return 0
    
    flac_files = sorted(flac_files)
    mode_text = "FORCE UPDATING" if force else "Updating"
    print(f"{mode_text} genre metadata for {len(flac_files)} FLAC files...")

    # Prefer tqdm when its output stream is a TTY. tqdm defaults to stderr; match that.
    use_tqdm = HAS_TQDM and not verbose and sys.stderr.isatty()
    pbar = None

    if use_tqdm:
        ACTIVE_TQDM = True
        # Use default tqdm formatting (same style as tag-explicit-mb) for compact bar width.
        pbar = tqdm(
            flac_files,
            desc="Tagging genre",
            file=sys.stderr,
            dynamic_ncols=False,
            ncols=80,
            miniters=1,
            mininterval=0.05,
        )
        flac_iterator = pbar
    else:
        if HAS_TQDM and not verbose and not sys.stderr.isatty():
            _log("Note: progress bar disabled (stderr is not a TTY); showing periodic progress instead")
        flac_iterator = flac_files
    
    for i, flac_file in enumerate(flac_iterator, start=1):
        # Check for shutdown request
        if SHUTDOWN_REQUESTED:
            if pbar is not None:
                pbar.close()
            ACTIVE_TQDM = False
            print(f"\nGraceful shutdown requested. Updated {updated_count} files before shutdown.")
            break
        
        result = update_file_genre(flac_file, dry_run, verbose, force)
        if result == "skipped":
            skipped_count += 1
        elif result == "unresolved":
            unresolved_count += 1
        elif result == "updated":
            updated_count += 1
            
        # If no tqdm bar (e.g. non-TTY), show periodic progress without spamming
        if not use_tqdm and (i == 1 or i % 500 == 0):
            print(f"Progress: {i}/{len(flac_files)}")
    
    if pbar is not None:
        pbar.close()
    ACTIVE_TQDM = False

    if unresolved_count:
        print(f"Processed: {updated_count} tracks (skipped {skipped_count} already tagged, unresolved {unresolved_count})")
    else:
        print(f"Processed: {updated_count} tracks (skipped {skipped_count} already tagged)")
    
    return updated_count

def main():
    parser = argparse.ArgumentParser(description='Update genre metadata for FLAC files')
    parser.add_argument('folder', help='Folder containing FLAC files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--recursive', action='store_true', help='Process subdirectories recursively')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--force', action='store_true', help='Force update existing genre tags')
    
    args = parser.parse_args()
    
    folder_path = Path(args.folder).resolve()
    if not folder_path.exists():
        print(f"Error: Path {folder_path} does not exist")
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
    
    if args.force:
        print("FORCE MODE - Will overwrite existing genre tags")
    
    # Load cache at start
    load_cache()
    
    updated_count = update_genres_in_folder(
        folder_path, 
        recursive=args.recursive,
        dry_run=args.dry_run,
        verbose=args.verbose,
        force=args.force
    )
    
    # Save cache at end (unless dry run)
    if not args.dry_run and not SHUTDOWN_REQUESTED:
        save_cache()
        print(f"Saved genre cache with {len(GENRE_CACHE)} entries")
    elif SHUTDOWN_REQUESTED and not args.dry_run:
        save_cache()
        print(f"Graceful shutdown: Saved genre cache with {len(GENRE_CACHE)} entries")
    
    if SHUTDOWN_REQUESTED:
        print(f"Script interrupted by user. Progress saved.")
    elif args.dry_run:
        action = "Would update" if args.force else "Would update"
        print(f"\n{action} {updated_count} files")
    else:
        action = "Force updated" if args.force else "Updated"
        print(f"\n{action} {updated_count} files")

if __name__ == '__main__':
    main()
