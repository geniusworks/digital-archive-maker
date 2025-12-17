#!/bin/bash
set -euo pipefail

# Root folder to scan (defaults to current folder)
ROOT="${1:-.}"

# Mode: copy (safe, keeps original) or replace (overwrite .m3u)
MODE="copy"

echo "Scanning root: $ROOT"
echo "Mode: $MODE"
echo

find "$ROOT" -type f -iname "*.m3u" ! -iname "*.m3u8" | while read -r file; do
    # Output path
    out="${file%.m3u}.m3u8"
    tmp="$(mktemp)"

    echo "Processing:"
    echo "  $file"
    echo "  -> $out"

    # -------------------------------
    # Encoding normalization
    # -------------------------------
    iconv -f UTF-8 -t UTF-8 "$file" > "$tmp" 2>/dev/null || \
    iconv -f ISO-8859-1 -t UTF-8 "$file" > "$tmp"

    # -------------------------------
    # Normalize line endings (LF)
    # -------------------------------
    sed -i '' $'s/\r$//' "$tmp"

    # -------------------------------
    # Ensure #EXTM3U header
    # -------------------------------
    grep -q "^#EXTM3U" "$tmp" || sed -i '' '1i\
#EXTM3U
' "$tmp"

    # -------------------------------
    # Validate tracks relative to playlist folder
    # -------------------------------
    PLAYLIST_DIR="$(dirname "$file")"
    while read -r line; do
        [[ "$line" =~ ^# ]] && continue
        if [ ! -f "$PLAYLIST_DIR/$line" ]; then
            echo "  ⚠ Missing file: $line"
        fi
    done < "$tmp"

    # -------------------------------
    # Move temp -> final output
    # -------------------------------
    mv "$tmp" "$out"

    if [ "$MODE" = "replace" ]; then
        rm "$file"
    fi

    echo
done

echo "All playlists processed."