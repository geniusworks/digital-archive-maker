# DVD/Blu-ray Ripping Guide (MakeMKV + HandBrakeCLI)

This guide documents a straightforward, automation-friendly workflow for backing up non-DMCA-protected DVDs and Blu-rays for personal use. It complements the CD workflow described in `docs/cd_ripping_guide.md`.

See also: `docs/workflow_overview.md` for the end-to-end procedures (CDs → FLACs → tagging → sync, and DVD/Blu-ray → MP4s → organize → server).

Tip: This repository centralizes output paths via `.env` using `LIBRARY_ROOT` (see `.env.sample`). By default, `LIBRARY_ROOT` is `/Volumes/Data/Media/Library`.

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
  OUTDIR="${LIBRARY_ROOT:-/Volumes/Data/Media/Library}/$DISCDIR/$STAMP"
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
OUTDIR="${LIBRARY_ROOT:-/Volumes/Data/Media/Library}/$DISCDIR/$TITLE"
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
  - `${LIBRARY_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`
- Extras/previews remain in the title-named (if Title/Year known) or date-stamped staging folder under `${LIBRARY_ROOT}/DVDs/` or `${LIBRARY_ROOT}/Blurays/`.

You can adjust the minimum title length MakeMKV considers with `MINLENGTH` (in seconds):

```bash
MINLENGTH=1800 make rip-movie TITLE="Movie Name" YEAR=1999
```

To organize into a different category folder (default is `Movies`), set `DEST_CATEGORY`:

```bash
DEST_CATEGORY=Films make rip-movie TITLE="Movie Name" YEAR=1999
```

## Tag MP4 movie metadata (optional)
After ripping/encoding and organizing into `Movies/Title (Year)/Title (Year).mp4`, you can tag the MP4 with rich metadata (title, year, plot, genres, director, cast, rating, and artwork) using:

- Script: `bin/tag-movie-metadata.py`
- API keys:
  - `TMDB_API_KEY` (recommended; enables artwork)
  - `OMDB_API_KEY` (fallback)
  - Scripts auto-load `.env` at the repo root via `python-dotenv` when available.

If no API keys are set, tagging scripts will still run, but online lookups are disabled and the scripts will only use local data (existing file tags, caches, and any manual overrides).

Example:
```bash
python3 bin/tag-movie-metadata.py "${LIBRARY_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4" --imdb-id tt0123456 --dry-run --verbose
python3 bin/tag-movie-metadata.py "${LIBRARY_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4" --imdb-id tt0123456

# Recursively tag an entire Movies folder (tries to infer Title/Year from folder/file names).
# By default, only missing tags/artwork are filled.
python3 bin/tag-movie-metadata.py "${LIBRARY_ROOT}/Movies" --recursive --dry-run --verbose
python3 bin/tag-movie-metadata.py "${LIBRARY_ROOT}/Movies" --recursive

# Overwrite existing tags/artwork (use carefully)
python3 bin/tag-movie-metadata.py "${LIBRARY_ROOT}/Movies" --recursive --force
```

## Handling multi-feature discs (double features, TV movies, etc.)
Some discs ship with two full movies or a mini-series. Use these tips when ripping:

- **Rip both long titles in one pass**. Increase `MINLENGTH` so short extras are skipped while the main features are kept. Example:
  ```bash
  MINLENGTH=3000 make rip-video TYPE=dvd TITLE="Psycho Double Feature" YEAR=1985
  ```
  This writes every qualifying `.mkv` to `${LIBRARY_ROOT}/DVDs/Psycho Double Feature (1985)/` for later processing.

- **Identify which MKV is which**. Durations usually match published runtimes. From the staging folder:
  ```bash
  cd "${LIBRARY_ROOT}/DVDs/Psycho Double Feature (1985)"
  for f in *.mkv; do
    echo "== $f =="
    ffprobe -v error -show_entries format=duration:format_tags=title -of json "$f"
  done
  ```
  Compare the seconds reported by `ffprobe` to runtime listings to label each feature accurately.

- **Encode each feature with its own TITLE/YEAR**. Run `HandBrakeCLI` once per `.mkv`, writing to the standard movie folders:
  ```bash
  HB_OPTS=(
    -e x264 -q 20 --encoder-preset medium --optimize
    --audio-lang-list eng --first-audio
    --audio-copy-mask ac3,eac3,dts --audio-fallback aac
  )

  mkdir -p "${LIBRARY_ROOT}/Movies/Psycho III (1986)"
  HandBrakeCLI \
    -i "A3_t00.mkv" \
    -o "${LIBRARY_ROOT}/Movies/Psycho III (1986)/Psycho III (1986).mp4" \
    "${HB_OPTS[@]}"
  ```
  Repeat for the second feature (e.g., `Psycho IV The Beginning (1990)`), adjusting input filenames and target folders.

- **Backfill subtitles per film**. After encoding, call the helper twice, pointing `SRC_DIR` to the shared staging folder but `DST_DIR` to each movie folder:
  ```bash
  make backfill-subs \
    SRC_DIR="${LIBRARY_ROOT}/DVDs/Psycho Double Feature (1985)" \
    DST_DIR="${LIBRARY_ROOT}/Movies/Psycho III (1986)" \
    INPLACE=yes DEFAULT=yes

  make backfill-subs \
    SRC_DIR="${LIBRARY_ROOT}/DVDs/Psycho Double Feature (1985)" \
    DST_DIR="${LIBRARY_ROOT}/Movies/Psycho IV The Beginning (1990)" \
    INPLACE=yes DEFAULT=yes
  ```

- **Cleanup**. Once both MP4s are confirmed, archive or remove any unused `.mkv` or `.backfill_ocr_*` files.

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

  # Force burn-in of English image-based subtitles (overrides auto-burn)
  AUDIO_SUBS_POLICY=prefer-burned make rip-movie TITLE="Movie" YEAR=1999

  # Keep streams as-is (no prompt, no auto-burn)
  AUDIO_SUBS_POLICY=keep make rip-movie TITLE="Movie" YEAR=1999
  ```

Notes:
- **Automatic burn-in**: For DVDs with non-English default audio and English image-based subtitles (VobSub/PGS) but no text-based English subs, the script automatically burns in the English subtitles. This ensures captions are always visible without manual intervention.
- Default policy is `keep` (prompt when interactive; auto-burn applies when non-interactive if conditions are met).
- Set `AUDIO_SUBS_POLICY=prefer-audio` to automatically pick English audio (fallback to English subs), `prefer-subs` to prioritize soft subs, `prefer-burned` to force burn-in even when text subs exist, or `keep` to suppress both prompts and auto-burn.

Implementation details:
- English audio selection uses HandBrakeCLI options: `--audio-lang-list eng --first-audio`.
- English text-based subtitles are muxed into the MP4 after encode (copy video/audio, `-c:s mov_text`). If you choose subtitles, the track is marked default; otherwise it is included but not defaulted.
- English image-based subtitles (VobSub/PGS) are automatically burned into the video during encode with `--subtitle N --subtitle-burned` when conditions are met (non-English audio, no soft subs available). This makes captions permanently visible.
  - **Track numbering**: HandBrake numbers subtitle tracks sequentially (1, 2, 3...) based on their position in the file, not by ffprobe's stream index. The script correctly calculates the HandBrake track number by finding the position of the English subtitle among all subtitle streams.
- **Manual OCR fallback**: If auto-burn is disabled or fails, the script will extract image-based subtitles and provide guidance for manual OCR using tools like Subtitle Edit. Use the `vobsub-to-srt` helper for placeholder SRT creation.

## Backfill English subtitles into existing MP4s
Use the provided helper to mux English soft subtitles from your archival MKVs into an existing MP4 without re-encoding video/audio.

- Makefile target (recommended):
  ```bash
  make backfill-subs \
    SRC_DIR="${LIBRARY_ROOT}/DVDs/Movie Name (Year)" \
    DST_DIR="${LIBRARY_ROOT}/Movies/Movie Name (Year)" \
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

### MakeMKV setup
The script performs preflight checks and warns if helper tools are missing. If you see errors like `mmgplsrv` or `mmccextr` not found, create symlinks:

```bash
sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/mmgplsrv /usr/local/bin/mmgplsrv
sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/mmccextr /usr/local/bin/mmccextr
```

On first run, launch the GUI once to accept the EULA and set the drive region, and consider removing quarantine:

```bash
xattr -dr com.apple.quarantine /Applications/MakeMKV.app
```

### Subtitle burn-in not working
If automatic subtitle burn-in fails or subtitles don't appear in the output:

1. **Verify subtitle detection**: Check that English subtitles are present:
   ```bash
   ffprobe -v error -select_streams s -show_entries stream=index,codec_name:stream_tags=language -of json "file.mkv" | jq .
   ```

2. **Check HandBrake scan**: Verify the subtitle track number:
   ```bash
   HandBrakeCLI --input "file.mkv" --title 0 --scan 2>&1 | grep -A 10 "subtitle tracks"
   ```

3. **Manual burn-in**: If auto-burn didn't trigger, use the explicit command:
   ```bash
   HandBrakeCLI -i "file.mkv" -o "output.mp4" \
     -e x264 -q 20 --optimize \
     --subtitle <TRACK_NUM> --subtitle-burned
   ```
   Replace `<TRACK_NUM>` with the track number from the HandBrake scan (e.g., 2 for "2, English (VOBSUB)").

4. **Recent fix**: A bug was fixed in Oct 2025 where the script incorrectly calculated HandBrake track numbers. Ensure you're using the latest version of `bin/rip_video.sh`.

---

## Metadata notes
- Automatic rich metadata for video is not included; consider renaming files manually or using a post-processor such as FileBot or tinyMediaManager.
- For Plex/Jellyfin/Emby, follow their naming conventions for movies and TV episodes to enable scraper metadata.

## Recommended naming for media servers
- Movies:
  ```
  /Volumes/Data/Media/Library/Movies/Movie Name (Year)/Movie Name (Year).mp4
  ```
- TV:
  ```
  /Volumes/Data/Media/Library/TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.mp4
  ```

See `docs/media_server_setup.md` for more complete examples and tips.

---

## Known issues and fixes

### HandBrake subtitle track numbering (Fixed: Oct 2025)
**Issue**: Auto-burn was calculating incorrect subtitle track numbers, causing burn-in to fail or select the wrong track.

**Root cause**: HandBrake numbers subtitle tracks sequentially (1, 2, 3...) based on their position in the file, NOT based on ffprobe's stream index values. For example:
- ffprobe shows: stream index 4 (Chinese), stream index 5 (English)
- HandBrake shows: track 1 (Chinese), track 2 (English)
- Old script calculated: 5 + 1 = track 6 ❌
- Correct calculation: track 2 ✓

**Fix**: The script now uses `ENG_IMAGE_HB_TRACK` which correctly calculates the HandBrake track number by finding the position of the English subtitle among all subtitle streams (1-indexed).

**Impact**: Auto-burn now works correctly for all DVD/Blu-ray configurations.

---

## Legal
This workflow is intended for personal backups of media you own, for local personal use only. Respect laws in your jurisdiction and the license terms of the tools used.
