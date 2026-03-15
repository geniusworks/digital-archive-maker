#!/usr/bin/env python3
"""
Tests for clean_playlists.py script.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "utils"))

try:
    import clean_playlists
except ImportError:
    pytest.skip("clean_playlists.py not available", allow_module_level=True)


@pytest.mark.unit
class TestCleanPlaylists:
    """Test cases for clean_playlists.py."""

    def test_normalize_line_endings(self):
        """Test line ending normalization."""
        # Test CRLF
        content = "line1\r\nline2\r\nline3"
        result = clean_playlists.normalize_line_endings(content)
        assert result == "line1\nline2\nline3"

        # Test CR only
        content = "line1\rline2\rline3"
        result = clean_playlists.normalize_line_endings(content)
        assert result == "line1\nline2\nline3"

        # Test mixed
        content = "line1\r\nline2\rline3\n"
        result = clean_playlists.normalize_line_endings(content)
        assert result == "line1\nline2\nline3\n"

    def test_ensure_extm3u_header_existing(self):
        """Test when #EXTM3U header already exists."""
        content = "#EXTM3U\nline1\nline2"
        result = clean_playlists.ensure_extm3u_header(content)
        assert result == "#EXTM3U\nline1\nline2"

    def test_ensure_extm3u_header_missing(self):
        """Test when #EXTM3U header is missing."""
        content = "line1\nline2\nline3"
        result = clean_playlists.ensure_extm3u_header(content)
        assert result == "#EXTM3U\nline1\nline2\nline3"

    def test_ensure_extm3u_header_with_empty_lines(self):
        """Test when header is missing but there are empty lines."""
        content = "\n\nline1\nline2"
        result = clean_playlists.ensure_extm3u_header(content)
        assert result == "#EXTM3U\n\n\nline1\nline2"

    def test_validate_tracks_all_exist(self, temp_dir):
        """Test track validation when all files exist."""
        content = "song1.flac\nsong2.flac\nsong3.flac"

        # Create the files
        for track in content.split("\n"):
            if track.strip():
                (temp_dir / track).touch()

        missing = clean_playlists.validate_tracks(content, temp_dir)
        assert missing == []

    def test_validate_tracks_missing_files(self, temp_dir):
        """Test track validation when files are missing."""
        content = "song1.flac\nsong2.flac\nsong3.flac"

        # Create only some files
        (temp_dir / "song1.flac").touch()
        (temp_dir / "song3.flac").touch()

        missing = clean_playlists.validate_tracks(content, temp_dir)
        assert missing == ["song2.flac"]

    def test_validate_tracks_with_comments(self, temp_dir):
        """Test track validation with comments and empty lines."""
        content = "#EXTM3U\n\nsong1.flac\n# Comment\nsong2.flac\n\nsong3.flac"

        # Create all files
        for track in ["song1.flac", "song2.flac", "song3.flac"]:
            (temp_dir / track).touch()

        missing = clean_playlists.validate_tracks(content, temp_dir)
        assert missing == []

    @patch("subprocess.run")
    def test_normalize_encoding_utf8_success(self, mock_subprocess, temp_dir):
        """Test successful UTF-8 encoding normalization."""
        test_file = temp_dir / "test.m3u"
        test_file.write_text("test content", encoding="utf-8")

        mock_subprocess.return_value.stdout = "normalized content"

        result = clean_playlists.normalize_encoding(test_file)

        assert result == "normalized content"
        mock_subprocess.assert_called_once_with(
            ["iconv", "-f", "UTF-8", "-t", "UTF-8", str(test_file)],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_normalize_encoding_fallback_to_iso(self, mock_subprocess, temp_dir):
        """Test fallback to ISO-8859-1 when UTF-8 fails."""
        test_file = temp_dir / "test.m3u"
        test_file.write_text("test content", encoding="utf-8")

        # First call fails, second succeeds
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, "iconv"),
            Mock(stdout="iso content"),
        ]

        result = clean_playlists.normalize_encoding(test_file)

        assert result == "iso content"
        assert mock_subprocess.call_count == 2

    @patch("subprocess.run")
    def test_normalize_encoding_both_fail(self, mock_subprocess, temp_dir):
        """Test when both encoding attempts fail."""
        test_file = temp_dir / "test.m3u"
        test_file.write_text("test content", encoding="utf-8")

        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "iconv")

        result = clean_playlists.normalize_encoding(test_file)

        # Should return original content
        assert result == "test content"

    @patch("clean_playlists.normalize_encoding")
    @patch("clean_playlists.normalize_line_endings")
    @patch("clean_playlists.ensure_extm3u_header")
    @patch("clean_playlists.validate_tracks")
    def test_process_playlist_success(
        self, mock_validate, mock_header, mock_lineendings, mock_normalize, temp_dir
    ):
        """Test successful playlist processing."""
        m3u_file = temp_dir / "test.m3u"
        m3u_file.write_text("test content")

        # Mock the processing steps
        mock_normalize.return_value = "normalized content"
        mock_lineendings.return_value = "line endings fixed"
        mock_header.return_value = "#EXTM3U\nline endings fixed"
        mock_validate.return_value = []

        clean_playlists.process_playlist(m3u_file, "copy")

        # Verify output file was created
        m3u8_file = temp_dir / "test.m3u8"
        assert m3u8_file.exists()

        # Verify original file still exists (copy mode)
        assert m3u_file.exists()

        # Verify processing steps were called
        mock_normalize.assert_called_once()
        mock_lineendings.assert_called_once()
        mock_header.assert_called_once()
        mock_validate.assert_called_once()

    @patch("clean_playlists.normalize_encoding")
    @patch("clean_playlists.normalize_line_endings")
    @patch("clean_playlists.ensure_extm3u_header")
    @patch("clean_playlists.validate_tracks")
    def test_process_playlist_replace_mode(
        self, mock_validate, mock_header, mock_lineendings, mock_normalize, temp_dir
    ):
        """Test playlist processing in replace mode."""
        m3u_file = temp_dir / "test.m3u"
        m3u_file.write_text("test content")

        mock_normalize.return_value = "normalized content"
        mock_lineendings.return_value = "line endings fixed"
        mock_header.return_value = "#EXTM3U\nline endings fixed"
        mock_validate.return_value = []

        clean_playlists.process_playlist(m3u_file, "replace")

        # Verify output file was created
        m3u8_file = temp_dir / "test.m3u8"
        assert m3u8_file.exists()

        # Verify original file was removed (replace mode)
        assert not m3u_file.exists()

    def test_process_playlist_nonexistent_file(self, temp_dir):
        """Test processing non-existent playlist file."""
        m3u_file = temp_dir / "nonexistent.m3u"

        # Should not raise exception
        clean_playlists.process_playlist(m3u_file, "copy")

    @patch("clean_playlists.process_playlist")
    def test_scan_directory_success(self, mock_process, temp_dir):
        """Test successful directory scanning."""
        # Create nested structure with M3U files
        (temp_dir / "album1").mkdir()
        (temp_dir / "album2").mkdir()

        (temp_dir / "album1" / "playlist.m3u").touch()
        (temp_dir / "album2" / "music.m3u").touch()
        (temp_dir / "album2" / "playlist.m3u8").touch()  # Should be ignored

        clean_playlists.scan_directory(temp_dir, "copy")

        # Should process only .m3u files (not .m3u8)
        assert mock_process.call_count == 2

    @patch("clean_playlists.process_playlist")
    def test_scan_directory_no_files(self, mock_process, temp_dir):
        """Test scanning directory with no M3U files."""
        clean_playlists.scan_directory(temp_dir, "copy")

        mock_process.assert_not_called()

    def test_scan_directory_invalid_path(self):
        """Test scanning invalid directory path."""
        with patch("builtins.print"):  # Mock print to avoid output
            # Should not raise SystemExit - it should print and return gracefully
            clean_playlists.scan_directory(Path("/nonexistent"), "copy")

    def test_scan_directory_not_directory(self, temp_dir):
        """Test scanning path that is not a directory."""
        file_path = temp_dir / "test.txt"
        file_path.touch()

        with patch("builtins.print"):  # Mock print to avoid output
            # Should not raise SystemExit - it should print and return gracefully
            clean_playlists.scan_directory(file_path, "copy")

    @patch("clean_playlists.scan_directory")
    def test_main_success(self, mock_scan, temp_dir):
        """Test successful main execution."""
        with patch("sys.argv", ["clean_playlists.py", str(temp_dir)]):
            with patch("clean_playlists.require_command"):
                clean_playlists.main()

        mock_scan.assert_called_once_with(temp_dir, "copy")

    @patch("clean_playlists.scan_directory")
    def test_main_default_directory(self, mock_scan, temp_dir):
        """Test main execution with default directory."""
        with patch("sys.argv", ["clean_playlists.py"]):
            with patch("clean_playlists.Path") as mock_path:
                with patch("clean_playlists.require_command"):
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.is_dir.return_value = True
                    clean_playlists.main()

        mock_scan.assert_called_once()

    @patch("clean_playlists.scan_directory")
    def test_main_replace_mode(self, mock_scan, temp_dir):
        """Test main execution in replace mode."""
        with patch("sys.argv", ["clean_playlists.py", "--replace", str(temp_dir)]):
            with patch("clean_playlists.require_command"):
                clean_playlists.main()

        mock_scan.assert_called_once_with(temp_dir, "replace")


@pytest.mark.unit
@pytest.mark.integration
class TestCleanPlaylistsIntegration:
    """Integration tests for clean_playlists.py."""

    def test_require_command_missing(self):
        """Test behavior when required command is missing."""
        with patch("subprocess.run", return_value=Mock(returncode=1)):
            with pytest.raises(SystemExit):
                clean_playlists.require_command("nonexistent_command")

    def test_require_command_exists(self):
        """Test behavior when required command exists."""
        with patch("subprocess.run", return_value=Mock(returncode=0)):
            # Should not raise exception
            clean_playlists.require_command("python3")
