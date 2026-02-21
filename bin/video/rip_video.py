#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _run(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    kwargs = {}
    if capture:
        kwargs.update({"capture_output": True, "text": True})
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
    # Preserve acronyms, title-case words, lowercase small stop-words except first/last.
    stop = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "per", "the", "to", "vs", "via"}

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
    res = _run(["makemkvcon", "-r", "--cache=1", "info", "disc:0"], check=False)
    out = res.stdout or ""
    if re.search(r"\bBlu-?ray\b", out, re.IGNORECASE):
        return "bluray"
    if re.search(r"\bDVD\b", out, re.IGNORECASE):
        return "dvd"

    return "dvd"


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
    for s in audio_streams:
        disp = s.get("disposition") or {}
        if disp.get("default") == 1:
            return ((s.get("tags") or {}).get("language") or "").lower()
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
        if lang.startswith("en") and codec in text_codecs:
            return int(s.get("index", -1))
    return -1


def first_eng_image_sub_index(subs: list[dict]) -> tuple[int, str]:
    text_codecs = {"subrip", "ass", "ssa", "text", "webvtt"}
    for s in subs:
        lang = ((s.get("tags") or {}).get("language") or "").lower()
        codec = (s.get("codec_name") or "").lower()
        if lang.startswith("en") and codec not in text_codecs:
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


def mux_text_sub_into_mp4(mp4_path: Path, src_mkv: Path, sub_stream_index: int, mark_default: bool) -> None:
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
                        _run(["diskutil", "eject", device], check=False, capture=False)
                        print(f"Disc ejected from {device}")
                        return
            print("No optical disc found to eject")
        except Exception:
            print("Could not eject disc")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rip DVD/Blu-ray discs to your LIBRARY_ROOT using MakeMKV + HandBrake")
    parser.add_argument("type", nargs="?", default="auto", choices=["dvd", "bluray", "auto"])
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root)

    # Defaults
    library_root = Path(get_env_str("LIBRARY_ROOT", "/Volumes/Data/Media/Library") or "/Volumes/Data/Media/Library")
    minlength = int(get_env_str("MINLENGTH", "120") or "120")
    
    # Encoding settings (faster defaults)
    quality = get_env_str("HB_QUALITY", "28") or "28"  # Higher number = lower quality but faster
    preset = get_env_str("HB_PRESET", "fast") or "fast"  # Encoding speed preset
    tune = get_env_str("HB_TUNE", None)  # Optional tuning

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

    outdir.mkdir(parents=True, exist_ok=True)

    # Check if MKV files already exist
    mkvs = sorted(outdir.glob("*.mkv"))
    
    if not mkvs:
        # Only rip if no MKV files exist
        print("No MKV files found, ripping from disc...")
        # Probe disc access early (best-effort)
        _run(["makemkvcon", "-r", "--cache=1", "info", "disc:0"], check=False)

        # Rip
        _run(["makemkvcon", "mkv", "disc:0", "all", str(outdir), f"--minlength={minlength}"])
        
        mkvs = sorted(outdir.glob("*.mkv"))
        if not mkvs:
            print(f"No MKV files found in {outdir} - skipping transcode.", file=sys.stderr)
            return 0
    else:
        print(f"Found {len(mkvs)} existing MKV files, skipping disc rip...")

    if not mkvs:
        print(f"No MKV files found in {outdir} - skipping transcode.", file=sys.stderr)
        return 0

    for mkv in mkvs:
        name = mkv.stem
        mp4_path = outdir / f"{name}.mp4"

        audio_streams = ffprobe_streams(mkv, "a")
        subs_streams = ffprobe_streams(mkv, "s")

        default_audio_lang = pick_default_audio_lang(audio_streams)
        needs_lang_action = not default_audio_lang.startswith("en") if default_audio_lang else False

        has_en_audio = has_lang(audio_streams, "en")
        has_en_subs = has_lang(subs_streams, "en")

        eng_text_idx = first_eng_text_sub_index(subs_streams)
        eng_image_idx, eng_image_codec = first_eng_image_sub_index(subs_streams)
        eng_image_hb_track = hb_track_for_sub_stream(subs_streams, eng_image_idx)

        hb_audio_opts: list[str] = []
        hb_sub_opts: list[str] = []
        mark_default_sub = False

        # Auto-burn: non-English audio + no text subs + English image subs
        if needs_lang_action and eng_text_idx == -1 and has_en_subs and eng_image_hb_track > 0:
            hb_sub_opts = ["--subtitle", str(eng_image_hb_track), "--subtitle-burned"]

        if needs_lang_action and policy:
            if policy == "prefer-audio" and has_en_audio:
                hb_audio_opts = ["--audio-lang-list", "eng", "--first-audio"]
            elif policy == "prefer-subs" and has_en_subs:
                mark_default_sub = True
            elif policy == "prefer-burned" and eng_text_idx == -1 and has_en_subs and eng_image_hb_track > 0:
                hb_sub_opts = ["--subtitle", str(eng_image_hb_track), "--subtitle-burned"]

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
        ] + (["--tune", tune] if tune else []) + hb_audio_opts + hb_sub_opts

        _run(hb_cmd)

        # Post-mux English text subs into MP4 (if available)
        if eng_text_idx != -1:
            mux_text_sub_into_mp4(mp4_path, mkv, eng_text_idx, mark_default_sub)
        elif has_en_subs and eng_image_codec:
            # Image subtitles exist but can't be muxed into mp4.
            pass

    # Auto-organize main feature only if TITLE and YEAR were provided.
    if safe_title and safe_year:
        target_dir = library_root / dest_category / f"{safe_title} ({safe_year})"
        target_dir.mkdir(parents=True, exist_ok=True)

        mp4s = list(outdir.glob("*.mp4"))
        if mp4s:
            largest = max(mp4s, key=lambda p: p.stat().st_size)
            dest = target_dir / f"{safe_title} ({safe_year}).mp4"
            if not dest.exists():
                shutil.move(str(largest), str(dest))

    print(f"Done: {outdir}")
    
    # Eject disc if requested via environment variable
    if get_env_str("EJECT_DISC", "false").lower() in ("true", "1", "yes"):
        eject_disc()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
