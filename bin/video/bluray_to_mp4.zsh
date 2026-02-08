#!/usr/bin/env zsh
set -euo pipefail

# Blu-ray to MP4 Conversion Script
# ================================
# 
# This script automates the complete Blu-ray to MP4 conversion workflow:
# 
# USAGE:
#   ./bluray_to_mp4.zsh [movie-title] [year]
#   
#   Examples:
#     ./bluray_to_mp4.zsh "The Matrix" 1999     ← Manual title + year
#     ./bluray_to_mp4.zsh "The Matrix"          ← Manual title only
#     ./bluray_to_mp4.zsh 1999                   ← Auto-detect title + manual year
#     ./bluray_to_mp4.zsh                        ← Auto-detect everything
#
# REQUIREMENTS:
#   - MakeMKV (for Blu-ray ripping)
#   - HandBrakeCLI (for MP4 encoding)
#   - MKVToolNix (mkvmerge, mkvextract, mkvinfo)
#   - pgsrip (for PGS subtitle OCR conversion)
#   - Tesseract OCR (for subtitle text recognition)
#
# WORKFLOW:
#   1. Detects Blu-ray disc and extracts volume name
#   2. Creates movie-specific folder (with optional year)
#   3. Rips all titles, keeps largest file (main feature)
#   4. Extracts PGS subtitles from main feature
#   5. Converts PGS subtitles to SRT via OCR
#   6. Detects default English audio track
#   7. Encodes MP4 with embedded subtitles (soft, on by default)
#   8. Cleans up intermediate files
#
# OUTPUT:
#   - Movie Name (Year).mp4    ← Final video file for Jellyfin/QuickTime
#   - Movie Name (Year).en.srt ← External subtitles for Jellyfin
#
# NOTES:
#   - Subtitles are soft-encoded (can be toggled on/off)
#   - English subtitles are enabled by default
#   - Script handles copy protection failures gracefully
#   - Intermediate files are automatically cleaned up
#

# ===== CONFIG =====
DISC="disc:0"

# ===== STEP 0: Read disc name from OS =====
echo "=== Reading disc information ==="

# Try drutil first (preferred method)
DISC_DEV=$(drutil status 2>&1 | awk '/Name:/{print $NF}')

# Fallback: check /Volumes/ for Blu-ray mounts
if [[ -z "$DISC_DEV" ]]; then
  echo "drutil failed, trying fallback detection..."
  # Look for Blu-ray/BD volumes in /Volumes/
  BD_MOUNT=$(find /Volumes -maxdepth 1 -type d -name "*BD*" -o -name "*BLURAY*" -o -name "*BDMV*" 2>/dev/null | head -1)
  if [[ -z "$BD_MOUNT" ]]; then
    # If no obvious BD naming, check for any non-system volume that might be a Blu-ray
    BD_MOUNT=$(find /Volumes -maxdepth 1 -type d ! -name "Macintosh*" ! -name "com.apple*" ! -name "Recovery*" ! -name "Volumes" 2>/dev/null | head -1)
  fi
  
  if [[ -n "$BD_MOUNT" ]]; then
    DISC_LABEL=$(basename "$BD_MOUNT")
    echo "Found Blu-ray mount: $DISC_LABEL"
  else
    echo "❌ No optical disc found."
    exit 1
  fi
else
  # drutil worked, get volume name
  DISC_LABEL=$(diskutil info "$DISC_DEV" | awk -F: '/Volume Name/{gsub(/^ +| +$/, "", $2); print $2}')
  if [[ -z "$DISC_LABEL" ]]; then
    echo "❌ Could not read disc volume name."
    exit 1
  fi
fi

# Parse command line arguments
# Usage: ./bluray_to_mp4.zsh [movie-title] [year]
if [[ -n "${2:-}" ]]; then
  # Both title and year provided
  MOVIE_NAME="${1}"
  MOVIE_YEAR="${2}"
  MOVIE_BASE="${MOVIE_NAME} (${MOVIE_YEAR})"
elif [[ -n "${1:-}" ]]; then
  # Check if first arg looks like a year (4 digits)
  if [[ "${1}" =~ ^[0-9]{4}$ ]]; then
    # Only year provided - auto-detect title
    MOVIE_NAME=$(echo "$DISC_LABEL" | tr '_' ' ')
    MOVIE_YEAR="${1}"
    MOVIE_BASE="${MOVIE_NAME} (${MOVIE_YEAR})"
  else
    # Only title provided
    MOVIE_NAME="${1}"
    MOVIE_BASE="${MOVIE_NAME}"
  fi
else
  # No arguments - auto-detect everything
  MOVIE_NAME=$(echo "$DISC_LABEL" | tr '_' ' ')
  MOVIE_BASE="${MOVIE_NAME}"
fi

echo "Disc detected: $MOVIE_BASE"

BASE="$HOME/Movies/Rips/${MOVIE_BASE}"

# Handle duplicate folders by appending a timestamp
if [[ -d "$BASE" ]]; then
  TIMESTAMP=$(date +%H%M%S)
  BASE="${BASE}_${TIMESTAMP}"
  MOVIE_BASE="${MOVIE_BASE}_${TIMESTAMP}"
fi

mkdir -p "$BASE"
cd "$BASE"

# ===== PATHS =====
MP4="$BASE/${MOVIE_BASE}.mp4"
SUP="$BASE/subs_eng.sup"
SRT="$BASE/${MOVIE_BASE}.en.srt"

# ===== STEP 1: Rip all titles, then keep only the largest MKV =====
MKV_COUNT=$(find "$BASE" -maxdepth 1 -name '*.mkv' | wc -l | tr -d ' ')
if [[ "$MKV_COUNT" -eq 0 ]]; then
  echo "Ripping all titles from disc..."
  if ! makemkvcon mkv $DISC all "$BASE"; then
    echo "⚠️ Some titles failed to rip (common with copy protection)"
  fi
fi

# Identify the largest MKV (main feature)
MKV=$(find "$BASE" -maxdepth 1 -name '*.mkv' -print0 | xargs -0 ls -S | head -1)
if [[ -z "$MKV" ]]; then
  echo "❌ No MKV files found after rip."
  exit 1
fi

echo "Main feature: $(basename "$MKV")"

# Remove all other MKVs
for f in "$BASE"/*.mkv; do
  [[ "$f" != "$MKV" ]] && rm -f "$f"
done

# ===== STEP 2: Extract first PGS subtitle =====
if [[ ! -f "$SUP" ]]; then
  TRACK=$(mkvmerge -i "$MKV" | awk '/subtitles \(HDMV PGS\)/{print $3; exit}' | tr -d '()')
  if [[ -n "$TRACK" ]]; then
    echo "Extracting subtitle track $TRACK → $SUP"
    mkvextract tracks "$MKV" "$TRACK:$SUP"
  else
    echo "⚠️ No subtitles found."
  fi
else
  echo "SUP exists, skipping extract."
fi

# ===== STEP 2.5: Convert PGS to SRT via OCR =====
if [[ -f "$SUP" && ! -f "$SRT" ]]; then
  echo "Converting PGS subtitles to SRT via OCR..."
  if ! command -v pgsrip &>/dev/null; then
    echo "Installing pgsrip..."
    if ! command -v pipx &>/dev/null; then
      brew install pipx --quiet
    fi
    pipx install pgsrip --quiet
  fi
  if pgsrip "$SUP" && mv "$(dirname "$SUP")/$(basename "$SUP" .sup).srt" "$SRT"; then
    echo "✅ SRT created: $SRT"
  else
    echo "⚠️ PGS to SRT conversion failed, continuing without subtitles"
  fi
fi

# ===== STEP 3: Encode MP4 =====
if [[ ! -f "$MP4" ]]; then
  echo "Encoding MP4..."
  
  # Find the default English audio track (usually the main feature audio)
  AUDIO_TRACK=$(mkvinfo "$MKV" 2>/dev/null | awk '
    /Track type: audio/ { 
      audio=1; 
      default=0; 
      english=0; 
      track_id="" 
    }
    audio && /"Default track" flag: 1/ { default=1 }
    audio && /Language: eng/ { english=1 }
    audio && /track ID for mkvmerge/ { track_id=$NF; gsub(/\)/, "", track_id) }
    audio && default && english && track_id { 
      print track_id; 
      exit 
    }
    /^$/ { audio=0 }
  ')
  
  if [[ -z "$AUDIO_TRACK" ]]; then
    echo "⚠️ Could not find default English audio, using track 1"
    AUDIO_TRACK=1
  fi
  
  echo "Using audio track: $AUDIO_TRACK"
  
  # Build HandBrake command with streaming-compatible settings
  HANDBRAKE_CMD=(
    -i "$MKV"
    -o "$MP4"
    -e x265
    -q 20
    --encoder-preset medium
    --encoder-profile main
    --encoder-level 4.1
    -a "$AUDIO_TRACK"
    --audio-copy-mask dts,ac3
    --audio-fallback av_aac
    -E av_aac
    -B 192
    --markers
    --optimize  # HandBrake's built-in faststart optimization
  )
  
  # Add subtitles if SRT file exists
  if [[ -f "$SRT" ]]; then
    echo "Embedding subtitles from $SRT (English, on by default)"
    HANDBRAKE_CMD+=(--subtitle-burned=0 --subtitle-default=1 -s "$SRT")
  fi
  
  if ! HandBrakeCLI "${HANDBRAKE_CMD[@]}"; then
    echo "❌ MP4 encoding failed."
    exit 1
  fi
else
  echo "MP4 exists, skipping encode."
fi

# ===== STEP 3.5: Post-encoding MP4 compliance check and repair =====
echo "Checking MP4 compliance for streaming..."

# Check if file needs repair (missing timestamps or faststart)
COMPLIANCE_CHECK=$(ffmpeg -i "$MP4" -v quiet -f null - 2>&1 | grep -E "(non-monotonic|missing timestamps)" || true)

if [[ -n "$COMPLIANCE_CHECK" ]] || [[ ! -f "$MP4.repaired" ]]; then
  echo "🔧 Repairing MP4 for streaming compatibility..."
  
  # Create repaired version with proper timestamps and faststart
  REPAIRED_MP4="${MP4%.mp4}.repaired.mp4"
  
  if ffmpeg -fflags +genpts -i "$MP4" \
    -map 0 \
    -c copy \
    -movflags +faststart \
    -avoid_negative_ts make_zero \
    "$REPAIRED_MP4" 2>/dev/null; then
    
    echo "✅ MP4 repaired successfully"
    
    # Verify the repaired file
    if ffmpeg -i "$REPAIRED_MP4" -v quiet -f null - 2>&1 | grep -E "(non-monotonic|missing timestamps)" > /dev/null; then
      echo "⚠️ Repaired file still has issues, keeping original"
      rm -f "$REPAIRED_MP4"
    else
      # Replace original with repaired version
      mv "$REPAIRED_MP4" "$MP4"
      echo "✅ Original file replaced with repaired version"
    fi
  else
    echo "⚠️ MP4 repair failed, keeping original"
  fi
else
  echo "✅ MP4 is already streaming compliant"
fi

# ===== STEP 4: Cleanup =====
if [[ -f "$SRT" ]]; then
  echo "Cleaning up intermediates..."
  rm -f "$MKV" "$SUP"
fi

echo ""
echo "✅ DONE"
echo "Final files:"
ls -lh "$BASE"

