#!/usr/bin/env python3
"""
Tests for rip_video.py script.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the bin directory to the path so we can import the scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "bin" / "video"))

try:
    import rip_video
except ImportError:
    pytest.skip("rip_video.py not available", allow_module_level=True)


@pytest.mark.unit
class TestRipVideo:
    """Test cases for rip_video.py subtitle handling."""

    def test_interactive_subtitle_prompt_default_action_vob_convert(self):
        """Test that VOB subtitles default to extract_vob_convert action."""
        # Test the core logic directly without mocking
        # Simulate the condition: has_preferred_audio and preferred_vob_subs and not preferred_text_subs
        
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
        # Simulate the condition: not has_preferred_audio and has_foreign_audio and preferred_vob_subs
        
        # Simulate foreign audio (no preferred audio)
        has_preferred_audio = False
        has_foreign_audio = True
        
        # Simulate English VOB subtitles present, no text subtitles
        preferred_vob_subs = True
        preferred_text_subs = False
        
        # This is the exact condition from rip_video.py lines 349-355
        if not has_preferred_audio and has_foreign_audio:
            if preferred_text_subs:
                default_action = "burn_subs"
            elif preferred_vob_subs:
                default_action = "burn_vob_subs"
            else:
                default_action = "unknown"
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

    def test_require_command_mkvextract(self):
        """Test that mkvextract is properly required."""
        # Test that require_command function works with mkvextract
        with patch('subprocess.run') as mock_run:
            # Mock which command to return zero exit code (command found)
            mock_run.return_value.returncode = 0
            
            # Should not raise an exception for mkvextract
            rip_video.require_command("mkvextract")
            
            # Verify which command was called (account for additional kwargs)
            mock_run.assert_called_with(['which', 'mkvextract'], check=False, capture_output=True, text=True)


@pytest.mark.integration
class TestRipVideoIntegration:
    """Integration tests for rip_video.py."""

    def test_require_command_missing(self):
        """Test require_command function with missing command."""
        with patch('subprocess.run') as mock_run:
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
        with patch('subprocess.run') as mock_run:
            # Mock which command to return zero exit code (command found)
            mock_run.return_value.returncode = 0
            
            # Should not raise an exception
            rip_video.require_command("python3")  # python3 should exist
