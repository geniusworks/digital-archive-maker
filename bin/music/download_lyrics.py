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
RATE_LIMIT = 2.0  # seconds between requests (increased from 1.0)
GENIUS_RATE_LIMIT = 3.0  # longer delay for Genius to avoid 429s
USER_AGENT = "Digital-Library-Lyrics-Downloader/1.0"

class LyricsDownloader:
    def __init__(self, genius_token: Optional[str] = None):
        """Initialize lyrics downloader with optional Genius API token."""
        self.cache = self._load_cache()
        self.failed_lookups = self._load_failed_lookups()
        self.genius_token = genius_token
        self.genius = None
        if genius_token:
            self.genius = lyricsgenius.Genius(genius_token)
            self.genius.verbose = False
            self.genius.remove_section_headers = True
            self.genius.skip_non_songs = True
            self.genius.excluded_terms = ["(Remix)", "(Live)", "(Acoustic)", "(Demo)"]
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.last_request_time = 0
    
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
    
    def _search_genius(self, artist: str, title: str) -> Optional[str]:
        """Search lyrics from Genius API (requires token)."""
        if not self.genius:
            return None
        
        try:
            # Longer rate limit for Genius to avoid 429s
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < GENIUS_RATE_LIMIT:
                time.sleep(GENIUS_RATE_LIMIT - time_since_last)
            self.last_request_time = time.time()
            
            song = self.genius.search_song(title, artist)
            if song and song.lyrics:
                # Clean up Genius lyrics (remove headers, etc.)
                lyrics = song.lyrics
                lyrics = re.sub(r'\d+Embed$', '', lyrics)  # Remove "Embed" at end
                lyrics = re.sub(r'You might also like$', '', lyrics, flags=re.IGNORECASE)
                return lyrics.strip()
                
        except Exception as e:
            if "429" in str(e) or "1015" in str(e):
                print(f"    ⚠️  Genius rate limited. Waiting 60 seconds...")
                time.sleep(60)  # Wait longer on rate limit
            else:
                print(f"    ⚠️  Genius search failed: {e}")
        
        return None
    
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
        
        pattern = "**/*" if recursive else "*"
        files_processed = 0
        files_successful = 0
        
        for file_path in directory.glob(pattern):
            if not file_path.is_file() or file_path.suffix.lower() not in audio_extensions:
                continue
            
            files_processed += 1
            if self.download_lyrics_for_file(file_path, force):
                files_successful += 1
        
        print(f"\n📊 Summary:")
        print(f"  Files processed: {files_processed}")
        print(f"  Lyrics downloaded: {files_successful}")
        print(f"  Success rate: {files_successful/files_processed*100:.1f}%" if files_processed > 0 else "  No files found")

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
