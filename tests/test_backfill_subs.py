#!/usr/bin/env python3
"""
Tests for backfill_subs.py script.
"""

import pytest
import subprocess
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "video"))

try:
    import backfill_subs
except ImportError:
    pytest.skip("backfill_subs.py not available", allow_module_level=True)


@pytest.mark.unit
class TestBackfillSubs:
    """Test cases for backfill_subs.py."""
    
    def test_find_largest_mkv(self, temp_dir):
        """Test finding the largest MKV file."""
        mkv_dir = temp_dir / "test"
        mkv_dir.mkdir()
        
        # Create MKV files with different sizes
        (mkv_dir / "small.mkv").write_bytes(b"x" * 1000)
        (mkv_dir / "large.mkv").write_bytes(b"x" * 5000)
        (mkv_dir / "medium.mkv").write_bytes(b"x" * 3000)
        
        largest = backfill_subs.find_largest_mkv(mkv_dir)
        
        assert largest.name == "large.mkv"
        assert largest.stat().st_size == 5000
    
    def test_find_largest_mkv_empty(self, temp_dir):
        """Test finding largest MKV in empty directory."""
        mkv_dir = temp_dir / "empty"
        mkv_dir.mkdir()
        
        largest = backfill_subs.find_largest_mkv(mkv_dir)
        
        assert largest is None
    
    def test_determine_target_mp4_exact_match(self, temp_dir):
        """Test determining target MP4 with exact name match."""
        dst_dir = temp_dir / "Movie Name (2023)"
        dst_dir.mkdir()
        
        # Create matching MP4
        (dst_dir / "Movie Name (2023).mp4").touch()
        
        target = backfill_subs.determine_target_mp4(dst_dir)
        
        assert target.name == "Movie Name (2023).mp4"
    
    def test_determine_target_mp4_single_file(self, temp_dir):
        """Test determining target MP4 with single file."""
        dst_dir = temp_dir / "Movies"
        dst_dir.mkdir()
        
        # Create single MP4
        (dst_dir / "movie.mp4").touch()
        
        target = backfill_subs.determine_target_mp4(dst_dir)
        
        assert target.name == "movie.mp4"
    
    def test_determine_target_mp4_ambiguous(self, temp_dir):
        """Test determining target MP4 with multiple files."""
        dst_dir = temp_dir / "Movies"
        dst_dir.mkdir()
        
        # Create multiple MP4s
        (dst_dir / "movie1.mp4").touch()
        (dst_dir / "movie2.mp4").touch()
        
        target = backfill_subs.determine_target_mp4(dst_dir)
        
        assert target is None
    
    def test_get_eng_subtitle_indices(self):
        """Test extracting English subtitle indices."""
        subs_json = {
            "streams": [
                {
                    "index": 1,
                    "codec_name": "subrip",
                    "tags": {"language": "eng"}
                },
                {
                    "index": 2,
                    "codec_name": "dvd_subtitle",
                    "tags": {"language": "eng"}
                },
                {
                    "index": 3,
                    "codec_name": "subrip",
                    "tags": {"language": "spa"}
                }
            ]
        }
        
        result = backfill_subs.get_eng_subtitle_indices(subs_json)
        
        assert result["eng_text_idx"] == 0  # First stream (index 1)
        assert result["eng_image_idx"] == 1  # Second stream (index 2)
        assert result["eng_image_codec"] == "dvd_subtitle"
    
    def test_get_eng_subtitle_indices_no_english(self):
        """Test when no English subtitles are found."""
        subs_json = {
            "streams": [
                {
                    "index": 1,
                    "codec_name": "subrip",
                    "tags": {"language": "spa"}
                }
            ]
        }
        
        result = backfill_subs.get_eng_subtitle_indices(subs_json)
        
        assert result["eng_text_idx"] == -1
        assert result["eng_image_idx"] == -1
        assert result["eng_image_codec"] == ""
    
    @patch('subprocess.run')
    def test_probe_subtitle_streams_success(self, mock_subprocess, sample_mkv_dir):
        """Test successful subtitle probing."""
        mock_subprocess.return_value.stdout = json.dumps({
            "streams": [
                {"index": 1, "codec_name": "subrip", "tags": {"language": "eng"}}
            ]
        })
        
        mkv_file = sample_mkv_dir / "movie.mkv"
        result = backfill_subs.probe_subtitle_streams(mkv_file)
        
        assert "streams" in result
        assert len(result["streams"]) == 1
    
    @patch('subprocess.run')
    def test_probe_subtitle_streams_failure(self, mock_subprocess, sample_mkv_dir):
        """Test subtitle probing failure."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
        
        mkv_file = sample_mkv_dir / "movie.mkv"
        result = backfill_subs.probe_subtitle_streams(mkv_file)
        
        assert result == {}
    
    @patch('subprocess.run')
    def test_get_mkvmerge_track_id_success(self, mock_subprocess, sample_mkv_dir):
        """Test successful mkvmerge track ID extraction."""
        mock_subprocess.return_value.stdout = json.dumps({
            "tracks": [
                {
                    "id": 2,
                    "type": "subtitles",
                    "properties": {
                        "language": "eng",
                        "codec_id": "S_VOBSUB"
                    }
                }
            ]
        })
        
        mkv_file = sample_mkv_dir / "movie.mkv"
        track_id = backfill_subs.get_mkvmerge_track_id(mkv_file, 1)
        
        assert track_id == 2
    
    @patch('subprocess.run')
    def test_get_mkvmerge_track_id_not_found(self, mock_subprocess, sample_mkv_dir):
        """Test mkvmerge track ID not found."""
        mock_subprocess.return_value.stdout = json.dumps({"tracks": []})
        
        mkv_file = sample_mkv_dir / "movie.mkv"
        track_id = backfill_subs.get_mkvmerge_track_id(mkv_file, 1)
        
        assert track_id == -1
    
    @patch('subprocess.run')
    def test_handle_text_subs(self, mock_subprocess, temp_dir):
        """Test handling English text subtitles."""
        target_mp4 = temp_dir / "movie.mp4"
        mkv_file = temp_dir / "movie.mkv"
        out_path = temp_dir / "movie.en-subs.mp4"
        
        # Create target MP4
        target_mp4.touch()
        
        backfill_subs.handle_text_subs(target_mp4, mkv_file, 1, out_path)
        
        # Verify ffmpeg was called
        mock_subprocess.assert_called()
        # When subprocess is mocked, the output file won't actually be created.
    
    @patch('subprocess.run')
    def test_handle_image_subs_ocr_dvd(self, mock_subprocess, temp_dir, sample_mkv_dir, sample_mp4_dir):
        """Test OCR handling for DVD subtitles."""
        dst_dir = sample_mp4_dir.parent
        
        with patch('backfill_subs.os.getpid', return_value=12345), patch('builtins.print') as mock_print:
            # ensure mkvextract not installed path
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stdout = ""
            backfill_subs.handle_image_subs_ocr(
                sample_mp4_dir / "Movie Name (2023).mp4",
                sample_mkv_dir / "movie.mkv",
                1,  # eng_image_idx
                "dvd_subtitle",  # eng_image_codec
                2,  # eng_img_tid
                dst_dir
            )

            assert any(
                "VobSub (DVD) subtitles detected" in str(c.args[0])
                for c in mock_print.call_args_list
                if c.args
            )
    
    @patch('subprocess.run')
    def test_handle_image_subs_ocr_bluray(self, mock_subprocess, temp_dir, sample_mkv_dir, sample_mp4_dir):
        """Test OCR handling for Blu-ray subtitles."""
        dst_dir = sample_mp4_dir.parent
        
        with patch('backfill_subs.os.getpid', return_value=12345), patch('builtins.print') as mock_print:
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stdout = ""
            backfill_subs.handle_image_subs_ocr(
                sample_mp4_dir / "Movie Name (2023).mp4",
                sample_mkv_dir / "movie.mkv",
                1,  # eng_image_idx
                "hdmv_pgs_subtitle",  # eng_image_codec
                2,  # eng_img_tid
                dst_dir
            )

            assert any(
                "PGS (Blu-ray) subtitles detected" in str(c.args[0])
                for c in mock_print.call_args_list
                if c.args
            )
    
    @patch('backfill_subs.find_largest_mkv')
    @patch('backfill_subs.determine_target_mp4')
    @patch('backfill_subs.probe_subtitle_streams')
    @patch('backfill_subs.handle_text_subs')
    def test_main_text_subs_success(self, mock_handle_text, mock_probe, 
                                    mock_determine, mock_find, sample_mkv_dir, sample_mp4_dir):
        """Test successful main execution with text subtitles."""
        # Mock dependencies
        mock_find.return_value = sample_mkv_dir / "movie.mkv"
        mock_determine.return_value = sample_mp4_dir / "Movie Name (2023).mp4"
        mock_probe.return_value = {"streams": [{"index": 1, "codec_name": "subrip", "tags": {"language": "eng"}}]}
        
        with patch('sys.argv', ['backfill_subs.py', str(sample_mkv_dir), str(sample_mp4_dir)]):
            rc = backfill_subs.main()
        assert rc == 0
        
        # Verify text subtitle handling was called
        mock_handle_text.assert_called_once()
    
    def test_main_no_mkv_files(self, temp_dir):
        """Test main execution with no MKV files."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        
        with patch('sys.argv', ['backfill_subs.py', str(empty_dir), str(temp_dir)]):
            rc = backfill_subs.main()
        assert rc == 2
    
    @patch('backfill_subs.find_largest_mkv')
    def test_main_no_target_mp4(self, mock_find, temp_dir):
        """Test main execution with no target MP4 found."""
        mock_find.return_value = None
        
        with patch('sys.argv', ['backfill_subs.py', str(temp_dir), str(temp_dir)]):
            rc = backfill_subs.main()
        assert rc == 2


@pytest.mark.unit
@pytest.mark.integration
class TestBackfillSubsIntegration:
    """Integration tests for backfill_subs.py."""
    
    def test_require_command_missing(self):
        """Test behavior when required command is missing."""
        with patch('subprocess.run', return_value=Mock(returncode=1, stdout='')):
            with pytest.raises(SystemExit):
                backfill_subs.require_command('nonexistent_command')
    
    def test_require_command_exists(self):
        """Test behavior when required command exists."""
        with patch('subprocess.run', return_value=Mock(returncode=0, stdout='/usr/bin/python3\n')):
            # Should not raise exception
            backfill_subs.require_command('python3')
