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
MINLENGTH=${MINLENGTH:-120}  # seconds; titles shorter than this are skipped by MakeMKV

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

# --- Preflight checks ---
require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    return 1
  fi
}

warn_missing_helper() {
  helper="$1"
  path_hint="$2"
  if ! command -v "$helper" >/dev/null 2>&1; then
    echo "Note: helper '$helper' not found. If MakeMKV errors reference it, symlink as:" >&2
    echo "  sudo ln -sf $path_hint /usr/local/bin/$helper" >&2
  fi
}

# Critical deps
require_cmd makemkvcon || { echo "Install MakeMKV and its CLI symlink." >&2; exit 1; }
require_cmd HandBrakeCLI || { echo "Install HandBrakeCLI (e.g., 'brew install handbrake')." >&2; exit 1; }

# Helpful MakeMKV helpers (warn if missing)
warn_missing_helper mmgplsrv "/Applications/MakeMKV.app/Contents/MacOS/mmgplsrv"
warn_missing_helper mmccextr "/Applications/MakeMKV.app/Contents/MacOS/mmccextr"

# Ensure output root is writable
if ! mkdir -p "$RIPS_ROOT" 2>/dev/null; then
  echo "Cannot create or write to RIPS_ROOT: $RIPS_ROOT" >&2
  exit 1
fi

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

# Optionally collect Title/Year up-front (for title-named staging folder)
SAFE_TITLE=""
SAFE_YEAR=""

# Helper to title-case and sanitize
titlecase_sanitize() {
  # $1 = raw title
  printf '%s\n' "$1" | awk '
    function cap(s){return toupper(substr(s,1,1)) tolower(substr(s,2))}
    function is_stop(w){
      return (w=="a"||w=="an"||w=="and"||w=="as"||w=="at"||w=="but"||w=="by"||w=="for"||w=="in"||w=="nor"||w=="of"||w=="on"||w=="or"||w=="per"||w=="the"||w=="to"||w=="vs"||w=="via")
    }
    {
      n=split($0, words, /[ ]+/)
      out=""
      for(i=1;i<=n;i++){
        w=words[i]
        if (w==toupper(w) && length(w)>1){ piece=w }
        else {
          m=split(w, parts, /-/)
          piece=""
          for(j=1;j<=m;j++){
            p=parts[j]
            low=tolower(p)
            if (i>1 && i<n && is_stop(low))
              piece = piece (j>1?"-":"") low
            else
              piece = piece (j>1?"-":"") cap(low)
          }
        }
        out = out (i>1?" ":"") piece
      }
      print out
    }' \
  | tr ':/\t' '--- ' \
  | sed -e 's/[\\?*"<>|]//g' -e 's/[[:cntrl:]]//g' -e 's/[[:space:]]\{1,\}/ /g' -e 's/[[:space:]]$//' -e 's/^[[:space:]]//' 
}

# If TITLE provided in environment, compute SAFE_TITLE/SAFE_YEAR now
if [ -n "${TITLE:-}" ]; then
  SAFE_TITLE=$(titlecase_sanitize "$TITLE")
fi
if [ -n "${YEAR:-}" ]; then
  SAFE_YEAR=$(printf %s "$YEAR" | tr -cd '0-9' | cut -c1-4)
  [ -n "$SAFE_YEAR" ] || SAFE_YEAR="$YEAR"
fi

# If missing and interactive, prompt now so staging folder uses Title (Year)
if { [ -z "$SAFE_TITLE" ] || [ -z "$SAFE_YEAR" ]; } && [ -t 0 ]; then
  printf "Name staging folder now? This helps use Title (Year) instead of a date. [Y/n]: "
  read -r _pre
  case "$_pre" in
    n|N) : ;;
    *)
      if [ -z "$SAFE_TITLE" ]; then
        printf "Enter Title: "
        read -r TITLE
        SAFE_TITLE=$(titlecase_sanitize "$TITLE")
      fi
      if [ -z "$SAFE_YEAR" ]; then
        printf "Enter Year (YYYY): "
        read -r YEAR
        SAFE_YEAR=$(printf %s "$YEAR" | tr -cd '0-9' | cut -c1-4)
        [ -n "$SAFE_YEAR" ] || SAFE_YEAR="$YEAR"
      fi
      ;;
  esac
fi

# Decide OUTDIR (prefer Title-based; fallback to date)
if [ -n "$SAFE_TITLE" ]; then
  if [ -n "$SAFE_YEAR" ]; then
    OUTDIR="$RIPS_ROOT/$DISCDIR/$SAFE_TITLE ($SAFE_YEAR)"
  else
    OUTDIR="$RIPS_ROOT/$DISCDIR/$SAFE_TITLE"
  fi
else
  STAMP=$(date "+%Y-%m-%d")
  OUTDIR="$RIPS_ROOT/$DISCDIR/$STAMP"
fi
mkdir -p "$OUTDIR"

# Probe disc access early (gives clearer errors for region/EULA/quarantine)
if ! makemkvcon -r --cache=1 info disc:0 >/dev/null 2>&1; then
  echo "MakeMKV 'info' probe failed. If this is your first run: open /Applications/MakeMKV.app, accept EULA, set drive region, and unquarantine the app." >&2
  echo "You may also need to run: xattr -dr com.apple.quarantine /Applications/MakeMKV.app" >&2
  # Continue anyway; mkv may still work depending on system state
fi

# Rip (skip short titles)
makemkvcon mkv disc:0 all "$OUTDIR" --minlength="$MINLENGTH"

# Transcode
for f in "$OUTDIR"/*.mkv; do
  [ -e "$f" ] || continue
  name=$(basename "$f" .mkv)
  HandBrakeCLI -i "$f" -o "$OUTDIR/${name}.mp4" -e x264 -q 22 -B 160 --optimize
done

# If TITLE/YEAR not provided, optionally prompt in interactive shells
if { [ -z "${TITLE:-}" ] || [ -z "${YEAR:-}" ]; } && [ -t 0 ]; then
  if ls "$OUTDIR"/*.mp4 >/dev/null 2>&1; then
    printf "Organize main feature into %s/Movies/? [y/N]: " "$RIPS_ROOT"
    read -r _ans
    case "$_ans" in
      y|Y)
        if [ -z "${TITLE:-}" ]; then
          printf "Enter Title: "
          read -r TITLE
        fi
        if [ -z "${YEAR:-}" ]; then
          printf "Enter Year (YYYY): "
          read -r YEAR
        fi
        # Normalize TITLE to Title Case (preserve acronyms, keep small words lowercase except at boundaries)
        TITLE=$(printf '%s\n' "$TITLE" | awk '
          function cap(s){return toupper(substr(s,1,1)) tolower(substr(s,2))}
          function is_stop(w){
            return (w=="a"||w=="an"||w=="and"||w=="as"||w=="at"||w=="but"||w=="by"||w=="for"||w=="in"||w=="nor"||w=="of"||w=="on"||w=="or"||w=="per"||w=="the"||w=="to"||w=="vs"||w=="via")
          }
          {
            n=split($0, words, /[ ]+/)
            out=""
            for(i=1;i<=n;i++){
              w=words[i]
              # Keep acronyms (2+ uppercase letters) as-is
              if (w==toupper(w) && length(w)>1){ piece=w }
              else {
                # Handle hyphenated subwords
                m=split(w, parts, /-/)
                piece=""
                for(j=1;j<=m;j++){
                  p=parts[j]
                  low=tolower(p)
                  if (i>1 && i<n && is_stop(low))
                    piece = piece (j>1?"-":"") low
                  else
                    piece = piece (j>1?"-":"") cap(low)
                }
              }
              out = out (i>1?" ":"") piece
            }
            print out
          }')
        ;;
    esac
  fi
fi

# Optional: auto-organize to Movies/Title (Year)/Title (Year).mp4
# Provide TITLE and YEAR in the environment, e.g.:
#   TITLE="Movie Name" YEAR=1999 make rip-movie TYPE=dvd
if [ "${TITLE:-}" ] && [ "${YEAR:-}" ]; then
  DEST_CATEGORY=${DEST_CATEGORY:-Movies}
  # Sanitize TITLE for filesystem safety
  SAFE_TITLE=$(printf %s "$TITLE" \
    | tr ':/\t' '--- ' \
    | sed -e 's/[\\?*"<>|]//g' \
          -e 's/[[:cntrl:]]//g' \
          -e 's/[[:space:]]\{1,\}/ /g' \
          -e 's/[[:space:]]$//' \
          -e 's/^[[:space:]]//' )
  SAFE_YEAR=$(printf %s "${YEAR}" | tr -cd '0-9' | cut -c1-4)
  [ -n "$SAFE_YEAR" ] || SAFE_YEAR="$YEAR"

  TARGET_DIR="$RIPS_ROOT/$DEST_CATEGORY/$SAFE_TITLE ($SAFE_YEAR)"
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
    dest="$TARGET_DIR/$SAFE_TITLE ($SAFE_YEAR).mp4"
    mv -n "$largest_mp4" "$dest"
    echo "Placed main feature: $dest"
  else
    echo "No MP4 found to organize under $TARGET_DIR" >&2
  fi
fi

echo "Done: $OUTDIR"
