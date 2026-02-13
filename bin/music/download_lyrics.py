#!/usr/bin/env python3
"""
Lyrics Downloader for Music Library
==================================

Downloads lyrics for songs and saves them in Jellyfin-compatible formats.
Supports multiple lyrics sources and saves as .lrc files with timestamps.

USAGE:
    python3 bin/music/download_lyrics.py "/path/to/music/library"
    python3 bin/music/download_lyrics.py "/path/to/album" --recursive
    python3 bin/music/download_lyrics.py "/path/to/song.mp3"

OUTPUT:
    - .lrc files with synchronized lyrics (Jellyfin compatible)
    - Skips files that already have lyrics
    - Respects rate limits and handles errors gracefully

REQUIRES:
    pip install lyricsgenius requests
"""

import argparse
import os
import sys
import re
import time
import unicodedata
import json
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote

# Load environment variables from .env file
def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # Fallback: simple .env parsing without overwriting existing env vars
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()

try:
    import lyricsgenius
    import requests
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3NoHeaderError
    from mutagen.mp4 import MP4
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("Install with: pip install lyricsgenius requests")
    sys.exit(1)

# Configuration
CACHE_FILE = Path.home() / ".digital_library_lyrics_cache.json"
FAILED_FILE = Path(__file__).parent.parent.parent / "log" / "failed_lyrics_lookups.txt"
SKIP_FILE = Path(__file__).parent.parent.parent / "log" / "skip_lyrics_lookups.txt"
RATE_LIMIT = 0.2  # seconds between requests for non-Genius sources (lyrics.ovh)
GENIUS_RATE_LIMIT = 3.0  # longer delay for Genius to avoid 429s
GENIUS_HOURLY_LIMIT = 60  # estimated hourly limit per token
GENIUS_REQUESTS_PER_MINUTE = 10  # requests per minute (6s intervals)
MAX_RATE_LIMIT_FAILURES = 5  # exit after this many real Genius 429 failures in a single run
MAX_FALLBACK_ACCESS_FAILURES = 50  # exit after this many consecutive lyrics.ovh access failures
GENIUS_SEARCH_TIMEOUT = 30  # hard timeout (seconds) for a single Genius search
ALBUM_COOLDOWN = 15  # seconds to pause between albums with new downloads
USER_AGENT = "Digital-Library-Lyrics-Downloader/1.0"

class LyricsDownloader:
    def __init__(self, genius_token: Optional[str] = None, retry_failed: bool = False):
        """Initialize lyrics downloader with optional Genius API token."""
        self.cache = self._load_cache()
        self.failed_lookups = self._load_failed_lookups()
        self.skip_lookups = self._load_skip_lookups()
        self.genius_token = genius_token
        self.genius = None
        self.genius_requests_this_hour = 0
        self.genius_hour_start = time.time()
        self.genius_cooldown_until = 0  # Timestamp when Genius can be retried after hourly limit
        self.rate_limit_failures = 0  # Count real Genius 429 failures
        self.fallback_access_failures = 0  # Consecutive lyrics.ovh access failures (timeouts/errors, not 404s)
        self.shutdown_requested = False
        self.retry_failed = retry_failed  # Only process previously failed tracks
        
        # Statistics tracking
        self.stats = {
            'files_skipped_existing_lyrics': 0,
            'files_skipped_previously_failed': 0,
            'files_no_lyrics_found': 0,
            'albums_skipped_complete': 0,
            'albums_with_new_lyrics': 0,
            'albums_no_new_lyrics': 0
        }
        
        # Artist name mapping cache (for split-lookup success)
        self.artist_mappings = {}  # original_artist -> successful_artist
        
        # Set up signal handler for clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if genius_token:
            self.genius = lyricsgenius.Genius(genius_token)
            self.genius.verbose = False
            self.genius.remove_section_headers = True
            self.genius.skip_non_songs = True
            self.genius.excluded_terms = ["(Remix)", "(Live)", "(Acoustic)", "(Demo)"]
            self.genius.timeout = 15  # 15-second timeout for API requests
            self.genius.retries = 1   # Only 1 internal retry
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.last_request_time = 0
    
    def _signal_handler(self, signum, frame):
        """Handle CTRL+C gracefully."""
        if not self.shutdown_requested:
            # First CTRL+C - graceful shutdown
            self.shutdown_requested = True
            print("\n\n🛑 Interrupt received. Finishing current song and saving progress...")
            print("Use CTRL+C again to force exit immediately.")
        else:
            # Second CTRL+C - force exit
            print("\n⚡ Force exit requested. Terminating immediately...")
            self._save_cache()  # Try to save cache one last time
            sys.exit(1)
    
    def _check_shutdown(self):
        """Check if shutdown was requested."""
        if self.shutdown_requested:
            print("\n🛑 Graceful shutdown initiated.")
            self._save_cache()
            print("✅ Progress saved. Use --force to retry any skipped songs.")
            sys.exit(0)
    
    def _load_failed_lookups(self) -> set:
        """Load failed lookups from log file."""
        failed = set()
        if FAILED_FILE.exists():
            try:
                with open(FAILED_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and ' - ' in line:
                            # Extract the artist|title part (after timestamp)
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                failed.add(parts[1])
            except IOError as e:
                print(f"⚠️  Warning: Could not read failed lookups log: {e}")
        return failed
    
    def _load_skip_lookups(self) -> set:
        """Load skip lookups from skip file."""
        skip = set()
        if SKIP_FILE.exists():
            try:
                with open(SKIP_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and ' - ' in line:
                            # Extract the artist|title part (after timestamp)
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                skip.add(parts[1])
                        elif line and '|' in line:
                            # Also support plain "artist|title" format without timestamp
                            skip.add(line)
            except IOError as e:
                print(f"⚠️  Warning: Could not read skip lookups file: {e}")
        return skip
    
    def add_to_skip_list(self, artist: str, title: str):
        """Add a track to the permanent skip list."""
        try:
            SKIP_FILE.parent.mkdir(parents=True, exist_ok=True)
            lookup_key = f"{artist}|{title}"
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if already exists
            for entry in self.skip_lookups:
                if entry == lookup_key or entry.startswith(f"{lookup_key}:"):
                    print(f"ℹ️  {artist} - {title} is already in skip list")
                    return
            
            # Add to file
            with open(SKIP_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {lookup_key}:1\n")
            
            # Update in-memory set
            self.skip_lookups.add(f"{lookup_key}:1")
            print(f"✅ Added to skip list: {artist} - {title}")
            
        except IOError as e:
            print(f"⚠️  Warning: Could not add to skip list: {e}")
    
    def _save_failed_lookup(self, artist: str, title: str):
        """Save failed lookup to log file (only for lyrics not available)."""
        try:
            FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
            lookup_key = f"{artist}|{title}"
            
            # Check if already exists and get current count
            existing_count = 0
            for entry in self.failed_lookups:
                if entry == lookup_key:
                    existing_count = 1
                    break
                elif entry.startswith(f"{lookup_key}:"):
                    # Split on last colon to handle titles with colons
                    parts = entry.rsplit(":", 1)
                    if len(parts) == 2 and parts[1].strip().isdigit():
                        existing_count = int(parts[1].strip())
                    break
            
            new_count = existing_count + 1
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Remove old entry if exists
            self._remove_failed_lookup(artist, title)
            
            # Add new entry with incremented count
            with open(FAILED_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {lookup_key}:{new_count}\n")
            
            # Update in-memory set
            self.failed_lookups.add(f"{lookup_key}:{new_count}")
            
        except IOError as e:
            print(f"⚠️  Warning: Could not write failed lookup: {e}")
    
    def _remove_failed_lookup(self, artist: str, title: str):
        """Remove a failed lookup from log file when lyrics are successfully found."""
        lookup_key = f"{artist}|{title}"
        
        # Find the entry to remove (with or without count)
        entry_to_remove = None
        for entry in self.failed_lookups:
            if entry.startswith(f"{lookup_key}:") or entry == lookup_key:
                entry_to_remove = entry
                break
        
        if not entry_to_remove:
            return  # Not in failed log, nothing to remove
        
        try:
            # Read all lines except the one to remove
            FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
            lines_to_keep = []
            if FAILED_FILE.exists():
                with open(FAILED_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line_content = line.strip()
                        # Check if this line matches the entry to remove
                        if ":" in entry_to_remove:
                            # Entry has count: "artist|title:3"
                            if not line_content.endswith(f" - {entry_to_remove}"):
                                lines_to_keep.append(line)
                        else:
                            # Old format without count: "artist|title"
                            if not line_content.endswith(f" - {lookup_key}"):
                                lines_to_keep.append(line)
            
            # Write back the filtered lines
            with open(FAILED_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines_to_keep)
            
            # Update in-memory set
            self.failed_lookups.discard(entry_to_remove)
            
        except IOError as e:
            print(f"⚠️  Warning: Could not remove failed lookup: {e}")
    
    def _check_rate_limit_exit(self):
        """Check if we should exit due to too many rate limit failures."""
        if self.rate_limit_failures >= MAX_RATE_LIMIT_FAILURES:
            if not self.shutdown_requested:
                print(f"\n⛔ {MAX_RATE_LIMIT_FAILURES} rate limit failures reached.")
                print("   Exiting to avoid further API pressure.")
                print("   Try again later when rate limits have reset.")
                print("   Progress has been saved.")
                self._save_cache()
                self.shutdown_requested = True
            return True
        return False
    
    def _check_fallback_access_exit(self):
        """Check if we should exit due to consecutive fallback service access failures.
        
        When lyrics.ovh is returning timeouts/connection errors (not 404s),
        exit after MAX_FALLBACK_ACCESS_FAILURES consecutive access failures.
        """
        if self.fallback_access_failures >= MAX_FALLBACK_ACCESS_FAILURES:
            if not self.shutdown_requested:
                print(f"\n⛔ {self.fallback_access_failures} consecutive access failures from fallback service.")
                print("   lyrics.ovh appears to be down or rate-limiting us.")
                print("   Stopping to avoid wasting time. Try again later.")
                print("   Progress has been saved.")
                self._save_cache()
                self.shutdown_requested = True
            return True
        return False
    
    def _is_genius_on_cooldown(self) -> bool:
        """Check if Genius is on hourly cooldown."""
        if self.genius_cooldown_until > 0:
            remaining = self.genius_cooldown_until - time.time()
            if remaining > 0:
                return True
        return False
    
    def _check_genius_rate_limit(self, indent: bool = False) -> bool:
        """Check if we're within Genius rate limits."""
        current_time = time.time()
        indent_str = "        " if indent else "    "
        
        # If on cooldown, skip silently
        if self._is_genius_on_cooldown():
            return False
        
        # Reset counter if hour has passed
        if current_time - self.genius_hour_start > 3600:  # 1 hour
            self.genius_requests_this_hour = 0
            self.genius_hour_start = current_time
        
        # Check hourly limit — enter 60-min cooldown
        if self.genius_requests_this_hour >= GENIUS_HOURLY_LIMIT:
            self.genius_cooldown_until = current_time + 3600
            mins_remaining = 60
            print(f"{indent_str}⚠️ Genius hourly limit reached ({GENIUS_HOURLY_LIMIT}/hour). Pausing Genius for {mins_remaining} min...")
            return False
        
        # Check minute rate (12 seconds between requests = 5/minute)
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / GENIUS_REQUESTS_PER_MINUTE
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            print(f"{indent_str}⏱️ Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        return True
    
    def _increment_genius_requests(self):
        """Track Genius API requests."""
        self.genius_requests_this_hour += 1
        self.last_request_time = time.time()
    
    def _is_failed_lookup(self, artist: str, title: str) -> bool:
        """Check if this lookup failed before."""
        lookup_key = f"{artist}|{title}"
        for entry in self.failed_lookups:
            # Handle both formats: "artist|title" and "artist|title:count"
            if entry == lookup_key:
                return True
            elif entry.startswith(f"{lookup_key}:"):
                return True
        return False
    
    def _is_skip_lookup(self, artist: str, title: str) -> bool:
        """Check if this lookup is in the permanent skip list."""
        lookup_key = f"{artist}|{title}"
        for entry in self.skip_lookups:
            # Handle both formats: "artist|title" and "artist|title:count"
            if entry == lookup_key:
                return True
            elif entry.startswith(f"{lookup_key}:"):
                return True
        return False
    
    def _get_failure_count(self, artist: str, title: str) -> int:
        """Get the failure count for this lookup."""
        lookup_key = f"{artist}|{title}"
        for entry in self.failed_lookups:
            if entry.startswith(lookup_key):
                if ":" in entry:
                    # Split on last colon to handle titles with colons
                    parts = entry.rsplit(":", 1)
                    if len(parts) == 2 and parts[1].strip().isdigit():
                        return int(parts[1].strip())
                    else:
                        return 1  # Malformed count, default to 1
                else:
                    return 1  # Old format without count
        return 0
    
    def _load_cache(self) -> Dict:
        """Load lyrics cache from disk."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _save_cache(self):
        """Save lyrics cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️  Warning: Could not save cache: {e}")
    
    def _rate_limit(self, indent: bool = False):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < RATE_LIMIT:
            sleep_time = RATE_LIMIT - time_since_last
            indent_str = "        " if indent else "    "
            print(f"{indent_str}⏱️ Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _get_cache_key(self, artist: str, title: str) -> str:
        """Generate cache key for lyrics lookup."""
        return f"{artist.lower().strip()}|{title.lower().strip()}"
    
    def _extract_metadata(self, file_path: Path) -> Tuple[str, str, str]:
        """Extract artist, album, and title from audio file."""
        try:
            if file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
                artist = audio.get('ARTIST', [''])[0]
                album = audio.get('ALBUM', [''])[0]
                title = audio.get('TITLE', [''])[0]
            elif file_path.suffix.lower() in ['.mp3']:
                audio = MP3(file_path)
                artist = str(audio.get('TPE1', [''])[0]) if 'TPE1' in audio else ''
                album = str(audio.get('TALB', [''])[0]) if 'TALB' in audio else ''
                title = str(audio.get('TIT2', [''])[0]) if 'TIT2' in audio else ''
            elif file_path.suffix.lower() in ['.mp4', '.m4a']:
                audio = MP4(file_path)
                artist = audio.get(r'\xaART', [''])[0] if r'\xaART' in audio else ''
                album = audio.get(r'\xaalb', [''])[0] if r'\xaalb' in audio else ''
                title = audio.get(r'\xanam', [''])[0] if r'\xanam' in audio else ''
            else:
                return "", "", ""
            
            return artist.strip(), album.strip(), title.strip()
        except (ID3NoHeaderError, Exception) as e:
            print(f"⚠️  Could not read metadata from {file_path.name}: {e}")
            return "", "", ""
    
    def _extract_from_filename(self, file_path: Path) -> Tuple[str, str]:
        """Extract artist and title from filename if metadata is missing."""
        name = file_path.stem
        
        # Try common patterns: "Artist - Title", "01 Artist - Title", etc.
        patterns = [
            r'^\d+\s+(.+?)\s*-\s*(.+)$',  # "01 Artist - Title"
            r'^(.+?)\s*-\s*(.+)$',          # "Artist - Title"
            r'^(.+?)\s*-\s*(.+?)\s*\(.*\)$', # "Artist - Title (extra)"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1).strip(), match.group(2).strip()
        
        # If no pattern matches, use filename as title
        return "", name
    
    def _search_lyrics_ovh(self, artist: str, title: str, indent: bool = False) -> Tuple[Optional[str], bool]:
        """Search lyrics from lyrics.ovh (free, no API key needed).
        
        Returns:
            Tuple[Optional[str], bool] - (lyrics_text, api_unavailable_flag)
            api_unavailable is True for timeouts/server errors (not a real lookup failure).
        """
        indent_str = "        " if indent else "    "
        try:
            self._rate_limit(indent)
            
            url = f"https://api.lyrics.ovh/v1/{quote(artist)}/{quote(title)}"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 404:
                return None, False  # Song genuinely not found
            
            response.raise_for_status()
            
            data = response.json()
            lyrics = data.get('lyrics', '')
            if lyrics and len(lyrics.strip()) > 50:
                return lyrics.strip(), False
            
            return None, False  # Lyrics empty or too short — genuine failure
                    
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"{indent_str}⚠️ lyrics.ovh search failed: {e}")
            return None, True  # Server unavailable — not a real lookup failure
        except Exception as e:
            print(f"{indent_str}⚠️ lyrics.ovh search failed: {e}")
            return None, True  # Treat unexpected errors as unavailable too

    
    def _search_genius_with_timeout(self, title: str, artist: str) -> Optional[object]:
        """Run genius.search_song with a hard timeout using a thread."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.genius.search_song, title, artist)
            try:
                return future.result(timeout=GENIUS_SEARCH_TIMEOUT)
            except FuturesTimeoutError:
                raise TimeoutError(f"Genius search timed out after {GENIUS_SEARCH_TIMEOUT}s")
    
    def _search_genius_with_retry(self, artist: str, title: str, max_retries: int = 2, indent: bool = False) -> Tuple[Optional[str], bool]:
        """Search Genius with automatic retry for rate limits.
        
        Returns:
            Tuple[Optional[str], bool] - (lyrics_text, api_unavailable_flag)
        """
        # Check rate limits before attempting
        if not self._check_genius_rate_limit(indent):
            # Hourly self-limit reached — just skip Genius, let lyrics.ovh handle it
            return None, True
        
        retry_count = 0
        connection_timeout_count = 0
        api_unavailable = False  # Track if API is completely down
        indent_str = "        " if indent else "    "
        
        while retry_count <= max_retries and connection_timeout_count <= 1:
            try:
                # Track this request
                self._increment_genius_requests()
                
                # Use thread-based hard timeout
                song = self._search_genius_with_timeout(title, artist)
                if song and song.lyrics:
                    lyrics = song.lyrics
                    lyrics = re.sub(r'\d+Embed$', '', lyrics)
                    lyrics = re.sub(r'You might also like$', '', lyrics, flags=re.IGNORECASE)
                    return lyrics.strip(), False
                else:
                    # Song not found — Genius searched, definitively not found
                    return None, False
                    
            except (TimeoutError, OSError) as e:
                connection_timeout_count += 1
                print(f"    ⚠️ Connection issue ({connection_timeout_count}/2): {e}")
                
                if connection_timeout_count <= 1:
                    print(f"    🔄 Retrying connection for {artist} - {title}")
                    time.sleep(5)
                    continue
                else:
                    # Connection failed twice - don't log here, let main function handle it
                    break
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle connection/timeout issues
                if any(keyword in error_msg for keyword in ['timeout', 'connection', 'aborted', 'remote end closed', 'timed out']):
                    connection_timeout_count += 1
                    print(f"{indent_str}⚠️ Connection issue ({connection_timeout_count}/2): {e}")
                    
                    if connection_timeout_count <= 1:
                        print(f"{indent_str}🔄 Retrying connection for {artist} - {title}")
                        time.sleep(5)
                        continue
                    else:
                        break
                
                # Handle rate limits
                elif "429" in str(e) or "1015" in str(e) or "rate limit" in error_msg:
                    self.rate_limit_failures += 1
                    print(f"{indent_str}⚠️ Rate limit hit ({self.rate_limit_failures}/{MAX_RATE_LIMIT_FAILURES})")
                    
                    if self._check_rate_limit_exit():
                        return None, True
                    
                    # Wait and retry
                    wait_time = 10 * (2 ** min(self.rate_limit_failures - 1, 2))
                    print(f"{indent_str}⏱️ Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                # Handle API authentication errors (401, etc.)
                elif "401" in str(e) or "invalid_token" in error_msg or "unauthorized" in error_msg:
                    print(f"{indent_str}⚠️ Genius API unavailable (authentication error)")
                    api_unavailable = True
                    break
                
                # Handle other API errors
                else:
                    print(f"{indent_str}⚠️ Genius search failed: {e}")
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f"{indent_str}🔄 Retry {retry_count}/{max_retries} for {artist} - {title}")
                        time.sleep(5)
                    else:
                        break
        
        return None, api_unavailable

    def _search_genius(self, artist: str, title: str, indent: bool = False) -> Tuple[Optional[str], bool]:
        """Search lyrics from Genius API (requires token).
        
        Returns:
            Tuple[Optional[str], bool] - (lyrics_text, api_unavailable_flag)
        """
        if not self.genius:
            return None, True  # API unavailable (no token)
        
        return self._search_genius_with_retry(artist, title, indent=indent)
    
    def _create_lrc_format(self, lyrics: str) -> str:
        """Convert plain lyrics to LRC format with estimated timestamps."""
        lines = lyrics.split('\n')
        lrc_lines = []
        
        # Add LRC header
        lrc_lines.append('[ar:Unknown Artist]')
        lrc_lines.append('[al:Unknown Album]')
        lrc_lines.append('[ti:Unknown Title]')
        lrc_lines.append('[offset:0]')
        lrc_lines.append('')
        
        # Estimate timestamps (roughly 3 seconds per line)
        for i, line in enumerate(lines):
            if line.strip():
                timestamp = i * 3  # 3 seconds per line
                minutes = timestamp // 60
                seconds = timestamp % 60
                lrc_timestamp = f"[{minutes:02d}:{seconds:02d}.00]"
                lrc_lines.append(f"{lrc_timestamp} {line.strip()}")
        
        return '\n'.join(lrc_lines)
    
    def _save_lyrics(self, file_path: Path, lyrics: str):
        """Save lyrics as .lrc file alongside the audio file."""
        lyrics_file = file_path.with_suffix('.lrc')
        formatted_lyrics = self._create_lrc_format(lyrics)
        
        try:
            with open(lyrics_file, 'w', encoding='utf-8') as f:
                f.write(formatted_lyrics)
            return lyrics_file
        except IOError as e:
            print(f"    ❌ Could not save lyrics: {e}")
            return None
    
    def _has_lyrics(self, file_path: Path) -> bool:
        """Check if lyrics file already exists."""
        return file_path.with_suffix('.lrc').exists()
    
    def _strip_accents(self, text: str) -> str:
        """Strip accents/diacritics from text for fallback lookups."""
        normalized = unicodedata.normalize("NFKD", text)
        return normalized.encode("ascii", "ignore").decode("ascii")

    def _get_artist_variations(self, artist: str, title: str) -> List[Tuple[str, str]]:
        """Generate alternative artist names by splitting compound names.
        
        Returns:
            List of (artist, title) tuples to try
        
        Examples:
        - "Sting & The Police" → [("Sting", "title"), ("The Police", "title")]
        - "The Beatles, Paul McCartney" → [("The Beatles", "title"), ("Paul McCartney", "title")]
        - "Artist feat. Guest" → [("Artist", "title"), ("Guest", "title")]
        """
        variations = []
        
        # Artist alias mappings for reversible alternative names
        artist_aliases = {
            "ELO": ["Electric Light Orchestra", "Jeff Lynne", "Jeff Lynne's ELO"],
            "Electric Light Orchestra": ["ELO", "Jeff Lynne", "Jeff Lynne's ELO"],
            "Jeff Lynne": ["ELO", "Electric Light Orchestra", "Jeff Lynne's ELO"],
            "Jeff Lynne's ELO": ["ELO", "Electric Light Orchestra", "Jeff Lynne"],
            
            "John Rutter": ["The Cambridge Singers", "The Cambridge Singers, John Rutter"],
            "The Cambridge Singers": ["John Rutter", "The Cambridge Singers, John Rutter"],
            "The Cambridge Singers, John Rutter": ["John Rutter", "The Cambridge Singers"],
            
            "Rupert's Kitchen Orchestra": ["Ruperts Kitchen Orchestra", "RUPERTS ☆ KITCHEN ☆ ORCHESTRA"],
            "Ruperts Kitchen Orchestra": ["Rupert's Kitchen Orchestra", "RUPERTS ☆ KITCHEN ☆ ORCHESTRA"],
            "RUPERTS ☆ KITCHEN ☆ ORCHESTRA": ["Rupert's Kitchen Orchestra", "Ruperts Kitchen Orchestra"],
            
            "Wendy & Lisa": ["Wendy and Lisa"],
            "Wendy and Lisa": ["Wendy & Lisa"],
            
            "The Alan Parsons Project": ["Alan Parsons", "Alan Parsons Project"],
            "Alan Parsons": ["The Alan Parsons Project", "Alan Parsons Project"],
            "Alan Parsons Project": ["The Alan Parsons Project", "Alan Parsons"],
            
            "Peter Fox & Cold Steel": ["Peter Fox"],
            "Peter Fox": ["Peter Fox & Cold Steel"],
            
            "John Cougar Mellencamp": ["John Mellencamp"],
            "John Mellencamp": ["John Cougar Mellencamp"],
            
            "Frank Sinatra with Billy May and His Orchestra": ["Frank Sinatra"],
            "Frank Sinatra": ["Frank Sinatra with Billy May and His Orchestra"],
        }
        
        # Check for exact artist alias matches
        if artist in artist_aliases:
            for alt_artist in artist_aliases[artist]:
                variations.append((alt_artist, title))
        
        # Check if any alias matches this artist (reverse mapping)
        for alias, alternatives in artist_aliases.items():
            if artist in alternatives and artist != alias:
                variations.append((alias, title))
                for alt in alternatives:
                    if alt != artist:
                        variations.append((alt, title))
        
        # Accent-stripped fallback (e.g., "André" -> "Andre")
        accentless = self._strip_accents(artist)
        if accentless and accentless != artist:
            variations.append((accentless, title))
        
        # Special case for "Various" album artist - extract artist from title
        clean_title = title
        if artist.lower() == "various":
            # Pattern: "Song Title (Artist)" or "Song Title (remix info) (Artist)"
            # Extract artist from parentheses in title
            import re
            
            # Try to find the last parenthesized group (usually the artist)
            parenthesized_matches = re.findall(r'\(([^)]+)\)', title)
            if parenthesized_matches:
                # The last group is usually the artist, but we need to filter out remix info
                potential_artists = []
                for match in parenthesized_matches:
                    # Skip if it looks like remix/version info
                    remix_keywords = ['remix', 'mix', 'version', 'edit', 'club', 'extended', 'original', 'rmx', 'dub']
                    if not any(keyword.lower() in match.lower() for keyword in remix_keywords):
                        # Skip if it's very short (likely not an artist)
                        if len(match.strip()) > 2:
                            potential_artists.append(match.strip())
                
                # Use the last valid match as the artist
                if potential_artists:
                    extracted_artist = potential_artists[-1]
                    variations.append((extracted_artist, title))
                    
                    # Also try extracting clean song title (before first parenthesis)
                    clean_title = re.split(r'\s*\(', title, 1)[0].strip()
                    if clean_title != title:
                        variations.append((extracted_artist, clean_title))
        
        # Split patterns to try
        separators = [' & ', ' and ', ' ft. ', ' feat. ', ' featuring ', ', ', ' x ', ' vs. ', ' + ']
        
        # Generate interchangeable variations for "and", "+", "&"
        and_variants = [' and ', ' + ', ' & ']
        
        for sep in separators:
            if sep.lower() in artist.lower():
                # Use case-sensitive split but find the separator case-insensitively
                parts = artist.lower().split(sep.lower())
                if len(parts) == 2:
                    # Find the actual separator in the original string to preserve case
                    sep_index = artist.lower().find(sep.lower())
                    if sep_index != -1:
                        part1 = artist[:sep_index].strip()
                        part2 = artist[sep_index + len(sep):].strip()
                        variations.append((part1, clean_title))
                        variations.append((part2, clean_title))
                        
                        # If this was an "and" variant, also try the other "and" variants
                        if sep.lower() in [' and ', ' + ', ' & ']:
                            for variant in and_variants:
                                if variant.lower() != sep.lower():
                                    # Create the alternative artist name with different "and" variant
                                    alt_artist = f"{part1}{variant}{part2}"
                                    variations.append((alt_artist, clean_title))
                        
                        break  # Only use the first matching separator
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var_artist, var_title in variations:
            if var_artist and (var_artist, var_title) not in seen and (var_artist, var_title) != (artist, title):
                seen.add((var_artist, var_title))
                unique_variations.append((var_artist, var_title))
        
        return unique_variations
    
    def _try_artist_variations(self, artist: str, title: str, indent: bool = False) -> Tuple[Optional[str], Optional[str], bool]:
        """Try alternative artist names if the original fails.
        
        Returns:
            (lyrics, successful_artist, success) - lyrics if found, the artist name that worked, success flag
        """
        variations = self._get_artist_variations(artist, title)
        
        for var_artist, var_title in variations:
            indent_str = "    " if indent else ""
            if var_title != title:
                print(f"{indent_str}🔄 Trying alternative: {var_artist} - {var_title}")
            else:
                print(f"{indent_str}🔄 Trying alternative artist: {var_artist}")
            
            # Try Genius first
            if self.genius:
                lyrics, genius_api_unavailable = self._search_genius(var_artist, var_title, indent)
                if lyrics:
                    print(f"{indent_str}✅ Found lyrics for {var_artist} - {var_title}")
                    return lyrics, var_artist, True
            
            # Try lyrics.ovh
            lyrics, ovh_api_unavailable = self._search_lyrics_ovh(var_artist, var_title, indent)
            if lyrics:
                print(f"{indent_str}✅ Found lyrics for {var_artist} - {var_title}")
                return lyrics, var_artist, True
        
        return None, None, False
    
    def download_lyrics_for_file(self, file_path: Path, force: bool = False, indent: bool = False) -> Optional[bool]:
        """Download lyrics for a single audio file.
        
        Returns:
            True  - new lyrics were downloaded
            False - lookup failed (no lyrics found)
            None  - skipped (already exists or previously failed)
        """
        # Check for shutdown request
        self._check_shutdown()
        
        # Skip existing lyrics unless retrying failed tracks or forcing
        if not force and not self.retry_failed and self._has_lyrics(file_path):
            indent_str = "    " if indent else ""
            print(f"{indent_str}⏭️ Skipping {file_path.name}")
            self.stats['files_skipped_existing_lyrics'] += 1
            return None
        
        # Extract metadata
        artist, album, title = self._extract_metadata(file_path)
        
        # Fallback to filename parsing
        if not artist or not title:
            artist, title = self._extract_from_filename(file_path)
        
        if not artist or not title:
            print(f"❌ Could not identify artist/title for {file_path.name}")
            return False
        
        # Check if title contains "instrumental" - auto-add to skip list
        if not force and 'instrumental' in title.lower():
            indent_str = "    " if indent else ""
            print(f"{indent_str}🎵 Instrumental detected, adding to skip list: {file_path.name}")
            
            # Add to skip list
            self.add_to_skip_list(artist, title)
            
            # Remove from failed list if it exists
            if self._is_failed_lookup(artist, title):
                self._remove_failed_lookup(artist, title)
                # Also check for mapped artist name
                search_artist = self.artist_mappings.get(artist, artist)
                if search_artist != artist:
                    self._remove_failed_lookup(search_artist, title)
            
            self.stats['files_skipped_previously_failed'] += 1
            return None
        
        # Check skip list first (highest priority)
        if not force and self._is_skip_lookup(artist, title):
            indent_str = "    " if indent else ""
            print(f"{indent_str}⏭️ Skipping {file_path.name} (in skip list)")
            self.stats['files_skipped_previously_failed'] += 1
            return None
        
        # Check if this lookup failed before (skip unless retrying failed or forcing)
        if not force and not self.retry_failed and self._is_failed_lookup(artist, title):
            indent_str = "    " if indent else ""
            print(f"{indent_str}⏭️ Skipping {file_path.name} (previously failed lookup)")
            self.stats['files_skipped_previously_failed'] += 1
            return None
        
        # In retry mode, only process tracks that previously failed
        if self.retry_failed and not self._is_failed_lookup(artist, title):
            indent_str = "    " if indent else ""
            print(f"{indent_str}⏭️ Skipping {file_path.name} (not in failed log)")
            return None
        
        # In retry mode, if lyrics already exist, remove from failed log and skip
        if self.retry_failed and self._has_lyrics(file_path):
            indent_str = "    " if indent else ""
            print(f"{indent_str}✅ Lyrics already exist, removing from failed log: {file_path.name}")
            self._remove_failed_lookup(artist, title)
            # Also check for mapped artist name
            search_artist = self.artist_mappings.get(artist, artist)
            if search_artist != artist:
                self._remove_failed_lookup(search_artist, title)
            return None
        
        indent_str = "    " if indent else ""
        
        # Check if we have a successful artist mapping from previous tracks
        search_artist = self.artist_mappings.get(artist, artist)
        if search_artist != artist:
            print(f"{indent_str}🔍 {search_artist} - {title} (mapped from {artist})")
        else:
            print(f"{indent_str}🔍 {artist} - {title}")
        
        # Check cache first (use mapped artist for cache key)
        cache_key = self._get_cache_key(search_artist, title)
        if cache_key in self.cache and not force:
            cached_lyrics = self.cache[cache_key]
            lyrics_file = self._save_lyrics(file_path, cached_lyrics)
            if lyrics_file:
                result_indent = "        " if indent else ""
                print(f"{result_indent}✅ Loaded from cache: {lyrics_file.name}")
                return True
        
        # Try different sources
        lyrics = None
        genius_api_unavailable = False
        ovh_api_unavailable = False
        result_indent = "        " if indent else "    "
        genius_on_cooldown = self._is_genius_on_cooldown()
        
        # Try Genius first (if available and not on cooldown)
        if self.genius and not genius_on_cooldown:
            genius_result, genius_api_unavailable = self._search_genius(search_artist, title, indent)
            if genius_result:
                lyrics = genius_result
        elif self.genius and genius_on_cooldown:
            genius_api_unavailable = True
        
        # Fallback to lyrics.ovh (free, no API key needed)
        if not lyrics:
            if genius_api_unavailable and not genius_on_cooldown:
                print(f"{result_indent}🔄 Genius unavailable, trying lyrics.ovh fallback...")
            ovh_result, ovh_api_unavailable = self._search_lyrics_ovh(search_artist, title, indent)
            if ovh_result:
                lyrics = ovh_result
        
        if not lyrics:
            # Try artist name variations if both sources failed
            variation_lyrics, successful_artist, variation_success = self._try_artist_variations(artist, title, indent)
            if variation_success and variation_lyrics and successful_artist:
                lyrics = variation_lyrics
                # Cache the successful artist mapping for future tracks in this album
                self.artist_mappings[artist] = successful_artist
                print(f"{result_indent}📝 Using artist mapping: {artist} → {successful_artist}")
        
        if not lyrics:
            print(f"{result_indent}❌ No lyrics found for {artist} - {title}")
            
            # Re-check cooldown (may have been triggered during Genius call above)
            genius_on_cooldown = self._is_genius_on_cooldown()
            
            # Did Genius actually perform a successful search (even if it found nothing)?
            genius_actually_searched = (self.genius 
                                        and not genius_api_unavailable 
                                        and not genius_on_cooldown)
            
            # Track lyrics.ovh access failures when Genius didn't provide results
            if ovh_api_unavailable and not genius_actually_searched:
                self.fallback_access_failures += 1
                print(f"{result_indent}ℹ️ lyrics.ovh access failure ({self.fallback_access_failures}/{MAX_FALLBACK_ACCESS_FAILURES})")
                if self._check_fallback_access_exit():
                    return False
            elif not ovh_api_unavailable:
                # lyrics.ovh was reachable — reset access failure counter
                self.fallback_access_failures = 0
            
            # Only log permanent failure if all available sources genuinely searched
            if not ovh_api_unavailable and (genius_actually_searched or not self.genius):
                self._save_failed_lookup(artist, title)
            
            self.stats['files_no_lyrics_found'] += 1
            return False
        
        # Save lyrics
        lyrics_file = self._save_lyrics(file_path, lyrics)
        if lyrics_file:
            print(f"{result_indent}✅ Saved lyrics: {lyrics_file.name}")
            
            # Reset fallback access failure counter on success
            self.fallback_access_failures = 0
            
            # Remove from failed lookups if it was there before
            self._remove_failed_lookup(artist, title)
            # Also remove the mapped artist name if we used one
            if search_artist != artist:
                self._remove_failed_lookup(search_artist, title)
            
            # Cache the result
            self.cache[cache_key] = lyrics
            self._save_cache()
            return True
        
        return False
    
    def process_directory(self, directory: Path, recursive: bool = False, force: bool = False):
        """Process all audio files in a directory."""
        audio_extensions = {'.flac', '.mp3', '.mp4', '.m4a', '.wav', '.aac'}
        
        if recursive:
            # Smart album-by-album processing
            self._process_albums_recursively(directory, force)
        else:
            # Single directory processing (original behavior)
            self._process_single_directory(directory, audio_extensions, force)
    
    def _process_single_directory(self, directory: Path, audio_extensions: set, force: bool):
        """Process a single directory (original behavior)."""
        files_processed = 0
        files_successful = 0
        
        for file_path in directory.glob("*"):
            # Check for shutdown request
            self._check_shutdown()
            
            if not file_path.is_file() or file_path.suffix.lower() not in audio_extensions:
                continue
            
            files_processed += 1
            result = self.download_lyrics_for_file(file_path, force)
            if result is True:  # Only count actual new downloads
                files_successful += 1
        
        print(f"\n📊 Summary:")
        print(f"  Files processed: {files_processed}")
        print(f"  Lyrics downloaded: {files_successful}")
        print(f"  Success rate: {files_successful/files_processed*100:.1f}%" if files_processed > 0 else "  No files found")
    
    def _process_albums_recursively(self, directory: Path, force: bool):
        """Process albums one at a time with smart progression."""
        # In retry-failed mode, process globally by failure count instead
        if self.retry_failed:
            self._process_failed_tracks_globally(directory, force)
            return
        
        audio_extensions = {'.flac', '.mp3', '.mp4', '.m4a', '.wav', '.aac'}
        albums_processed = 0
        albums_with_changes = 0
        total_files_processed = 0
        total_lyrics_downloaded = 0
        
        # Find all album directories (directories containing audio files)
        album_dirs = self._find_album_directories(directory, audio_extensions)
        
        if not album_dirs:
            print("ℹ️  No albums found with audio files")
            return
        
        print(f"📁 Found {len(album_dirs)} albums to process")
        
        for album_dir in album_dirs:
            # Check for shutdown request
            self._check_shutdown()
            
            albums_processed += 1
            album_name = album_dir.relative_to(directory)
            print(f"\n📀 Album {albums_processed}/{len(album_dirs)}: {album_name}")
            
            # Check if album already has complete lyrics (skip unless force or retrying failed)
            if not force and not self.retry_failed and self._album_has_complete_lyrics(album_dir, audio_extensions):
                print(f"    ⏭️ Skipping album (already has complete lyrics)")
                self.stats['albums_skipped_complete'] += 1
                continue
            
            # Process this album
            files_processed, lyrics_downloaded, quota_failures = self._process_album(album_dir, audio_extensions, force)
            
            total_files_processed += files_processed
            total_lyrics_downloaded += lyrics_downloaded
            
            # If entire album failed due to rate limits, exit immediately
            if files_processed > 0 and quota_failures == files_processed:
                print(f"\n⚠️  Entire album failed due to rate limits ({quota_failures}/{files_processed} songs).")
                print(f"   Stopping to avoid further API pressure.")
                print(f"   Progress has been saved. Try again later when quotas reset.")
                break
            
            # Check for rate limit exit
            if self._check_rate_limit_exit():
                break
            
            # Check for fallback service access failures
            if self._check_fallback_access_exit():
                break
            
            if lyrics_downloaded > 0:
                albums_with_changes += 1
                self.stats['albums_with_new_lyrics'] += 1
                print(f"    ✅ Album complete — {lyrics_downloaded} new lyrics downloaded")
                
                # Cooldown pause before next album to respect API limits
                print(f"    ⏳ Cooling down {ALBUM_COOLDOWN}s before next album...")
                try:
                    time.sleep(ALBUM_COOLDOWN)
                except KeyboardInterrupt:
                    print(f"\n⏹️  Interrupted during cooldown. Progress saved.")
                    break
            else:
                self.stats['albums_no_new_lyrics'] += 1
                print(f"    ℹ️ No new lyrics for this album")
        
        print(f"\n📊 Final Summary:")
        print(f"  Albums scanned: {albums_processed}/{len(album_dirs)}")
        print(f"  Albums with new lyrics: {albums_with_changes}")
        print(f"  Total files processed: {total_files_processed}")
        print(f"  Total lyrics downloaded: {total_lyrics_downloaded}")
        
        # Detailed file statistics
        print(f"\n📋 File Details:")
        print(f"  Files skipped (lyrics already exist): {self.stats['files_skipped_existing_lyrics']}")
        print(f"  Files skipped (previously failed): {self.stats['files_skipped_previously_failed']}")
        print(f"  Files searched but no lyrics found: {self.stats['files_no_lyrics_found']}")
        
        # Album details
        print(f"\n📁 Album Details:")
        print(f"  Albums with new lyrics: {self.stats['albums_with_new_lyrics']}")
        print(f"  Albums with no new lyrics: {self.stats['albums_no_new_lyrics']}")
        if self.stats['albums_skipped_complete'] > 0:
            print(f"  Albums skipped (already complete): {self.stats['albums_skipped_complete']}")
        
        remaining = len(album_dirs) - albums_processed
        if remaining > 0:
            print(f"\n  Albums remaining: {remaining}")
        
        if self.rate_limit_failures >= MAX_RATE_LIMIT_FAILURES:
            print(f"\n⚠️  Exited early due to rate limits. Run again later to continue.")
            sys.exit(1)
        elif remaining == 0:
            print(f"\n🎉 All albums processed!")
    
    def _find_album_directories(self, directory: Path, audio_extensions: set) -> List[Path]:
        """Find all directories containing audio files (albums)."""
        album_dirs = []
        
        for item in directory.rglob("*"):
            if item.is_dir():
                # Check if this directory contains audio files
                has_audio = any(
                    f.is_file() and f.suffix.lower() in audio_extensions 
                    for f in item.glob("*")
                )
                if has_audio:
                    album_dirs.append(item)
        
        return sorted(album_dirs)
    
    def _album_has_complete_lyrics(self, album_dir: Path, audio_extensions: set) -> bool:
        """Check if all audio files in album have lyrics or are in the failed log."""
        for file_path in album_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                if self._has_lyrics(file_path):
                    continue
                # Check if this file's lookup previously failed
                artist, album, title = self._extract_metadata(file_path)
                if not artist or not title:
                    artist, title = self._extract_from_filename(file_path)
                if artist and title and self._is_failed_lookup(artist, title):
                    continue
                return False
        return True
    
    def _process_album(self, album_dir: Path, audio_extensions: set, force: bool) -> Tuple[int, int, int]:
        """Process a single album and return (files_processed, lyrics_downloaded, rate_limit_failures)."""
        files_processed = 0
        lyrics_downloaded = 0
        rate_limit_failures = 0
        
        # Get all audio files in this album
        audio_files = []
        for file_path in album_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                audio_files.append(file_path)
        
        # In retry mode, sort by failure count (least failures first)
        if self.retry_failed:
            def get_failure_count(file_path):
                try:
                    artist, album, title = self._extract_metadata(file_path)
                    if not artist or not title:
                        artist, title = self._extract_from_filename(file_path)
                    if artist and title:
                        return self._get_failure_count(artist, title)
                except:
                    pass
                return 0  # Unknown files get priority 0
            
            audio_files.sort(key=get_failure_count)
            if audio_files and any(get_failure_count(f) > 0 for f in audio_files):
                print(f"    📊 Prioritizing {len(audio_files)} tracks by failure count (least first)")
        
        for file_path in audio_files:
            if self.shutdown_requested:
                break
            
            files_processed += 1
            result = self.download_lyrics_for_file(file_path, force, indent=True)
            if result is True:  # Only count actual new downloads, not skips
                lyrics_downloaded += 1
            elif result is False:
                # Check if this was a rate limit failure by checking current counter
                # If we're in a rate limit state, this was likely a rate limit failure
                if self.rate_limit_failures > 0:
                    rate_limit_failures += 1
        
        return files_processed, lyrics_downloaded, rate_limit_failures
    
    def _process_failed_tracks_globally(self, directory: Path, force: bool):
        """Process failed tracks globally, sorted by failure count (ascending)."""
        audio_extensions = {'.flac', '.mp3', '.mp4', '.m4a', '.wav', '.aac'}
        
        # Collect all failed tracks with their file paths and failure counts
        failed_tracks = []
        
        print("🔍 Scanning for failed tracks...")
        album_dirs = self._find_album_directories(directory, audio_extensions)
        
        for album_dir in album_dirs:
            for file_path in album_dir.glob("*"):
                if not file_path.is_file() or file_path.suffix.lower() not in audio_extensions:
                    continue
                
                # Extract metadata
                artist, album, title = self._extract_metadata(file_path)
                if not artist or not title:
                    artist, title = self._extract_from_filename(file_path)
                
                if artist and title and self._is_failed_lookup(artist, title):
                    failure_count = self._get_failure_count(artist, title)
                    failed_tracks.append((failure_count, file_path, artist, title))
        
        if not failed_tracks:
            print("ℹ️  No failed tracks found to retry")
            return
        
        # Sort by failure count (ascending)
        failed_tracks.sort(key=lambda x: x[0])
        
        print(f"📊 Found {len(failed_tracks)} failed tracks, prioritizing by failure count (least first)")
        
        # Process tracks in priority order
        processed = 0
        successful = 0
        
        for failure_count, file_path, artist, title in failed_tracks:
            if self.shutdown_requested:
                break
            
            processed += 1
            album_name = file_path.parent.relative_to(directory)
            print(f"\n📀 Track {processed}/{len(failed_tracks)}: {album_name}/{file_path.name}")
            print(f"    📈 Failed {failure_count} time{'s' if failure_count != 1 else ''} previously")
            
            result = self.download_lyrics_for_file(file_path, force, indent=True)
            if result is True:
                successful += 1
                print(f"    ✅ Success! ({successful}/{processed} successful so far)")
            
            # Brief pause between tracks to respect API limits
            if processed < len(failed_tracks):
                time.sleep(2)
        
        print(f"\n📊 Retry Summary:")
        print(f"  Tracks processed: {processed}/{len(failed_tracks)}")
        print(f"  Lyrics found: {successful}")
        print(f"  Success rate: {successful/processed*100:.1f}%" if processed > 0 else "  No tracks processed")

def main():
    parser = argparse.ArgumentParser(
        description="Download lyrics for music files in Jellyfin-compatible format"
    )
    parser.add_argument("path", help="Path to music file, album, or library")
    parser.add_argument("--recursive", "-r", action="store_true", 
                       help="Process directories recursively")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Overwrite existing lyrics files")
    parser.add_argument("--genius-token", help="Genius API token (overrides .env)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--clear-failed", action="store_true",
                       help="Clear failed lookups log before running")
    parser.add_argument("--retry-failed", action="store_true",
                       help="Only process tracks that previously failed (ignores existing lyrics)")
    parser.add_argument("--add-to-skip", nargs=2, metavar=("ARTIST", "TITLE"),
                       help="Add a track to the permanent skip list")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    # Get Genius token from command line, then .env
    genius_token = args.genius_token or os.getenv('GENIUS_API_TOKEN')
    
    if not genius_token:
        print("ℹ️  No Genius API token provided.")
        print("   Add GENIUS_API_TOKEN to your .env file for better lyrics quality")
        print("   Get a free token at: https://genius.com/api-clients")
        print("   Using free sources only (limited coverage).")
    
    # Handle add-to-skip option
    if args.add_to_skip:
        artist, title = args.add_to_skip
        downloader = LyricsDownloader(genius_token)
        downloader.add_to_skip_list(artist, title)
        return
    
    downloader = LyricsDownloader(genius_token, retry_failed=args.retry_failed)
    
    if args.retry_failed:
        print("🔄 Retry mode: Only processing tracks that previously failed")
        print("   (ignoring existing lyrics, focusing on failed lookups)")
    
    # Clear failed lookups if requested
    if args.clear_failed:
        if FAILED_FILE.exists():
            FAILED_FILE.unlink()
            print("🗑️  Cleared failed lookups log")
        else:
            print("ℹ️  No failed lookups log to clear")
    
    if path.is_file():
        # Single file
        if path.suffix.lower() in {'.flac', '.mp3', '.mp4', '.m4a', '.wav', '.aac'}:
            downloader.download_lyrics_for_file(path, args.force)
        else:
            print(f"❌ Not a supported audio file: {path}")
    else:
        # Directory
        print(f"📁 Processing directory: {path}")
        downloader.process_directory(path, args.recursive, args.force)

if __name__ == "__main__":
    main()
