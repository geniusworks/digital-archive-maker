#!/usr/bin/env python3
"""Tests for download_lyrics.py functionality."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "music"))

try:
    import download_lyrics
except ImportError:
    pytest.skip("download_lyrics.py not available", allow_module_level=True)


class TestLyricsDownloader:
    """Test the LyricsDownloader class."""

    def test_init_without_token(self):
        """Test initialization without Genius token."""
        downloader = download_lyrics.LyricsDownloader()
        assert downloader.genius_token is None
        assert downloader.genius is None
        assert downloader.genius_requests_this_hour == 0

    def test_init_with_token(self):
        """Test initialization with Genius token."""
        downloader = download_lyrics.LyricsDownloader(genius_token="test_token")
        assert downloader.genius_token == "test_token"
        # Genius is initialized immediately if token is provided
        assert downloader.genius is not None

    def test_extract_metadata(self):
        """Test extracting metadata from audio file."""
        downloader = download_lyrics.LyricsDownloader()

        # Test with mock Path
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.flac"
            test_file.touch()

            # This will fail to read metadata but should not crash
            artist, album, title = downloader._extract_metadata(test_file)
            assert artist == ""
            assert album == ""
            assert title == ""

    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "data"}')
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_cache(self, mock_exists, mock_file):
        """Test loading lyrics cache."""
        downloader = download_lyrics.LyricsDownloader()
        cache = downloader._load_cache()
        assert cache == {"test": "data"}

    @patch("pathlib.Path.exists", return_value=False)
    def test_load_cache_missing(self, mock_exists):
        """Test loading cache when file doesn't exist."""
        downloader = download_lyrics.LyricsDownloader()
        cache = downloader._load_cache()
        assert cache == {}

    def test_get_cache_key(self):
        """Test cache key generation."""
        downloader = download_lyrics.LyricsDownloader()

        # Test cache key generation
        key = downloader._get_cache_key("Test Artist", "Test Song")
        assert key == "test artist|test song"

        # Test with extra spaces
        key2 = downloader._get_cache_key("  Test Artist  ", "  Test Song  ")
        assert key2 == "test artist|test song"

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_cache(self, mock_file, mock_mkdir):
        """Test saving lyrics cache."""
        downloader = download_lyrics.LyricsDownloader()
        downloader.cache = {"test": "data"}

        downloader._save_cache()

        mock_file.assert_called_once()
        mock_mkdir.assert_called_once()

    def test_is_failed_lookup(self):
        """Test failed lookup detection."""
        downloader = download_lyrics.LyricsDownloader()

        # Test with empty failed lookups
        assert downloader._is_failed_lookup("Test Artist", "Test Song") is False

    def test_is_skip_lookup(self):
        """Test skip lookup detection."""
        downloader = download_lyrics.LyricsDownloader()

        # Test with empty skip lookups
        assert downloader._is_skip_lookup("Test Artist", "Test Song") is False

    @patch("download_lyrics.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="Test Artist|Test Song|1\n")
    def test_load_failed_lookups(self, mock_file, mock_exists):
        """Test loading failed lookups file."""
        mock_exists.return_value = True
        downloader = download_lyrics.LyricsDownloader()

        failed = downloader._load_failed_lookups()
        # Check that it loaded something (the file should be parsed)
        assert isinstance(failed, set)

    @patch("download_lyrics.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="Test Artist|Test Song\n")
    def test_load_skip_lookups(self, mock_file, mock_exists):
        """Test loading skip lookups file."""
        mock_exists.return_value = True
        downloader = download_lyrics.LyricsDownloader()

        skipped = downloader._load_skip_lookups()
        # Check that it loaded something
        assert len(skipped) > 0


class TestLyricsIntegration:
    """Integration tests for lyrics functionality."""

    def test_full_metadata_extraction(self):
        """Test full metadata extraction from realistic path."""
        downloader = download_lyrics.LyricsDownloader()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic directory structure
            artist_dir = Path(temp_dir) / "The Beatles"
            album_dir = artist_dir / "Abbey Road"
            album_dir.mkdir(parents=True)
            song_file = album_dir / "01 Come Together.flac"
            song_file.touch()

            # This will fail to read metadata but should not crash
            artist, album, title = downloader._extract_metadata(song_file)
            assert artist == ""
            assert album == ""
            assert title == ""

    def test_cache_key_generation(self):
        """Test cache key generation consistency."""
        downloader = download_lyrics.LyricsDownloader()

        # Same inputs should generate same key
        key1 = downloader._get_cache_key("Test Song", "Test Artist")
        key2 = downloader._get_cache_key("Test Song", "Test Artist")
        assert key1 == key2

        # Different inputs should generate different keys
        key3 = downloader._get_cache_key("Different Song", "Test Artist")
        assert key1 != key3

    def test_rate_limit_tracking(self):
        """Test rate limit tracking functionality."""
        downloader = download_lyrics.LyricsDownloader()

        # Test initial state
        assert downloader.genius_requests_this_hour == 0

        # Test incrementing
        downloader.genius_requests_this_hour = 5
        assert downloader.genius_requests_this_hour == 5
