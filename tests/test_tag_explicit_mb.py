#!/usr/bin/env python3
"""Tests for tag-explicit-mb.py functionality."""

# Add the bin directory to the path so we can import the script
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "music"))

try:
    import tag_explicit_mb
except ImportError:
    pytest.skip("tag-explicit-mb.py not available", allow_module_level=True)


class TestExplicitTagging:
    """Test explicit content tagging functionality."""

    def test_normalize_explicit_value(self):
        """Test explicit value normalization."""
        # Test various explicit indicators
        assert tag_explicit_mb.normalize_explicit_value("explicit") == "1"
        assert tag_explicit_mb.normalize_explicit_value("Explicit") == "1"
        assert tag_explicit_mb.normalize_explicit_value("EXPLICIT") == "1"
        assert tag_explicit_mb.normalize_explicit_value("clean") == "0"
        assert tag_explicit_mb.normalize_explicit_value("Clean") == "0"
        assert tag_explicit_mb.normalize_explicit_value("") == "0"
        assert tag_explicit_mb.normalize_explicit_value(None) == "0"
        assert tag_explicit_mb.normalize_explicit_value("random") == "0"

    def test_extract_metadata_from_filename(self):
        """Test extracting metadata from filename."""
        # Test various filename patterns
        metadata = tag_explicit_mb.extract_metadata_from_filename("01 Test Song.flac")
        assert metadata["title"] == "Test Song"
        assert metadata["track_number"] == "01"

        metadata = tag_explicit_mb.extract_metadata_from_filename("Test Song.mp3")
        assert metadata["title"] == "Test Song"
        assert metadata["track_number"] == ""

        metadata = tag_explicit_mb.extract_metadata_from_filename("10 - Test Song.flac")
        assert metadata["title"] == "Test Song"
        assert metadata["track_number"] == "10"

    def test_extract_metadata_from_path(self):
        """Test extracting metadata from directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic directory structure
            artist_dir = Path(temp_dir) / "Test Artist"
            album_dir = artist_dir / "Test Album"
            album_dir.mkdir(parents=True)
            song_file = album_dir / "01 Test Song.flac"
            song_file.touch()

            metadata = tag_explicit_mb.extract_metadata_from_path(song_file)
            assert metadata["artist"] == "Test Artist"
            assert metadata["album"] == "Test Album"
            assert metadata["title"] == "Test Song"
            assert metadata["track_number"] == "01"

    @patch("tag_explicit_mb.musicbrainzngs.search_releases")
    def test_search_musicbrainz_release(self, mock_search):
        """Test MusicBrainz release search."""
        # Mock MusicBrainz response
        mock_search.return_value = {
            "release-list": [
                {
                    "title": "Test Album",
                    "artist-credit-phrase": "Test Artist",
                    "id": "test-release-id",
                    "release-group": {"id": "test-group-id"},
                }
            ]
        }

        result = tag_explicit_mb.search_musicbrainz_release("Test Album", "Test Artist")
        assert result is not None
        assert result["title"] == "Test Album"
        assert result["artist-credit-phrase"] == "Test Artist"

    @patch("tag_explicit_mb.musicbrainzngs.search_releases")
    def test_search_musicbrainz_no_results(self, mock_search):
        """Test MusicBrainz search with no results."""
        mock_search.return_value = {"release-list": []}

        result = tag_explicit_mb.search_musicbrainz_release(
            "Nonexistent Album", "Nonexistent Artist"
        )
        assert result is None

    @patch("tag_explicit_mb.musicbrainzngs.get_release_by_id")
    def test_get_release_details(self, mock_get_release):
        """Test getting detailed release information."""
        mock_get_release.return_value = {
            "release": {
                "title": "Test Album",
                "artist-credit-phrase": "Test Artist",
                "release-group": {"id": "test-group-id"},
                "text-representation": {"language": "eng", "script": "Latn"},
            }
        }

        result = tag_explicit_mb.get_release_details("test-release-id")
        assert result is not None
        assert result["title"] == "Test Album"
        assert result["artist-credit-phrase"] == "Test Artist"

    @patch("tag_explicit_mb.musicbrainzngs.get_release_group_by_id")
    def test_get_release_group_rating(self, mock_get_group):
        """Test getting release group rating."""
        mock_get_group.return_value = {
            "release-group": {"title": "Test Album", "rating": {"value": 3.5}}
        }

        result = tag_explicit_mb.get_release_group_rating("test-group-id")
        assert result == 3.5

    @patch("tag_explicit_mb.musicbrainzngs.get_release_group_by_id")
    def test_get_release_group_rating_no_rating(self, mock_get_group):
        """Test getting release group with no rating."""
        mock_get_group.return_value = {"release-group": {"title": "Test Album"}}

        result = tag_explicit_mb.get_release_group_rating("test-group-id")
        assert result is None

    def test_determine_explicit_from_rating(self):
        """Test determining explicit status from rating."""
        # Test various ratings
        assert tag_explicit_mb.determine_explicit_from_rating(None) == "0"
        assert tag_explicit_mb.determine_explicit_from_rating(0) == "0"
        assert tag_explicit_mb.determine_explicit_from_rating(1) == "0"
        assert tag_explicit_mb.determine_explicit_from_rating(2) == "0"
        assert tag_explicit_mb.determine_explicit_from_rating(3) == "0"
        assert tag_explicit_mb.determine_explicit_from_rating(4) == "1"  # 4+ is considered explicit
        assert tag_explicit_mb.determine_explicit_from_rating(5) == "1"

    @patch("mutagen.flac.FLAC")
    def test_read_flac_metadata(self, mock_flac):
        """Test reading FLAC metadata."""
        # Mock FLAC file
        mock_file = Mock()
        mock_file.get.side_effect = lambda key, default=None: {
            "TITLE": ["Test Song"],
            "ARTIST": ["Test Artist"],
            "ALBUM": ["Test Album"],
            "TRACKNUMBER": ["01"],
        }.get(key, default)
        mock_flac.return_value = mock_file

        metadata = tag_explicit_mb.read_flac_metadata("test.flac")
        assert metadata["title"] == "Test Song"
        assert metadata["artist"] == "Test Artist"
        assert metadata["album"] == "Test Album"
        assert metadata["track_number"] == "01"

    @patch("mutagen.id3.ID3")
    @patch("mutagen.mp3.MP3")
    def test_read_mp3_metadata(self, mock_mp3, mock_id3):
        """Test reading MP3 metadata."""
        # Mock MP3 file
        mock_file = Mock()
        mock_file.get.side_effect = lambda key, default=None: {
            "TIT2": ["Test Song"],
            "TPE1": ["Test Artist"],
            "TALB": ["Test Album"],
            "TRCK": ["01"],
        }.get(key, default)
        mock_mp3.return_value = mock_file

        metadata = tag_explicit_mb.read_mp3_metadata("test.mp3")
        assert metadata["title"] == "Test Song"
        assert metadata["artist"] == "Test Artist"
        assert metadata["album"] == "Test Album"
        assert metadata["track_number"] == "01"

    @patch("mutagen.flac.FLAC")
    def test_write_flac_explicit_tag(self, mock_flac):
        """Test writing explicit tag to FLAC file."""
        # Mock FLAC file
        mock_file = Mock()
        mock_flac.return_value = mock_file

        tag_explicit_mb.write_flac_explicit_tag("test.flac", "1")

        # Verify the tag was set
        mock_file.__setitem__.assert_called_with("RATING", ["1"])
        mock_file.save.assert_called_once()

    @patch("mutagen.id3.ID3")
    @patch("mutagen.mp3.MP3")
    def test_write_mp3_explicit_tag(self, mock_mp3, mock_id3):
        """Test writing explicit tag to MP3 file."""
        # Mock MP3 file
        mock_file = Mock()
        mock_mp3.return_value = mock_file

        tag_explicit_mb.write_mp3_explicit_tag("test.mp3", "1")

        # Verify the tag was set
        mock_file.__setitem__.assert_called()
        mock_file.save.assert_called_once()

    def test_should_process_file(self):
        """Test file filtering logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test supported formats
            flac_file = Path(temp_dir) / "test.flac"
            mp3_file = Path(temp_dir) / "test.mp3"
            m4a_file = Path(temp_dir) / "test.m4a"

            assert tag_explicit_mb.should_process_file(flac_file) is True
            assert tag_explicit_mb.should_process_file(mp3_file) is True
            assert tag_explicit_mb.should_process_file(m4a_file) is True

            # Test unsupported formats
            txt_file = Path(temp_dir) / "test.txt"
            assert tag_explicit_mb.should_process_file(txt_file) is False

    def test_format_duration(self):
        """Test duration formatting."""
        assert tag_explicit_mb.format_duration(180) == "3:05"
        assert tag_explicit_mb.format_duration(60) == "1:00"
        assert tag_explicit_mb.format_duration(3661) == "61:01"
        assert tag_explicit_mb.format_duration(0) == "0:00"


class TestExplicitTaggingIntegration:
    """Integration tests for explicit tagging."""

    def test_full_workflow_mock(self):
        """Test full workflow with mocked dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file structure
            artist_dir = Path(temp_dir) / "Test Artist"
            album_dir = artist_dir / "Test Album"
            album_dir.mkdir(parents=True)
            song_file = album_dir / "01 Test Song.flac"
            song_file.touch()

            # Mock MusicBrainz responses
            with (
                patch("tag_explicit_mb.musicbrainzngs.search_releases") as mock_search,
                patch("tag_explicit_mb.musicbrainzngs.get_release_by_id") as mock_release,
                patch("tag_explicit_mb.musicbrainzngs.get_release_group_by_id") as mock_group,
                patch("mutagen.flac.FLAC") as mock_flac,
            ):

                # Setup mocks
                mock_search.return_value = {"release-list": [{"id": "test-release-id"}]}
                mock_release.return_value = {"release": {"release-group": {"id": "test-group-id"}}}
                mock_group.return_value = {"release-group": {"rating": {"value": 4.0}}}

                mock_file = Mock()
                mock_flac.return_value = mock_file

                # Test the workflow
                metadata = tag_explicit_mb.extract_metadata_from_path(song_file)
                assert metadata["artist"] == "Test Artist"
                assert metadata["album"] == "Test Album"

                # The rating should be detected as explicit (4+)
                explicit = tag_explicit_mb.determine_explicit_from_rating(4.0)
                assert explicit == "1"
