# DVD/Blu-ray Ripping Guide (MakeMKV + HandBrakeCLI)

This guide documents a straightforward, automation-friendly workflow for backing up non-DMCA-protected DVDs and Blu-rays for personal use. It complements the CD workflow described in `docs/cd_ripping_guide.md`.

Tip: This repository centralizes output paths via `.env` using `RIPS_ROOT` (see `.env.sample`). By default, `RIPS_ROOT` is `/Volumes/Data/Media/Rips`.

---

## Prerequisites
- macOS
- Install via Homebrew:
  ```bash
  brew install handbrake ffmpeg
  ```
- Install MakeMKV manually:
  - Download: https://www.makemkv.com/download/
  - Drag `MakeMKV.app` to `/Applications`
  - Enable CLI:
    ```bash
    sudo ln -s /Applications/MakeMKV.app/Contents/MacOS/makemkvcon /usr/local/bin/makemkvcon
    ```

Note: This guide avoids Bash 4+ features to remain compatible with macOS's default shell environments.

---

## Workflow

1. Insert your disc.
2. Choose a disc type and create an output folder.

   Example (POSIX-compatible):
   ```bash
   # Set disc type: one of dvd|bluray
   DISCTYPE="dvd"   # or: bluray

   # Map to a human-friendly folder name without relying on Bash 4+ case modifiers
   case "$DISCTYPE" in
     dvd)   DISCDIR="DVDs" ;;
     bluray) DISCDIR="Blurays" ;;
     *) echo "Unknown DISCTYPE: $DISCTYPE" >&2; exit 1 ;;
   esac

   TITLE=$(date "+%Y-%m-%d")
   OUTDIR="${RIPS_ROOT:-/Volumes/Data/Media/Rips}/$DISCDIR/$TITLE"
   mkdir -p "$OUTDIR"
   ```

3. Rip titles to MKV using MakeMKV CLI:
   ```bash
   makemkvcon mkv disc:0 all "$OUTDIR"
   ```

4. Transcode each MKV to optimized MP4 with HandBrakeCLI (H.264):
   ```bash
   for file in "$OUTDIR"/*.mkv; do
     [ -e "$file" ] || continue
     BASENAME=$(basename "$file" .mkv)
     HandBrakeCLI \
       -i "$file" \
       -o "$OUTDIR/${BASENAME}.mp4" \
       -e x264 -q 22 -B 160 --optimize
   done
   ```

5. Optional: keep both MKV (lossless container) and MP4 (space-efficient), or delete MKV after verifying the MP4.

---

## Automation script (optional)
Save as `~/rip_video.sh` and make executable `chmod +x ~/rip_video.sh`:
```bash
#!/bin/sh
set -eu

printf "Select disc type: 1) DVD  2) Blu-ray\n" >&2
printf "Choice: " >&2
read -r choice
case "$choice" in
  1) DISCDIR="DVDs" ;;
  2) DISCDIR="Blurays" ;;
  *) echo "Invalid option" >&2; exit 1 ;;
 esac

TITLE=$(date "+%Y-%m-%d")
OUTDIR="${RIPS_ROOT:-/Volumes/Data/Media/Rips}/$DISCDIR/$TITLE"
mkdir -p "$OUTDIR"

makemkvcon mkv disc:0 all "$OUTDIR"

for f in "$OUTDIR"/*.mkv; do
  [ -e "$f" ] || continue
  name=$(basename "$f" .mkv)
  HandBrakeCLI -i "$f" -o "$OUTDIR/${name}.mp4" -e x264 -q 22 -B 160 --optimize
done

echo "Done: $OUTDIR"
```

## Repo helper script
This repository provides a ready-to-use helper and a Makefile target:

- Direct script:
  ```bash
  ./bin/rip_video.sh dvd    # or bluray
  ```
- Makefile target:
  ```bash
  make rip-video TYPE=dvd   # or TYPE=bluray
  ```

---

## Metadata notes
- Automatic rich metadata for video is not included; consider renaming files manually or using a post-processor such as FileBot or tinyMediaManager.
- For Plex/Jellyfin/Emby, follow their naming conventions for movies and TV episodes to enable scraper metadata.

## Recommended naming for media servers
- Movies:
  ```
  /Volumes/Data/Media/Rips/Movies/Movie Name (Year)/Movie Name (Year).mp4
  ```
- TV:
  ```
  /Volumes/Data/Media/Rips/TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.mp4
  ```

See `docs/media_server_setup.md` for more complete examples and tips.

---

## Legal
This workflow is intended for personal backups of media you own, for local personal use only. Respect laws in your jurisdiction and the license terms of the tools used.
