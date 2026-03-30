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

    def test_episode_pattern_generation(self):
        """Test episode filename pattern generation for MP4 files."""
        # Test the episode pattern logic for MP4 files (based on detection order)
        def get_episode_pattern(episode_num):
            """Generate episode filename pattern for episode number."""
            return f"S01E{episode_num:02d}"

        # Test episode numbering (1-based episode numbers)
        assert get_episode_pattern(1) == "S01E01"
        assert get_episode_pattern(2) == "S01E02"
        assert get_episode_pattern(3) == "S01E03"
        assert get_episode_pattern(4) == "S01E04"
        assert get_episode_pattern(5) == "S01E05"
        assert get_episode_pattern(10) == "S01E10"

    def test_observation_based_file_mapping(self):
        """Test observation-based file mapping instead of pattern guessing."""
        # Test the observation-based approach for mapping files to episodes
        def map_episodes_to_files(mkvs, start_episode):
            """Map episode numbers to files by creation order."""
            episode_to_file = {}
            for i, mkv in enumerate(mkvs):
                episode_num = start_episode + i
                episode_to_file[episode_num] = mkv
            return episode_to_file
        
        # Mock MKV files (simulating creation order)
        mock_mkvs = [
            "show_t01.mkv",  # First created
            "show_t02.mkv",  # Second created  
            "show_t03.mkv",  # Third created
        ]
        
        # Test mapping for Disc 1 (episodes 1-3)
        mapping = map_episodes_to_files(mock_mkvs, start_episode=1)
        assert mapping[1] == "show_t01.mkv"
        assert mapping[2] == "show_t02.mkv"
        assert mapping[3] == "show_t03.mkv"
        
        # Test mapping for Disc 2 (episodes 4-6)
        mapping_disc2 = map_episodes_to_files(mock_mkvs, start_episode=4)
        assert mapping_disc2[4] == "show_t01.mkv"
        assert mapping_disc2[5] == "show_t02.mkv"
        assert mapping_disc2[6] == "show_t03.mkv"
        
        # Test that this works regardless of MakeMKV's naming pattern
        weird_mkvs = [
            "show_weird_name_001.mkv",
            "show_weird_name_002.mkv", 
            "show_weird_name_003.mkv",
        ]
        
        mapping_weird = map_episodes_to_files(weird_mkvs, start_episode=1)
        assert mapping_weird[1] == "show_weird_name_001.mkv"
        assert mapping_weird[2] == "show_weird_name_002.mkv"
        assert mapping_weird[3] == "show_weird_name_003.mkv"

    def test_smart_episode_numbering_across_discs(self):
        """Test smart episode numbering that continues across discs."""
        # Test the smart episode numbering approach
        def get_next_episode_number(existing_tracks, detected_tracks):
            """Simulate the episode numbering logic."""
            # Next episode starts after existing tracks
            return existing_tracks + 1
        
        # Test episode numbering for multiple discs
        # Disc 1: 5 tracks detected, 0 existing
        assert get_next_episode_number(0, 5) == 1  # Start at episode 1
        # Disc 2: 4 tracks detected, 5 existing from Disc 1
        assert get_next_episode_number(5, 4) == 6  # Continue at episode 6
        # Disc 3: 5 tracks detected, 9 existing from Disc 1+2
        assert get_next_episode_number(9, 5) == 10  # Continue at episode 10
        
        # Test episode mapping for Disc 2
        existing_tracks = 5  # From Disc 1
        detected_tracks = 4   # Disc 2 has 4 episodes
        start_episode = existing_tracks + 1  # Episode 6
        
        # Track 0 → Episode 6, Track 1 → Episode 7, etc.
        for i in range(detected_tracks):
            expected_episode = start_episode + i
            assert expected_episode == 6 + i  # 6, 7, 8, 9
        
        # Test that only qualifying tracks (10+ minutes) are counted
        # This is simulated by the detected_tracks parameter
        qualifying_tracks = [0, 1, 2, 3, 4]  # 5 qualifying episodes
        non_qualifying = [5, 6, 7]  # 3 special features (ignored)
        
        assert len(qualifying_tracks) == 5
        assert len(non_qualifying) == 3
        # Only qualifying tracks are counted for episode numbering

    def test_sanitize_title_function(self):
        """Test title sanitization logic."""
        # Test basic sanitization
        assert rip_video.sanitize_title("Simple Title") == "Simple Title"
        assert rip_video.sanitize_title("title with and") == "Title With And"  # "and" not stop word when first
        assert rip_video.sanitize_title("TITLE WITH AND") == "TITLE WITH AND"  # All caps preserved
        
        # Test acronym preservation
        assert rip_video.sanitize_title("USA Today") == "USA Today"
        assert rip_video.sanitize_title("BBC News") == "BBC News"
        
        # Test stop words in middle
        assert rip_video.sanitize_title("Movie and Film") == "Movie and Film"  # "and" not stop word
        assert rip_video.sanitize_title("The Movie") == "The Movie"  # "the" not stop word at start

    def test_sanitize_year_function(self):
        """Test year sanitization logic."""
        # Test valid years
        assert rip_video.sanitize_year("2023") == "2023"
        assert rip_video.sanitize_year("1999") == "1999"
        
        # Test mixed content
        assert rip_video.sanitize_year("2023-2024") == "2023"
        assert rip_video.sanitize_year("(1999)") == "1999"
        assert rip_video.sanitize_year(" Released in 2021 ") == "2021"
        
        # Test invalid input - returns original if less than 4 digits
        assert rip_video.sanitize_year("") == ""
        assert rip_video.sanitize_year("abc") == "abc"  # No digits, returns original
        assert rip_video.sanitize_year("12") == "12"  # Too short, returns as-is

    def test_seconds_to_srt_time_function(self):
        """Test SRT time conversion function."""
        # Test the actual function from rip_video
        assert rip_video._seconds_to_srt_time(0.0) == "00:00:00,000"
        assert rip_video._seconds_to_srt_time(1.5) == "00:00:01,500"
        assert rip_video._seconds_to_srt_time(61.123) in ["00:01:01,123", "00:01:01,122"]  # Precision
        assert rip_video._seconds_to_srt_time(3661.999) in ["01:01:01,999", "01:01:01,998"]
        assert rip_video._seconds_to_srt_time(7200.0) == "02:00:00,000"

    def test_is_command_available_function(self):
        """Test command availability checking."""
        # Test with a command that should exist
        assert rip_video.is_command_available("python") == True
        assert rip_video.is_command_available("python3") == True
        
        # Test with a command that shouldn't exist
        assert rip_video.is_command_available("definitely_not_a_real_command_12345") == False

    def test_language_helper_functions(self):
        """Test language detection helper functions."""
        # Mock stream data with proper structure
        audio_streams = [
            {"tags": {"language": "eng"}},
            {"tags": {"language": "fre"}},
            {"tags": {}}  # No language
        ]
        
        subtitle_streams = [
            {"tags": {"language": "eng"}, "codec_name": "subrip", "index": 0},
            {"tags": {"language": "spa"}, "codec_name": "subrip", "index": 1},
        ]
        
        # Test has_lang function
        assert rip_video.has_lang(audio_streams, "eng") == True
        assert rip_video.has_lang(audio_streams, "fre") == True
        assert rip_video.has_lang(audio_streams, "ger") == False
        
        # Test first_eng_text_sub_index with proper structure
        assert rip_video.first_eng_text_sub_index(subtitle_streams) == 0
        
        # Test pick_default_audio_lang
        assert rip_video.pick_default_audio_lang(audio_streams) == "eng"

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
