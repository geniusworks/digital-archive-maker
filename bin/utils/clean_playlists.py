#!/usr/bin/env python3
"""
Clean and normalize M3U playlists.

Converts .m3u files to .m3u8 format with proper encoding and validation.

Usage:
    python3 clean_playlists.py [root_directory]
    root_directory: Directory to scan (defaults to current directory)
"""

import argparse
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


def require_command(cmd: str) -> None:
    """Check if a required command is available."""
    result = subprocess.run(['which', cmd], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: Required command '{cmd}' not found. Please install it.", file=sys.stderr)
        sys.exit(1)


def normalize_encoding(file_path: Path) -> str:
    """Normalize file encoding to UTF-8."""
    try:
        # Try UTF-8 first
        result = subprocess.run(
            ['iconv', '-f', 'UTF-8', '-t', 'UTF-8', str(file_path)],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        try:
            # Fallback to ISO-8859-1
            result = subprocess.run(
                ['iconv', '-f', 'ISO-8859-1', '-t', 'UTF-8', str(file_path)],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            # If both fail, read as-is (might already be UTF-8)
            return file_path.read_text(encoding='utf-8', errors='replace')


def normalize_line_endings(content: str) -> str:
    """Normalize line endings to LF."""
    return content.replace('\r\n', '\n').replace('\r', '\n')


def ensure_extm3u_header(content: str) -> str:
    """Ensure #EXTM3U header is present."""
    lines = content.split('\n')
    
    # Find first non-empty line
    first_non_empty = 0
    while first_non_empty < len(lines) and not lines[first_non_empty].strip():
        first_non_empty += 1
    
    # If first non-empty line is not #EXTM3U, add it at the beginning
    if (first_non_empty >= len(lines) or 
        not lines[first_non_empty].strip().startswith('#EXTM3U')):
        lines.insert(0, '#EXTM3U')
    
    return '\n'.join(lines)


def validate_tracks(content: str, playlist_dir: Path) -> List[str]:
    """Validate that tracks referenced in playlist exist."""
    missing_files = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        track_path = playlist_dir / line
        if not track_path.exists():
            missing_files.append(line)
    
    return missing_files


def process_playlist(m3u_file: Path, mode: str = "copy") -> None:
    """Process a single M3U playlist file."""
    if not m3u_file.exists():
        return
    
    # Output path
    m3u8_file = m3u_file.with_suffix('.m3u8')
    
    print("Processing:")
    print(f"  {m3u_file}")
    print(f"  -> {m3u8_file}")
    
    # Create temporary file for processing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tmp_file:
        try:
            # Normalize encoding
            content = normalize_encoding(m3u_file)
            
            # Normalize line endings
            content = normalize_line_endings(content)
            
            # Ensure #EXTM3U header
            content = ensure_extm3u_header(content)
            
            # Write to temp file
            tmp_file.write(content)
            tmp_file.flush()
            
            # Validate tracks
            missing_files = validate_tracks(content, m3u_file.parent)
            for missing_file in missing_files:
                print(f"  ⚠ Missing file: {missing_file}")
            
            # Move temp file to final location
            tmp_path = Path(tmp_file.name)
            tmp_path.rename(m3u8_file)
            
            # Remove original if in replace mode
            if mode == "replace":
                m3u_file.unlink()
            
        except Exception as e:
            print(f"  Error processing {m3u_file}: {e}", file=sys.stderr)
            # Clean up temp file
            try:
                Path(tmp_file.name).unlink()
            except FileNotFoundError:
                pass
            raise
    
    print()


def scan_directory(root_dir: Path, mode: str = "copy") -> None:
    """Scan directory for M3U files and process them."""
    print(f"Scanning root: {root_dir}")
    print(f"Mode: {mode}")
    print()
    
    # Find all .m3u files (excluding .m3u8)
    m3u_files = list(root_dir.rglob('*.m3u'))
    m3u_files = [f for f in m3u_files if not f.name.endswith('.m3u8')]
    
    if not m3u_files:
        print("No .m3u files found.")
        return
    
    for m3u_file in m3u_files:
        process_playlist(m3u_file, mode)
        print()
    
    print("All playlists processed.")


def main():
    parser = argparse.ArgumentParser(
        description="Clean and normalize M3U playlists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Scan current directory
  %(prog)s /path/to/music           # Scan specific directory
  %(prog)s --replace /path/to/music # Replace original files
        """
    )
    parser.add_argument("root", nargs="?", default=".", 
                       help="Directory to scan (defaults to current directory)")
    parser.add_argument("--replace", action="store_true",
                       help="Replace original .m3u files instead of keeping them")
    args = parser.parse_args()
    
    # Check for required commands
    require_command('iconv')
    
    root_dir = Path(args.root)
    
    if not root_dir.exists():
        print(f"Error: {root_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not root_dir.is_dir():
        print(f"Error: {root_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    mode = "replace" if args.replace else "copy"
    scan_directory(root_dir, mode)


if __name__ == "__main__":
    main()
