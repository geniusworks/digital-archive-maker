#!/usr/bin/env python3
"""
Test configuration and fixtures for the digital library scripts.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import json


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_album_dir(temp_dir):
    """Create a sample album directory with FLAC files."""
    album_dir = temp_dir / "Test Artist" / "Test Album"
    album_dir.mkdir(parents=True)
    
    # Create sample FLAC files
    flac_files = [
        "track1.flac",
        "track2.flac", 
        "track3.flac"
    ]
    
    for flac_file in flac_files:
        (album_dir / flac_file).touch()
    
    return album_dir


@pytest.fixture
def sample_mkv_dir(temp_dir):
    """Create a sample MKV directory with subtitle files."""
    mkv_dir = temp_dir / "Movie Name (2023)"
    mkv_dir.mkdir(parents=True)
    
    # Create sample MKV files
    (mkv_dir / "movie.mkv").write_bytes(b"fake mkv content")
    (mkv_dir / "extra.mkv").write_bytes(b"fake mkv content smaller")
    
    return mkv_dir


@pytest.fixture
def sample_mp4_dir(temp_dir):
    """Create a sample MP4 directory."""
    mp4_dir = temp_dir / "Movies" / "Movie Name (2023)"
    mp4_dir.mkdir(parents=True)
    
    # Create sample MP4 file
    (mp4_dir / "Movie Name (2023).mp4").write_bytes(b"fake mp4 content")
    
    return mp4_dir


@pytest.fixture
def mock_musicbrainz_response():
    """Mock MusicBrainz API response."""
    return {
        "releases": [
            {
                "id": "test-release-id",
                "title": "Test Album",
                "artist-credit": [
                    {"artist": {"name": "Test Artist"}}
                ]
            }
        ]
    }


@pytest.fixture
def mock_tracklist_response():
    """Mock MusicBrainz tracklist response."""
    return {
        "media": [
            {
                "tracks": [
                    {"title": "First Track"},
                    {"title": "Second Track"},
                    {"title": "Third Track"}
                ]
            }
        ]
    }


@pytest.fixture
def mock_subtitle_streams():
    """Mock ffprobe subtitle streams response."""
    return {
        "streams": [
            {
                "index": 2,
                "codec_name": "subrip",
                "tags": {"language": "eng"}
            },
            {
                "index": 3,
                "codec_name": "dvd_subtitle",
                "tags": {"language": "eng"}
            }
        ]
    }


@pytest.fixture
def mock_cover_art_response():
    """Mock cover art image content."""
    return b"fake jpeg content"


class MockSubprocess:
    """Mock subprocess for testing."""
    
    @staticmethod
    def run(cmd, capture_output=True, text=True, check=True, **kwargs):
        """Mock subprocess.run."""
        result = Mock()
        result.stdout = ""
        result.returncode = 0
        
        # Mock different commands
        if 'curl' in cmd and 'musicbrainz' in ' '.join(cmd):
            if 'release' in ' '.join(cmd):
                result.stdout = json.dumps({
                    "releases": [{"id": "test-release-id"}]
                })
            else:
                result.stdout = json.dumps({
                    "media": [{"tracks": [{"title": "Test Track"}]}]
                })
        elif 'curl' in cmd and 'coverartarchive' in ' '.join(cmd):
            result.stdout = "fake jpeg content"
        elif 'ffprobe' in cmd:
            result.stdout = json.dumps({
                "streams": [{"index": 2, "codec_name": "subrip", "tags": {"language": "eng"}}]
            })
        elif 'file' in cmd:
            result.stdout = "JPEG image data"
        elif 'which' in cmd:
            result.returncode = 0  # Command exists
        
        return result


@pytest.fixture
def mock_subprocess():
    """Mock subprocess module."""
    with patch('subprocess.run', MockSubprocess.run):
        yield
