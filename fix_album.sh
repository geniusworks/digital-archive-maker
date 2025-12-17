#!/bin/bash

set -e

# Capture the path to this script early before changing directories
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

album_path="$1"
if [[ ! -d "$album_path" ]]; then
  echo "Usage: $0 /path/to/Artist/Album"
  exit 1
fi

cd "$album_path" || exit 1

# Extract artist and album name from folder path
album_name=$(basename "$album_path")
artist_name=$(basename "$(dirname "$album_path")")

# URL-encode for query
q_artist=$(jq -rn --arg x "$artist_name" '$x|@uri')
q_album=$(jq -rn --arg x "$album_name" '$x|@uri')

# Query MusicBrainz
echo "Searching MusicBrainz for $artist_name - $album_name ..."
mb_url="https://musicbrainz.org/ws/2/release/?query=artist:$q_artist%20release:$q_album&fmt=json&limit=1"
release=$(curl -s "$mb_url")

release_id=$(echo "$release" | jq -r '.releases[0].id // empty')
if [[ -z "$release_id" ]]; then
  echo "No matching release found."
  exit 1
fi

# Get tracklist for release
tracklist_url="https://musicbrainz.org/ws/2/release/$release_id?inc=recordings&fmt=json"
tracks_json=$(curl -s "$tracklist_url")

titles=()
while IFS= read -r line; do
  titles+=("$line")
done < <(echo "$tracks_json" | jq -r '.media[].tracks[].title')

count_files=$(find . -maxdepth 1 -name '*.flac' | wc -l)
count_titles=${#titles[@]}

if [[ "$count_files" -ne "$count_titles" ]]; then
  echo "File count ($count_files) does not match track count ($count_titles)."
  exit 1
fi

# Prepare M3U8 file
playlist_file="${album_name}.m3u8"
printf '%s\n' '#EXTM3U' > "$playlist_file"  # truncate or create

# Rename files and write to M3U8
i=0
for file in *.flac; do
  num=$(printf "%02d" $((i + 1)))
  title="${titles[$i]}"
  clean_title=$(echo "$title" | tr '/' '_' | tr -cd '[:alnum:] _-')
  newname="${num} - ${clean_title}.flac"

  if [[ "$file" != "$newname" ]]; then
    mv -i -- "$file" "$newname"
    echo "Renamed: $file -> $newname"
  fi

  echo "$newname" >> "$playlist_file"
  ((i++))
done

# Clean up old/placeholder playlist if it exists
if [[ -f "Unknown Album.m3u" ]]; then
  rm -f "Unknown Album.m3u"
  echo "Removed stale playlist: Unknown Album.m3u"
fi
if [[ -f "Unknown Album.m3u8" ]]; then
  rm -f "Unknown Album.m3u8"
  echo "Removed stale playlist: Unknown Album.m3u8"
fi

echo "Playlist created: $playlist_file"

# Run fix_metadata.py using the original script directory
echo "Running metadata fix script..."
"$script_dir/fix_metadata.py" "$album_path" --fix

# Run find_missing_covers.sh using the original script directory
echo "Running covert art fix script..."
"$script_dir/fix_album_covers.sh" "$album_path"
