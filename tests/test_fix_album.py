#!/usr/bin/env python3
"""
Tests for fix_album.py script.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "music"))

try:
    import fix_album
except ImportError:
    pytest.skip("fix_album.py not available", allow_module_level=True)


@pytest.mark.unit
class TestFixAlbum:
    """Test cases for fix_album.py."""

    def test_url_encode(self):
        """Test URL encoding function."""
        assert fix_album.url_encode("Test Artist") == "Test%20Artist"
        assert fix_album.url_encode("Artist/Album") == "Artist%2FAlbum"
        assert fix_album.url_encode("Test & Artist") == "Test%20%26%20Artist"

    def test_clean_filename(self):
        """Test filename cleaning function."""
        assert fix_album.clean_filename("Test/Song") == "Test_Song"
        assert fix_album.clean_filename("Test - Song") == "Test - Song"
        assert fix_album.clean_filename("Test/Song/Name") == "Test_Song_Name"

    def test_get_track_titles(self, mock_tracklist_response):
        """Test track title extraction from MusicBrainz response."""
        titles = fix_album.get_track_titles(mock_tracklist_response)
        assert titles == ["First Track", "Second Track", "Third Track"]

    @patch("subprocess.run")
    @patch("fix_album.query_musicbrainz")
    @patch("fix_album.run_script")
    def test_main_success(
        self,
        mock_run_script,
        mock_query,
        mock_subprocess,
        sample_album_dir,
        mock_tracklist_response,
    ):
        """Test successful album processing."""
        # Mock MusicBrainz query
        mock_query.return_value = {"release_id": "test-id", "tracklist": mock_tracklist_response}

        # Mock subprocess for file operations
        mock_subprocess.return_value = Mock(returncode=0)

        # Run the script
        with patch("sys.argv", ["fix_album.py", str(sample_album_dir)]):
            with patch("fix_album.Path.cwd", return_value=sample_album_dir):
                with patch("os.chdir"):
                    fix_album.main()

        # Verify scripts were called
        assert mock_run_script.call_count == 2  # fix_metadata and fix_album_covers

    def test_main_invalid_directory(self):
        """Test handling of invalid directory."""
        with patch("sys.argv", ["fix_album.py", "/nonexistent/path"]):
            with pytest.raises(SystemExit):
                fix_album.main()

    @patch("subprocess.run")
    def test_query_musicbrainz_success(self, mock_subprocess, mock_musicbrainz_response):
        """Test successful MusicBrainz query."""
        mock_subprocess.return_value.stdout = json.dumps(mock_musicbrainz_response)

        result = fix_album.query_musicbrainz("Test Artist", "Test Album")

        assert result["release_id"] == "test-release-id"
        assert "tracklist" in result

    @patch("subprocess.run")
    def test_query_musicbrainz_no_results(self, mock_subprocess):
        """Test MusicBrainz query with no results."""
        mock_subprocess.return_value.stdout = json.dumps({"releases": []})

        with pytest.raises(SystemExit):
            fix_album.query_musicbrainz("Unknown Artist", "Unknown Album")

    def test_rename_files_and_create_playlist(self, sample_album_dir, mock_tracklist_response):
        """Test file renaming and playlist creation."""
        titles = ["First Track", "Second Track", "Third Track"]

        # Change to album directory
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(sample_album_dir)

            playlist_file = fix_album.rename_files_and_create_playlist(titles, sample_album_dir)

            # Check playlist was created
            assert playlist_file.exists()
            assert playlist_file.name == "Test Album.m3u8"

            # Check playlist content
            content = playlist_file.read_text()
            assert "#EXTM3U" in content
            assert "01 - First Track.flac" in content
            assert "02 - Second Track.flac" in content
            assert "03 - Third Track.flac" in content

        finally:
            os.chdir(original_dir)

    def test_clean_old_playlists(self, sample_album_dir):
        """Test removal of old playlist files."""
        # Create old playlist files
        (sample_album_dir / "Unknown Album.m3u").touch()
        (sample_album_dir / "Unknown Album.m3u8").touch()

        fix_album.clean_old_playlists(sample_album_dir)

        # Verify old playlists were removed
        assert not (sample_album_dir / "Unknown Album.m3u").exists()
        assert not (sample_album_dir / "Unknown Album.m3u8").exists()

    def test_file_count_mismatch(self, sample_album_dir, mock_tracklist_response):
        """Test handling of file count mismatch."""
        # Create only 2 FLAC files but tracklist has 3 tracks
        (sample_album_dir / "track1.flac").unlink()

        titles = ["First Track", "Second Track", "Third Track"]

        original_dir = Path.cwd()
        try:
            import os

            os.chdir(sample_album_dir)

            with pytest.raises(SystemExit):
                fix_album.rename_files_and_create_playlist(titles, sample_album_dir)

        finally:
            os.chdir(original_dir)


@pytest.mark.unit
@pytest.mark.integration
class TestFixAlbumIntegration:
    """Integration tests for fix_album.py (may require external tools)."""

    def test_require_command_missing(self):
        """Test behavior when required command is missing."""
        with patch("subprocess.run", return_value=Mock(returncode=1)):
            with pytest.raises(SystemExit):
                fix_album.require_command("nonexistent_command")

    def test_require_command_exists(self):
        """Test behavior when required command exists."""
        with patch("subprocess.run", return_value=Mock(returncode=0)):
            # Should not raise exception
            fix_album.require_command("python3")
