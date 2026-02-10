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
    - .txt files with plain lyrics (fallback)
    - Skips files that already have lyrics
    - Respects rate limits and handles errors gracefully

REQUIRES:
    pip install lyricsgenius requests beautifulsoup4 lxml
"""

import argparse
import os
import sys
import re
import time
import json
import signal
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

try:
    import lyricsgenius
    import requests
    from bs4 import BeautifulSoup
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3NoHeaderError
    from mutagen.mp4 import MP4
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("Install with: pip install lyricsgenius requests beautifulsoup4 lxml")
    sys.exit(1)

# Configuration
CACHE_FILE = Path.home() / ".digital_library_lyrics_cache.json"
FAILED_FILE = Path(__file__).parent.parent.parent / "log" / "failed_lyrics_lookups.txt"
RATE_LIMIT = 2.0  # seconds between requests (conservative)
GENIUS_RATE_LIMIT = 3.0  # longer delay for Genius to avoid 429s
GENIUS_HOURLY_LIMIT = 60  # estimated hourly limit per token
GENIUS_REQUESTS_PER_MINUTE = 5  # conservative: 5 requests per minute max
MAX_CONSECUTIVE_RATE_LIMITS = 5  # exit after this many consecutive rate limits
USER_AGENT = "Digital-Library-Lyrics-Downloader/1.0"

class LyricsDownloader:
    def __init__(self, genius_token: Optional[str] = None):
        """Initialize lyrics downloader with optional Genius API token."""
        self.cache = self._load_cache()
        self.failed_lookups = self._load_failed_lookups()
        self.genius_token = genius_token
        self.genius = None
        self.genius_requests_this_hour = 0
        self.genius_hour_start = time.time()
        self.consecutive_rate_limits = 0
        self.shutdown_requested = False
        
        # Set up signal handler for clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if genius_token:
            self.genius = lyricsgenius.Genius(genius_token)
            self.genius.verbose = False
            self.genius.remove_section_headers = True
            self.genius.skip_non_songs = True
            self.genius.excluded_terms = ["(Remix)", "(Live)", "(Acoustic)", "(Demo)"]
        
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
                        if line and not line.startswith('#'):
                            failed.add(line)
            except IOError as e:
                print(f"⚠️  Warning: Could not read failed lookups log: {e}")
        return failed
    
    def _save_failed_lookup(self, artist: str, title: str, reason: str = ""):
        """Save failed lookup to log file."""
        try:
            FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FAILED_FILE, 'a', encoding='utf-8') as f:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                entry = f"{artist}|{title}"
                if reason:
                    entry += f"  # {reason}"
                f.write(f"{timestamp} - {entry}\n")
            self.failed_lookups.add(f"{artist}|{title}")
        except IOError as e:
            print(f"⚠️  Warning: Could not write failed lookup: {e}")
    
    def _check_genius_rate_limit(self) -> bool:
        """Check if we're within Genius rate limits."""
        current_time = time.time()
        
        # Reset counter if hour has passed
        if current_time - self.genius_hour_start > 3600:  # 1 hour
            self.genius_requests_this_hour = 0
            self.genius_hour_start = current_time
        
        # Check hourly limit
        if self.genius_requests_this_hour >= GENIUS_HOURLY_LIMIT:
            print(f"    ⚠️  Genius hourly limit reached ({GENIUS_HOURLY_LIMIT}/hour). Skipping...")
            return False
        
        # Check minute rate (12 seconds between requests = 5/minute)
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / GENIUS_REQUESTS_PER_MINUTE
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            print(f"    ⏱️  Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        return True
    
    def _check_consecutive_rate_limits(self) -> bool:
        """Check if we've hit too many consecutive rate limits."""
        if self.consecutive_rate_limits >= MAX_CONSECUTIVE_RATE_LIMITS:
            print(f"\n❌ {MAX_CONSECUTIVE_RATE_LIMITS} consecutive rate limits detected.")
            print("   Genius API appears to be temporarily unavailable.")
            print("   Try again later when rate limits have reset.")
            print("   Progress has been saved.")
            self._save_cache()
            return True
        return False
    
    def _increment_genius_requests(self):
        """Track Genius API requests."""
        self.genius_requests_this_hour += 1
        self.last_request_time = time.time()
        # Reset consecutive rate limit counter on successful request
        self.consecutive_rate_limits = 0
    
    def _is_failed_lookup(self, artist: str, title: str) -> bool:
        """Check if this lookup failed before."""
        return f"{artist}|{title}" in self.failed_lookups
    
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
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < RATE_LIMIT:
            time.sleep(RATE_LIMIT - time_since_last)
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
    
    def _search_lyricswikia(self, artist: str, title: str) -> Optional[str]:
        """Search lyrics from lyrics.wikia.com (free, no API key needed)."""
        try:
            self._rate_limit()
            
            # Format search URL
            search_url = f"https://lyrics.fandom.com/wiki/{quote(artist)}:{quote(title)}"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for lyrics content
            lyrics_div = soup.find('div', class_='lyrics')
            if lyrics_div:
                lyrics = lyrics_div.get_text(strip=True)
                if lyrics and len(lyrics) > 50:  # Basic quality check
                    return lyrics
            
            # Alternative: look for any div with lyrics content
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if len(text) > 100 and '\n' in text:  # Likely lyrics
                    return text
                    
        except Exception as e:
            print(f"    ⚠️  LyricsWikia search failed: {e}")
        
        return None
    
    def _search_genius_with_retry(self, artist: str, title: str, max_retries: int = 2) -> Optional[str]:
        """Search Genius with automatic retry for rate limits."""
        # Check rate limits before attempting
        if not self._check_genius_rate_limit():
            self._save_failed_lookup(artist, title, "Genius hourly limit reached")
            return None
        
        # Check if we've had too many consecutive rate limits
        if self._check_consecutive_rate_limits():
            self._save_failed_lookup(artist, title, f"Genius API unavailable ({MAX_CONSECUTIVE_RATE_LIMITS} consecutive rate limits)")
            return None
        
        retry_count = 0  # Only count actual retries, not rate limits
        
        while retry_count <= max_retries:
            try:
                # Track this request
                self._increment_genius_requests()
                
                song = self.genius.search_song(title, artist)
                if song and song.lyrics:
                    lyrics = song.lyrics
                    lyrics = re.sub(r'\d+Embed$', '', lyrics)
                    lyrics = re.sub(r'You might also like$', '', lyrics, flags=re.IGNORECASE)
                    return lyrics.strip()
                    
            except Exception as e:
                if "429" in str(e) or "1015" in str(e) or "rate limit" in str(e).lower():
                    self.consecutive_rate_limits += 1
                    print(f"    ⚠️  Genius rate limited ({self.consecutive_rate_limits}/{MAX_CONSECUTIVE_RATE_LIMITS}). Waiting and retrying...")
                    
                    # Check if we should exit due to too many consecutive rate limits
                    if self._check_consecutive_rate_limits():
                        return None
                    
                    # Exponential backoff for rate limits: 10s, 20s, 40s
                    wait_time = 10 * (2 ** min(self.consecutive_rate_limits - 1, 2))  # Cap at 40s
                    print(f"    ⏱️  Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    # Don't increment retry_count for rate limits
                    continue  # Retry without counting against retry limit
                else:
                    print(f"    ⚠️  Genius search failed: {e}")
                    retry_count += 1  # Only count actual failures
                    if retry_count <= max_retries:
                        print(f"    🔄 Retry {retry_count}/{max_retries} for {artist} - {title}")
                        wait_time = 5 * (2 ** (retry_count - 1))  # 5s, 10s for actual failures
                        print(f"    ⏱️  Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    break  # Exit loop after handling retry
        
        # If we get here, all retries failed
        if retry_count > max_retries:
            print(f"    ⚠️  Max retries reached for {artist} - {title}")
            self._save_failed_lookup(artist, title, f"Failed after {max_retries} actual retries")
        else:
            self._save_failed_lookup(artist, title, "Genius rate limited (retries exhausted)")
        
        return None

    def _search_genius(self, artist: str, title: str) -> Optional[str]:
        """Search lyrics from Genius API (requires token)."""
        if not self.genius:
            return None
        
        return self._search_genius_with_retry(artist, title)
    
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
    
    def _save_lyrics(self, file_path: Path, lyrics: str, format_type: str = 'lrc'):
        """Save lyrics to file alongside the audio file."""
        if format_type == 'lrc':
            lyrics_file = file_path.with_suffix('.lrc')
            if self.genius:  # If we have Genius, try to get better timing
                formatted_lyrics = self._create_lrc_format(lyrics)
            else:
                formatted_lyrics = self._create_lrc_format(lyrics)
        else:
            lyrics_file = file_path.with_suffix('.txt')
            formatted_lyrics = lyrics
        
        try:
            with open(lyrics_file, 'w', encoding='utf-8') as f:
                f.write(formatted_lyrics)
            return lyrics_file
        except IOError as e:
            print(f"    ❌ Could not save lyrics: {e}")
            return None
    
    def _has_lyrics(self, file_path: Path) -> bool:
        """Check if lyrics file already exists."""
        return file_path.with_suffix('.lrc').exists() or file_path.with_suffix('.txt').exists()
    
    def download_lyrics_for_file(self, file_path: Path, force: bool = False) -> bool:
        """Download lyrics for a single audio file."""
        # Check for shutdown request
        self._check_shutdown()
        
        if not force and self._has_lyrics(file_path):
            print(f"⏭️  Skipping {file_path.name} (lyrics already exist)")
            return True
        
        # Extract metadata
        artist, album, title = self._extract_metadata(file_path)
        
        # Fallback to filename parsing
        if not artist or not title:
            artist, title = self._extract_from_filename(file_path)
        
        if not artist or not title:
            print(f"❌ Could not identify artist/title for {file_path.name}")
            return False
        
        # Check if this lookup failed before
        if not force and self._is_failed_lookup(artist, title):
            print(f"⏭️  Skipping {file_path.name} (previously failed lookup)")
            return True
        
        print(f"🔍 Searching lyrics for: {artist} - {title}")
        
        # Check cache first
        cache_key = self._get_cache_key(artist, title)
        if cache_key in self.cache and not force:
            cached_lyrics = self.cache[cache_key]
            lyrics_file = self._save_lyrics(file_path, cached_lyrics)
            if lyrics_file:
                print(f"✅ Loaded from cache: {lyrics_file.name}")
                return True
        
        # Try different sources
        lyrics = None
        failure_reason = ""
        
        # Try Genius first (if available)
        if self.genius:
            lyrics = self._search_genius(artist, title)
            if not lyrics:
                failure_reason = "Genius API failed or rate limited"
        
        # Fallback to LyricsWikia
        if not lyrics:
            lyrics = self._search_lyricswikia(artist, title)
            if not lyrics:
                if failure_reason:
                    failure_reason += "; LyricsWikia failed"
                else:
                    failure_reason = "LyricsWikia failed"
        
        if not lyrics:
            print(f"❌ No lyrics found for {artist} - {title}")
            self._save_failed_lookup(artist, title, failure_reason)
            return False
        
        # Save lyrics
        lyrics_file = self._save_lyrics(file_path, lyrics)
        if lyrics_file:
            print(f"✅ Saved lyrics: {lyrics_file.name}")
            
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
            if self.download_lyrics_for_file(file_path, force):
                files_successful += 1
        
        print(f"\n📊 Summary:")
        print(f"  Files processed: {files_processed}")
        print(f"  Lyrics downloaded: {files_successful}")
        print(f"  Success rate: {files_successful/files_processed*100:.1f}%" if files_processed > 0 else "  No files found")
    
    def _process_albums_recursively(self, directory: Path, force: bool):
        """Process albums one at a time with smart progression."""
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
            print(f"\n🎵 Album {albums_processed}/{len(album_dirs)}: {album_name}")
            
            # Check if album already has complete lyrics (skip unless force)
            if not force and self._album_has_complete_lyrics(album_dir, audio_extensions):
                print(f"⏭️  Skipping album (already has complete lyrics)")
                continue
            
            # Process this album
            files_processed, lyrics_downloaded = self._process_album(album_dir, audio_extensions, force)
            
            total_files_processed += files_processed
            total_lyrics_downloaded += lyrics_downloaded
            
            # Smart progression logic
            if lyrics_downloaded > 0:
                albums_with_changes += 1
                print(f"✅ Album processed with {lyrics_downloaded} new lyrics")
                
                # Exit after first album with changes (smart early exit)
                if albums_with_changes >= 1:
                    print(f"\n🎯 Smart exit: Found album with changes, stopping to avoid rate limits")
                    print(f"   Run again to continue with next albums")
                    break
            else:
                print(f"ℹ️  Album processed with no new lyrics")
        
        print(f"\n📊 Final Summary:")
        print(f"  Albums processed: {albums_processed}/{len(album_dirs)}")
        print(f"  Albums with changes: {albums_with_changes}")
        print(f"  Total files processed: {total_files_processed}")
        print(f"  Total lyrics downloaded: {total_lyrics_downloaded}")
        
        if albums_processed < len(album_dirs):
            remaining = len(album_dirs) - albums_processed
            print(f"  Albums remaining: {remaining} (run again to continue)")
    
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
        """Check if all audio files in album have corresponding lyrics files."""
        for file_path in album_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                if not self._has_lyrics(file_path):
                    return False
        return True
    
    def _process_album(self, album_dir: Path, audio_extensions: set, force: bool) -> Tuple[int, int]:
        """Process a single album and return (files_processed, lyrics_downloaded)."""
        files_processed = 0
        lyrics_downloaded = 0
        
        for file_path in album_dir.glob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in audio_extensions:
                continue
            
            files_processed += 1
            if self.download_lyrics_for_file(file_path, force):
                lyrics_downloaded += 1
        
        return files_processed, lyrics_downloaded

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
    
    downloader = LyricsDownloader(genius_token)
    
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
