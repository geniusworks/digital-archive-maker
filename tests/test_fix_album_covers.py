#!/usr/bin/env python3
"""
Tests for fix_album_covers.py script.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "music"))

try:
    import fix_album_covers
except ImportError:
    pytest.skip("fix_album_covers.py not available", allow_module_level=True)


@pytest.mark.unit
class TestFixAlbumCovers:
    """Test cases for fix_album_covers.py."""

    def test_url_encode(self):
        """Test URL encoding function."""
        assert fix_album_covers.url_encode("Test Artist") == "Test%20Artist"
        assert fix_album_covers.url_encode("Artist/Album") == "Artist%2FAlbum"

    @patch("subprocess.run")
    def test_process_album_dir_has_cover(self, mock_subprocess, sample_album_dir):
        """Test processing album that already has cover."""
        # Create existing cover
        (sample_album_dir / "cover.jpg").touch()

        fix_album_covers.process_album_dir(sample_album_dir)

        # Should not attempt to download
        mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    def test_process_album_dir_skip_invalid(self, mock_subprocess, temp_dir):
        """Test skipping albums with invalid names."""
        invalid_album = temp_dir / "Unknown" / "Unknown Album"
        invalid_album.mkdir(parents=True)

        fix_album_covers.process_album_dir(invalid_album)

        # Should not attempt to download
        mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    @patch("fix_album_covers.Path")
    def test_process_album_dir_success(self, mock_path, mock_subprocess, sample_album_dir):
        """Test successful cover download."""

        # Mock subprocess responses
        def mock_run(cmd, **kwargs):
            cmd_str = " ".join(str(x) for x in cmd)
            check = kwargs.get("check", False)

            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            if "musicbrainz.org" in cmd_str:
                result.stdout = json.dumps({"releases": [{"id": "test-release-id"}]})
                return result

            if "coverartarchive.org" in cmd_str:
                # Simulate curl writing a file by creating the output file passed after -o
                if "-o" in cmd:
                    out_path = Path(cmd[cmd.index("-o") + 1])
                    out_path.write_bytes(b"fakejpeg")
                return result

            if cmd[:2] == ["file", "--mime-type"]:
                result.stdout = "image/jpeg\n"
                return result

            if cmd[:2] == ["which", "magick"]:
                # Pretend magick isn't installed
                result.returncode = 1
                return result

            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=result.stdout, stderr=result.stderr
                )
            return result

        mock_subprocess.side_effect = mock_run

        fix_album_covers.process_album_dir(sample_album_dir)

        # Verify cover was created
        assert (sample_album_dir / "cover.jpg").exists()

    @patch("subprocess.run")
    def test_process_album_dir_no_musicbrainz_result(self, mock_subprocess, sample_album_dir):
        """Test handling when no MusicBrainz release is found."""
        mock_subprocess.return_value.stdout = json.dumps({"releases": []})
        mock_subprocess.return_value.returncode = 0

        fix_album_covers.process_album_dir(sample_album_dir)

        # Should not create cover
        assert not (sample_album_dir / "cover.jpg").exists()

    @patch("subprocess.run")
    def test_process_album_dir_download_failure(self, mock_subprocess, sample_album_dir):
        """Test handling when cover download fails."""

        # Mock MusicBrainz success
        def mock_run(cmd, **kwargs):
            cmd_str = " ".join(str(x) for x in cmd)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            if "musicbrainz.org" in cmd_str:
                result.stdout = json.dumps({"releases": [{"id": "test-release-id"}]})
                return result

            if "coverartarchive.org" in cmd_str:
                result.returncode = 22
                return result

            if cmd[:2] == ["file", "--mime-type"]:
                result.stdout = "image/jpeg\n"
                return result

            return result

        mock_subprocess.side_effect = mock_run

        fix_album_covers.process_album_dir(sample_album_dir)

        # Should not create cover
        assert not (sample_album_dir / "cover.jpg").exists()

    @patch("subprocess.run")
    def test_process_album_dir_invalid_image(self, mock_subprocess, sample_album_dir):
        """Test handling when downloaded file is not a valid JPEG."""

        # Mock subprocess responses
        def mock_run(cmd, **kwargs):
            cmd_str = " ".join(str(x) for x in cmd)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            if "musicbrainz.org" in cmd_str:
                result.stdout = json.dumps({"releases": [{"id": "test-release-id"}]})
                return result

            if "coverartarchive.org" in cmd_str:
                if "-o" in cmd:
                    out_path = Path(cmd[cmd.index("-o") + 1])
                    out_path.write_bytes(b"fakepng")
                return result

            if cmd[:2] == ["file", "--mime-type"]:
                result.stdout = "image/png\n"
                return result

            if cmd[:2] == ["which", "magick"]:
                result.returncode = 1
                return result

            return result

        mock_subprocess.side_effect = mock_run

        fix_album_covers.process_album_dir(sample_album_dir)

        # Should not create cover
        assert not (sample_album_dir / "cover.jpg").exists()

    @patch("fix_album_covers.process_album_dir")
    def test_scan_library_single_album(self, mock_process, sample_album_dir):
        """Test scanning library with single album (FLAC files in root)."""
        # Add FLAC files to album directory
        (sample_album_dir / "test.flac").touch()

        fix_album_covers.scan_library(sample_album_dir)

        # Should process the album directory
        mock_process.assert_called_once_with(sample_album_dir)

    @patch("fix_album_covers.process_album_dir")
    def test_scan_library_recursive(self, mock_process, temp_dir):
        """Test recursive library scanning."""
        # Create nested structure
        artist_dir = temp_dir / "Artist" / "Album"
        artist_dir.mkdir(parents=True)
        (artist_dir / "track.flac").touch()

        # Create another album without cover
        artist2_dir = temp_dir / "Artist2" / "Album2"
        artist2_dir.mkdir(parents=True)
        (artist2_dir / "track2.flac").touch()

        fix_album_covers.scan_library(temp_dir)

        # Should process both albums
        assert mock_process.call_count == 2

    @patch("fix_album_covers.process_album_dir")
    def test_scan_library_no_albums_found(self, mock_process, temp_dir):
        """Test scanning library with no albums found."""
        # Create directory without FLAC files
        (temp_dir / "empty").mkdir()

        with patch("builtins.print") as mock_print:
            fix_album_covers.scan_library(temp_dir)

            # Should print "no albums found" message
            mock_print.assert_any_call("✔ No album folders missing cover.jpg found.")

    def test_main_invalid_directory(self):
        """Test handling of invalid directory."""
        with patch("sys.argv", ["fix_album_covers.py", "/nonexistent/path"]):
            with pytest.raises(SystemExit):
                fix_album_covers.main()

    @patch("fix_album_covers.scan_library")
    def test_main_success(self, mock_scan, temp_dir):
        """Test successful main execution."""
        with patch("sys.argv", ["fix_album_covers.py", str(temp_dir)]):
            fix_album_covers.main()

        mock_scan.assert_called_once_with(temp_dir)

    @patch("fix_album_covers.scan_library")
    def test_main_default_directory(self, mock_scan):
        """Test main execution with default directory."""
        with patch("sys.argv", ["fix_album_covers.py"]):
            with patch("fix_album_covers.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                fix_album_covers.main()

        mock_scan.assert_called_once()


@pytest.mark.unit
@pytest.mark.integration
class TestFixAlbumCoversIntegration:
    """Integration tests for fix_album_covers.py."""

    def test_require_command_missing(self):
        """Test behavior when required command is missing."""
        with patch("subprocess.run", return_value=Mock(returncode=1)):
            with pytest.raises(SystemExit):
                fix_album_covers.require_command("nonexistent_command")

    def test_require_command_exists(self):
        """Test behavior when required command exists."""
        with patch("subprocess.run", return_value=Mock(returncode=0)):
            # Should not raise exception
            fix_album_covers.require_command("python3")
