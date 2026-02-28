#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import signal
from datetime import datetime
from pathlib import Path

# Import authoritative language code mapping
try:
    from language_codes import normalize_language_code, get_all_variants, matches_language
except ImportError:
    # Fallback if language_codes.py not available
    def normalize_language_code(lang_code: str) -> str:
        return lang_code.lower() if lang_code else 'und'
    
    def get_all_variants(lang_code: str) -> list[str]:
        return [lang_code] if lang_code else []
    
    def matches_language(code1: str, code2: str) -> bool:
        return code1.lower() == code2.lower() if code1 and code2 else False

# Load language preferences from environment
LANG_AUDIO = normalize_language_code(os.getenv('LANG_AUDIO', 'en'))
LANG_SUBTITLES = normalize_language_code(os.getenv('LANG_SUBTITLES', 'en'))

# Global flag for graceful cancellation
CANCELLED = False

def signal_handler(signum, frame):
    global CANCELLED
    if not CANCELLED:
        print("\n⚠️  Interrupt received (Ctrl+C)")
        print("   → Gracefully cancelling...")
        CANCELLED = True
    else:
        print("\n❌ Force exit")
        sys.exit(1)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def check_virtual_environment() -> None:
    """Check if we're running in the virtual environment and exit gracefully if not."""
    # Check if VIRTUAL_ENV environment variable is set
    if not os.getenv("VIRTUAL_ENV"):
        print("❌ Virtual environment not detected!")
        print()
        print("🔧 To activate the virtual environment, run:")
        print("   source venv/bin/activate")
        print()

        # Check if this was called from make and show the appropriate retry
        # command
        if os.getenv("TITLE") and os.getenv("YEAR"):
            # This was called from make rip-movie
            cmd_type = os.getenv("TYPE", "auto")
            print("Then try again:")
            print(
                f"   make rip-movie TYPE={cmd_type} TITLE=\"{os.getenv('TITLE')}\" YEAR={os.getenv('YEAR')}")
        else:
            # Direct script call
            print("Then try again:")
            print(f"   {' '.join(sys.argv)}")

        sys.exit(1)


def configure_makemkv() -> None:
    """Ensure MakeMKV is configured to extract all tracks including subtitles."""
    makemkv_dir = Path.home() / ".MakeMKV"
    makemkv_dir.mkdir(parents=True, exist_ok=True)
    settings_file = makemkv_dir / "settings.conf"

    # Select all tracks, but deselect the lossy core of HD audio formats
    desired_setting = 'app_DefaultSelectionString="+sel:all,-sel:(core)"'

    try:
        if settings_file.exists():
            content = settings_file.read_text()
            if "app_DefaultSelectionString" not in content:
                settings_file.write_text(
                    content.rstrip() + f"\n{desired_setting}\n")
                print("  ✓ Configured MakeMKV to extract all subtitles")
        else:
            settings_file.write_text(f"{desired_setting}\n")
            print("  ✓ Created MakeMKV configuration for subtitle extraction")
    except Exception as e:
        print(f"  ⚠ Could not configure MakeMKV settings: {e}")


def _run(cmd: list[str], *, check: bool = True,
         capture: bool = True) -> subprocess.CompletedProcess:
    kwargs = {}
    if capture:
        kwargs.update({"capture_output": True, "text": True})
    
    # Check for cancellation before running
    global CANCELLED
    if CANCELLED:
        raise KeyboardInterrupt("Operation cancelled by user")
    
    return subprocess.run(cmd, check=check, **kwargs)


def require_command(cmd: str) -> None:
    res = _run(["which", cmd], check=False)
    if res.returncode != 0:
        raise RuntimeError(f"Missing required command: {cmd}")


def load_dotenv(repo_root: Path) -> None:
    env_path = repo_root / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "python-dotenv is required to load .env. Install deps with: python3 -m pip install -r requirements.txt"
        ) from e

    load_dotenv(env_path)


def get_env_str(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    return val


def sanitize_title(raw: str) -> str:
    # Preserve acronyms, title-case words, lowercase small stop-words except
    # first/last.
    stop = {"a", "an", "and", "as", "at", "but", "by", "for", "in",
            "nor", "of", "on", "or", "per", "the", "to", "vs", "via"}

    def cap(word: str) -> str:
        return word[:1].upper() + word[1:].lower() if word else word

    raw = re.sub(r"[\t:/]", " ", raw)
    raw = re.sub(r"[\\?*\"<>|]", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    parts = raw.split(" ")
    out: list[str] = []
    for i, w in enumerate(parts):
        if len(w) > 1 and w.isupper():
            out.append(w)
            continue

        subparts = w.split("-")
        built: list[str] = []
        for sp in subparts:
            low = sp.lower()
            if i > 0 and i < len(parts) - 1 and low in stop:
                built.append(low)
            else:
                built.append(cap(low))
        out.append("-".join(built))

    return " ".join(out)


def sanitize_year(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) >= 4:
        return digits[:4]
    return raw


def detect_disc_type() -> str:
    # Prefer drutil on macOS.
    try:
        res = _run(["drutil", "status"], check=False)
        if res.returncode == 0:
            m = re.search(r"^\s*Type:\s*(.+)$", res.stdout, re.MULTILINE)
            if m:
                t = m.group(1).lower()
                if "dvd" in t:
                    return "dvd"
                if "bd" in t or "blu" in t:
                    return "bluray"
    except FileNotFoundError:
        pass

    # Fallback to makemkvcon info.
    res = _run(["makemkvcon", "-r", "--cache=1",
               "info", "disc:0"], check=False)
    out = res.stdout or ""
    if re.search(r"\bBlu-?ray\b", out, re.IGNORECASE):
        return "bluray"
    if re.search(r"\bDVD\b", out, re.IGNORECASE):
        return "dvd"

    return "auto"  # No disc detected


def parse_disc_stream_info(info_output: str) -> tuple[list, list]:
    """Parse MakeMKV disc info to extract audio and subtitle stream info"""
    audio_streams = []
    subtitle_streams = []
    streams = {}
    
    lines = info_output.split('\n')
    
    for line in lines:
        if not line.startswith('SINFO:'):
            continue
            
        parts = line.split(',', 4)
        if len(parts) < 5:
            continue
            
        try:
            title_id = parts[0].split(':')[1]
            stream_id = parts[1]
            attr_id = parts[2]
            value = parts[4].strip('"').strip()
        except:
            continue
            
        key = (title_id, stream_id)
        if key not in streams:
            streams[key] = {'title': title_id, 'track': stream_id, 'type': 'unknown', 'language': 'und', 'codec': 'unknown'}
            
        if attr_id == '1':
            streams[key]['type'] = parts[3]
        elif attr_id == '3':
            # Language code is usually 3 chars
            streams[key]['language'] = value[:3] if len(value) >= 3 else value
        elif attr_id == '5':
            # Standardize codec names
            codec = value.lower()
            if 'pgs' in codec:
                streams[key]['codec'] = 'hdmv_pgs_subtitle'
            elif 'ac3' in codec:
                streams[key]['codec'] = 'ac3'
            elif 'dts' in codec:
                streams[key]['codec'] = 'dts'
            elif 'subrip' in codec or 'srt' in codec:
                streams[key]['codec'] = 'subrip'
            else:
                streams[key]['codec'] = codec
    
    for key, stream in sorted(streams.items(), key=lambda x: (int(x[0][0]), int(x[0][1]))):
        if stream['type'] == '6202':
            audio_streams.append(stream)
        elif stream['type'] == '6203':
            subtitle_streams.append(stream)
    
    return audio_streams, subtitle_streams


def interactive_subtitle_prompt(audio_streams: list, subtitle_streams: list, 
                               source_name: str = "MKV File", main_title_id: str = None) -> dict:
    """Interactive prompt for subtitle processing
    
    Args:
        audio_streams: List of audio stream dictionaries
        subtitle_streams: List of subtitle stream dictionaries  
        source_name: Name of the source (e.g., "Disc Analysis", "MKV File")
        main_title_id: If provided, filter streams for this title (disc mode)
    """
    import sys
    
    # Filter streams for main title if in disc mode
    if main_title_id:
        main_audio = [s for s in audio_streams if s.get('title') == main_title_id]
        main_subs = [s for s in subtitle_streams if s.get('title') == main_title_id]
    else:
        main_audio = audio_streams
        main_subs = subtitle_streams
    
    # Analyze content
    has_preferred_audio = any(matches_language(s.get('language', ''), LANG_AUDIO) for s in main_audio)
    has_foreign_audio = any(not matches_language(s.get('language', ''), LANG_AUDIO) for s in main_audio)
    preferred_text_subs = any(s.get('codec') in ['subrip', 'webvtt', 'ass', 'ssa'] 
                       and matches_language(s.get('language', ''), LANG_SUBTITLES)
                       for s in main_subs)
    preferred_pgs_subs = any(s.get('codec') in ['hdmv_pgs_subtitle', 's_vobsub']
                      and matches_language(s.get('language', ''), LANG_SUBTITLES)
                      for s in main_subs)
    
    # Determine default action (most useful option)
    default_action = "standard_mp4"
    if not has_preferred_audio and has_foreign_audio:
        if preferred_text_subs:
            default_action = "burn_subs"
        elif preferred_pgs_subs:
            default_action = "burn_pgs_subs"
    elif has_preferred_audio and preferred_text_subs:
        # Preferred audio + soft subs → extract SRT (preferred)
        default_action = "extract_srt"
    elif has_preferred_audio and preferred_pgs_subs and not preferred_text_subs:
        # Preferred audio + PGS subs (no soft subs) → extract PGS for OCR
        default_action = "extract_pgs_ocr"
    
    print(f"\n🎬 {source_name}\n")
    print("=" * 50 + "\n")
    
    # Audio analysis
    print(f"🎵 Audio Tracks: {len(main_audio)}")
    
    # Find the best audio track (most channels among preferred language)
    preferred_audio_tracks = [s for i, s in enumerate(main_audio) 
                             if matches_language(s.get('language', ''), LANG_AUDIO)]
    
    if preferred_audio_tracks:
        best_audio_track = max(preferred_audio_tracks, key=lambda s: s.get('channels', 0))
        best_audio_index = main_audio.index(best_audio_track)
    else:
        best_audio_index = 0
        best_audio_track = main_audio[0] if main_audio else None
    
    for i, stream in enumerate(main_audio):
        lang = stream.get('language', 'und')
        codec = stream.get('codec', 'unknown')
        marker = " 👉" if i == best_audio_index else "   "
        
        # Show channel count if available
        channels = stream.get('channels', '')
        if channels:
            track_info = f"{lang.upper()} ({codec}, {channels}ch)"
        else:
            track_info = f"{lang.upper()} ({codec})"
        
        # Add note for the selected track
        if i == best_audio_index and len(main_audio) > 1:
            track_info += " ← SELECTED"
        
        print(f"{marker} Track {i}: {track_info}")
    
    print(f"\n📝 Subtitle Tracks: {len(main_subs)}")
    
    # Find the best subtitle track (text preferred over image, first matching)
    preferred_sub_tracks = [s for i, s in enumerate(main_subs) 
                          if matches_language(s.get('language', ''), LANG_SUBTITLES)]
    
    if preferred_sub_tracks:
        # Prefer text subtitles over image subtitles
        text_codecs = ['subrip', 'ass', 'ssa', 'text', 'webvtt']
        text_subs = [s for s in preferred_sub_tracks if s.get('codec') in text_codecs]
        
        if text_subs:
            # Use first text subtitle
            best_sub_track = text_subs[0]
        else:
            # Use first image subtitle
            best_sub_track = preferred_sub_tracks[0]
        
        best_sub_index = main_subs.index(best_sub_track)
    else:
        best_sub_index = -1
        best_sub_track = None
    
    for i, stream in enumerate(main_subs):
        lang = stream.get('language', 'und')
        codec = stream.get('codec', 'unknown')
        marker = " 👉" if i == best_sub_index else "   "
        
        track_info = f"{lang.upper()} ({codec})"
        
        # Add note for the selected track
        if i == best_sub_index and len(main_subs) > 1:
            track_info += " ← SELECTED"
        
        print(f"{marker} Track {i}: {track_info}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Present options based on what's available (preferred first)
    available_actions = []
    
    # Text subtitles (preferred - soft, toggleable)
    if preferred_text_subs:
        available_actions.append(("extract_srt", "MP4 + Create .srt file"))
        if has_foreign_audio:
            available_actions.append(("burn_subs", "MP4 + Burn text subtitles"))
    
    # PGS subtitles (image-based, good for OCR extraction)
    if preferred_pgs_subs:
        available_actions.append(("extract_pgs_ocr", "MP4 + Convert image subtitles"))
        if has_foreign_audio:
            available_actions.append(("burn_pgs_subs", "MP4 + Burn image subtitles"))
    
    # Always available as fallback
    available_actions.append(("standard_mp4", "MP4 (no subtitles)"))
    
    options = []
    for i, (action, description) in enumerate(available_actions, 1):
        options.append((str(i), action, description))
    
    print("Available Options:\n")
    for key, action, description in options:
        marker = " 👉" if action == default_action else "   "
        print(f"{marker} {key}) {description}")
    
    print(f"\nPress 1-{len(options)} to select (default: {next(k for k,a,_ in options if a==default_action)})")
    print()  # Empty line for countdown
    
    # Non-blocking countdown with keypress detection
    import select
    import termios
    import tty
    
    timeout_seconds = 31
    choice = None
    default_key = next(k for k, a, _ in options if a == default_action)
    
    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin.fileno())
    try:
        # Set raw mode for non-blocking input
        tty.setraw(sys.stdin.fileno())
        
        # Countdown loop
        for remaining in range(timeout_seconds, 0, -1):
            sys.stdout.write(f"\rContinuing with default in {remaining}s...")
            sys.stdout.flush()
            
            # Check for keypress (non-blocking)
            if sys.stdin.isatty():
                try:
                    dr, dw, de = select.select([sys.stdin], [], [], 1)
                    if dr:
                        key = sys.stdin.read(1)
                        if key in [opt[0] for opt in options]:
                            choice = key
                            # Clear the countdown line and reset cursor position
                            sys.stdout.write("\r" + " " * 50 + "\r")
                            sys.stdout.flush()
                            print(f"Selected option {choice}")
                            # Ensure cursor is at start of line for next output
                            sys.stdout.write("\r")
                            sys.stdout.flush()
                            break
                except KeyboardInterrupt:
                    print("\nOperation cancelled.")
                    sys.exit(0)
            
            # Check if we already have a choice
            if choice:
                break
        
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
    
    if not choice:
        print(f"\rUsing default option {default_key}...          \n")
        choice = default_key
    
    # Convert choice to action
    selected_action = next(opt[1] for opt in options if opt[0] == choice)
    
    return {
        'action': selected_action,
        'has_foreign_audio': has_foreign_audio,
        'preferred_text_subs': preferred_text_subs,
        'preferred_pgs_subs': preferred_pgs_subs,
        'subtitle_streams': main_subs
    }


def analyze_mkv_streams(mkv_path: Path) -> tuple[list, list]:
    """Analyze MKV file and return audio and subtitle stream information"""
    try:
        # Get audio streams
        audio_res = _run([
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=index,codec_name:stream_tags=language",
            "-of", "csv=p=0", str(mkv_path)
        ], capture=True)
        
        audio_streams = []
        for line in audio_res.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 3:
                    audio_streams.append({
                        'index': parts[0],
                        'codec': parts[1],
                        'language': parts[2] if parts[2] else 'und'
                    })
        
        # Get subtitle streams
        sub_res = _run([
            "ffprobe", "-v", "error", "-select_streams", "s",
            "-show_entries", "stream=index,codec_name:stream_tags=language",
            "-of", "csv=p=0", str(mkv_path)
        ], capture=True)
        
        subtitle_streams = []
        for line in sub_res.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 3:
                    subtitle_streams.append({
                        'index': parts[0],
                        'codec': parts[1],
                        'language': parts[2] if parts[2] else 'und'
                    })
        
        return audio_streams, subtitle_streams
        
    except Exception as e:
        print(f"  ⚠️  Error analyzing streams: {e}")
        return [], []


def extract_pgs_subtitles(mkv_path: Path, output_dir: Path) -> list[Path]:
    """Extract English PGS subtitles to .sup files for later OCR processing"""
    extracted_files = []
    
    try:
        sub_res = _run([
            "ffprobe", "-v", "error", "-select_streams", "s",
            "-show_entries", "stream=index,codec_name:stream_tags=language",
            "-of", "csv=p=0", str(mkv_path)
        ], capture=True)
        
        pgs_streams = []
        for line in sub_res.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 3 and 'pgs' in parts[1].lower():
                    pgs_streams.append({
                        'index': parts[0],
                        'codec': parts[1],
                        'language': parts[2] if parts[2] else 'und'
                    })
        
        for stream in pgs_streams:
            if matches_language(stream['language'], LANG_AUDIO):
                sup_path = output_dir / f"{mkv_path.stem}.en.sup"
                print(f"  → Extracting English PGS subtitles to {sup_path.name}")
                
                extract_cmd = [
                    "ffmpeg", "-i", str(mkv_path),
                    "-map", f"0:{stream['index']}",
                    "-c", "copy", str(sup_path), "-y"
                ]
                _run(extract_cmd)
                extracted_files.append(sup_path)
                print(f"  ✓ PGS extracted: {sup_path.name}")
                
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Could not extract PGS subtitles: {e}")
    
    return extracted_files


def extract_subtitles_to_srt(mkv_path: Path, output_dir: Path) -> list[Path]:
    """Extract English subtitles from MKV to SRT files for Jellyfin compatibility"""
    srt_files = []

    try:
        # Get subtitle streams info
        res = _run([
            "ffprobe", "-v", "error", "-select_streams", "s",
            "-show_entries", "stream=index,codec_name:stream_tags=language",
            "-of", "csv=p=0", str(mkv_path)
        ], capture=True)

        subtitle_streams = res.stdout.strip().split('\n') if res.stdout else []

        for stream_info in subtitle_streams:
            if not stream_info.strip():
                continue

            parts = stream_info.split(',')
            if len(parts) < 2:
                continue

            stream_index = parts[0]
            # codec = parts[1]  # Unused variable
            lang = parts[2] if len(parts) > 2 else "und"

            # Extract English subtitles
            if matches_language(lang, LANG_SUBTITLES):
                srt_path = output_dir / f"{mkv_path.stem}.en.srt"

                print(f"  → Extracting English subtitles to {srt_path.name}")

                # Extract subtitle to SRT
                extract_cmd = [
                    "ffmpeg", "-i", str(mkv_path),
                    "-map", f"0:{stream_index}",
                    "-c:s", "srt",
                    str(srt_path),
                    "-y"
                ]

                _run(extract_cmd)
                srt_files.append(srt_path)
                print(f"  ✓ Subtitle extracted: {srt_path.name}")

    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Could not extract subtitles: {e}")

    return srt_files


def ffprobe_streams(path: Path, selector: str) -> list[dict]:
    res = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            selector,
            "-show_entries",
            "stream=index,codec_name,disposition:stream_tags=language",
            "-of",
            "json",
            str(path),
        ],
        check=False,
    )
    if res.returncode != 0:
        return []
    try:
        j = json.loads(res.stdout)
    except json.JSONDecodeError:
        return []
    return j.get("streams") or []


def pick_default_audio_lang(audio_streams: list[dict]) -> str:
    if not audio_streams:
        return ""

    # First, look for a track marked as default
    for s in audio_streams:
        disp = s.get("disposition") or {}
        if disp.get("default") == 1:
            lang = ((s.get("tags") or {}).get("language") or "").lower()
            if lang:
                return lang

    # If no default track, prefer English tracks
    for s in audio_streams:
        lang = ((s.get("tags") or {}).get("language") or "").lower()
        if matches_language(lang, LANG_AUDIO):
            return lang

    # Fall back to first track
    return ((audio_streams[0].get("tags") or {}).get("language") or "").lower()


def has_lang(streams: list[dict], prefix: str) -> bool:
    for s in streams:
        lang = ((s.get("tags") or {}).get("language") or "").lower()
        if lang.startswith(prefix):
            return True
    return False


def first_eng_text_sub_index(subs: list[dict]) -> int:
    text_codecs = {"subrip", "ass", "ssa", "text", "webvtt"}
    for s in subs:
        lang = ((s.get("tags") or {}).get("language") or "").lower()
        codec = (s.get("codec_name") or "").lower()
        if matches_language(lang, LANG_SUBTITLES) and codec in text_codecs:
            return int(s.get("index", -1))
    return -1


def first_eng_image_sub_index(subs: list[dict]) -> tuple[int, str]:
    text_codecs = {"subrip", "ass", "ssa", "text", "webvtt"}
    for s in subs:
        lang = ((s.get("tags") or {}).get("language") or "").lower()
        codec = (s.get("codec_name") or "").lower()
        if matches_language(lang, LANG_SUBTITLES) and codec not in text_codecs:
            return int(s.get("index", -1)), codec
    return -1, ""


def hb_track_for_sub_stream(subs: list[dict], stream_index: int) -> int:
    if stream_index < 0:
        return -1
    indices = [int(s.get("index", -1)) for s in subs]
    try:
        pos = indices.index(stream_index)
    except ValueError:
        return -1
    return pos + 1


def mux_text_sub_into_mp4(mp4_path: Path, src_mkv: Path,
                          sub_stream_index: int, mark_default: bool) -> None:
    tmp_out = mp4_path.with_suffix(".tmp.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_path),
        "-i",
        str(src_mkv),
        "-map",
        "0",
        "-map",
        f"1:{sub_stream_index}",
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
    ]
    if mark_default:
        cmd += ["-disposition:s:0", "default"]
    cmd += ["-movflags", "+faststart", str(tmp_out)]

    _run(cmd)
    tmp_out.replace(mp4_path)


def eject_disc() -> None:
    """Eject the disc from the drive."""
    try:
        # Try drutil first (macOS standard)
        _run(["drutil", "eject"], check=False, capture=False)
        print("Disc ejected")
    except Exception:
        # Fallback to diskutil if drutil fails
        try:
            # Find optical disc devices
            res = _run(["diskutil", "list"], capture=True)
            lines = res.stdout.split('\n')
            for line in lines:
                if 'DVD' in line or 'CD' in line or 'BD' in line:
                    # Extract device identifier
                    parts = line.strip().split()
                    if parts and parts[-1].startswith('/dev/'):
                        device = parts[-1]
                        _run(["diskutil", "eject", device],
                             check=False, capture=False)
                        print(f"Disc ejected from {device}")
                        return
            print("No optical disc found to eject")
        except Exception:
            print("Could not eject disc")


def main() -> int:
    # Check virtual environment first
    check_virtual_environment()

    # Configure MakeMKV to extract subtitles
    configure_makemkv()

    parser = argparse.ArgumentParser(
        description="Rip DVD/Blu-ray discs to your LIBRARY_ROOT using MakeMKV + HandBrake")
    parser.add_argument("type", nargs="?", default="auto",
                        choices=["dvd", "bluray", "auto"])
    parser.add_argument("--force-all-tracks", action="store_true",
                        help="Encode all tracks instead of just the main feature (largest file)")
    parser.add_argument("--title-index", type=int, default=0,
                        help="Select title by size ranking (0=largest, 1=2nd largest, etc.)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root)

    # Defaults
    library_root = Path(get_env_str(
        "LIBRARY_ROOT", "/Volumes/Data/Media/Library") or "/Volumes/Data/Media/Library")
    minlength = int(get_env_str("MINLENGTH", "120") or "120")

    # Encoding settings (faster defaults)
    # Higher number = lower quality but faster
    quality = get_env_str("HB_QUALITY", "28") or "28"
    # Encoding speed preset
    preset = get_env_str(
        "HB_PRESET", "Apple 1080p30 Surround") or "Apple 1080p30 Surround"
    tune = get_env_str("HB_TUNE", None)  # Optional tuning

    # Track selection settings
    force_all_tracks = args.force_all_tracks or get_env_str(
        "FORCE_ALL_TRACKS", "false").lower() in ("true", "1", "yes")

    # Streaming optimization settings
    streaming_optimize = get_env_str(
        "STREAMING_OPTIMIZE", "true").lower() in ("true", "1", "yes")

    # Environment-provided optional metadata
    title_raw = get_env_str("TITLE", None)
    year_raw = get_env_str("YEAR", None)
    dest_category = get_env_str("DEST_CATEGORY", "Movies") or "Movies"
    policy = (get_env_str("AUDIO_SUBS_POLICY", "keep") or "keep").strip()

    require_command("makemkvcon")
    require_command("HandBrakeCLI")
    require_command("ffprobe")
    require_command("ffmpeg")

    disc_type = args.type
    if disc_type == "auto":
        disc_type = detect_disc_type()

    disc_dir = "DVDs" if disc_type == "dvd" else "Blurays"

    safe_title = sanitize_title(title_raw) if title_raw else ""
    safe_year = sanitize_year(year_raw) if year_raw else ""

    if safe_title:
        if safe_year:
            outdir = library_root / disc_dir / f"{safe_title} ({safe_year})"
        else:
            outdir = library_root / disc_dir / safe_title
    else:
        stamp = datetime.now().strftime("%Y-%m-%d")
        outdir = library_root / disc_dir / stamp

    # Check if MKV files already exist in source folder only
    # MKV files should NEVER be in Movies folder - only in Blurays/DVDs folders
    source_mkvs = sorted(outdir.glob("*.mkv")) if outdir.exists() else []

    # Check destination folder for existing MP4 files (not MKV!)
    dest_mp4s = []
    if safe_title and safe_year:
        dest_dir = library_root / dest_category / f"{safe_title} ({safe_year})"
        if dest_dir.exists():
            dest_mp4s = sorted(dest_dir.glob("*.mp4"))

    mkvs = source_mkvs  # Only use source MKV files

    # If we have destination MP4 files, check if we're already done
    if dest_mp4s and not source_mkvs:
        # We have final MP4 files but no source MKV files
        largest_dest = max(dest_mp4s, key=lambda p: p.stat().st_size)
        dest_size_gb = largest_dest.stat().st_size / (1024**3)
        if dest_size_gb < 10:  # Already compressed
            print(
                f"  ✓ Already processed: {largest_dest.name} ({dest_size_gb:.1f}GB)")
            return

    if not mkvs:
        # Only rip if no MKV files exist
        print("No MKV files found, ripping from disc...")

        # Check if disc is actually present using existing detection
        detected_type = detect_disc_type()
        if detected_type == "auto":
            print("  ❌ No Blu-ray/DVD disc found in drive")
            print("  💡 Please insert a disc and try again")
            return 1

        print(f"  ✓ Detected {detected_type.upper()} disc")
        # Probe disc access early (best-effort)
        _run(["makemkvcon", "-r", "--cache=1", "info", "disc:0"], check=False)

    # NOW create the output directory (only after we know we have a disc or
    # files)
    outdir.mkdir(parents=True, exist_ok=True)

    if not mkvs:
        # Smart ripping: main feature only vs all tracks
        if not force_all_tracks:
            print("Scanning for main feature...")
            print("  → Primary: Longest duration")
            print("  → Secondary: Largest file size if durations similar (±1 min)")
            try:
                # Get disc info to find all titles
                info_res = _run(["makemkvcon", "-r", "--cache=1",
                                "info", "disc:0"], capture=True)

                # Parse titles from MakeMKV info output
                # Look for lines like: TINFO:0,9,0,"2:09:20" (duration is field
                # 9)
                titles = []
                lines = info_res.stdout.split('\n')
                for line in lines:
                    # Look for duration info (field 9)
                    if line.startswith('TINFO:') and ',9,' in line:
                        parts = line.split(',')
                        if len(parts) >= 4:
                            title_id = parts[0].split(':')[1]
                            duration = parts[3].strip(
                                '"')  # Format: "HH:MM:SS"
                            try:
                                # Convert duration to seconds for comparison
                                h, m, s = map(int, duration.split(':'))
                                total_seconds = h * 3600 + m * 60 + s
                                if total_seconds >= minlength:  # Only consider titles longer than minlength
                                    titles.append(
                                        (int(title_id), total_seconds, duration))
                            except ValueError:
                                continue

                if titles:
                    # Sort by duration (longest first) and pick the main
                    # feature
                    titles.sort(key=lambda x: x[1], reverse=True)

                    # If multiple titles have same duration (within 1 minute),
                    # pick the larger one
                    if len(titles) > 1:
                        longest_duration = titles[0][1]
                        same_duration_titles = [t for t in titles if abs(
                            t[1] - longest_duration) <= 60]

                        if len(same_duration_titles) > 1:
                            print(
                                f"Found {len(same_duration_titles)} titles with similar duration, checking sizes...")
                            # Get file sizes for titles with same duration
                            title_sizes = []
                            for title_id, _, _ in same_duration_titles:
                                size_line = next((line for line in info_res.stdout.split('\n')
                                                 if f"TINFO:{title_id},10," in line), None)
                                if size_line:
                                    size_str = size_line.split(
                                        ',')[3].strip('"')
                                    # Parse size string like "19.0 GB" or "23.8
                                    # GB"
                                    if 'GB' in size_str:
                                        size_gb = float(
                                            size_str.replace(' GB', ''))
                                        title_sizes.append((title_id, size_gb))

                            if title_sizes:
                                # Sort by size (largest first) and pick by index
                                title_sizes.sort(
                                    key=lambda x: x[1], reverse=True)
                                
                                # Validate title_index is within range
                                if args.title_index >= len(title_sizes):
                                    print(f"❌ Title index {args.title_index} out of range (only {len(title_sizes)} titles available)")
                                    print(f"  → Available titles: 0-{len(title_sizes)-1}")
                                    return 1
                                
                                main_title_id = title_sizes[args.title_index][0]
                                main_duration = next(
                                    t[1] for t in titles if t[0] == main_title_id)
                                main_duration_str = next(
                                    t[2] for t in titles if t[0] == main_title_id)
                                
                                size_desc = "largest" if args.title_index == 0 else f"{args.title_index + 1}{'st' if args.title_index == 1 else 'nd' if args.title_index == 2 else 'rd' if args.title_index == 3 else 'th'} largest"
                                print(
                                    f"Selected {size_desc} title: {main_title_id} ({title_sizes[args.title_index][1]} GB)")
                            else:
                                main_title_id, main_duration, main_duration_str = titles[0]
                        else:
                            main_title_id, main_duration, main_duration_str = titles[0]
                    else:
                        main_title_id, main_duration, main_duration_str = titles[0]

                    print(
                        f"Found main feature: Title {main_title_id} ({main_duration_str})")
                    print(f"Skipping {len(titles) - 1} shorter tracks")

                    # Show interactive prompt BEFORE ripping starts
                    # First, get full disc info to analyze streams
                    info_res = _run(["makemkvcon", "-r", "--cache=1",
                                    "info", "disc:0"], capture=True)
                    audio_streams, subtitle_streams = parse_disc_stream_info(info_res.stdout)
                    
                    # Check if we can skip the prompt for simple English content
                    main_audio = [s for s in audio_streams if s.get('title') == str(main_title_id)]
                    main_subs = [s for s in subtitle_streams if s.get('title') == str(main_title_id)]
                    
                    all_preferred_audio = all(matches_language(s.get('language', ''), LANG_AUDIO) for s in main_audio)
                    preferred_soft_subs = any(s.get('codec') in ['subrip', 'webvtt', 'ass', 'ssa'] 
                                       and matches_language(s.get('language', ''), LANG_SUBTITLES)
                                       for s in main_subs)
                    
                    if all_preferred_audio and preferred_soft_subs:
                        # Simple case - skip prompt, just proceed with extraction
                        print(f"\n🎬 Detected: English movie with English audio and soft subtitles")
                        print(f"  → Will automatically extract English soft subtitles to .srt file")
                        subtitle_config = {'action': 'extract_srt', 'preferred_text_subs': True}
                        pre_rip_choice = True
                    else:
                        # Show interactive prompt
                        subtitle_config = interactive_subtitle_prompt(
                            audio_streams, subtitle_streams, 
                            source_name="Disc Analysis (Main Feature)", 
                            main_title_id=str(main_title_id)
                        )
                        pre_rip_choice = True
                    
                    print("=" * 50 + "\n")

                    # Rip only the main feature
                    try:
                        # For DVDs, try backup first if direct rip fails
                        cmd = ["makemkvcon", "mkv", "disc:0",
                               str(main_title_id), str(outdir)]
                        print(f"  → Running: {' '.join(cmd)}")
                        result = _run(cmd, capture=True)
                        print(f"  ✓ MakeMKV output: {result.stdout.strip()}")
                        if result.stderr:
                            print(
                                f"  ⚠ MakeMKV stderr: {result.stderr.strip()}")
                    except KeyboardInterrupt:
                        print(f"\n❌ Rip cancelled by user")
                        print(f"   → Cleaning up partial files...")
                        # Clean up any partial files
                        for partial_file in outdir.glob(f"*t{main_title_id:02d}*"):
                            try:
                                partial_file.unlink()
                                print(f"   → Removed: {partial_file.name}")
                            except:
                                pass
                        return 1

                        # Check if file was actually created
                        # MakeMKV uses different naming: DVDs use "title_t00.mkv", Blu-rays use "MovieName_t00.mkv"
                        # Look for any file with the correct title ID
                        mkv_files = list(outdir.glob(
                            f"*_t{main_title_id:02d}.mkv"))
                        if not mkv_files:
                            print(
                                f"  ✗ No MKV file found for title {main_title_id}")
                            print(
                                f"  → Looking for any MKV files in {outdir}...")
                            existing_files = list(outdir.glob("*.mkv"))
                            if existing_files:
                                print(
                                    f"  → Found existing MKV files: {[f.name for f in existing_files]}")
                                print(
                                    f"  → Using largest file as main feature")
                                # Continue with existing files - skip backup
                            else:
                                print(
                                    f"  → Trying backup method for problematic disc...")

                                # Try backup method for problematic DVDs
                                backup_cmd = ["makemkvcon",
                                              "backup", "disc:0", str(outdir)]
                                print(
                                    f"  → Running backup: {' '.join(backup_cmd)}")
                                backup_result = _run(backup_cmd, capture=True)
                                # Last 200 chars
                                print(
                                    f"  ✓ Backup output: {backup_result.stdout.strip()[-200:]}")

                                # Now rip ALL titles from backup (don't rely on
                                # title ID mapping)
                                backup_mkv_cmd = ["makemkvcon", "mkv", f"file:{outdir}", "all", str(
                                    outdir), f"--minlength={minlength}"]
                                print(
                                    f"  → Running rip from backup (all titles): {' '.join(backup_mkv_cmd)}")
                                backup_rip_result = _run(
                                    backup_mkv_cmd, capture=True)
                                print(
                                    f"  ✓ Backup rip output: {backup_rip_result.stdout.strip()}")

                            # After backup rip, we'll let the existing largest
                            # file logic pick the right one

                        print(f"  ✓ Successfully ripped title {main_title_id}")
                    except subprocess.CalledProcessError as e:
                        print(
                            f"  ✗ MakeMKV failed to rip title {main_title_id}: {e}")
                        if hasattr(e, 'stdout') and e.stdout:
                            print(f"    stdout: {e.stdout.strip()}")
                        if hasattr(e, 'stderr') and e.stderr:
                            print(f"    stderr: {e.stderr.strip()}")
                        raise
                else:
                    print("❌ Could not determine main feature")
                    print("\n� Trying HandBrake CLI as fallback...")
                    
                    # Try HandBrake CLI directly from disc
                    try:
                        hb_output = outdir / f"{TITLE}_{YEAR}_handbrake.mkv"
                        
                        # Find DVD device
                        dvd_device = "/dev/rdisk1"  # Default macOS DVD device
                        if not Path(dvd_device).exists():
                            # Try other common DVD devices
                            for device in ["/dev/disk1", "/dev/rdisk2", "/dev/disk2"]:
                                if Path(device).exists():
                                    dvd_device = device
                                    break
                        
                        hb_cmd = [
                            "HandBrakeCLI",
                            "-i", dvd_device,
                            "-o", str(hb_output),
                            "-t", "0",  # First title
                            "-c", "1",  # Chapter 1 (main feature)
                            "--min-duration", "1200",  # 20 minutes minimum
                            "--preset", "Fast 1080p30",
                            "--encoder", "x264",
                            "--quality", "20",
                            # Audio: prefer preferred language, most channels
                            "--audio-lang-list", LANG_AUDIO,
                            "--first-audio",  # Use first matching audio track
                            "--aencoder", "copy",  # Copy audio quality
                            # Subtitles: prefer preferred language
                            "--subtitle-lang-list", LANG_SUBTITLES,
                            "--first-subtitle",  # Use first matching subtitle
                            "--subtitle-burned"  # Burn subtitles (HandBrake limitation)
                        ]
                        print(f"  → Running HandBrake: {' '.join(hb_cmd[:5])}...")
                        print(f"  → Using device: {dvd_device}")
                        print(f"  → Audio preference: {LANG_AUDIO.upper()}")
                        print(f"  → Subtitle preference: {LANG_SUBTITLES.upper()}")
                        hb_result = _run(hb_cmd, capture=False)  # Don't capture to show progress
                        
                        if hb_output.exists():
                            print(f"  ✓ HandBrake succeeded: {hb_output.name}")
                            mkvs = [hb_output]
                        else:
                            print(f"  ✗ HandBrake failed to create output")
                    except Exception as hb_error:
                        print(f"  ✗ HandBrake fallback failed: {hb_error}")
                    
                    if not mkvs:
                        print("\n�� This could be due to:")
                        print("   - Disc with multiple equal-length features")
                        print("   - MakeMKV unable to identify the main title")
                        print("   - Unusual disc structure")
                        print("\n🔧 Suggestions:")
                        print("   - Try using --force-all-tracks if you want all content")
                        print("   - Check the disc manually for the main feature")
                        print("   - Use a different ripping tool for this disc")
                        print("\n⚠️  Exiting gracefully - no files were created")
                        return 1  # Exit with error code

            except Exception as e:
                print(f"\n❌ Error during disc processing: {e}")
                print("\n💡 This could be due to:")
                print("   - Disc reading issues (try cleaning the disc)")
                print("   - MakeMKV compatibility problems")
                print("   - Internal script errors")
                print("\n🔧 Suggestions:")
                print("   - Try cleaning the disc and re-running")
                print("   - Use a different Blu-ray drive if available")
                print("   - Check the disc for scratches or damage")
                print("\n⚠️  Exiting gracefully - no files were created")
                return 1  # Exit with error code

        else:
            print("Ripping all tracks (forced)...")
            try:
                _run(["makemkvcon", "mkv", "disc:0", "all",
                     str(outdir), f"--minlength={minlength}"])
                print(f"✓ Successfully ripped all tracks (forced)")
            except subprocess.CalledProcessError as e:
                print(f"✗ MakeMKV failed to rip all tracks (forced): {e}")
                print(f"  → Trying backup method for problematic disc...")

                # Try backup method for problematic discs
                backup_cmd = ["makemkvcon", "backup", "disc:0", str(outdir)]
                print(f"  → Running backup: {' '.join(backup_cmd)}")
                backup_result = _run(backup_cmd, capture=True)
                # Last 200 chars
                print(
                    f"  ✓ Backup output: {backup_result.stdout.strip()[-200:]}")

                # Now rip ALL titles from backup (don't rely on title ID
                # mapping)
                backup_mkv_cmd = ["makemkvcon", "mkv", f"file:{outdir}", "all", str(
                    outdir), f"--minlength={minlength}"]
                print(
                    f"  → Running rip from backup (all titles): {' '.join(backup_mkv_cmd)}")
                try:
                    backup_rip_result = _run(backup_mkv_cmd, capture=True)
                    print(
                        f"  ✓ Backup rip output: {backup_rip_result.stdout.strip()}")
                    print(f"  ✓ Successfully ripped using backup method")
                except subprocess.CalledProcessError as e3:
                    print(f"  ✗ Backup rip also failed: {e3}")
                    print(
                        f"  ❌ This disc appears to be unreadable or heavily protected")
                    print(
                        f"  💡 Try cleaning the disc or using a different Blu-ray drive")
                    return 1  # Exit gracefully

        # Eject disc if requested (default: true for disc rips)
        if get_env_str("EJECT_DISC", "true").lower() in ("true", "1", "yes"):
            print("Disc rip complete, ejecting...")
            eject_disc()

        # Debug: Check what files exist after rip
        print(f"  → Checking files in {outdir}:")
        try:
            files = list(outdir.glob("*"))
            if files:
                for f in files:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    print(f"     {f.name} ({size_mb:.1f}MB)")
            else:
                print(f"     No files found!")
        except Exception as e:
            print(f"     Error listing files: {e}")

        mkvs = sorted(outdir.glob("*.mkv"))
        if not mkvs:
            print(
                f"  ❌ No MKV files created after ripping - something went wrong")
            return 1

        print(f"  ✓ Found {len(mkvs)} MKV file(s) after ripping")

    # Filter for main feature only (largest file) unless forcing all tracks
    if not force_all_tracks and len(mkvs) > 1:
        # Find the largest file (main feature)
        largest_mkv = max(mkvs, key=lambda p: p.stat().st_size)
        mkvs = [largest_mkv]
        print(
            f"Focusing on main feature: {largest_mkv.name} ({largest_mkv.stat().st_size / (1024**3):.1f}GB)")
    elif force_all_tracks:
        print(f"Processing all {len(mkvs)} tracks (forced)")

    # Check if we can skip the prompt for simple English content
    # Skip prompt if: English movie + English audio + English SOFT subtitles
    # Also skip if we already made a choice during pre-rip prompt
    skip_prompt = False
    if not force_all_tracks and mkvs:
        main_mkv = max(mkvs, key=lambda p: p.stat().st_size)
        
        # Analyze streams
        audio_streams, subtitle_streams = analyze_mkv_streams(main_mkv)
        
        # Check if all preferred language (movie + audio + soft subs)
        all_preferred_audio = all(matches_language(s.get('language', ''), LANG_AUDIO) for s in audio_streams)
        preferred_soft_subs = any(s.get('codec') in ['subrip', 'webvtt', 'ass', 'ssa'] 
                           and matches_language(s.get('language', ''), LANG_SUBTITLES)
                           for s in subtitle_streams)
        
        if 'subtitle_config' in dir() and subtitle_config:
            skip_prompt = True
        elif all_preferred_audio and preferred_soft_subs:
            # Simple case - skip prompt, just proceed with extraction
            skip_prompt = True
            print(f"\n🎬 Detected: English movie with English audio and soft subtitles")
            print(f"  → Will automatically extract English soft subtitles to .srt file")
            subtitle_config = {'action': 'extract_srt', 'preferred_text_subs': True}
        elif not force_all_tracks and mkvs:
            # Show interactive prompt for complex cases
            print(f"\n🎬 Analyzing main feature: {main_mkv.name}")
            subtitle_config = interactive_subtitle_prompt(
                audio_streams, subtitle_streams, 
                source_name=f"Analyzing {main_mkv.name}"
            )
        
        print("=" * 50 + "\n")

    for mkv in mkvs:
        # Check if file still exists (might have been deleted/moved)
        if not mkv.exists():
            print(f"Skipping missing file: {mkv.name}")
            continue

        name = mkv.stem

        # Use MP4 for both DVD and Blu-ray (simpler, more compatible)
        mp4_path = outdir / f"{name}.mp4"
        print(f"  → Using MP4 container (Jellyfin compatible)")

        print(
            f"Processing: {mkv.name} ({mkv.stat().st_size / (1024**3):.1f}GB)")

        # Skip if MP4 already exists and is reasonably sized (compressed)
        if mp4_path.exists() and mp4_path.stat().st_size > 1000000:  # > 1MB
            # Additional check: ensure file is actually compressed (not
            # original MakeMKV rip)
            file_size_gb = mp4_path.stat().st_size / (1024**3)
            if file_size_gb < 10:  # If file is less than 10GB, assume it's compressed
                print(
                    f"  ✓ Already encoded: {mp4_path.name} ({file_size_gb:.1f}GB)")
                continue
            else:
                print(
                    f"  ⚠️  Found large file ({file_size_gb:.1f}GB) - re-encoding to compress...")
                # Continue with encoding to compress the large file
                # Use a different output filename to avoid overwriting input
                mp4_path = outdir / f"{name}_compressed.mp4"
                print(f"  → Using temporary output: {mp4_path.name}")

        audio_streams = ffprobe_streams(mkv, "a")
        subs_streams = ffprobe_streams(mkv, "s")

        default_audio_lang = pick_default_audio_lang(audio_streams)
        needs_lang_action = not default_audio_lang.startswith(
            "en") if default_audio_lang else False

        has_en_audio = has_lang(audio_streams, "en")
        has_en_subs = has_lang(subs_streams, "en")

        eng_text_idx = first_eng_text_sub_index(subs_streams)
        eng_image_idx, eng_image_codec = first_eng_image_sub_index(
            subs_streams)
        eng_image_hb_track = hb_track_for_sub_stream(
            subs_streams, eng_image_idx)

        hb_audio_opts: list[str] = []
        hb_sub_opts: list[str] = []
        mark_default_sub = False

        # Prefer English audio if available
        if has_en_audio:
            # For multiple English tracks, prefer the one with most channels
            # (main movie over commentary)
            preferred_tracks = [s for s in audio_streams if (
                matches_language((s.get("tags") or {}).get("language") or "", LANG_AUDIO))]
            if len(preferred_tracks) > 1:
                # Find the preferred track with the most channels
                best_track = max(
                    preferred_tracks, key=lambda s: s.get("channels", 0))
                # HandBrake uses 1-based indexing
                best_idx = audio_streams.index(best_track) + 1
                hb_audio_opts = ["--audio", str(best_idx)]
            else:
                hb_audio_opts = ["--audio-lang-list", "eng", "--first-audio"]

        if needs_lang_action and policy:
            if policy == "prefer-audio" and has_en_audio:
                # For multiple preferred tracks, prefer the one with most
                # channels (main movie over commentary)
                preferred_tracks = [s for s in audio_streams if (
                    matches_language((s.get("tags") or {}).get("language") or "", LANG_AUDIO))]
                if len(preferred_tracks) > 1:
                    # Find the preferred track with the most channels
                    best_track = max(
                        preferred_tracks, key=lambda s: s.get("channels", 0))
                    # HandBrake uses 1-based indexing
                    best_idx = audio_streams.index(best_track) + 1
                    hb_audio_opts = ["--audio", str(best_idx)]
                else:
                    hb_audio_opts = ["--audio-lang-list",
                                     "eng", "--first-audio"]
            elif policy == "prefer-subs" and has_en_subs:
                mark_default_sub = True

        # For MP4 + external SRT, we don't embed subtitles by default
        # Use interactive subtitle configuration or default behavior
        if 'subtitle_config' in locals() and subtitle_config:
            # User made interactive choice
            action = subtitle_config['action']
            
            if action == "burn_subs" and subtitle_config['preferred_text_subs']:
                # Burn English text subtitles
                if eng_text_idx >= 0:
                    hb_sub_opts = ["--subtitle", str(eng_text_idx + 1), "--subtitle-burned"]
                    print(f"  ⚠️  BURNING English text subtitles (user choice)")
            elif action == "burn_pgs_subs" and subtitle_config['preferred_pgs_subs']:
                # Burn English PGS subtitles
                if eng_image_idx >= 0:
                    hb_sub_opts = ["--subtitle", str(eng_image_hb_track), "--subtitle-burned"]
                    print(f"  ⚠️  BURNING English PGS subtitles (user choice)")
            elif action == "extract_srt" and subtitle_config['preferred_text_subs']:
                # Extract text subtitles to SRT
                print(f"  → Extracting English text subtitles to SRT (user choice)")
            elif action == "extract_pgs_ocr":
                # Extract PGS for later OCR
                pgs_files = extract_pgs_subtitles(mkv, outdir)
                if pgs_files:
                    print(f"  ✓ Extracted {len(pgs_files)} PGS file(s) for future OCR")
                else:
                    print(f"  ⚠️  No PGS files extracted")
            elif action == "no_subs":
                print(f"  → Skipping all subtitle processing (user choice)")
            else:
                print(f"  → Standard MP4 processing (user choice)")
        else:
            # Default automatic behavior (existing logic)
            burn_subs = get_env_str("BURN_SUBTITLES", "false").lower() in ("true", "1", "yes")
            
            if burn_subs and needs_lang_action and has_en_subs:
                # Foreign audio + English subtitles available + burning requested
                if eng_text_idx >= 0:
                    hb_sub_opts = ["--subtitle", str(eng_text_idx + 1), "--subtitle-burned"]
                    print(f"  ⚠️  BURNING English text subtitles (foreign language audio)")
                elif eng_image_idx >= 0:
                    hb_sub_opts = ["--subtitle", str(eng_image_hb_track), "--subtitle-burned"]
                    print(f"  ⚠️  BURNING English image subtitles (foreign language audio)")
            elif burn_subs and needs_lang_action and not has_en_subs:
                # Foreign audio but no English subtitles - can't burn!
                print("  ⚠️  Foreign language audio detected but no English subtitles available")
                print("  ⚠️  Cannot burn subtitles - will extract external subs if found")

        hb_cmd = [
            "HandBrakeCLI",
            "-i",
            str(mkv),
            "-o",
            str(mp4_path),
            "-e",
            "x264",
            "-q",
            quality,
            "--preset",
            preset,
            "-B",
            "160",
            "--optimize",
            "--no-markers",
            "--format", "mp4"  # Always use MP4 now
        ] + (["--tune", tune] if tune else []) + hb_audio_opts + hb_sub_opts

        # Add streaming optimization flags if enabled
        if streaming_optimize:
            hb_cmd.extend([
                "--encoder-preset", "fast",
                "--encoder-profile", "high",  # High profile for better compatibility
                "--encoder-level", "4.0",
            ])

        container = "MP4"  # Always MP4 now
        print(f"  → Encoding to {container}...")
        print(f"  → Input: {mkv}")
        print(f"  → Output: {mp4_path}")
        print(f"  → Input exists: {mkv.exists()}")
        print(f"  → Output exists: {mp4_path.exists()}")
        try:
            _run(hb_cmd)
            print(f"  ✓ Encoding complete: {mp4_path.name}")

            # Extract subtitles based on user choice
            if 'subtitle_config' in locals() and subtitle_config:
                action = subtitle_config['action']
                
                if action == "extract_srt" and subtitle_config['preferred_text_subs']:
                    # Extract text subtitles to SRT
                    srt_files = extract_subtitles_to_srt(mkv, outdir)
                    if srt_files:
                        print(f"  ✓ Extracted {len(srt_files)} subtitle file(s)")
                    else:
                        print("  ⚠️  No text subtitles extracted")
                elif action in ["burn_subs", "burn_pgs_subs"]:
                    # Already handled in HandBrake options
                    print(f"  ✓ Subtitles burned into video")
                elif action == "extract_pgs_ocr":
                    print(f"  ✓ PGS extraction completed (OCR not yet implemented)")
                else:
                    print(f"  → No subtitle extraction (user choice)")
            else:
                # Default behavior - extract if English subtitles exist
                if has_en_subs:
                    srt_files = extract_subtitles_to_srt(mkv, outdir)
                    if srt_files:
                        print(f"  ✓ Extracted {len(srt_files)} subtitle file(s)")
                    else:
                        print("  ⚠️  No subtitles extracted")
                else:
                    print("  ⚠️  No English subtitles found in source")

        except subprocess.CalledProcessError as e:
            print(f"  ✗ Encoding failed for {mkv.name}: {e}")
            continue

        # Post-mux English text subs into MP4 (if available)
        if eng_text_idx != -1:
            mux_text_sub_into_mp4(
                mp4_path, mkv, eng_text_idx, mark_default_sub)
        elif has_en_subs and eng_image_codec:
            # Image subtitles exist but can't be muxed into mp4.
            pass

    # Auto-organize main feature only if TITLE and YEAR were provided.
    if safe_title and safe_year:
        target_dir = library_root / dest_category / \
            f"{safe_title} ({safe_year})"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Look for the final compressed MP4 file (prefer _compressed if exists)
        mp4_files = list(outdir.glob("*.mp4"))
        if mp4_files:
            # Prefer _compressed.mp4 files (these are the re-encoded ones)
            compressed_files = [f for f in mp4_files if "_compressed" in f.name]
            target_file = compressed_files[0] if compressed_files else max(mp4_files, key=lambda p: p.stat().st_size)
            
            # Always use MP4 now
            dest = target_dir / f"{safe_title} ({safe_year}).mp4"
            if not dest.exists():
                shutil.move(str(target_file), str(dest))

            # Move subtitle files too
            srt_files = list(outdir.glob("*.en.srt"))
            for srt_file in srt_files:
                srt_dest = target_dir / f"{safe_title} ({safe_year}).en.srt"
                if not srt_dest.exists():
                    shutil.move(str(srt_file), str(srt_dest))
                    print(f"  ✓ Moved subtitle: {srt_dest.name}")
            
            # Move PGS subtitle files too
            sup_files = list(outdir.glob("*.en.sup"))
            for sup_file in sup_files:
                sup_dest = target_dir / f"{safe_title} ({safe_year}).en.sup"
                if not sup_dest.exists():
                    shutil.move(str(sup_file), str(sup_dest))
                    print(f"  ✓ Moved PGS subtitle: {sup_dest.name}")

            # Apply streaming optimization to the final organized file
            if streaming_optimize:
                try:
                    print(
                        f"  → Applying streaming optimization to final file...")
                    temp_path = dest.with_suffix(f".temp{dest.suffix}")
                    cmd = [
                        "ffmpeg",
                        "-i", str(dest),
                        "-c", "copy",  # Copy streams without re-encoding
                        # Generate proper timestamps (fixes warning)
                        "-fflags", "+genpts",
                        "-movflags", "+faststart",  # Standard web optimization
                        "-f", "mp4",  # Always use MP4 now
                        str(temp_path)
                    ]
                    _run(cmd, capture=False)
                    temp_path.replace(dest)
                    print(f"  ✓ Streaming optimization applied to {dest.name}")
                except Exception as e:
                    print(f"  ⚠ Streaming optimization failed: {e}")
                    # Continue without optimization - file should still be
                    # usable

    print(f"\nDone: {outdir}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
