# Media Server Setup and Naming Conventions (Plex/Jellyfin/Emby)

This guide outlines recommended folder structures and filenames so your media server (Plex/Jellyfin/Emby) can automatically match metadata.

> **Prerequisites:** Follow the [Quick Start Guide](../QUICKSTART.md) for initial setup.  
> **Before running Python scripts:** Activate virtual environment with `source venv/bin/activate`

---

## Library roots
- Music library root: `${LIBRARY_ROOT}/CDs`
- Video library root (examples):
  - Movies: `${LIBRARY_ROOT}/Movies`
  - TV: `${LIBRARY_ROOT}/TV`
  - Disc backups (raw MKV/MP4 by title or date): `${LIBRARY_ROOT}/DVDs` and `${LIBRARY_ROOT}/Blurays`

Note: `LIBRARY_ROOT` is centralized in `.env` (see `.env.sample`). Make targets auto-load `.env`.

Use the title-named (preferred when Title/Year are known) or date-based folders under `${LIBRARY_ROOT}` for staging. After verification/renaming, move items into the long-term library roots for your media server.

---

## Music naming (albums)
Recommended structure (matches `abcde` config in this repo):
```
${LIBRARY_ROOT}/CDs/
  Artist/
    Album/
      01 - Track Title.flac
      02 - Track Title.flac
      ...
      cover.jpg
      Album.m3u8
```

Notes:
- Various Artists: consider `Various/Album/NN - Artist - Title.flac` (see `VAOUTPUTFORMAT` in `.abcde.conf.sample`).
- Multi-disc albums: either separate as `Album (Disc 1)` / `Album (Disc 2)` or subfolders within the album.
- Keep `cover.jpg` at 1000x1000 for best compatibility with many clients.

---

## Explicit tagging and “family safe” sync
This repo supports explicit content tagging via per-track metadata (FLAC and MP3), which can later drive sync policies (e.g., skip explicit content on a destination Jellyfin server).

### Tagging
- Script: `bin/music/tag-explicit-mb.py`
- Writes a per-track tag: `EXPLICIT=Yes|No|Unknown`
- Supports both FLAC (CD rips) and MP3 (digital purchases) files
- Automatically loads `.env` for API credentials (no manual sourcing needed)

If optional API credentials are not configured (e.g., Spotify), the script will still run and will simply skip that lookup source.
- Waterfall (highest priority first):
  1. **Manual overrides** from `config/explicit_overrides.csv` (use `*` as wildcard for artist/album/title)
  2. **iTunes** album/track lookup — `explicit` and `cleaned` count as explicit; `notExplicit` blocks album inference
  3. **iTunes track search fallback** — only marks explicit if `trackExplicitness=explicit|cleaned`
  4. **Spotify** track search (requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`)
  5. **MusicBrainz** — only `adult_content=True` treated as explicit

**Limitation:** Both iTunes and Spotify have incomplete data for older albums (e.g., Prince's "Controversy" shows `notExplicit` for all tracks). Use `config/explicit_overrides.csv` for known false negatives.

- Output files (organized in `log/explicit/`):
  - `explicit_tagging_run.log` - Tracks processed during this run
  - `explicit_tracks_current.csv` - **Definitive list of ALL EXPLICIT=Yes tracks**
  - `explicit_tagging_cache.json` - Performance cache (moved to `cache/`)
  - `explicit_tagging_errors.log` - API errors only
- Playlist of explicit tracks (if enabled):
  - `log/explicit/Explicit.m3u8`

Environment variables:
- `EXPLICIT_DRY_RUN=1` — preview without writing tags
- `EXPLICIT_ONLY_UNKNOWN=1` — re-process only `Unknown`/missing tags
- `EXPLICIT_ITUNES_TRACK_FALLBACK=1` — enable per-track iTunes search (auto-enabled with `ONLY_UNKNOWN`)
- `EXPLICIT_SPOTIFY_FALLBACK=0` — disable Spotify fallback (enabled by default if credentials set)
- `EXPLICIT_SKIP_CACHED=0` — force full re-run even if album is cached (by default, skips cached albums unless override needs applying)

### Manual tag management
To manually set or override EXPLICIT tags:

**Using metaflac (FLAC files):**
```bash
# Set single track
metaflac --set-tag=EXPLICIT=Yes "Artist/Album/01 - Song.flac"

# Set all tracks in album
for f in "Artist/Album"/*.flac; do
  metaflac --set-tag=EXPLICIT=No "$f"
done

# Check current tag
metaflac --show-tag=EXPLICIT "Artist/Album/01 - Song.flac"
```

**Using the helper script (`bin/music/set_explicit.py`):**
```bash
# Set single file (auto-detects format)
python3 bin/music/set_explicit.py "/path/to/file" Yes

# Set entire album
python3 bin/music/set_explicit.py "/path/to/album" Yes --album
```

**To revert to API-determined tags:**
1. Remove the EXPLICIT tag: `metaflac --remove-tag=EXPLICIT "file.flac"`
2. Run the tagging script again to re-query APIs

### Sync to media server (Jellyfin/Plex/Emby)
This repo provides intelligent sync capabilities that respect explicit content tagging:

#### Single library sync
```bash
python3 bin/sync/sync-library.py \
  --src "${LIBRARY_ROOT}/CDs" \
  --dest "jellyfin@server:/mnt/media/Music" \
  --exclude-explicit \
  --exclude-unknown
```

#### Multi-library orchestration (recommended)
The `bin/sync/` directory provides advanced sync orchestration:

**Features:**
- **Explicit content filtering** - Excludes tracks with `EXPLICIT=Yes` tags
- **Associated lyrics exclusion** - Automatically excludes `.lrc` files for explicit tracks
- **Override support** - Uses `config/explicit_overrides.csv` for manual rules
- **Cache-aware** - Only processes Unknown tracks when overrides change

**Configuration (sync-config.yaml):**
```yaml
global:
  delete: false  # Global delete mode - removes folders that no longer exist in ANY source
  dry_run: false

sync_jobs:
  - name: "clean-cd-library"
    src: "${LIBRARY_ROOT}/CDs"
    dest: "jellyfin@server:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  - name: "clean-digital-archive"
    src: "${LIBRARY_ROOT}/Music"
    dest: "jellyfin@server:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  - name: "clean-movies-library"
    src: "${LIBRARY_ROOT}/Movies"
    dest: "jellyfin@server:/mnt/media/Movies"
    media: "movies"
    max_mpaa: "PG-13"
    exclude_unrated: true
    exclude_unknown: true
```

**Key features:**
- **Two-phase sync:** All jobs sync first (without delete), then global cleanup runs
- **Source-aware delete:** Only deletes folders that don't exist in ANY source for that destination
- **Target-specific:** Each destination (Music, Movies) is handled separately
- **Empty folder exclusion:** Automatically skips artist/album folders with no included files
- **Enhanced progress:** Shows detailed transfer progress information

**Usage:**
```bash
# Dry run to test configuration
python3 bin/sync/master-sync.py --dry-run

# Run all jobs
python3 bin/sync/master-sync.py

# Run specific job only
python3 bin/sync/master-sync.py --job clean-cd-library

# Enable global delete mode (set in config)
python3 bin/sync/master-sync.py  # Will clean up orphaned folders
```

**Benefits for media servers:**
- Maintains clean library structure without cross-library conflicts
- Respects explicit content policies automatically
- Handles multiple sources (CDs, Digital) to same destination safely
- Provides detailed progress and error reporting

---

## Movie naming
Follow Plex/Jellyfin recommendations:
```
${LIBRARY_ROOT}/Movies/
  Movie Name (Year)/
    Movie Name (Year).mp4
    Movie Name (Year).nfo   # optional
```

- Avoid extra text in filenames; prefer the title and year only.
- Keep one movie per folder named exactly as the file.

---

## TV series naming
```
${LIBRARY_ROOT}/TV/
  Show Name/
    Season 01/
      Show Name - S01E01 - Episode Title.mp4
      Show Name - S01E02 - Episode Title.mp4
```

- Specials: `Season 00` with `S00EXX` numbering.
- Multi-episode files: `S01E01E02`.

---

## Moving from staging to library
- Ripping guides output to title-named folders when Title/Year are provided or prompted (e.g., `${LIBRARY_ROOT}/DVDs/Movie Name (1999)`), otherwise to date-based folders (e.g., `${LIBRARY_ROOT}/DVDs/2025-09-13`). Verify, then rename/move into library roots as needed.
- Tools such as FileBot or tinyMediaManager can speed up renaming based on online databases.

### Backfilling English subtitles into existing MP4s
If your MP4 is missing English soft subtitles but the archival MKV has them (as text subs), you can mux them in without re-encoding:

```
make backfill-subs \
  SRC_DIR="${LIBRARY_ROOT}/DVDs/Movie Name (Year)" \
  DST_DIR="${LIBRARY_ROOT}/Movies/Movie Name (Year)" \
  [INPLACE=yes] [DEFAULT=yes]
```

- Requires `ffmpeg`/`ffprobe` and `jq`.
- For image-based subs (VobSub/PGS), OCR to SRT first or burn-in during a re-encode.

---

## Tips for scrapers
- Use the official names and years from The Movie Database (TMDb) or The TV Database (TVDb) for best matches.
- Avoid extra tags (e.g., `1080p`, `x264`) in filenames; put those into folder names or leave them out.
- Keep one show per top-level directory, one movie per directory.

---

## Legal
This setup is intended for personal backups of media you own, for local personal use only.
