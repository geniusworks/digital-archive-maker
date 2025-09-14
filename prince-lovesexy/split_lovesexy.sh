#!/bin/bash

set -euo pipefail

input="${1:-Lovesexy.flac}"

if [[ ! -f "$input" ]]; then
  echo "Error: input file '$input' not found."
  exit 1
fi

# Tracks array: "Title|StartTime"
tracks=(
  "👁 No|00:00"
  "Alphabet St.|05:46"
  "Glam Slam|11:25"
  "Anna Stesia|16:33"
  "Dance On|21:31"
  "Lovesexy|25:15"
  "When 2 R in Love|31:04"
  "I Wish U Heaven|35:02"
  "Positivity|37:53"
)

mkdir -p "Lovesexy_Split"

total_tracks="${#tracks[@]}"

for (( i=0; i<total_tracks; i++ )); do
  line="${tracks[i]}"

  # Split title and start time on first '|'
  title="${line%%|*}"
  start="${line#*|}"

  # Sanitize title for safe filenames:
  # Replace only forbidden characters (/, \, :, *, ?, ", <, >, |) by underscore.
  # Keep spaces and Unicode characters including emoji intact.
  safe_title=$(echo "$title" | sed 's#[\/\\:*?"<>|]#_#g')

  tracknum=$(printf "%02d" $((i + 1)))
  outfile="Lovesexy_Split/${tracknum} - ${safe_title}.flac"

  if (( i < total_tracks - 1 )); then
    next_line="${tracks[i+1]}"
    next_start="${next_line#*|}"
    ffmpeg -hide_banner -loglevel error -y -ss "$start" -to "$next_start" -i "$input" -c copy "$outfile" || \
      echo "Failed to split track $tracknum: $title"
  else
    # Last track: go to end of file
    ffmpeg -hide_banner -loglevel error -y -ss "$start" -i "$input" -c copy "$outfile" || \
      echo "Failed to split track $tracknum: $title"
  fi
done

