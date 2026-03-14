#!/usr/bin/env python3
"""
Backfill English soft subtitles from a source MKV folder into an existing MP4.

Usage:
    python3 backfill_subs.py /path/to/source_mkv_dir /path/to/target_mp4_dir [INPLACE=yes]

Behavior:
- Picks the largest MKV in the source folder as the source for subtitles.
- Picks the MP4 that matches the target folder name, or the only MP4 present.
- Detects the first English text subtitle stream (subrip/ass/ssa/text/webvtt).
- If no English text subs exist, attempts automatic OCR:
  - DVD (dvd_subtitle): extract VobSub (idx/sub), OCR via sub2srt + tesseract => SRT
  - Blu-ray (hdmv_pgs_subtitle): extract PGS (.sup), convert to VobSub via bdsup2sub, 
  OCR via sub2srt + tesseract => SRT
- Muxes the resulting subtitle (text stream) into the MP4 as a soft subtitle 
  (mov_text). By default, it is NOT marked default.
- Set DEFAULT=yes to mark the English subtitle track as default (players may auto-enable it).
- Outputs a new file with suffix `.en-subs.mp4` next to the original by default.
- Set INPLACE=yes to replace the original MP4 in-place (original backed up as .bak).

Requirements: ffprobe, ffmpeg, jq
Optional for OCR fallback: sub2srt, tesseract, bdsup2sub
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def require_command(cmd: str) -> None:
    """Check if a required command is available."""
    result = subprocess.run(["which", cmd], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Missing required command: {cmd}", file=sys.stderr)
        sys.exit(1)


def find_largest_mkv(source_dir: Path) -> Optional[Path]:
    """Find the largest MKV file in the source directory."""
    largest_mkv = None
    largest_size = 0

    for mkv_file in source_dir.glob("*.mkv"):
        try:
            size = mkv_file.stat().st_size
            if size > largest_size:
                largest_size = size
                largest_mkv = mkv_file
        except OSError:
            continue

    return largest_mkv


def determine_target_mp4(dst_dir: Path) -> Optional[Path]:
    """Determine the target MP4 file: prefer file matching folder name or exactly one MP4."""
    base_name = dst_dir.name
    preferred_mp4 = dst_dir / f"{base_name}.mp4"

    if preferred_mp4.exists():
        return preferred_mp4

    # If exactly one MP4 exists, use it
    mp4_files = list(dst_dir.glob("*.mp4"))
    if len(mp4_files) == 1:
        return mp4_files[0]

    return None


def probe_subtitle_streams(mkv_file: Path) -> dict:
    """Probe English subtitle streams from MKV using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language",
        "-of",
        "json",
        str(mkv_file),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error probing subtitles: {e}", file=sys.stderr)
        return {}


def get_eng_subtitle_indices(subs_json: dict) -> dict:
    """Extract English subtitle indices and codec information."""
    eng_text_idx = -1
    eng_image_idx = -1
    eng_image_codec = ""

    streams = subs_json.get("streams", [])

    # Find English text subtitle
    for i, stream in enumerate(streams):
        lang = stream.get("tags", {}).get("language", "").lower()
        codec = stream.get("codec_name", "")
        if lang.startswith("en") and codec in (
            "subrip",
            "ass",
            "ssa",
            "text",
            "webvtt",
        ):
            eng_text_idx = i

    # Find English image subtitle
    for i, stream in enumerate(streams):
        lang = stream.get("tags", {}).get("language", "").lower()
        codec = stream.get("codec_name", "")
        if lang.startswith("en") and codec not in (
            "subrip",
            "ass",
            "ssa",
            "text",
            "webvtt",
        ):
            eng_image_idx = i
            eng_image_codec = codec
            break

    return {
        "eng_text_idx": eng_text_idx,
        "eng_image_idx": eng_image_idx,
        "eng_image_codec": eng_image_codec,
    }


def get_mkvmerge_track_id(mkv_file: Path, eng_img_idx: int) -> int:
    """Get MKV track ID for English image subtitles using mkvmerge."""
    try:
        result = subprocess.run(
            ["mkvmerge", "-J", str(mkv_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        merge_json = json.loads(result.stdout)

        tracks = merge_json.get("tracks", [])
        for track in tracks:
            if (
                track.get("type") == "subtitles"
                and track.get("properties", {}).get("language", "").lower().startswith("en")
                and track.get("properties", {}).get("codec_id", "") in ("S_VOBSUB", "S_HDMV/PGS")
            ):
                return track.get("id", -1)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return -1

    return -1


def add_srt_to_mp4(
    target_mp4: Path,
    srt_file: Path,
    out_path: Path,
    default_subtitle: bool = False,
) -> None:
    """Add SRT subtitle to MP4 file."""
    tmp_out = out_path.with_suffix(".tmp.mp4")

    disp_args = ""
    if default_subtitle:
        disp_args = "-disposition:s:0 default"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(target_mp4),
        "-i",
        str(srt_file),
        "-map",
        "0",
        "-map",
        "1:0",
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        disp_args,
        "-movflags",
        "+faststart",
        str(tmp_out),
    ]

    subprocess.run(cmd, check=True)
    tmp_out.rename(out_path)

    print(f"Created: {out_path}")


def handle_text_subs(
    target_mp4: Path,
    mkv_file: Path,
    eng_text_idx: int,
    out_path: Path,
    default_subtitle: bool = False,
) -> None:
    """Handle English text subtitles by muxing them directly."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(target_mp4),
        "-i",
        str(mkv_file),
        "-map",
        "0",
        "-map",
        f"1:{eng_text_idx}",
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        "-movflags",
        "+faststart",
        str(out_path),
    ]

    if default_subtitle:
        cmd.insert(-1, "-disposition:s:0", "default")

    subprocess.run(cmd, check=True)
    print(f"Created: {out_path}")


def handle_image_subs_ocr(
    target_mp4: Path,
    mkv_file: Path,
    eng_img_idx: int,
    eng_img_codec: str,
    eng_img_tid: int,
    dst_dir: Path,
) -> None:
    """Handle image-based subtitles with OCR guidance."""
    tmp_base = dst_dir / f".backfill_ocr_{os.getpid()}"
    dst_dir.mkdir(exist_ok=True)

    print(f"Extracting image subtitles ({eng_img_codec}) for OCR...")

    if eng_img_codec == "dvd_subtitle":
        sub_ext = "sub"
        print("VobSub (DVD) subtitles detected. For best results, use a dedicated OCR tool like:")
        print("  - Subtitle Edit (GUI): https://www.nikse.dk/subtitleedit")
        print("  - vobsub2srt: brew install vobsub2srt (if available)")
        print("Extracting VobSub files for manual OCR...")

        mkvextract_check = subprocess.run(["which", "mkvextract"], capture_output=True, text=True)
        if mkvextract_check.returncode == 0:
            try:
                subprocess.run(
                    [
                        "mkvextract",
                        "tracks",
                        str(mkv_file),
                        f'{eng_img_tid}:"{tmp_base}.{sub_ext}',
                    ],
                    capture_output=True,
                    check=True,
                )
                sub_path = Path(str(tmp_base) + f".{sub_ext}")
                idx_path = Path(str(tmp_base) + ".idx")
                if sub_path.exists() and idx_path.exists():
                    print("Extracted VobSub files:")
                    print(f"  Index: {idx_path}")
                    print(f"  Subtitles: {sub_path}")
                    print(
                        "Use these files with an OCR tool to create an SRT, "
                        "then re-run this command."
                    )
                else:
                    print("Extraction of VobSub files failed.")
            except subprocess.CalledProcessError:
                print("Error extracting VobSub files.")
        else:
            print("mkvextract not available for VobSub extraction.")

    elif eng_img_codec == "hdmv_pgs_subtitle":
        print("PGS (Blu-ray) subtitles detected. For best results, use a dedicated OCR tool like:")
        print("  - Subtitle Edit (GUI): https://www.nikse.dk/subtitleedit")
        print("  - BDSup2Sub++: Manual installation required")
        print("Extracting PGS file for manual OCR...")

        mkvextract_check = subprocess.run(["which", "mkvextract"], capture_output=True, text=True)
        if mkvextract_check.returncode == 0:
            try:
                subprocess.run(
                    [
                        "mkvextract",
                        "tracks",
                        str(mkv_file),
                        f'{eng_img_tid}:"{tmp_base}.sup',
                    ],
                    capture_output=True,
                    check=True,
                )
                sup_path = Path(str(tmp_base) + ".sup")
                if sup_path.exists():
                    print(f"Extracted PGS file: {sup_path}")
                    print(
                        "Use this file with an OCR tool to create an SRT, then re-run this command."
                    )
                else:
                    print("Extraction of PGS file failed.")
            except subprocess.CalledProcessError:
                print("Error extracting PGS files.")
        else:
            print("mkvextract not available for PGS extraction.")

    else:
        print(f"English subtitle codec '{eng_img_codec}' not recognized for OCR path.")

    # Clean up temp files
    for pattern in [
        str(tmp_base) + ".idx",
        str(tmp_base) + ".sub",
        str(tmp_base) + ".srt",
        str(tmp_base) + ".sup",
    ]:
        try:
            Path(pattern).unlink()
        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Backfill English soft subtitles from a source MKV folder into an existing MP4"
    )
    parser.add_argument("src_dir", help="Path to source MKV directory")
    parser.add_argument("dst_dir", help="Path to target MP4 directory")
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Replace the original MP4 in-place (original backed up as .bak)",
    )
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    dst_dir = Path(args.dst_dir)

    if not src_dir.exists():
        print(f"No MKV files found in: {src_dir}")
        return 2

    # Find largest MKV in source dir
    largest_mkv = find_largest_mkv(src_dir)
    if not largest_mkv:
        print(f"No MKV files found in: {src_dir}")
        return 2

    print(f"Source MKV: {largest_mkv}")

    # Determine target MP4
    target_mp4 = determine_target_mp4(dst_dir)
    if not target_mp4:
        print(
            f"Could not uniquely determine target MP4. Expected: {dst_dir.name}.mp4 "
            f"or exactly one MP4 in {dst_dir}"
        )
        return 1

    print(f"Target MP4: {target_mp4}")

    # Probe subtitle streams from MKV
    subs_json = probe_subtitle_streams(largest_mkv)
    subtitle_info = get_eng_subtitle_indices(subs_json)

    # Build output path
    ext_suffix = ".en-subs.mp4"
    out_path = target_mp4.with_suffix(ext_suffix)

    print(f"Writing: {out_path}")

    # Handle English text subtitles
    if subtitle_info["eng_text_idx"] != -1:
        print(f"Using English text subtitle stream index: {subtitle_info['eng_text_idx']}")
        handle_text_subs(
            target_mp4,
            largest_mkv,
            subtitle_info["eng_text_idx"],
            out_path,
            default_subtitle=args.inplace,
        )
        if args.inplace:
            backup_path = target_mp4.with_suffix(".bak")
            print(f"In-place mode: backing up original to {backup_path} and replacing it")
            backup_path.write_bytes(target_mp4.read_bytes())
            target_mp4.write_bytes(out_path.read_bytes())
            print(
                f"Replaced original MP4 with new file containing English subs. "
                f"Backup at: {backup_path}"
            )
        return 0

    # Fallback: OCR image subtitles if present
    if subtitle_info["eng_image_idx"] == -1:
        print("No English subtitles found in MKV. Nothing to add.")
        return 2

    # Handle image-based subtitles with OCR
    handle_image_subs_ocr(
        target_mp4,
        largest_mkv,
        subtitle_info["eng_image_idx"],
        subtitle_info["eng_image_codec"],
        subtitle_info["eng_img_tid"],
        dst_dir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
