#!/bin/sh
# Backfill English soft subtitles from a source MKV folder into an existing MP4
# Usage:
#   bin/backfill_subs.sh \
#     "/Volumes/Data/Media/Rips/DVDs/Movie Name (Year)" \
#     "/Volumes/Data/Media/Rips/Movies/Movie Name (Year)"
#
# Behavior:
# - Picks the largest MKV in the source folder as the source for subtitles.
# - Picks the MP4 that matches the target folder name, or the only MP4 present.
# - Detects the first English text subtitle stream (subrip/ass/ssa/text/webvtt).
# - If no English text subs exist, attempts automatic OCR:
#   - DVD (dvd_subtitle): extract VobSub (idx/sub), OCR via sub2srt + tesseract => SRT
#   - Blu-ray (hdmv_pgs_subtitle): extract PGS (.sup), convert to VobSub via bdsup2sub, OCR via sub2srt + tesseract => SRT
# - Muxes the resulting subtitle (text stream) into the MP4 as a soft subtitle (mov_text). By default, it is NOT marked default.
# - Set DEFAULT=yes to mark the English subtitle track as default (players may auto-enable it).
# - Outputs a new file with suffix `.en-subs.mp4` next to the original by default.
# - Set INPLACE=yes to replace the original MP4 in-place (original backed up as .bak).
#
# Requirements: ffprobe, ffmpeg, jq
# Optional for OCR fallback: sub2srt, tesseract, bdsup2sub

set -eu

SRC_DIR=${1:-}
DST_DIR=${2:-}

if [ -z "$SRC_DIR" ] || [ -z "$DST_DIR" ]; then
  echo "Usage: $0 /path/to/source_mkv_dir /path/to/target_mp4_dir" >&2
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd ffprobe
require_cmd ffmpeg
require_cmd jq

# Find largest MKV in source dir
largest_mkv=""
largest_size=0
for f in "$SRC_DIR"/*.mkv; do
  [ -e "$f" ] || continue
  size=$(wc -c < "$f" | tr -d ' ')
  case "$size" in ''|*[!0-9]*) size=0 ;; esac
  if [ "$size" -gt "$largest_size" ]; then
    largest_size=$size
    largest_mkv="$f"
  fi
done

if [ -z "$largest_mkv" ]; then
  echo "No MKV files found in: $SRC_DIR" >&2
  exit 1
fi

echo "Source MKV: $largest_mkv"

# Determine target MP4: prefer file matching folder name
base_name=$(basename "$DST_DIR")
preferred_mp4="$DST_DIR/$base_name.mp4"

target_mp4=""
if [ -f "$preferred_mp4" ]; then
  target_mp4="$preferred_mp4"
else
  # If exactly one MP4 exists, use it
  set +e
  mp4_count=$(ls -1 "$DST_DIR"/*.mp4 2>/dev/null | wc -l | tr -d ' ')
  set -e
  if [ "$mp4_count" = "1" ]; then
    target_mp4=$(ls -1 "$DST_DIR"/*.mp4)
  else
    echo "Could not uniquely determine target MP4. Expected: $preferred_mp4 or exactly one MP4 in $DST_DIR" >&2
    exit 1
  fi
fi

echo "Target MP4: $target_mp4"

# Probe English subtitle streams from MKV (text and image)
SUBS_JSON=$(ffprobe -v error -select_streams s -show_entries stream=index,codec_name:stream_tags=language -of json "$largest_mkv")

eng_text_idx=$(printf '%s' "$SUBS_JSON" | jq -r '
  (.streams // [])
  | map(select(((.tags.language // "") | ascii_downcase | startswith("en"))
               and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$"))))
  | (.[0].index // -1)
')

eng_image_idx=$(printf '%s' "$SUBS_JSON" | jq -r '
  (.streams // [])
  | map(select(((.tags.language // "") | ascii_downcase | startswith("en"))
               and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$") | not)))
  | (.[0].index // -1)
')

eng_image_codec=$(printf '%s' "$SUBS_JSON" | jq -r '
  (.streams // [])
  | map(select(((.tags.language // "") | ascii_downcase | startswith("en"))
               and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$") | not)))
  | (.[0].codec_name // "")
')

# Build output path
ext_suffix=".en-subs.mp4"
out_path="${target_mp4%*.mp4}$ext_suffix"

echo "Writing: $out_path"

DISP_ARGS=""
[ "${DEFAULT:-}" = "yes" ] && DISP_ARGS="-disposition:s:0 default"

add_srt_to_mp4() {
  srt_file="$1"
  tmp_out="${out_path%.mp4}.tmp.mp4"
  ffmpeg -y \
    -i "$target_mp4" \
    -i "$srt_file" \
    -map 0 -map 1:0 \
    -c copy -c:s mov_text \
    -metadata:s:s:0 language=eng $DISP_ARGS \
    -movflags +faststart \
    "$tmp_out"
  mv -f "$tmp_out" "$out_path"
  echo "Created: $out_path"
  if [ "${INPLACE:-}" = "yes" ]; then
    backup_path="${target_mp4}.bak"
    echo "In-place mode: backing up original to $backup_path and replacing it"
    mv -f "$target_mp4" "$backup_path"
    mv -f "$out_path" "$target_mp4"
    echo "Replaced original MP4 with new file containing English subs. Backup at: $backup_path"
  fi
}

if [ "$eng_text_idx" != "-1" ]; then
  echo "Using English text subtitle stream index: $eng_text_idx"
  ffmpeg -y \
    -i "$target_mp4" \
    -i "$largest_mkv" \
    -map 0 -map 1:${eng_text_idx} \
    -c copy -c:s mov_text \
    -metadata:s:s:0 language=eng $DISP_ARGS \
    -movflags +faststart \
    "$out_path"
  echo "Created: $out_path"
  if [ "${INPLACE:-}" = "yes" ]; then
    backup_path="${target_mp4}.bak"
    echo "In-place mode: backing up original to $backup_path and replacing it"
    mv -f "$target_mp4" "$backup_path"
    mv -f "$out_path" "$target_mp4"
    echo "Replaced original MP4 with new file containing English subs. Backup at: $backup_path"
  fi
  exit 0
fi

# Fallback: OCR image subtitles if present
if [ "$eng_image_idx" = "-1" ]; then
  echo "No English subtitles found in MKV. Nothing to add." >&2
  exit 2
fi

tmp_base="$DST_DIR/.backfill_ocr_$$"
mkdir -p "$DST_DIR" >/dev/null 2>&1 || true

case "$eng_image_codec" in
  dvd_subtitle)
    if command -v sub2srt >/dev/null 2>&1 && command -v tesseract >/dev/null 2>&1; then
      echo "Extracting VobSub (idx/sub) for OCR..."
      ffmpeg -y -i "$largest_mkv" -map 0:${eng_image_idx} -c:s copy -f vobsub "$tmp_base.idx"
      if [ -f "$tmp_base.idx" ] && [ -f "$tmp_base.sub" ]; then
        echo "Running OCR (sub2srt + tesseract)..."
        sub2srt "$tmp_base.idx"
        if [ -f "$tmp_base.srt" ]; then
          add_srt_to_mp4 "$tmp_base.srt"
          rm -f "$tmp_base.idx" "$tmp_base.sub" "$tmp_base.srt" "$tmp_base.sup" 2>/dev/null || true
          exit 0
        fi
      fi
      echo "OCR failed to produce SRT. Please OCR manually or provide an SRT." >&2
      rm -f "$tmp_base.idx" "$tmp_base.sub" "$tmp_base.srt" "$tmp_base.sup" 2>/dev/null || true
      exit 3
    else
      echo "Missing tools for OCR: install with 'brew install sub2srt tesseract'" >&2
      exit 4
    fi
    ;;
  hdmv_pgs_subtitle)
    if command -v bdsup2sub >/dev/null 2>&1 && command -v sub2srt >/dev/null 2>&1 && command -v tesseract >/dev/null 2>&1; then
      echo "Extracting PGS (.sup) and converting to VobSub..."
      ffmpeg -y -i "$largest_mkv" -map 0:${eng_image_idx} -c:s copy "$tmp_base.sup"
      bdsup2sub "$tmp_base.sup" "$tmp_base.idx" || bdsup2sub -o "$tmp_base.idx" "$tmp_base.sup"
      if [ -f "$tmp_base.idx" ] && [ -f "$tmp_base.sub" ]; then
        echo "Running OCR (sub2srt + tesseract)..."
        sub2srt "$tmp_base.idx"
        if [ -f "$tmp_base.srt" ]; then
          add_srt_to_mp4 "$tmp_base.srt"
          rm -f "$tmp_base.idx" "$tmp_base.sub" "$tmp_base.srt" "$tmp_base.sup" 2>/dev/null || true
          exit 0
        fi
      fi
      echo "PGS OCR failed to produce SRT. Please OCR manually or provide an SRT." >&2
      rm -f "$tmp_base.idx" "$tmp_base.sub" "$tmp_base.srt" "$tmp_base.sup" 2>/dev/null || true
      exit 5
    else
      echo "Missing tools for PGS OCR: install with 'brew install bdsup2sub sub2srt tesseract'" >&2
      exit 6
    fi
    ;;
  *)
    echo "English subtitle codec '$eng_image_codec' not recognized for OCR path." >&2
    exit 7
    ;;
esac
