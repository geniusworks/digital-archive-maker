#!/usr/bin/env python3
"""
Tests for set_explicit.py script.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "metadata"))

try:
    import set_explicit
except ImportError:
    pytest.skip("set_explicit.py not available", allow_module_level=True)


@pytest.mark.unit
class TestSetExplicit:
    """Test cases for set_explicit.py."""

    @patch("subprocess.run")
    def test_get_explicit_tag_success(self, mock_subprocess, temp_dir):
        """Test successful EXPLICIT tag retrieval."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        mock_subprocess.return_value.stdout = "EXPLICIT=Yes\n"

        result = set_explicit.get_explicit_tag(flac_file)

        assert result == "Yes"
        mock_subprocess.assert_called_once_with(
            ["metaflac", "--show-tag=EXPLICIT", str(flac_file)],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_explicit_tag_missing(self, mock_subprocess, temp_dir):
        """Test EXPLICIT tag retrieval when tag is missing."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        mock_subprocess.return_value.stdout = ""

        result = set_explicit.get_explicit_tag(flac_file)

        assert result == "None"

    @patch("subprocess.run")
    def test_set_explicit_tag_success(self, mock_subprocess, temp_dir):
        """Test successful EXPLICIT tag setting."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        # Configure mock to return different values for get vs set operations
        mock_subprocess.return_value.stdout = "EXPLICIT=None\n"

        old_value = set_explicit.set_explicit_tag(flac_file, "Yes")

        # The function should return the old value (None)
        assert old_value == "None"

        # Verify both operations were called (get + set)
        assert mock_subprocess.call_count == 2

        # Verify the set command was called with the correct arguments
        set_calls = [
            call
            for call in mock_subprocess.call_args_list
            if "--set-tag" in str(call) and "EXPLICIT=Yes" in str(call)
        ]
        assert len(set_calls) == 1

    @patch("subprocess.run")
    def test_set_explicit_tag_failure(self, mock_subprocess, temp_dir):
        """Test EXPLICIT tag setting failure."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "metaflac")

        with pytest.raises(subprocess.CalledProcessError):
            set_explicit.set_explicit_tag(flac_file, "Yes")

    @patch("set_explicit.set_explicit_tag")
    def test_process_album_success(self, mock_set_tag, temp_dir):
        """Test successful album processing."""
        album_dir = temp_dir / "Test Album"
        album_dir.mkdir()

        # Create FLAC files
        flac_files = ["song1.flac", "song2.flac", "song3.flac"]
        for flac in flac_files:
            (album_dir / flac).touch()

        # Mock tag setting to return old values
        mock_set_tag.side_effect = ["None", "Yes", "No"]

        with patch("builtins.print") as mock_print:
            count = set_explicit.process_album(album_dir, "Unknown")

        assert count == 3
        assert mock_set_tag.call_count == 3
        mock_set_tag.assert_any_call(album_dir / "song1.flac", "Unknown")
        mock_set_tag.assert_any_call(album_dir / "song2.flac", "Unknown")
        mock_set_tag.assert_any_call(album_dir / "song3.flac", "Unknown")

    def test_process_album_invalid_directory(self, temp_dir):
        """Test processing invalid album directory."""
        invalid_dir = temp_dir / "nonexistent"

        with pytest.raises(SystemExit):
            set_explicit.process_album(invalid_dir, "Yes")

    @patch("set_explicit.set_explicit_tag")
    def test_process_single_file_success(self, mock_set_tag, temp_dir):
        """Test successful single file processing."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        mock_set_tag.return_value = "None"

        with patch("builtins.print") as mock_print:
            set_explicit.process_single_file(flac_file, "Yes")

        mock_set_tag.assert_called_once_with(flac_file, "Yes")

    def test_process_single_file_invalid_file(self, temp_dir):
        """Test processing invalid file."""
        # Non-existent file
        non_existent = temp_dir / "nonexistent.flac"

        with pytest.raises(SystemExit):
            set_explicit.process_single_file(non_existent, "Yes")

        # Wrong extension
        wrong_ext = temp_dir / "test.mp3"
        wrong_ext.touch()

        with pytest.raises(SystemExit):
            set_explicit.process_single_file(wrong_ext, "Yes")

    @patch("set_explicit.process_album")
    def test_main_album_mode(self, mock_process, temp_dir):
        """Test main function in album mode."""
        album_dir = temp_dir / "Test Album"
        album_dir.mkdir()

        with patch("sys.argv", ["set_explicit.py", str(album_dir), "Yes", "--album"]):
            with patch("set_explicit.require_command"):
                set_explicit.main()

        mock_process.assert_called_once_with(album_dir, "Yes")

    @patch("set_explicit.process_single_file")
    def test_main_single_file_mode(self, mock_process, temp_dir):
        """Test main function in single file mode."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        with patch("sys.argv", ["set_explicit.py", str(flac_file), "No"]):
            with patch("set_explicit.require_command"):
                set_explicit.main()

        mock_process.assert_called_once_with(flac_file, "No")

    def test_main_invalid_value(self, temp_dir):
        """Test main function with invalid value."""
        flac_file = temp_dir / "test.flac"
        flac_file.touch()

        with patch("sys.argv", ["set_explicit.py", str(flac_file), "Invalid"]):
            with pytest.raises(SystemExit):
                set_explicit.main()


@pytest.mark.unit
@pytest.mark.integration
class TestSetExplicitIntegration:
    """Integration tests for set_explicit.py."""

    def test_require_command_missing(self):
        """Test behavior when required command is missing."""
        with patch("subprocess.run", return_value=Mock(returncode=1)):
            with pytest.raises(SystemExit):
                set_explicit.require_command("nonexistent_command")

    def test_require_command_exists(self):
        """Test behavior when required command exists."""
        with patch("subprocess.run", return_value=Mock(returncode=0)):
            # Should not raise exception
            set_explicit.require_command("python3")
