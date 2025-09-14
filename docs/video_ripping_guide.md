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

   # If using the repo script/Makefile, the staging folder will prefer
  # Title (Year) when provided/prompted; otherwise it falls back to a date.
  STAMP=$(date "+%Y-%m-%d")
  OUTDIR="${RIPS_ROOT:-/Volumes/Data/Media/Rips}/$DISCDIR/$STAMP"
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
  - If you don't provide `TITLE`/`YEAR` and you're in an interactive terminal, the script will offer to organize after transcoding and prompt you for Title and Year.
  - In non-interactive contexts (e.g., CI), no prompt appears and only the staging folder is produced.

## Auto-organize to Movies/Title (Year)
To rip and automatically place the main feature into a Plex/Jellyfin-friendly folder:

```bash
make rip-movie TYPE=dvd TITLE="Movie Name" YEAR=1999
```

- The script picks the largest MP4 as the main feature and moves it to:
  - `${RIPS_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`
- Extras/previews remain in the title-named (if Title/Year known) or date-stamped staging folder under `${RIPS_ROOT}/DVDs/` or `${RIPS_ROOT}/Blurays/`.

You can adjust the minimum title length MakeMKV considers with `MINLENGTH` (in seconds):

```bash
MINLENGTH=1800 make rip-movie TYPE=dvd TITLE="Movie Name" YEAR=1999
```

To organize into a different category folder (default is `Movies`), set `DEST_CATEGORY`:

```bash
DEST_CATEGORY=Films make rip-movie TYPE=dvd TITLE="Movie Name" YEAR=1999
```

## Preflight and troubleshooting
The script now performs preflight checks and warns if helper tools are missing. If you see errors like `mmgplsrv` or `mmccextr` not found, create symlinks:

```bash
sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/mmgplsrv /usr/local/bin/mmgplsrv
sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/mmccextr /usr/local/bin/mmccextr
```

On first run, launch the GUI once to accept the EULA and set the drive region, and consider removing quarantine:

```bash
xattr -dr com.apple.quarantine /Applications/MakeMKV.app
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
