#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def optimize_mp4_for_streaming(mp4_path: Path, dry_run: bool = False) -> bool:
    """Optimize an MP4 file for streaming by moving moov atom to beginning."""
    if not mp4_path.exists():
        print(f"❌ File not found: {mp4_path}")
        return False
    
    print(f"🎬 Optimizing: {mp4_path.name}")
    
    if dry_run:
        print(f"   (DRY RUN) Would optimize with ffmpeg faststart flags")
        return True
    
    try:
        # Create temporary file
        temp_path = mp4_path.with_suffix(".temp.mp4")
        
        # Apply streaming optimization
        cmd = [
            "ffmpeg",
            "-i", str(mp4_path),
            "-c", "copy",  # Copy streams without re-encoding
            "-movflags", "+faststart",  # Standard web optimization (removes fragmentation if present)
            "-f", "mp4",
            str(temp_path)
        ]
        
        print(f"   📦 Applying streaming optimization...")
        result = run_cmd(cmd, check=True)
        
        # Replace original file
        original_size = mp4_path.stat().st_size
        temp_path.replace(mp4_path)
        new_size = mp4_path.stat().st_size
        
        print(f"   ✅ Optimized: {original_size / (1024**2):.1f}MB → {new_size / (1024**2):.1f}MB")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def find_mp4_files(directory: Path, recursive: bool = True) -> list[Path]:
    """Find all MP4 files in directory."""
    pattern = "**/*.mp4" if recursive else "*.mp4"
    return sorted(directory.glob(pattern))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Optimize MP4 files for streaming (Jellyfin/Plex compatibility)"
    )
    parser.add_argument(
        "directory", 
        help="Directory containing MP4 files to optimize"
    )
    parser.add_argument(
        "--recursive", "-r", 
        action="store_true", 
        default=True,
        help="Search recursively (default)"
    )
    parser.add_argument(
        "--no-recursive", 
        action="store_false", 
        dest="recursive",
        help="Don't search recursively"
    )
    parser.add_argument(
        "--dry-run", "-n", 
        action="store_true",
        help="Show what would be optimized without making changes"
    )
    parser.add_argument(
        "--pattern", "-p",
        help="Only optimize files matching this pattern (e.g., '*Barry*')"
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"❌ Directory not found: {directory}")
        return 1
    
    # Find MP4 files
    mp4_files = find_mp4_files(directory, args.recursive)
    
    # Filter by pattern if specified
    if args.pattern:
        mp4_files = [f for f in mp4_files if args.pattern.lower() in f.name.lower()]
        print(f"🔍 Pattern filter: '{args.pattern}'")
    
    if not mp4_files:
        print(f"📂 No MP4 files found in {directory}")
        return 0
    
    print(f"📁 Found {len(mp4_files)} MP4 file(s) in {directory}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    # Optimize each file
    success_count = 0
    for mp4_file in mp4_files:
        if optimize_mp4_for_streaming(mp4_file, args.dry_run):
            success_count += 1
    
    if args.dry_run:
        print(f"\n🔍 DRY RUN: Would optimize {success_count} file(s)")
    else:
        print(f"\n✅ Successfully optimized {success_count}/{len(mp4_files)} file(s)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
