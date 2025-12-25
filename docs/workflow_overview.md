# Workflow Overview (Disc → Digital Library)

This repository is organized around two primary workflows:

- **Audio CDs → FLAC library → tagging → optional sync to a server**
- **DVD/Blu-ray → MP4 library → subtitles/organization → server-ready layout**

Each step links to the detailed guide or script.

---

## Workflow A: CDs → FLACs → tagging → sync

### A1) Rip CD to FLAC (MusicBrainz + cover + playlist)
- Guide: `docs/cd_ripping_guide.md`
- Typical command:
  - `make rip-cd`

Output (default):
- `${RIPS_ROOT:-/Volumes/Data/Media/Rips}/CDs/Artist/Album/NN - Title.flac`
- `cover.jpg`
- `Album.m3u8`

### A2) Normalize/fix an existing album folder (optional)
- Helper: `fix_album.sh`
  - Renames tracks to `NN - Title.flac`
  - Rebuilds playlist
  - Fixes tags and cover art

### A3) Tag explicit content (per-track)
- Script: `bin/tag-explicit-mb.py`
- Writes per-track tag: `EXPLICIT=Yes|No|Unknown`

Debug options:
- `EXPLICIT_DRY_RUN=1` (no writes)
- `EXPLICIT_MAX_TRACKS=500` (limit scanning)

Artifacts:
- `./log/explicit_tagging.log`
- `./log/explicit_tagging_errors.log`
- `./log/explicit_tagging_cache.json`
- `.../CDs/Explicit.m3u8` (playlist of tracks tagged `EXPLICIT=Yes`)

### A4) Sync to a destination server while excluding explicit/unknown (optional)
- Script: `bin/sync-library.py`
- Excludes are driven by the `EXPLICIT` tag:
  - `--exclude-explicit` skips `EXPLICIT=Yes`
  - `--exclude-unknown` skips `EXPLICIT=Unknown` and missing tags

---

## Workflow B: DVD/Blu-ray → MP4s → organize/subtitles → server

### B1) Rip discs to staging (MKV/MP4)
- Guide: `docs/video_ripping_guide.md`
- Commands:
  - `make rip-video` (staging)
  - `make rip-movie TITLE="Movie Name" YEAR=1999` (organize main feature)

### B2) Organize into a server-friendly layout
- Guide: `docs/media_server_setup.md`
- Recommended:
  - Movies: `.../Movies/Movie Name (Year)/Movie Name (Year).mp4`
  - TV: `.../TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.mp4`

### B3) Ensure subtitles are present (optional)
- Video guide covers:
  - English subtitle selection/burn-in policies
  - Backfilling English soft subs into existing MP4s

### B4) Tag movie metadata and ratings (optional)
- Scripts:
  - `bin/tag-movie-metadata.py` — rich metadata (plot/genres/cast/artwork) via TMDb/OMDb
  - `bin/tag-movie-ratings.py` — MPAA rating tag (`©rat`) via TMDb/OMDb + overrides/cache
