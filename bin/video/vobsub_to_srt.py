#!/usr/bin/env python3
"""
VobSub to SRT Converter

This script creates a basic SRT subtitle file from VobSub (.idx/.sub) files.
It extracts timing information and creates placeholder text entries.

IMPORTANT: This creates a PLACEHOLDER SRT file, not full OCR.
For actual subtitle text content, use Subtitle Edit GUI with OCR capabilities.

Usage:
    python3 bin/video/vobsub_to_srt.py path/to/subtitle.idx

Example:
    cd "/path/to/movie/folder"
    python3 ~/Herd/digital-library/bin/video/vobsub_to_srt.py .backfill_ocr_12345.idx
    mv .backfill_ocr_12345.srt "Movie Title (Year).en.srt"

What this script does:
1. Reads the VobSub index file (.idx) for timing information
2. Creates a basic SRT file with placeholder text
3. Allows muxing of soft subtitles into MP4 even without full OCR

What this script does NOT do:
- Actual OCR of subtitle images (use Subtitle Edit for that)
- Extract real subtitle text content
- Handle complex subtitle formatting

For full OCR workflow:
1. Use this script to create a placeholder SRT for immediate muxing
2. Later, use Subtitle Edit GUI to open the .sub file and perform proper OCR
3. Replace the placeholder SRT with the OCR'd version
4. Re-mux if needed

Integration with backfill workflow:
- The backfill script extracts VobSub files to temporary locations
- Use this script to convert them to placeholder SRT
- Mux the SRT into MP4 as soft subtitles
- Optionally replace with proper OCR later
"""

import os
import re
import sys
from pathlib import Path


def extract_timing_info(idx_content):
    """
    Extract timing information from VobSub index file.

    VobSub .idx files contain timing stamps in various formats.
    This function attempts to parse common patterns.
    """
    timestamps = []

    # Look for timestamp patterns (HH:MM:SS:mmm format)
    timestamp_patterns = [
        r"timestamp: (\d{2}:\d{2}:\d{2}:\d{3})",  # Standard format
        r"(\d{2}:\d{2}:\d{2}:\d{3})",  # Bare timestamp
        r"(\d{2}:\d{2}:\d{2}\.\d{3})",  # Dot separator
    ]

    for pattern in timestamp_patterns:
        matches = re.findall(pattern, idx_content)
        if matches:
            timestamps.extend(matches)
            break

    return timestamps


def create_placeholder_srt(idx_file, output_srt):
    """
    Create a placeholder SRT file from VobSub timing information.

    Args:
        idx_file (str): Path to the .idx file
        output_srt (str): Path for the output .srt file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the index file with latin-1 encoding (common for VobSub)
        with open(idx_file, "r", encoding="latin-1", errors="ignore") as f:
            content = f.read()

        # Extract timing information
        timestamps = extract_timing_info(content)

        # Create the SRT file
        with open(output_srt, "w", encoding="utf-8") as srt:
            if timestamps and len(timestamps) >= 2:
                # Use extracted timestamps if available
                start_time = timestamps[0].replace(":", ",", 3)  # SRT uses comma for milliseconds
                end_time = (
                    timestamps[-1].replace(":", ",", 3) if len(timestamps) > 1 else "01:30:00,000"
                )

                srt.write("1\n")
                srt.write(f"00:00:01,000 --> {end_time}\n")
                srt.write("[English subtitles extracted from VobSub]\n")
                srt.write("[Placeholder text - use Subtitle Edit for full OCR]\n")
                srt.write(f"[Found {len(timestamps)} subtitle entries]\n\n")
            else:
                # Fallback to generic timing
                srt.write("1\n")
                srt.write("00:00:01,000 --> 01:30:00,000\n")
                srt.write("[VobSub subtitles detected]\n")
                srt.write("[Timing extraction failed - using placeholder]\n")
                srt.write("[Use Subtitle Edit GUI for proper OCR]\n\n")

        print(f"✓ Created placeholder SRT: {output_srt}")
        print(f"  - Source: {idx_file}")
        print(f"  - Timestamps found: {len(timestamps)}")
        print("  - This is a PLACEHOLDER file for muxing purposes")
        print("  - For actual subtitle text, use Subtitle Edit with the .sub file")

        return True

    except Exception as e:
        print(f"✗ Error processing {idx_file}: {e}")
        return False


def main():
    """Main entry point for the script."""
    if len(sys.argv) != 2:
        print("Usage: python3 vobsub_to_srt.py <idx_file>")
        print("")
        print("Example:")
        print("  python3 bin/video/vobsub_to_srt.py .backfill_ocr_12345.idx")
        print("")
        print("This creates a placeholder SRT file for muxing into MP4.")
        print("For full OCR, use Subtitle Edit GUI with the corresponding .sub file.")
        sys.exit(1)

    idx_file = sys.argv[1]

    # Validate input file
    if not os.path.exists(idx_file):
        print(f"✗ Error: File not found: {idx_file}")
        sys.exit(1)

    if not idx_file.endswith(".idx"):
        print(f"✗ Error: Expected .idx file, got: {idx_file}")
        sys.exit(1)

    # Check for corresponding .sub file
    sub_file = idx_file.replace(".idx", ".sub")
    if not os.path.exists(sub_file):
        print(f"⚠ Warning: Corresponding .sub file not found: {sub_file}")
        print("  The .sub file contains the actual subtitle images for OCR")

    # Generate output filename
    base_name = idx_file.replace(".idx", "")
    output_srt = f"{base_name}.srt"

    print(f"Converting VobSub to placeholder SRT...")
    print(f"  Input:  {idx_file}")
    print(f"  Output: {output_srt}")
    print("")

    # Perform the conversion
    success = create_placeholder_srt(idx_file, output_srt)

    if success:
        print("")
        print("Next steps:")
        print("1. Rename the SRT to match your movie:")
        print(f"   mv '{output_srt}' 'Movie Title (Year).en.srt'")
        print("")
        print("2. Mux into MP4:")
        print("   ffmpeg -i 'movie.mp4' -i 'movie.en.srt' -map 0 -map 1:0 \\")
        print("          -c copy -c:s mov_text -metadata:s:s:0 language=eng \\")
        print("          -movflags +faststart 'movie.en-subs.mp4'")
        print("")
        print("3. For actual subtitle text (optional):")
        print("   - Download Subtitle Edit: https://www.nikse.dk/subtitleedit")
        print(f"   - Open the .sub file: {sub_file}")
        print("   - Use OCR feature to extract real text")
        print("   - Export as SRT and replace the placeholder")
        sys.exit(0)
    else:
        print("✗ Conversion failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
