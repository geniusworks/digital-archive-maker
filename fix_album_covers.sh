#!/bin/bash

# Usage:
#   ./find_missing_covers.sh [/path/to/album/or/library]
#   Examples:
#     ./find_missing_covers.sh /Volumes/Data/Media/Library/CDs       # full scan
#     ./find_missing_covers.sh /Volumes/Data/Media/Library/CDs/U2/The Joshua Tree  # specific album
#   Defaults to current directory if no argument is given.

set -e

SEARCH_PATH="${1:-.}"

# Require jq
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed."
    exit 1
fi

process_album_dir() {
    local album_dir="$1"
    local album_name
    local artist_dir
    local artist_name

    if [[ -f "$album_dir/cover.jpg" ]]; then
        echo "✔ Already has cover: $album_dir"
        return
    fi

    album_name=$(basename "$album_dir")
    artist_dir=$(dirname "$album_dir")
    artist_name=$(basename "$artist_dir")

    if [[ "$artist_name" =~ ^(Unknown|Untitled)$ || "$album_name" =~ ^(Unknown|Untitled)$ ]]; then
        echo "✘ Skipping invalid: $artist_name - $album_name"
        return
    fi

    echo "→ Searching cover for: $artist_name - $album_name"

    # URL-encode
    q_artist=$(jq -rn --arg x "$artist_name" '$x|@uri')
    q_album=$(jq -rn --arg x "$album_name" '$x|@uri')

    mb_url="https://musicbrainz.org/ws/2/release/?query=artist:$q_artist%20release:$q_album&fmt=json&limit=1"
    release_json=$(curl -s "$mb_url")
    release_id=$(echo "$release_json" | jq -r '.releases[0].id // empty')

    if [[ -z "$release_id" ]]; then
        echo "  ✘ No MusicBrainz release found."
        return
    fi

    # Cover Art Archive URL
	cover_url="https://coverartarchive.org/release/$release_id/front.jpg"
	target_path="$album_dir/cover.jpg"

	# Download to a temp file first
	tmpfile=$(mktemp)

	if curl -sSL --fail -o "$tmpfile" "$cover_url"; then
	    if file "$tmpfile" | grep -q 'JPEG image data'; then
			if command -v magick &>/dev/null; then
			    magick "$tmpfile" -resize 1000x1000\> "$tmpfile"
			fi
	        mv "$tmpfile" "$target_path"
	        echo "  ✔ Downloaded cover: $target_path"
	    else
	        echo "  ✘ Downloaded file is not a valid JPEG"
	        rm -f "$tmpfile"
	    fi
	else
	    echo "  ✘ Cover not found on Cover Art Archive."
	    rm -f "$tmpfile"
	fi
}

if [[ -d "$SEARCH_PATH" ]]; then
	if find "$SEARCH_PATH" -maxdepth 1 -type f -name '*.flac' | grep -q .; then
	    # It's an album folder (contains FLACs) — process directly
	    process_album_dir "$SEARCH_PATH"
	else
	    # It's a library root or higher-level folder — scan recursively for album dirs missing cover.jpg
	    echo "📂 Scanning for albums missing cover.jpg under: $SEARCH_PATH"
	    found_any=false
	    # Find all directories under SEARCH_PATH
	    while IFS= read -r dir; do
	        # Check if directory contains FLAC files
	        if find "$dir" -maxdepth 1 -type f -name '*.flac' | grep -q .; then
	            # Check if cover.jpg is missing
	            if [[ ! -f "$dir/cover.jpg" ]]; then
	                found_any=true
	                process_album_dir "$dir"
	            fi
	        fi
	    done < <(find "$SEARCH_PATH" -type d)
	    if ! $found_any; then
	        echo "✔ No album folders missing cover.jpg found."
	    fi
	fi
else
    echo "Error: '$SEARCH_PATH' is not a valid directory"
    exit 1
fi