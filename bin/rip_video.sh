#!/bin/sh
# POSIX-friendly video ripper using MakeMKV and HandBrakeCLI
# Usage: bin/rip_video.sh [dvd|bluray]
set -eu

# Configuration loading
# Default root, then override from .env, then optional config.sh (deprecated).
SCRIPT_DIR=$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)
ROOT_DIR=$(dirname "$SCRIPT_DIR")

# Defaults
RIPS_ROOT=${RIPS_ROOT:-/Volumes/Data/Media/Rips}

# Load .env if present (centralized project config)
if [ -r "$ROOT_DIR/.env" ]; then
  # export variables defined in .env
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

# Optional legacy override via config.sh (kept for backward compatibility)
CONFIG_FILE="$ROOT_DIR/config.sh"
[ -r "$CONFIG_FILE" ] && . "$CONFIG_FILE"

TYPE="${1:-}"
if [ -z "$TYPE" ]; then
  echo "Usage: $0 [dvd|bluray]" >&2
  exit 1
fi

case "$TYPE" in
  dvd) DISCDIR="DVDs" ;;
  bluray) DISCDIR="Blurays" ;;
  *) echo "Unknown type: $TYPE (expected dvd|bluray)" >&2; exit 1 ;;
 esac

STAMP=$(date "+%Y-%m-%d")
OUTDIR="$RIPS_ROOT/$DISCDIR/$STAMP"
mkdir -p "$OUTDIR"

# Rip
makemkvcon mkv disc:0 all "$OUTDIR"

# Transcode
for f in "$OUTDIR"/*.mkv; do
  [ -e "$f" ] || continue
  name=$(basename "$f" .mkv)
  HandBrakeCLI -i "$f" -o "$OUTDIR/${name}.mp4" -e x264 -q 22 -B 160 --optimize
done

# Optional: auto-organize to Movies/Title (Year)/Title (Year).mp4
# Provide TITLE and YEAR in the environment, e.g.:
#   TITLE="Movie Name" YEAR=1999 make rip-movie TYPE=dvd
if [ "${TITLE:-}" ] && [ "${YEAR:-}" ]; then
  DEST_CATEGORY=${DEST_CATEGORY:-Movies}
  TARGET_DIR="$RIPS_ROOT/$DEST_CATEGORY/$TITLE ($YEAR)"
  mkdir -p "$TARGET_DIR"

  # Pick the largest MP4 as the main feature
  largest_mp4=""
  largest_size=0
  for mp4 in "$OUTDIR"/*.mp4; do
    [ -e "$mp4" ] || continue
    # portable file size
    size=$(wc -c < "$mp4" | tr -d ' ')
    case "$size" in
      ''|*[!0-9]*) size=0 ;;
    esac
    if [ "$size" -gt "$largest_size" ]; then
      largest_size=$size
      largest_mp4="$mp4"
    fi
  done

  if [ "$largest_mp4" ]; then
    dest="$TARGET_DIR/$TITLE ($YEAR).mp4"
    mv -n "$largest_mp4" "$dest"
    echo "Placed main feature: $dest"
  else
    echo "No MP4 found to organize under $TARGET_DIR" >&2
  fi
fi

echo "Done: $OUTDIR"
