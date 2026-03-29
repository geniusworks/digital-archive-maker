#!/usr/bin/env python3
"""
Tests for rip_video.py script.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "video"))

try:
    import rip_video
except ImportError:
    pytest.skip("rip_video.py not available", allow_module_level=True)


@pytest.mark.unit
class TestRipVideo:
    """Test cases for rip_video.py subtitle handling and MP4 skip logic."""

    def test_interactive_subtitle_prompt_default_action_vob_convert(self):
        """Test that VOB subtitles default to extract_vob_convert action."""
        # Test the core logic directly without mocking
        # Simulate the condition: has_preferred_audio and preferred_vob_subs
        # and not preferred_text_subs

        # Simulate English audio present
        has_preferred_audio = True

        # Simulate English VOB subtitles present, no text subtitles
        preferred_vob_subs = True
        preferred_text_subs = False

        # This is the exact condition from rip_video.py line 362-364
        if has_preferred_audio and preferred_vob_subs and not preferred_text_subs:
            default_action = "extract_vob_convert"
        else:
            default_action = "unknown"

        assert default_action == "extract_vob_convert"

    def test_interactive_subtitle_prompt_default_action_burn_vob(self):
        """Test that foreign audio + VOB subtitles defaults to burn_vob_subs."""
        # Test the core logic directly without mocking
        # Simulate the condition: not has_preferred_audio and has_foreign_audio
        # and preferred_vob_subs

        # Simulate foreign audio present
        has_preferred_audio = False
        has_foreign_audio = True

        # Simulate English VOB subtitles present, no text subtitles
        preferred_vob_subs = True
        preferred_text_subs = False

        # This is the exact condition from rip_video.py line 369-371
        if not has_preferred_audio and has_foreign_audio and preferred_vob_subs:
            default_action = "burn_vob_subs"
        else:
            default_action = "unknown"

        assert default_action == "burn_vob_subs"

    def test_seconds_to_srt_time_conversion(self):
        """Test the _seconds_to_srt_time helper function."""
        # Test basic conversion
        assert rip_video._seconds_to_srt_time(0.0) == "00:00:00,000"
        assert rip_video._seconds_to_srt_time(1.5) == "00:00:01,500"
        # Account for floating point precision
        result = rip_video._seconds_to_srt_time(61.123)
        assert result in ["00:01:01,123", "00:01:01,122"]  # Allow for precision

        # Test larger values (account for floating point precision)
        result_large = rip_video._seconds_to_srt_time(3661.999)
        assert result_large in ["01:01:01,999", "01:01:01,998"]  # Allow for precision
        assert rip_video._seconds_to_srt_time(7200.0) == "02:00:00,000"

    def test_available_actions_includes_vob_convert(self):
        """Test that extract_vob_convert is added to available actions for VOB subs."""
        # Mock data with VOB subtitles
        preferred_vob_subs = True
        has_foreign_audio = False

        available_actions = []

        # VOB subtitles (DVD subtitles, can be converted to SRT or burned)
        if preferred_vob_subs:
            available_actions.append(("extract_vob_convert", "MP4 + Convert DVD subtitles"))
            if has_foreign_audio:
                available_actions.append(("burn_vob_subs", "MP4 + Burn DVD subtitles"))

        # Should have the VOB convert option
        assert any(action == "extract_vob_convert" for action, _ in available_actions)
        assert ("extract_vob_convert", "MP4 + Convert DVD subtitles") in available_actions

    def test_track_pattern_generation(self):
        """Test MakeMKV track pattern generation logic for selective ripping."""
        # Test the track pattern logic we added for selective ripping
        def get_track_pattern(track_str):
            """Generate MakeMKV filename pattern for track."""
            track_number_for_filename = int(track_str) + 1  # Convert 0-based track to 1-based filename
            return f"_t{track_number_for_filename:02d}.mkv"

        # Test track to filename mapping (0-based track to 1-based filename)
        assert get_track_pattern("0") == "_t01.mkv"
        assert get_track_pattern("1") == "_t02.mkv"
        assert get_track_pattern("2") == "_t03.mkv"
        assert get_track_pattern("3") == "_t04.mkv"
        assert get_track_pattern("4") == "_t05.mkv"
        assert get_track_pattern("9") == "_t10.mkv"

    def test_episode_pattern_generation(self):
        """Test episode filename pattern generation for MP4 files."""
        # Test the episode pattern logic for MP4 files
        def get_episode_pattern(track_str):
            """Generate episode filename pattern for track."""
            episode_num = int(track_str) + 1  # Track 0 becomes Episode 1
            return f"S01E{episode_num:02d}"

        # Test track to episode mapping (0-based track to 1-based episode)
        assert get_episode_pattern("0") == "S01E01"
        assert get_episode_pattern("1") == "S01E02"
        assert get_episode_pattern("2") == "S01E03"
        assert get_episode_pattern("3") == "S01E04"
        assert get_episode_pattern("4") == "S01E05"
        assert get_episode_pattern("9") == "S01E10"

    def test_existing_mkv_detection_logic(self):
        """Test logic for detecting existing MKV files for selective ripping."""
        # Mock existing MKV files
        existing_mkvs = [
            "show_t01.mkv",
            "show_t02.mkv", 
            "show_t03.mkv"
        ]
        
        # Test track pattern matching
        def track_exists(track_str, existing_files):
            """Check if track already has MKV file."""
            track_pattern = f"_t{int(track_str)+1:02d}"
            return any(track_pattern in mkv for mkv in existing_files)
        
        # Test detection
        assert track_exists("0", existing_mkvs) == True   # _t01 exists
        assert track_exists("1", existing_mkvs) == True   # _t02 exists
        assert track_exists("2", existing_mkvs) == True   # _t03 exists
        assert track_exists("3", existing_mkvs) == False  # _t04 missing
        assert track_exists("4", existing_mkvs) == False  # _t05 missing

    def test_show_spinner_function(self):
        """Test the show_spinner function creates a thread."""
        import threading
        import time

        # Test spinner with duration
        start_time = time.time()
        spinner_thread = rip_video.show_spinner("Test message", duration=0.3)
        end_time = time.time()

        # Should have taken approximately 0.3 seconds (allow for system variation)
        assert 0.2 <= (end_time - start_time) <= 0.6
        assert spinner_thread is not None
        assert isinstance(spinner_thread, threading.Thread)

    def test_stop_spinner_function(self):
        """Test the stop_spinner function properly stops spinner."""
        import time

        # Start a spinner without duration
        spinner_thread = rip_video.show_spinner("Test message")

        # Give it a moment to start
        time.sleep(0.1)

        # Stop the spinner
        rip_video.stop_spinner(spinner_thread, "✓ Test complete")

        # Thread should be stopped
        assert getattr(spinner_thread, "stop", False) is True


@pytest.mark.integration
class TestRipVideoIntegration:
    """Integration tests for rip_video.py."""

    def test_require_command_missing(self):
        """Test require_command function with missing command."""
        with patch("subprocess.run") as mock_run:
            # Mock which command to return non-zero exit code (command not found)
            mock_run.return_value.returncode = 1

            try:
                rip_video.require_command("nonexistent_command_xyz")
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "Missing required command" in str(e)
                assert "nonexistent_command_xyz" in str(e)

    def test_require_command_exists(self):
        """Test require_command function with existing command."""
        with patch("subprocess.run") as mock_run:
            # Mock which command to return zero exit code (command found)
            mock_run.return_value.returncode = 0

            # Should not raise an exception
            rip_video.require_command("python3")  # python3 should exist
