#!/usr/bin/env python3
"""
Embed thumbnail image into MP4/M4V file as cover art.

Usage:
    python3 embed_thumbnail.py /path/to/video.mp4 /path/to/thumbnail.jpg
"""

import sys
from pathlib import Path

try:
    from mutagen.mp4 import MP4, MP4Cover
except ImportError:
    print("Error: mutagen library not available. Install with: pip install mutagen")
    sys.exit(1)


def embed_thumbnail(video_path: Path, thumbnail_path: Path) -> bool:
    """Embed thumbnail as cover art in MP4/M4V file."""
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return False
    
    if not thumbnail_path.exists():
        print(f"❌ Thumbnail file not found: {thumbnail_path}")
        return False
    
    try:
        # Load the video file
        print(f"📹 Loading video: {video_path.name}")
        mp4 = MP4(str(video_path))
        
        # Check if already has cover
        has_existing = 'covr' in mp4
        if has_existing:
            print("⚠️  File already has embedded cover art - will replace")
        
        # Load thumbnail image
        print(f"🖼️  Loading thumbnail: {thumbnail_path.name}")
        with open(thumbnail_path, "rb") as f:
            thumbnail_data = f.read()
        
        # Embed as cover art
        mp4['covr'] = [MP4Cover(thumbnail_data, imageformat=MP4Cover.FORMAT_JPEG)]
        
        # Save the file
        mp4.save()
        print("✅ Thumbnail embedded successfully!")
        
        # Verify
        mp4 = MP4(str(video_path))
        if 'covr' in mp4:
            cover_size = len(mp4['covr'][0])
            print(f"✅ Verified: Cover art embedded ({cover_size} bytes)")
        else:
            print("❌ Verification failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error embedding thumbnail: {e}")
        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 embed_thumbnail.py <video_file> <thumbnail_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    thumbnail_path = Path(sys.argv[2])
    
    success = embed_thumbnail(video_path, thumbnail_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
