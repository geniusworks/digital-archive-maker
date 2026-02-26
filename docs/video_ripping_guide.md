# Video Disc Ripping Guide

Complete workflow for ripping DVDs and Blu-rays to high-quality MP4 files with proper metadata and organization.

> **📚 See Also:** [Video Workflows](video_workflows.md) for detailed scenario diagrams and decision trees  
> **Prerequisites:** Follow the [Quick Start Guide](../QUICKSTART.md) for initial setup.  
> **Before running Python scripts:** Activate virtual environment with `source venv/bin/activate`

---

## 🎬 Quick Start

**For all video processing, use the unified command:**

```bash
# English films (DVD or Blu-ray)
make rip-movie TITLE="Movie Title" YEAR=2023 TYPE=bluray

# Foreign films with subtitle burning
BURN_SUBTITLES=true make rip-movie TITLE="Foreign Film" YEAR=2023 TYPE=bluray

# Process existing MKV files
make rip-movie TITLE="Movie Title" YEAR=2023 TYPE=bluray
```

**📖 For detailed workflows, scenarios, and diagrams, see [Video Workflows](video_workflows.md)**

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

## 🎯 Key Features

### ✅ Universal MP4 Output
- **DVD and Blu-ray:** Both output to MP4 format
- **External SRT subtitles:** Jellyfin-compatible
- **Foreign film support:** Optional subtitle burning
- **Streaming optimization:** Web-ready files

### ✅ Intelligent Processing
- **Smart compression:** Only re-encode when needed (>10GB)
- **Existing file handling:** Works with already-ripped MKV files
- **Error resilience:** Graceful handling of missing discs
- **Automatic organization:** Proper folder structure

### ✅ Subtitle Management
- **Interactive prompt:** Choose subtitle processing before ripping starts
- **English films:** External SRT files (auto-extracted for soft subs)
- **Foreign films:** Option to burn subtitles or extract externally
- **PGS subtitles:** Option to burn or convert with OCR (future feature)
- **Jellyfin ready:** Auto-detected subtitle files

---

## 🎛️ Control Variables

| Variable | Values | Effect |
|----------|--------|--------|
| `TYPE` | `dvd` | `bluray` | Disc type detection |
| `FORCE_ALL_TRACKS` | `true` | `false` (default) | Rip all titles vs main feature |
| `STREAMING_OPTIMIZE` | `true` (default) | `false` | Apply web optimization |

---

## 🎬 Interactive Subtitle Processing

When you run a rip, the script will analyze the disc and present you with subtitle options **before** ripping starts:

### Auto-Skip (Simple Case)
If the disc has English audio + English soft subtitles, the script automatically proceeds:
```
🎬 Detected: English movie with English audio and soft subtitles
  → Will automatically extract English soft subtitles to .srt file
```

### Interactive Prompt (Complex Cases)
For foreign audio, PGS subtitles, or other complex cases:
```
🎬 Disc Analysis (Main Feature)
==================================================
🎵 Audio Tracks: 3
   Track 0: ENG (dts)
   Track 1: ENG (ac3)
   Track 2: FRE (ac3)

📝 Subtitle Tracks: 2
   Track 0: ENG (hdmv_pgs_subtitle)
   Track 1: FRE (hdmv_pgs_subtitle)

🎯 Recommended Action: standard_mp4
==================================================
Available Options:
👉 1) Standard MP4 (no subtitle processing)
  4) Burn image subtitles into video (hard subtitles)
  5) Convert image subtitles to text file with OCR (future feature)
  6) Skip all subtitle processing

Select option [1-4, default=standard_mp4]:
```

### Options Explained
- **Soft subtitles:** External .srt files that can be toggled on/off in players
- **Hard subtitles:** Burned into video permanently, always visible
- **PGS:** Image-based subtitles (common on Blu-rays)

---

## 📁 File Organization

**Success Pattern:**
```
/Users/martin/Movies/Rips/
├── Blurays/Movie Title (Year)/          # Source files
│   └── Movie Title (Year).mkv           # Original rip
└── Movies/Movie Title (Year)/           # Final destination
    ├── Movie Title (Year).mp4           # Compressed video
    └── Movie Title (Year).en.srt        # External subtitles
```

---

## 🚨 Common Scenarios

### English Film (DVD or Blu-ray)
```bash
make rip-movie TITLE="The Goonies" YEAR=1985 TYPE=bluray
```
**Result:** MP4 + external SRT subtitles

### Foreign Film with English Subtitles
```bash
BURN_SUBTITLES=true make rip-movie TITLE="Amélie" YEAR=2001 TYPE=bluray
```
**Result:** MP4 with burned subtitles + external SRT

### Existing Large MKV File
```bash
make rip-movie TITLE="Silent Running" YEAR=1972 TYPE=bluray
```
**Result:** Compressed MP4 + external SRT (if >10GB)

---

## 🔧 Advanced Options

### Process All Tracks (Special Features)
```bash
FORCE_ALL_TRACKS=true make rip-movie TITLE="Special Film" YEAR=2023 TYPE=dvd
```

### Disable Streaming Optimization
```bash
STREAMING_OPTIMIZE=false make rip-movie TITLE="Film" YEAR=2023 TYPE=bluray
```

---

## 📞 Troubleshooting

### Common Issues
- **"No disc found"** - Insert disc or check MKV files in correct location
- **"Silent HandBrake failure"** - Check file permissions and disk space
- **"No subtitles extracted"** - Source may not have English subtitle tracks
- **"File too large"** - Script will automatically re-compress files >10GB

### Getting Help
- **Detailed workflows:** See [Video Workflows](video_workflows.md)
- **Log output:** Check console messages for specific errors
- **Prerequisites:** Ensure `make install-video-deps` was run
- **MakeMKV:** Verify installation in `/Applications/`

---

## 📚 Related Documentation

- **[Video Workflows](video_workflows.md)** - Detailed scenarios and decision trees
- **[Workflow Overview](workflow_overview.md)** - General system workflows
- **[Media Server Setup](media_server_setup.md)** - Jellyfin configuration
- **[Quick Start Guide](../QUICKSTART.md)** - Initial setup instructions
- **Flexible output directory** (provide path or use default)

### Option 2: Manual Step-by-Step Workflow
For more control over the process:

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
       -e x264 -q 28 --preset "Fast 1080p30" -B 160 --optimize
   done
   ```
   *Note: Uses faster encoding settings (quality 28, Fast 1080p30) for better speed.*

5. Optional: keep both MKV (lossless container) and MP4 (space-efficient), or delete MKV after verifying the MP4.

---

## Repo helper script
This repository provides a ready-to-use helper and a Makefile target:

- Direct script:
  ```bash
  python3 bin/video/rip_video.py        # auto-detects disc type
  python3 bin/video/rip_video.py dvd    # or bluray (explicit)
  ```
- Makefile target:
  ```bash
  make rip-video            # auto-detects disc type
  make rip-video TYPE=dvd   # or TYPE=bluray (explicit)
  ```
  - **Auto-detection**: The script now automatically detects DVD vs Blu-ray discs using `drutil` and `makemkvcon`. You can still override with explicit `TYPE` if needed.
  - The script is non-interactive (no prompts). To enable auto-organization, provide `TITLE` and `YEAR` via the environment/Makefile.

## Auto-organize to Movies/Title (Year)
To rip and automatically place the main feature into a Plex/Jellyfin-friendly folder:

```bash
make rip-movie TITLE="Movie Name" YEAR=1999    # auto-detects disc type, main feature only
make rip-movie TYPE=dvd TITLE="Movie Name" YEAR=1999    # explicit type
```

- **Smart track selection**: Automatically focuses on the largest file (main feature) for faster ripping
- **Smart disc ripping**: Only rips the main feature from Blu-ray discs (skips extras during initial read)
- The script picks the largest MP4 as the main feature and moves it to:
  - `${LIBRARY_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`
- Extras/previews remain in the title-named (if Title/Year known) or date-stamped staging folder under `${LIBRARY_ROOT}/DVDs/` or `${LIBRARY_ROOT}/Blurays/`.

### Process All Tracks (Optional)
If you need to rip ALL tracks instead of just the main feature:

```bash
make rip-movie-all TITLE="Movie Name" YEAR=1999    # processes all tracks
# Or set environment variable:
FORCE_ALL_TRACKS=true make rip-movie TITLE="Movie Name" YEAR=1999
```

### How Smart Disc Ripping Works
The script now intelligently analyzes Blu-ray discs before ripping:

1. **Disc Analysis**: Scans all titles and their durations
2. **Main Feature Detection**: Identifies the longest track (typically the main movie)
3. **Selective Ripping**: Only extracts the main feature by default
4. **Time Savings**: Skips ripping extras, previews, and special features

**Example Output:**
```
Scanning for main feature (longest track)...
Found main feature: Title 0 (02:18:45)
Skipping 7 shorter tracks
```

This approach can reduce disc reading time by **60-80%** for typical Blu-ray movies.

### Encoding Speed Options
Control encoding speed vs quality with environment variables:

```bash
# Faster encoding (default, good for most movies)
HB_QUALITY=28 HB_PRESET="Fast 1080p30" make rip-movie TITLE="Movie" YEAR=2024

# Higher quality (slower)
HB_QUALITY=22 HB_PRESET="Medium 1080p30" make rip-movie TITLE="Movie" YEAR=2024

# Very fast (lower quality)
HB_QUALITY=32 HB_PRESET="Very Fast 1080p30" make rip-movie TITLE="Movie" YEAR=2024
```

### Streaming Optimization (Jellyfin/Plex)
For better performance with media servers, enable streaming optimizations:

```bash
# Enable streaming optimization (default)
STREAMING_OPTIMIZE=true make rip-movie TITLE="Movie" YEAR=2024

# Disable if you have issues (faster encoding, slower loading)
STREAMING_OPTIMIZE=false make rip-movie TITLE="Movie" YEAR=2024
```

**What streaming optimization does:**
- **Fast start**: Moves MP4 moov atom to beginning for instant playback
- **Keyframe alignment**: Ensures proper keyframe spacing for seeking
- **Fragmented MP4**: Better for adaptive streaming
- **Audio alignment**: Syncs audio/video frames properly

**Benefits:**
- ⚡ Faster video startup in Jellyfin/Plex
- 🎯 Better seeking and scrubbing
- 📱 Improved mobile device compatibility
- 🔄 Better transcoding performance

### Auto-Eject Disc
Automatically eject the disc after processing:

```bash
EJECT_DISC=true make rip-movie TITLE="Movie" YEAR=1999
```

## Processing Existing MKV Files
If you already have MKV files ripped and want to convert them to MP4:

```bash
# The script automatically detects existing MKV files and skips disc ripping
TITLE="Movie Name" YEAR=1999 python3 bin/video/rip_video.py bluray

# Works with make targets too
make rip-movie TITLE="Movie Name" YEAR=1999
```

- **Smart detection**: Automatically finds existing MKV files and skips MakeMKV ripping
- **Resume capability**: If encoding was interrupted, it will continue from where it left off
- **Error handling**: Gracefully handles missing files and continues processing remaining tracks

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
When the default audio track is not English, the helper script uses `AUDIO_SUBS_POLICY` to determine behavior (no prompts).

To guarantee inclusion when available, the script post-muxes any English text-based subtitles (SubRip/ASS/SSA/Text/WebVTT) from the source MKV into the final MP4 after encoding. This requires `ffmpeg` (for both `ffmpeg` and `ffprobe`) and `jq`.

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

## MP4 Streaming Compliance and Repair

### Automatic Compliance (Built into bluray_to_mp4.zsh)
The automated Blu-ray script includes built-in compliance checking and repair:
- **HandBrake optimization** with `--optimize` flag
- **Post-encoding compliance check** for timestamp issues
- **Automatic repair** with `-fflags +genpts` and `-movflags +faststart`
- **Verification** of repaired files before replacement

### Manual MP4 Repair
For existing MP4 files that may have streaming issues:

```bash
# Repair a single MP4 file
./bin/video/repair_mp4.sh "/path/to/movie.mp4"

# The script will:
# - Check for timestamp and faststart issues
# - Create backup before repair
# - Fix missing timestamps and add faststart flag
# - Verify the repair was successful
```

### Common Issues Fixed
- **Missing timestamps** - Regenerates proper PTS/DTS timing
- **Missing faststart flag** - Moves metadata to file beginning for streaming
- **Non-monotonic timestamps** - Fixes timing sync issues
- **Web compatibility** - Ensures proper MP4 container structure

### When to Use Repair
Use the repair script if you experience:
- Long loading times before video starts
- Seeking issues in video players
- Web streaming problems
- Audio/video sync issues

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

4. **Recent fix**: A bug was fixed in Oct 2025 where the script incorrectly calculated HandBrake track numbers. Ensure you're using the latest version of `bin/video/rip_video.py`.

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

See **[Media Server Setup](media_server_setup.md)** for more complete examples and tips.

---

## Known issues and fixes

### HandBrake subtitle track numbering (Fixed: Oct 2025)
**Issue**: Auto-burn was calculating incorrect subtitle track numbers, causing burn-in to fail or select the wrong track.

**Root cause**: HandBrake numbers subtitle tracks sequentially (1, 2, 3...) based on their position in the file, NOT based on ffprobe's stream index values. For example:
- ffprobe shows: stream index 4 (Chinese), stream index 5 (English)
- HandBrake shows: track 1 (Chinese), track 2 (English)
- Old script calculated: 5 + 1 = track 6 
- Correct calculation: track 2 

**Fix**: The script now uses `ENG_IMAGE_HB_TRACK` which correctly calculates the HandBrake track number by finding the position of the English subtitle among all subtitle streams (1-indexed).

**Impact**: Auto-burn now works correctly for all DVD/Blu-ray configurations.

### Missing thumbnails in Jellyfin/Plex
**Issue**: Some video files don't show thumbnail images in media servers.

**Solution**: Use the `embed_thumbnail.py` script to add cover art:
```bash
python3 bin/video/embed_thumbnail.py "/path/to/video.mp4" "/path/to/thumbnail.jpg"
```

This embeds the image as MP4 cover art (`covr` tag) which Jellyfin, Plex, and other media servers recognize for display.

---

## Legal
This workflow is intended for personal backups of media you own, for local personal use only. Respect laws in your jurisdiction and the license terms of the tools used.
