#!/bin/bash
# Set EXPLICIT tag for FLAC files
# Usage: set-explicit.sh <path> <value> [--album]
# path: path to FLAC file or album directory
# value: Yes, No, or Unknown
# --album: apply to all FLAC files in directory

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <path> <value> [--album]"
    echo "  path: path to FLAC file or album directory"
    echo "  value: Yes, No, or Unknown"
    echo "  --album: apply to all FLAC files in directory"
    exit 1
fi

PATH="$1"
VALUE="$2"
ALBUM_MODE="$3"

if [ "$VALUE" != "Yes" ] && [ "$VALUE" != "No" ] && [ "$VALUE" != "Unknown" ]; then
    echo "Error: value must be Yes, No, or Unknown"
    exit 1
fi

if [ "$ALBUM_MODE" = "--album" ]; then
    # Album mode: process all FLAC files in directory
    if [ ! -d "$PATH" ]; then
        echo "Error: $PATH is not a directory"
        exit 1
    fi
    
    echo "Setting EXPLICIT=$VALUE for all FLAC files in: $PATH"
    count=0
    for flac in "$PATH"/*.flac; do
        if [ -f "$flac" ]; then
            old_value=$(metaflac --show-tag=EXPLICIT "$flac" 2>/dev/null | sed 's/^EXPLICIT=//' || echo "None")
            metaflac --set-tag=EXPLICIT="$VALUE" "$flac"
            echo "  $(basename "$flac"): $old_value → $VALUE"
            ((count++))
        fi
    done
    echo "Updated $count files"
else
    # Single file mode
    if [ ! -f "$PATH" ] || [[ "$PATH" != *.flac ]]; then
        echo "Error: $PATH is not a FLAC file (use --album for directories)"
        exit 1
    fi
    
    old_value=$(metaflac --show-tag=EXPLICIT "$PATH" 2>/dev/null | sed 's/^EXPLICIT=//' || echo "None")
    metaflac --set-tag=EXPLICIT="$VALUE" "$PATH"
    echo "$(basename "$PATH"): $old_value → $VALUE"
fi
