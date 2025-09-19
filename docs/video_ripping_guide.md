# DVD/Blu-ray Ripping Guide (MakeMKV + HandBrakeCLI)

This guide documents a straightforward, automation-friendly workflow for backing up non-DMCA-protected DVDs and Blu-rays for personal use. It complements the CD workflow described in `docs/cd_ripping_guide.md`.

Tip: This repository centralizes output paths via `.env` using `RIPS_ROOT` (see `.env.sample`). By default, `RIPS_ROOT` is `/Volumes/Data/Media/Rips`.

---

## Prerequisites
- macOS
- Install all video tools with one command:
  ```bash
  make install-video-deps
  ```
  This installs: HandBrakeCLI, ffmpeg/ffprobe, jq, tesseract, mkvtoolnix, and links makemkvcon.

- Install MakeMKV manually:
  - Download: https://www.makemkv.com/download/
  - Drag `MakeMKV.app` to `/Applications`
  - The `make install-video-deps` command will link the CLI automatically

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
  ./bin/rip_video.sh        # auto-detects disc type
  ./bin/rip_video.sh dvd    # or bluray (explicit)
  ```
- Makefile target:
  ```bash
  make rip-video            # auto-detects disc type
  make rip-video TYPE=dvd   # or TYPE=bluray (explicit)
  ```
  - **Auto-detection**: The script now automatically detects DVD vs Blu-ray discs using `drutil` and `makemkvcon`. You can still override with explicit `TYPE` if needed.
  - If you don't provide `TITLE`/`YEAR` and you're in an interactive terminal, the script will offer to organize after transcoding and prompt you for Title and Year.
  - In non-interactive contexts (e.g., CI), no prompt appears and only the staging folder is produced.

## Auto-organize to Movies/Title (Year)
To rip and automatically place the main feature into a Plex/Jellyfin-friendly folder:

```bash
make rip-movie TITLE="Movie Name" YEAR=1999    # auto-detects disc type
make rip-movie TYPE=dvd TITLE="Movie Name" YEAR=1999    # explicit type
```

- The script picks the largest MP4 as the main feature and moves it to:
  - `${RIPS_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`
- Extras/previews remain in the title-named (if Title/Year known) or date-stamped staging folder under `${RIPS_ROOT}/DVDs/` or `${RIPS_ROOT}/Blurays/`.

You can adjust the minimum title length MakeMKV considers with `MINLENGTH` (in seconds):

```bash
MINLENGTH=1800 make rip-movie TITLE="Movie Name" YEAR=1999
```

To organize into a different category folder (default is `Movies`), set `DEST_CATEGORY`:

```bash
DEST_CATEGORY=Films make rip-movie TITLE="Movie Name" YEAR=1999
```

## Audio/subtitle language handling (English preference)
When the default audio track is not English, the helper script will, by default, pause and prompt you to choose how to proceed. No environment variable is required for this default behavior.

To guarantee inclusion when available, the script post-muxes any English text-based subtitles (SubRip/ASS/SSA/Text/WebVTT) from the source MKV into the final MP4 after encoding. This requires `ffmpeg` (for both `ffmpeg` and `ffprobe`) and `jq`.

- Interactive (default when attached to a terminal):
  - After probing the MKV, if default audio is not English and an English audio or subtitle stream is present, you’ll be prompted to choose:
    - `[a]` Use English audio (if available)
    - `[s]` Add English subtitles (if available)
    - `[k]` Keep as-is

- Non-interactive or to override the default policy, use `AUDIO_SUBS_POLICY`:
  ```bash
  # Prefer English audio if present; else English subs if present; else keep
  AUDIO_SUBS_POLICY=prefer-audio make rip-movie TITLE="Movie" YEAR=1999

  # Prefer adding English subtitles if present; else prefer English audio if present; else keep
  AUDIO_SUBS_POLICY=prefer-subs make rip-movie TITLE="Movie" YEAR=1999

  # Keep streams as-is (no prompt)
  AUDIO_SUBS_POLICY=keep make rip-movie TITLE="Movie" YEAR=1999
  ```

Notes:
- Default policy is `keep` (prompt when interactive; leave streams as-is when not interactive).
- Set `AUDIO_SUBS_POLICY=prefer-audio` to automatically pick English audio (fallback to English subs), or `prefer-subs` to prioritize subs, or `keep` to keep streams as-is with no prompt.

Implementation details:
- English audio selection uses HandBrakeCLI options: `--audio-lang-list eng --first-audio`.
- English subtitles are muxed into the MP4 after encode (copy video/audio, `-c:s mov_text`). If you choose subtitles, the track is marked default; otherwise it is included but not defaulted.
- **Image-based subtitle handling**: If only image-based subtitles (VobSub/PGS) exist, the script will extract them and provide guidance for manual OCR using tools like Subtitle Edit. Use the `vobsub-to-srt` helper for placeholder SRT creation.

## Backfill English subtitles into existing MP4s
Use the provided helper to mux English soft subtitles from your archival MKVs into an existing MP4 without re-encoding video/audio.

- Makefile target (recommended):
  ```bash
  make backfill-subs \
    SRC_DIR="${RIPS_ROOT}/DVDs/Movie Name (Year)" \
    DST_DIR="${RIPS_ROOT}/Movies/Movie Name (Year)" \
    [INPLACE=yes] [DEFAULT=yes]
  ```

- What it does:
  - Picks the largest MKV in `SRC_DIR`.
  - Finds the MP4 in `DST_DIR` that matches the folder name (or the only MP4 present).
  - Detects the first English text subtitle stream (SubRip/ASS/SSA/Text/WebVTT).
  - Muxes it into the MP4 as a soft subtitle (`mov_text`).
  - By default, writes a new file with suffix `.en-subs.mp4` next to the original.
  - Options:
    - `INPLACE=yes` replaces the original MP4 after backing it up to `.bak`.
    - `DEFAULT=yes` marks the English subtitle track as default.

Notes:
- Requires `ffprobe`/`ffmpeg` and `jq`.
- **Image-based subtitle handling**: If your MKV only has image-based subs (VobSub/PGS), the script will:
  - Extract the subtitle files to a temporary location
  - Provide clear instructions for manual OCR using Subtitle Edit
  - You can use the `vobsub-to-srt` helper to create placeholder SRT files for immediate muxing:
    ```bash
    make vobsub-to-srt FILE=".backfill_ocr_12345.idx"
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
