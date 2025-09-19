#!/bin/sh
# POSIX-friendly video ripper using MakeMKV and HandBrakeCLI
# Usage: bin/rip_video.sh [dvd|bluray|auto]
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
# Required for subtitle detection and post-mux to guarantee soft subs when available
require_cmd ffprobe || { echo "Install ffmpeg for ffprobe (e.g., 'brew install ffmpeg')." >&2; exit 1; }
require_cmd ffmpeg  || { echo "Install ffmpeg (e.g., 'brew install ffmpeg')." >&2; exit 1; }
require_cmd jq      || { echo "Install jq (e.g., 'brew install jq')." >&2; exit 1; }

# Helpful MakeMKV helpers (warn if missing)
warn_missing_helper mmgplsrv "/Applications/MakeMKV.app/Contents/MacOS/mmgplsrv"
warn_missing_helper mmccextr "/Applications/MakeMKV.app/Contents/MacOS/mmccextr"

# Ensure output root is writable
if ! mkdir -p "$RIPS_ROOT" 2>/dev/null; then
  echo "Cannot create or write to RIPS_ROOT: $RIPS_ROOT" >&2
  exit 1
fi

TYPE="${1:-auto}"

# Detect disc type if not specified or set to auto
if [ "$TYPE" = "auto" ] || [ -z "$TYPE" ]; then
  DETECTED=""
  # Try MakeMKV info first (already required)
  if info_out=$(makemkvcon -r --cache=1 info disc:0 2>/dev/null); then
    if printf '%s' "$info_out" | grep -Eqi 'Blu-?ray|\bBD\b'; then
      DETECTED="bluray"
    elif printf '%s' "$info_out" | grep -Eqi '\bDVD\b'; then
      DETECTED="dvd"
    fi
  fi
  # Fallback to drutil status if still unknown
  if [ -z "$DETECTED" ] && command -v drutil >/dev/null 2>&1; then
    if drutil status 2>/dev/null | grep -Eqi 'Blu-?ray|\bBD\b'; then
      DETECTED="bluray"
    elif drutil status 2>/dev/null | grep -Eqi '\bDVD\b'; then
      DETECTED="dvd"
    fi
  fi
  # Default to dvd with a warning if still unknown
  if [ -z "$DETECTED" ]; then
    echo "Warning: Could not auto-detect disc type; defaulting to 'dvd'. You can pass 'bluray' explicitly." >&2
    TYPE="dvd"
  else
    TYPE="$DETECTED"
  fi
fi

case "$TYPE" in
  dvd) DISCDIR="DVDs" ;;
  bluray) DISCDIR="Blurays" ;;
  *) echo "Unknown type: $TYPE (expected dvd|bluray|auto)" >&2; exit 1 ;;
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

  HB_AUDIO_OPTS=""
  HB_SUB_OPTS="" # unused for HandBrake now; kept for context
  HB_SUB_BASE=""  # unused for HandBrake now; kept for context
  SUBS_MARK_DEFAULT=0

  # Probe audio/subtitle streams
  DEFAULT_AUDIO_LANG=""
  HAS_EN_AUDIO=0
  HAS_EN_SUBS=0
  if command -v ffprobe >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    AUDIO_JSON=$(ffprobe -v error -select_streams a -show_entries stream=index,disposition:stream_tags=language -of json "$f" 2>/dev/null || printf '{}')
    SUBS_JSON=$(ffprobe -v error -select_streams s -show_entries stream=index,codec_name:stream_tags=language -of json "$f" 2>/dev/null || printf '{}')
    DEFAULT_AUDIO_LANG=$(printf '%s' "$AUDIO_JSON" | jq -r '(.streams // []) | (map(select((.disposition.default//0)==1)) + .) | .[0].tags.language // ""' 2>/dev/null || printf '')
    HAS_EN_AUDIO=$(printf '%s' "$AUDIO_JSON" | jq -r '((.streams // []) | any((.tags.language // "") | ascii_downcase | startswith("en"))) as $x | if $x then 1 else 0 end' 2>/dev/null || printf '0')
    HAS_EN_SUBS=$(printf '%s' "$SUBS_JSON" | jq -r '((.streams // []) | any((.tags.language // "") | ascii_downcase | startswith("en"))) as $x | if $x then 1 else 0 end' 2>/dev/null || printf '0')
    HAS_EN_TEXT_SUBS=$(printf '%s' "$SUBS_JSON" | jq -r '((.streams // []) | any(((.tags.language // "") | ascii_downcase | startswith("en")) and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$")))) as $x | if $x then 1 else 0 end' 2>/dev/null || printf '0')
    ENG_TEXT_IDX=$(printf '%s' "$SUBS_JSON" | jq -r '((.streams // [])
      | map(select(((.tags.language // "") | ascii_downcase | startswith("en")) and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$"))))
      | (.[0].index // -1))' 2>/dev/null || printf '--')
    ENG_IMAGE_IDX=$(printf '%s' "$SUBS_JSON" | jq -r '((.streams // [])
      | map(select(((.tags.language // "") | ascii_downcase | startswith("en")) and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$") | not)))
      | (.[0].index // -1))' 2>/dev/null || printf '--')
    ENG_IMAGE_CODEC=$(printf '%s' "$SUBS_JSON" | jq -r '((.streams // [])
      | map(select(((.tags.language // "") | ascii_downcase | startswith("en")) and ((.codec_name // "") | test("^(subrip|ass|ssa|text|webvtt)$") | not)))
      | (.[0].codec_name // ""))' 2>/dev/null || printf '')
  fi

  # Always include English soft subs if text-based subs are present (non-default).
  # HandBrake requires --subtitle-lang-list together with --all-subtitles to include by language.
  if [ "${HAS_EN_TEXT_SUBS:-0}" -eq 1 ]; then
    HB_SUB_BASE="--subtitle-lang-list eng --all-subtitles"
  elif [ "${HAS_EN_SUBS:-0}" -eq 1 ]; then
    echo "Note: English subtitles appear to be image-based (e.g., VobSub/PGS); MP4 cannot carry them as soft subs. Consider burn-in or backfill after OCR." >&2
  fi

  NEEDS_LANG_ACTION=0
  DEFAULT_AUDIO_LANG_LC=$(printf '%s' "${DEFAULT_AUDIO_LANG:-}" | tr 'A-Z' 'a-z')
  case "$DEFAULT_AUDIO_LANG_LC" in
    en*) NEEDS_LANG_ACTION=0 ;;
    *)   NEEDS_LANG_ACTION=1 ;;
  esac

  # Decide policy (default: keep -> interactive prompt if terminal is attached)
  POLICY=${AUDIO_SUBS_POLICY:-keep}
  if [ "$NEEDS_LANG_ACTION" -eq 1 ]; then
    case "$POLICY" in
      prefer-audio)
        if [ "$HAS_EN_AUDIO" -eq 1 ]; then
          HB_AUDIO_OPTS="--audio-lang-list eng --first-audio"
        elif [ "$HAS_EN_SUBS" -eq 1 ]; then
          HB_SUB_OPTS="--subtitle-lang-list eng --subtitle-default=1"
        fi
        ;;
      prefer-subs)
        if [ "$HAS_EN_SUBS" -eq 1 ]; then
          SUBS_MARK_DEFAULT=1
        elif [ "$HAS_EN_AUDIO" -eq 1 ]; then
          HB_AUDIO_OPTS="--audio-lang-list eng --first-audio"
        fi
        ;;
      keep|"")
        # Interactive prompt only if attached to a terminal and tools available
        if [ -t 0 ] && command -v ffprobe >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
          if [ "$HAS_EN_AUDIO" -eq 1 ] || [ "$HAS_EN_SUBS" -eq 1 ]; then
            printf "Default audio is '%s'. Choose: [a] Use English audio%s, [s] Add English subs%s, [k] Keep as-is: " \
              "${DEFAULT_AUDIO_LANG:-unknown}" \
              "$([ "$HAS_EN_AUDIO" -eq 1 ] && printf '' || printf ' (unavailable)')" \
              "$([ "$HAS_EN_SUBS" -eq 1 ] && printf '' || printf ' (unavailable)')"
            read -r _choice
            case "$_choice" in
              a|A)
                [ "$HAS_EN_AUDIO" -eq 1 ] && HB_AUDIO_OPTS="--audio-lang-list eng --first-audio" || : ;;
              s|S)
                [ "$HAS_EN_SUBS" -eq 1 ] && SUBS_MARK_DEFAULT=1 || : ;;
              *) : ;;
            esac
          fi
        fi
        ;;
      *) : ;;
    esac
  fi

  HandBrakeCLI -i "$f" -o "$OUTDIR/${name}.mp4" -e x264 -q 22 -B 160 --optimize $HB_AUDIO_OPTS

  # Post-process: if a text-based English subtitle exists in the MKV, mux it into the MP4
  if command -v ffprobe >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 && command -v ffmpeg >/dev/null 2>&1; then
    if [ "${ENG_TEXT_IDX:- -1}" != "-1" ] && [ "${ENG_TEXT_IDX:- -1}" != "--" ]; then
      DISP_ARGS=""
      if [ "$SUBS_MARK_DEFAULT" -eq 1 ]; then
        DISP_ARGS="-disposition:s:0 default"
      fi
      tmp_out="$OUTDIR/${name}.tmp.mp4"
      ffmpeg -y \
        -i "$OUTDIR/${name}.mp4" \
        -i "$f" \
        -map 0 -map 1:${ENG_TEXT_IDX} \
        -c copy -c:s mov_text \
        -metadata:s:s:0 language=eng \
        $DISP_ARGS \
        -movflags +faststart \
        "$tmp_out" && mv -f "$tmp_out" "$OUTDIR/${name}.mp4"
    elif [ "${HAS_EN_SUBS:-0}" -eq 1 ]; then
      # Try automatic OCR for DVD VobSub (dvd_subtitle) if tools are available (sub2srt + tesseract)
      if [ "${ENG_IMAGE_CODEC:-}" = "dvd_subtitle" ] && command -v sub2srt >/dev/null 2>&1; then
        out_base="$OUTDIR/${name}.eng_ocr"
        # Extract VobSub (idx/sub) from MKV
        ffmpeg -y -i "$f" -map 0:${ENG_IMAGE_IDX} -c:s copy -f vobsub "$out_base.idx" >/dev/null 2>&1 || true
        if [ -f "$out_base.idx" ] && [ -f "$out_base.sub" ]; then
          # Run OCR to SRT (requires tesseract language data for eng)
          if command -v tesseract >/dev/null 2>&1; then
            # sub2srt takes the .idx file and writes an .srt next to it
            sub2srt "$out_base.idx" >/dev/null 2>&1 || true
            if [ -f "$out_base.srt" ]; then
              DISP_ARGS=""
              [ "$SUBS_MARK_DEFAULT" -eq 1 ] && DISP_ARGS="-disposition:s:0 default"
              tmp_out="$OUTDIR/${name}.tmp.mp4"
              ffmpeg -y -i "$OUTDIR/${name}.mp4" -i "$out_base.srt" \
                -map 0 -map 1:0 -c copy -c:s mov_text \
                -metadata:s:s:0 language=eng $DISP_ARGS -movflags +faststart \
                "$tmp_out" >/dev/null 2>&1 && mv -f "$tmp_out" "$OUTDIR/${name}.mp4"
              echo "Added OCR'd English subtitles (VobSub->SRT) to ${name}.mp4"
            else
              echo "Warning: OCR step did not produce SRT. Consider manual OCR or backfill." >&2
            fi
          else
            echo "Note: tesseract is not installed; cannot OCR VobSub to SRT automatically. Install via 'brew install tesseract sub2srt'." >&2
          fi
        else
          echo "Warning: Could not extract VobSub (idx/sub) for OCR." >&2
        fi
      elif [ "${ENG_IMAGE_CODEC:-}" = "hdmv_pgs_subtitle" ]; then
        # Blu-ray PGS -> VobSub (via bdsup2sub), then OCR via sub2srt + tesseract
        if (command -v bdsup2sub >/dev/null 2>&1) && (command -v sub2srt >/dev/null 2>&1) && (command -v tesseract >/dev/null 2>&1); then
          sup_path="$OUTDIR/${name}.eng.sup"
          out_base="$OUTDIR/${name}.eng_ocr"
          # Extract PGS (.sup)
          ffmpeg -y -i "$f" -map 0:${ENG_IMAGE_IDX} -c:s copy "$sup_path" >/dev/null 2>&1 || true
          # Convert PGS to VobSub (try both common CLI syntaxes)
          bdsup2sub "$sup_path" "$out_base.idx" >/dev/null 2>&1 || bdsup2sub -o "$out_base.idx" "$sup_path" >/dev/null 2>&1 || true
          if [ -f "$out_base.idx" ] && [ -f "$out_base.sub" ]; then
            sub2srt "$out_base.idx" >/dev/null 2>&1 || true
            if [ -f "$out_base.srt" ]; then
              DISP_ARGS=""
              [ "$SUBS_MARK_DEFAULT" -eq 1 ] && DISP_ARGS="-disposition:s:0 default"
              tmp_out="$OUTDIR/${name}.tmp.mp4"
              ffmpeg -y -i "$OUTDIR/${name}.mp4" -i "$out_base.srt" \
                -map 0 -map 1:0 -c copy -c:s mov_text \
                -metadata:s:s:0 language=eng $DISP_ARGS -movflags +faststart \
                "$tmp_out" >/dev/null 2>&1 && mv -f "$tmp_out" "$OUTDIR/${name}.mp4"
              echo "Added OCR'd English subtitles (PGS->VobSub->SRT) to ${name}.mp4"
            else
              echo "Warning: PGS OCR step did not produce SRT. Consider manual OCR or backfill." >&2
            fi
          else
            echo "Note: Could not convert PGS to VobSub. Install BDSup2Sub++ (command 'bdsup2sub')." >&2
          fi
        else
          echo "Note: PGS OCR requires 'bdsup2sub', 'sub2srt', and 'tesseract'. Install via Homebrew where available." >&2
        fi
      else
        echo "Note: English subtitles present but appear non-text (e.g., ${ENG_IMAGE_CODEC:-unknown}). MP4 cannot carry them as soft subs. Consider burn-in or OCR + backfill." >&2
      fi
    fi
  fi
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
