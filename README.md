### Video prerequisites (DVD/Blu-ray)
- Install all video tools with one command:
  ```bash
  make install-video-deps
  ```
  This installs: HandBrakeCLI, ffmpeg/ffprobe, jq, tesseract, mkvtoolnix, and links makemkvcon.

- MakeMKV (GUI; provides CLI `makemkvcon`)
  - Download: https://www.makemkv.com/download/
  - Install: drag `MakeMKV.app` to `/Applications`
  - The `make install-video-deps` command will link the CLI automatically

- First run tip: launch MakeMKV GUI once to accept EULA and set drive region. If you see macOS quarantine errors, run:
  ```bash
  xattr -dr com.apple.quarantine /Applications/MakeMKV.app
  ```
# Disc-to-Digital Scripts

Scripts and configuration for ripping optical media and organizing to a clean, metadata-rich library. The current focus is audio CDs to FLAC, with utilities to normalize covers, fix tags, and compare libraries. The intent is strictly for local, personal backups and playback.

## Workflow entrypoint
- End-to-end overview: `docs/workflow_overview.md`
  - CDs → FLAC → explicit tagging → optional sync
  - DVD/Blu-ray → MP4 → organize/subtitles → server-ready layout

## Overview
- Primary audio workflow uses `abcde` to rip CDs to `.flac`, then normalizes filenames, playlists, and cover art. See `docs/cd_ripping_guide.md`.
- Helper scripts fix metadata, fetch missing covers, and reconcile two libraries.
- Video backups (DVD/Blu-ray) are supported via MakeMKV + HandBrakeCLI. See `docs/video_ripping_guide.md`.
- Some utilities are archived but preserved for reference.

## Directory layout
- `docs/` — user guides and how-tos
  - `cd_ripping_guide.md` — end-to-end CD ripping with `abcde`
  - `video_ripping_guide.md` — DVD/Blu-ray workflow using MakeMKV + HandBrakeCLI
- `_install/`
  - `install_setup_abcde_environment.py` — checks/installs Homebrew deps (abcde, eye-d3, flac, imagemagick, wget, curl) and creates an example cleanup helper.
  - `install_cleanup_abcde_xs.py` — removes an incompatible `DiscID.bundle` in some abcde installs.
- `_archive/` (kept for reference)
  - `backup_cover_art.py` — finds `cover.jpg`, logs dimensions, renames non-1000x1000 covers to `_cover.jpg`.
  - `check_flac_metadata.py` — compares FLAC tags to MusicBrainz; respects a skip list in `check_flac_metadata.skip`.
- `bin/` — primary scripts directory (organized by domain)
  - `bin/music/`
    - `fix_album.py` — normalize an album folder using MusicBrainz track titles; renames to `NN - Title.flac`; writes `.m3u8`; runs tag + cover fixes
    - `fix_album_covers.py` — fetch missing `cover.jpg` via Cover Art Archive (via MusicBrainz)
    - `fix_metadata.py` — validates and fixes FLAC tags based on filename pattern
    - `fix_track.py` — organizes a single loose track using AcoustID/MusicBrainz
    - `set_explicit.py` — set `EXPLICIT=Yes|No|Unknown` tags for FLAC files
    - `compare_music.py` — fast fuzzy comparison of two library roots; can group differences by album/artist
  - `bin/video/`
    - `rip_video.py` — rip DVD/Blu-ray via MakeMKV + HandBrakeCLI (no interactive prompts)
    - `backfill_subs.py` — mux English soft subs from MKV into existing MP4 (no re-encode)
  - `bin/utils/`
    - `clean_playlists.py` — normalize `.m3u` to `.m3u8` and validate track references
  - `bin/sync/`
  - `bin/sync/`
    - `master-sync.py` — run multiple sync jobs from YAML config; automatically runs explicit tagging before each sync
    - `sync-config.yaml` — define source/destination mappings (gitignored)
    - `sync-config.yaml.example` — example configuration template
  - `bin/music/specialized/` — special-case one-off workflows
    - `prince-lovesexy/split_lovesexy.py` — example special-case splitter for a single-file album (`ffmpeg`-based)
- `.abcde.conf.sample` — sample abcde configuration matching this repo's defaults.
- `.env.sample` — example environment variables (e.g., `ACOUSTID_API_KEY`).
- `docs/disc_ripping_guide.md` — earlier combined guide for CDs/DVDs/Blu-rays (kept for reference).

## Prerequisites
- macOS with Homebrew.
- Core tools: `abcde`, `flac` (metaflac), `imagemagick` (`convert`/`magick`), `jq`, `curl`, `wget`, `ffmpeg`.
  - Use `_install/install_setup_abcde_environment.py` to verify/install common packages.
- Python 3 with packages:
  - `mutagen`, `rapidfuzz`, `musicbrainzngs`, `acoustid`, `pyyaml`
  - Install via `requirements.txt`:
    - Create venv: `python3 -m venv ~/venvs/media && source ~/venvs/media/bin/activate`
    - Install deps: `pip install -r requirements.txt`
  - Example manual install: `pip install mutagen rapidfuzz musicbrainzngs pyacoustid pyyaml`
- Accounts/keys (optional but recommended):
  - AcoustID API key for `bin/music/fix_track.py`.
    - Set in your shell: `export ACOUSTID_API_KEY=...`
    - Or copy `.env.sample` to `.env` and load it via your shell init or a tool like `direnv`.

## Guides
- CD ripping: see `docs/cd_ripping_guide.md`.
- DVD/Blu-ray ripping: see `docs/video_ripping_guide.md`.
- Media server setup: see `docs/media_server_setup.md`.

## Genre metadata tagging (music)
- Script: `bin/music/update-genre-mb.py`
- Updates FLAC genre tags using MusicBrainz API with curated whitelist validation
- **NEW:** Automatic Christmas content detection (tags as "christmas")
- **NEW:** Genre transformers (e.g., "rhythm and blues" → "r&b", "symphony orchestra" → "classical")
- **NEW:** Additive rejected genres logging (preserves existing entries, removes duplicates)
- **NEW:** `--force-missing` flag to only update files without existing genre tags
- **NEW:** Improved timeout/retry logic (15s timeout, 4 retries) for reliable API calls
- **NEW:** Smart cache bypassing - forces fresh API lookups for untagged files in force modes
- **NEW:** Comprehensive genre whitelist with 100+ curated genres across all major families
- Waterfall (highest priority first):
  1. **Christmas detection** - automatically detects Christmas content in artist/album/title
  2. **Genre transformers** - maps common variants to whitelist equivalents
  3. **MusicBrainz API** - primary genre source with priority genre selection
  4. **Whitelist validation** - only accepts curated real genres (not decades/subjective tags)

**Genre selection logic:**
- Prioritizes core genres (rock, pop, jazz, classical, etc.) over decade tags
- Filters out non-genre tags (seen live, favorite, beautiful, 90s, catchy, etc.)
- Validates against curated whitelist before caching
- Logs rejected genres for review in `log/rejected_genres.txt`

**Christmas detection:**
- Detects Christmas terms: christmas, xmas, noel, holiday, winter, santa, carol, jingle, etc.
- Includes classic carol names: silent night, joy to the world, hark the herald, etc.
- Automatically tags as "christmas" genre (added to whitelist)
- Takes priority over other genres when both detected

**Genre transformers:**
- "rhythm and blues" → "r&b"
- "symphony orchestra" → "classical" 
- "rhythm & blues" → "r&b"
- "rnb" → "r&b"
- "orchestral" → "classical"
- "symphonic" → "classical"
- "orchestra" → "classical"

**Usage:**
```bash
# Normal mode (skip files with valid existing genres)
python3 bin/music/update-genre-mb.py "/path/to/music" --verbose --recursive

# Force mode (update ALL files, overwrite existing genres)
python3 bin/music/update-genre-mb.py "/path/to/music" --force --verbose --recursive

# Force missing mode (only update files without genre tags)
python3 bin/music/update-genre-mb.py "/path/to/music" --force-missing --verbose --recursive

# Dry run to preview changes
python3 bin/music/update-genre-mb.py "/path/to/music" --dry-run --verbose --recursive
```

**Cache and logging:**
- Genre cache: `~/.cache/genre_cache.json` (avoids repeated API calls)
- **Smart cache bypassing**: Force modes bypass cache for untagged files to ensure fresh lookups
- Rejected genres: `log/rejected_genres.txt` (additive, unique entries only)
- **Unresolved files**: `log/unresolved_genres.txt` (real-time logging of files with no genre found)
- Cache busting: Remove `~/.cache/genre_cache.json` to force fresh lookups for all files

**Benefits:**
- Consistent, high-quality genre tagging across entire music library
- Automatic handling of Christmas content without manual intervention
- Smart mapping of genre variants to standardized whitelist entries
- Reliable API handling with improved timeouts and retry logic
- **Intelligent cache management** - Uses cache for tagged files, forces fresh lookups for untagged files in force modes
- **Manual override capability** - Manual genre tagging script for problematic cases
- **Real-time unresolved file logging** - See problematic files immediately while script runs
- Comprehensive logging for whitelist management and improvement

## Manual genre tagging (music)
- Script: `bin/music/tag-manual-genre.py`
- **NEW:** Manual genre assignment with whitelist validation
- Leverages the same curated whitelist and transformers as the automatic script
- Perfect for problematic cases where automatic lookup fails or needs correction
- Supports single files, folders, and recursive processing

**Features:**
- **Whitelist validation** - Only accepts genres from the curated whitelist
- **Genre transformers** - Applies the same transformations (e.g., "rhythm and blues" → "r&b")
- **Dry-run mode** - Preview changes without modifying files
- **Force mode** - Overwrite existing genre tags
- **Verbose output** - Detailed progress information
- **Genre listing** - `--list-genres` shows all valid whitelist entries

**Usage:**
```bash
# Tag single file
python3 bin/music/tag-manual-genre.py "/path/to/song.flac" --genre "jazz"

# Tag entire album
python3 bin/music/tag-manual-genre.py "/path/to/album" --genre "rock" --recursive

# Preview changes
python3 bin/music/tag-manual-genre.py "/path/to/album" --genre "classical" --dry-run --verbose

# Force overwrite existing genres
python3 bin/music/tag-manual-genre.py "/path/to/album" --genre "progressive rock" --force --recursive

# List all valid genres
python3 bin/music/tag-manual-genre.py --list-genres
```

**Technical details:**
- **Import system**: Uses `importlib` to load functions from `update-genre-mb.py` (handles hyphenated filename)
- **Shared whitelist**: Leverages the same curated genre whitelist as automatic tagging
- **Consistent transformers**: Applies the same genre transformations for standardization
- **Safe validation**: Only accepts genres that pass whitelist validation

**Real-time workflow:**
```bash
# Run automatic tagging with real-time unresolved logging
python3 bin/music/update-genre-mb.py "/path/to/music" --force-missing --verbose --recursive

# In another terminal, monitor unresolved files as they appear
tail -f /Users/martin/Herd/digital-library/log/unresolved_genres.txt

# Or check progress periodically
cat /Users/martin/Herd/digital-library/log/unresolved_genres.txt

# Use manual tagging script for problematic files
python3 bin/music/tag-manual-genre.py "/path/to/problematic.flac" --genre "punk"
```

**Benefits:**
- **Perfect for problematic albums** where automatic lookup fails
- **Consistent with automatic script** - uses same whitelist and transformers
- **Safe operation** - validation prevents invalid genre assignments
- **Bulk operations** - can tag entire albums or collections efficiently
- **Robust import system** - handles hyphenated filenames with importlib
- **Real-time validation** - immediate feedback on genre validity

## Explicit content tagging (music)
- Script: `bin/music/tag-explicit-mb.py`
- Writes per-track FLAC tag: `EXPLICIT=Yes|No|Unknown`
- Automatically loads `.env` for API credentials (no manual sourcing needed)
- Waterfall (highest priority first):
  1. **Manual overrides** from `log/explicit_overrides.csv` (use `*` as wildcard)
  2. **iTunes** album/track lookup — treats `explicit` and `cleaned` as explicit; `notExplicit` blocks album-level inference
  3. **iTunes track search fallback** (when album lookup fails) — only marks explicit if `trackExplicitness=explicit|cleaned`
  4. **Spotify** track search (requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`)
  5. **MusicBrainz** — only positive `adult_content=True` treated as explicit

**Limitation:** Both iTunes and Spotify have incomplete data for older albums (e.g., Prince). Use `log/explicit_overrides.csv` for known false negatives.

Outputs:
- Run log: `./log/explicit_tagging.log`
- Error log (API failures only): `./log/explicit_tagging_errors.log`
- Cache: `./log/explicit_tagging_cache.json`
- Playlist of tagged-explicit tracks: `${LIBRARY_ROOT:-/Volumes/Data/Media/Library}/CDs/Explicit.m3u8`

Environment variables:
- `EXPLICIT_DRY_RUN=1` — do not write FLAC tags (still produces logs/playlist/summary)
- `EXPLICIT_MAX_TRACKS=500` — only process the first N FLACs (debug)
- `EXPLICIT_ONLY_UNKNOWN=1` — re-process only files currently tagged `Unknown` or missing
- `EXPLICIT_ITUNES_TRACK_FALLBACK=1` — enable per-track iTunes search (auto-enabled with `ONLY_UNKNOWN`)
- `EXPLICIT_SPOTIFY_FALLBACK=0` — disable Spotify fallback (enabled by default if credentials set)
- `EXPLICIT_SKIP_CACHED=0` — force full re-run even if album is cached (by default, skips cached albums unless override needs applying)

For manual tag management and media server sync details, see `docs/media_server_setup.md`.

## M3U8 Playlist Processing
- Script: `bin/music/update-from-m3u.py`
- Updates filenames and metadata from M3U8 playlists
- Supports both FLAC and MP3 formats with proper tag handling
- Handles generic CD rip filenames ("Track 1.flac", "Track 2.flac")
- Smart artist/title parsing with folder structure fallbacks

**Usage:**
```bash
# Process M3U8 file (dry run)
python3 bin/music/update-from-m3u.py /path/to/album.m3u8 --dry-run

# Process folder (finds M3U8 automatically)
python3 bin/music/update-from-m3u.py /path/to/album/ --dry-run

# Apply changes
python3 bin/music/update-from-m3u.py /path/to/album.m3u8

# Force updates even if metadata appears correct
python3 bin/music/update-from-m3u.py /path/to/album.m3u8 --force
```

**Features:**
- **Filename updates** - Renames files to match M3U8 entries
- **Metadata writing** - Updates artist, title, album, and track number tags
- **Smart parsing** - Extracts "Artist - Title" from M3U8 filenames
- **Fallback logic** - Uses folder names when artist info not available
- **Position matching** - Handles unordered "Track N.flac" files from CD rips
- **Format support** - FLAC (Vorbis comments) and MP3 (ID3 tags)

**Metadata Sources (in priority order):**
1. M3U8 filename parsing ("Artist - Title" format)
2. M3U8 EXTINF title information
3. Parent folder name (for artist fallback)
4. Filename after track number (for title fallback)

**Use Cases:**
- CD rips with generic "Track N.flac" filenames
- Albums with existing M3U8 playlists
- Various artist compilations
- Metadata restoration from playlist information


## MPAA rating tagging (movies and shows)
- Script: `bin/video/tag-movie-ratings.py`
- Writes MP4 atom: `©rat` with MPAA rating (G, PG, PG-13, R, NC-17, NR, Unrated)
- Automatic lookups use **any** of:
  - `TMDB_READ_ACCESS_TOKEN` (preferred; TMDb v4 read token)
  - `TMDB_API_KEY` (fallback; TMDb v3 API key)
  - `OMDB_API_KEY` (optional fallback; OMDb)
  - The script will auto-load these from `.env` at the repo root if present (via `python-dotenv`).
- Waterfall (highest priority first):
  1. **IMDb ID-based overrides** from `log/movie_rating_overrides.json` (if IMDb ID exists in MP4 metadata)
  2. **Title-based overrides** from `log/movie_rating_overrides.json` (fallback)
  3. **Cache** from `log/movie_rating_cache.json` (or `log/shows_rating_cache.json` for shows)
  4. **Existing tags** in the MP4 file
  5. **TMDb** lookup by title/year (US certification only) when TMDb credentials are set
  6. **OMDb** lookup by title/year when `OMDB_API_KEY` is set

### IMDb ID-based overrides (recommended for "same title, wrong movie" cases)
The override system now supports IMDb ID as the definitive key, solving conflicts where different movies share the same title.

**Override format:**
```json
{
  "title_based": {
    "Groundhog Day": "PG-13"
  },
  "imdb_id_based": {
    "tt0107048": "PG-13",
    "tt0111167": "R"
  }
}
```

**Priority logic:**
1. If MP4 has IMDb ID metadata → check `imdb_id_based` first
2. Fall back to `title_based` overrides
3. Use cache/API lookups if no override found

**Managing IMDb ID overrides:**
```bash
# List movies with their IMDb IDs
python3 bin/set-movie-imdb-override.py --list --directory "/Volumes/Data/Media/Library/Movies"

# Add IMDb ID-based override (reads IMDb ID from file metadata)
python3 bin/set-movie-imdb-override.py --add "/path/to/movie.mp4" --rating "R"

# Add override with explicit IMDb ID
python3 bin/set-movie-imdb-override.py --add "/path/to/movie.mp4" --rating "R" --imdb-id "tt1234567"
```

**Benefits:**
- Permanent fix for "same title, wrong movie" issues
- Different movies with same title get distinct overrides
- Backward compatible with existing title-based overrides
- Clear source identification in output (shows "IMDb ID (tt1234567)" vs "Title (Movie Name)")

Shows:
- Ratings for items under the Shows library are tracked separately for reference:
  - Overrides: `log/shows_rating_overrides.csv`
  - Cache: `log/shows_rating_cache.json`
- Use `--media shows` to tag the Shows library (defaults to movies).

If no API keys are set, the script will still run but will only use overrides/cache/existing tags.

Rate limits:
- OMDb has a daily request limit depending on your plan. If the script detects a daily limit error, it will stop making OMDb requests for the rest of the day and record this in `log/movie_rating_cache.json` so you can rerun the next day and continue.

Outputs:
- Cache: `log/movie_rating_cache.json`
- Overrides: `log/movie_rating_overrides.json` (create/edit manually)
- Utility: `bin/set-movie-imdb-override.py` (manage IMDb ID-based overrides)

Console output:
- Valid ratings print as `RATING=PG: Title (Year) (Source)`
- With `--verbose`, Unknown titles also print as `UNKNOWN: Title (Year) (Source)`
- Titles already ending with `(YYYY)` avoid double-printing the year.
- IMDb ID-based overrides show source as `IMDb ID (tt1234567)`

Usage:
```bash
# Tag movies (dry run by default)
python3 bin/video/tag-movie-ratings.py "/path/to/movies" --dry-run

# Actually write tags
python3 bin/video/tag-movie-ratings.py "/path/to/movies"

# Verbose output (includes Unknown titles)
python3 bin/video/tag-movie-ratings.py "/path/to/movies" --verbose

# Limit files processed
python3 bin/video/tag-movie-ratings.py "/path/to/movies" --max-files 50

# Tag shows library (uses shows_rating_* files)
python3 bin/video/tag-movie-ratings.py "/path/to/shows" --media shows --dry-run
python3 bin/video/tag-movie-ratings.py "/path/to/shows" --media shows
```

## Comprehensive movie metadata tagging
- Script: `bin/video/tag-movie-metadata.py`
- Writes comprehensive MP4 metadata including title, year, genre, director, actors, synopsis, ratings, studio, and poster artwork
- Automatic lookups require **one** of:
  - `TMDB_API_KEY` (preferred; free from TMDb, includes poster artwork)
  - `OMDB_API_KEY` (fallback; from OMDb)
  - The script will auto-load these from `.env` at the repo root if present (via `python-dotenv`).
- Input methods:
  - `--imdb-id` (tt####### format)
  - `--tmdb-id` (numeric TMDb ID)
  - `--title` and `--year` (for search lookup)
  - If no ID/title is provided, the script will try to infer `Title (Year)` from the filename or parent folder (recommended layout: `Movies/Title (Year)/Title (Year).mp4`).
- Metadata sources (highest priority first):
  1. **TMDb** lookup by IMDb ID, TMDb ID, or title/year when `TMDB_API_KEY` is set
  2. **OMDb** lookup by IMDb ID (or title/year) when `OMDB_API_KEY` is set
- By default, the script only fills missing tags/artwork. Use `--force` to overwrite existing tags.
- Written MP4 atoms:
  - `©nam` - Title
  - `©day` - Year/Release date
  - `©des` - Description/Synopsis
  - `©gen` - Genre
  - `©ART` - Director
  - `©wrt` - Writers
  - `©act` - Actors
  - `©rat` - MPAA rating
  - `©cpy` - Studio
  - `covr` - Poster artwork (TMDb only)
  - Custom atoms: IMDb ID, TMDb ID, runtime, budget, revenue, keywords

Usage:
```bash
# Tag single movie by IMDb ID (dry run by default)
python3 bin/tag-movie-metadata.py "/path/to/movie.mp4" --imdb-id tt0095250 --dry-run

# Actually write metadata
python3 bin/tag-movie-metadata.py "/path/to/movie.mp4" --imdb-id tt0095250

# Tag by title/year search
python3 bin/tag-movie-metadata.py "/path/to/movie.mp4" --title "The Big Blue" --year 1988

# Process directory recursively (attempt to infer Title/Year per movie)
python3 bin/tag-movie-metadata.py "/path/to/movies/" --recursive --dry-run --verbose
python3 bin/tag-movie-metadata.py "/path/to/movies/" --recursive

# Overwrite existing tags/artwork (use carefully)
python3 bin/tag-movie-metadata.py "/path/to/movies/" --recursive --force

# Verbose output to see all metadata found
python3 bin/tag-movie-metadata.py "/path/to/movie.mp4" --imdb-id tt0095250 --verbose
```

## TV show metadata tagging
- Script: `bin/tag-show-metadata.py`
- **NEW:** Manual override support for problematic shows using `--tmdb-id` and `--imdb-id`
- **NEW:** Automatic show override system via `log/show_tmdb_overrides.json`
- **NEW:** Filename character correction (macOS colon → dash conversion handling)
- **NEW:** IMDb fallback using OMDb API for shows not available on TMDb
- Writes comprehensive TV show metadata including title, year, genre, description, and episode information
- Supports both TMDb and IMDb metadata sources with intelligent fallback logic

**Override system:**
- **TMDb overrides**: Use `--tmdb-id` to specify exact TMDb show ID (skips search)
- **IMDb overrides**: Use `--imdb-id` to fetch show metadata via OMDb API
- **Automatic overrides**: Create `log/show_tmdb_overrides.json` for persistent problematic show handling
- **Filename correction**: Automatically fixes macOS filesystem colon-to-dash conversion in episode titles

**Override file format:**
```json
{
  "overrides": {
    "Alan Parson's Art & Science of Sound Recording (2002)": {
      "tmdb_id": null,
      "imdb_id": "tt3461480",
      "notes": "Use IMDb - TMDb deleted this show"
    },
    "China - A Century of Revolution (1989)": {
      "tmdb_id": null,
      "imdb_id": "tt5776992",
      "notes": "Use IMDb - better episode coverage"
    }
  }
}
```

**Usage:**
```bash
# Normal TMDb lookup
python3 bin/tag-show-metadata.py "/path/to/show" --recursive --dry-run

# Manual TMDb ID override
python3 bin/tag-show-metadata.py "/path/to/show" --tmdb-id 12345 --recursive

# Manual IMDb ID override (uses OMDb)
python3 bin/tag-show-metadata.py "/path/to/show" --imdb-id tt3461480 --recursive

# Verbose output to see lookup process
python3 bin/tag-show-metadata.py "/path/to/show" --verbose --recursive --dry-run
```

**Metadata sources:**
1. **TMDb ID override** (highest priority) - exact TMDb show ID
2. **IMDb ID override** - OMDb API lookup for show metadata
3. **Automatic overrides** - reads from `show_tmdb_overrides.json`
4. **TMDb search** - fallback search by show name/year
5. **Filename-based episodes** - for IMDb shows without episode data

**Benefits:**
- Handles shows deleted from TMDb by using IMDb as fallback
- Corrects filesystem character conversion issues automatically
- Persistent override system for consistently problematic shows
- Verbose logging shows exactly which metadata source is being used

## Configuration: `.abcde.conf`
- Output: `FLAC` to `${LIBRARY_ROOT}/CDs` (defaults to `/Volumes/Data/Media/Library/CDs`) using format `${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}`.
- Uses MusicBrainz for album/track lookup and `getalbumart` in the `ACTIONS` chain.
- Playlists enabled (`.m3u8`).
- Ejects the disc after encoding via abcde built-in eject (`EJECTCD=y`).
- Filename sanitizer in `mungefilename()` removes forbidden characters and squashes spaces.

Copy the sample file to your home directory:
```bash
cp ./.abcde.conf.sample ~/.abcde.conf
```

## Makefile tasks
Run `make help` for a summary. Common tasks:
- `make install-deps` — install Homebrew dependencies and Python packages
- `make install-video-deps` — install video tools (HandBrakeCLI, ffmpeg, jq, tesseract, mkvtoolnix) and link makemkvcon
- `make rip-cd` — run `abcde` using your `~/.abcde.conf`
- `make rip-video [TYPE=dvd|bluray]` — rip video discs (auto-detects disc type if TYPE omitted)
- `make rip-movie [TYPE=dvd|bluray] TITLE="Movie Name" YEAR=1999` — rip and organize the main feature to `Movies/Title (Year)/Title (Year).mp4` (auto-detects disc type if TYPE omitted)
- Notes: you can set `MINLENGTH=1800` to skip short titles and `DEST_CATEGORY=Films` to change the destination category from `Movies`.
- `make fix-album DIR="/path/to/Artist/Album"` — normalize, tag, covers, playlist
- `make fetch-covers ROOT="/path/or/library"` — fetch missing `cover.jpg`
- `make fix-track FILE="/path/file.ext" TARGET="${LIBRARY_ROOT}/Music"` — organize a single track
- `make compare OLD="/old" NEW="/new" [MODE=albums|artists] [THRESHOLD=90]` — compare two libraries
- `make backfill-subs SRC_DIR="/path/to/source_mkv_dir" DST_DIR="/path/to/target_mp4_dir" [INPLACE=yes] [DEFAULT=yes]` — mux English soft subs from MKV into existing MP4
- `make vobsub-to-srt FILE="/path/to/subtitle.idx"` — convert VobSub files to placeholder SRT for muxing
- `python3 bin/music/check_album_integrity.py [--show-ok]` — validate album folders (cover, playlists, `_cover.jpg`), scanning `${LIBRARY_ROOT}/CDs`

## Typical workflows
- Rip a CD to FLAC
  1. Insert disc; run `abcde` (uses `.abcde.conf`).
  2. Result at `${LIBRARY_ROOT}/CDs/Artist/Album/NN - Title.flac` with `cover.jpg` and playlist.

- Rip and organize a DVD/Blu-ray
  - Staging only:
    - `make rip-video` (auto-detects disc type). In an interactive terminal, the script can prompt to name the staging folder and optionally organize afterward.
  - Rip + organize in one step:
    - `make rip-movie TITLE="Movie Name" YEAR=1999` (auto-detects disc type)
    - Moves the largest MP4 to `${LIBRARY_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`; keeps MKVs (and any extras) under `${LIBRARY_ROOT}/DVDs/` or `${LIBRARY_ROOT}/Blurays/`.
  - Auto-detection: The script now automatically detects DVD vs Blu-ray discs. You can still override with `TYPE=dvd` or `TYPE=bluray` if needed.
  - Automatic subtitle burn-in: For non-English audio discs with English image-based subtitles (VobSub/PGS) but no soft English subs, the script automatically burns in the subtitles. Override with `AUDIO_SUBS_POLICY=keep` to disable.
  - Recent fix (Oct 2025): Corrected HandBrake subtitle track numbering calculation for reliable auto-burn across all disc configurations.

- Backfill English subtitles into an existing MP4
  - Create a new MP4 with subs next to the original:
    ```bash
    make backfill-subs \
      SRC_DIR="${LIBRARY_ROOT}/DVDs/Movie Name (Year)" \
      DST_DIR="${LIBRARY_ROOT}/Movies/Movie Name (Year)"
    ```
  - Replace the original in-place and mark subs default:
    ```bash
    make backfill-subs \
      SRC_DIR="${LIBRARY_ROOT}/DVDs/Movie Name (Year)" \
      DST_DIR="${LIBRARY_ROOT}/Movies/Movie Name (Year)" \
      INPLACE=yes DEFAULT=yes
    ```
  - For image-based subtitles (VobSub/PGS): The script will extract subtitle files and provide guidance for manual OCR using tools like Subtitle Edit.

- Convert VobSub to SRT (for manual OCR workflow)
  ```bash
  make vobsub-to-srt FILE=".backfill_ocr_12345.idx"
  ```
  Creates a placeholder SRT file for immediate muxing. For full OCR, use Subtitle Edit GUI with the corresponding .sub file.

- Normalize and complete an album folder
  1. `python3 bin/music/fix_album.py "/path/to/Artist/Album"`
  2. Script fetches MusicBrainz release, renames files to track order, writes `Album.m3u8`, fixes tags, and fetchs `cover.jpg` if missing.

- Repair FLAC tags using .m3u8 playlist and folder structure
  ```bash
  # Preview what would be repaired (dry run)
  python3 bin/music/repair-flac-tags.py --dry-run "/path/to/album/folder"
  
  # Actually repair the tags
  python3 bin/music/repair-flac-tags.py "/path/to/album/folder"
  
  # Verbose output
  python3 bin/music/repair-flac-tags.py -v "/path/to/album/folder"
  ```
  Repairs FLAC tags (ARTIST, ALBUM, TITLE, TRACKNUMBER) by detecting differences between current tags and expected values:
  - Extracts expected artist/album from folder structure (e.g., `/Artist/Album/`)
  - Parses .m3u8 playlist to get expected track titles and filenames
  - Matches FLAC files to playlist entries
  - Compares current tags against expected values and fixes any differences
  - Shows detailed diff output (current → expected) for each field that needs repair
  - Supports both simple and extended M3U playlist formats
  - Safe operation: only modifies tags that differ from expected values

- Tag explicit content across the library
  ```bash
  # Tag default library (CDs) - supports FLAC and MP3
  python3 bin/music/tag-explicit-mb.py
  
  # Tag specific folder - supports FLAC and MP3
  python3 bin/music/tag-explicit-mb.py "/path/to/music/folder"
  
  # Dry run (no writes)
  python3 bin/music/tag-explicit-mb.py "/path/to/music/folder" --dry-run
  
  # Limit number of tracks processed
  python3 bin/music/tag-explicit-mb.py "/path/to/music/folder" --max-tracks 100 --dry-run
  
  # Generate Explicit.m3u8 playlist (disabled by default)
  python3 bin/music/tag-explicit-mb.py "/path/to/music/folder" --generate-explicit-playlist
  
  # Verbose output (show all EXPLICIT=Yes tracks, including cached ones)
  python3 bin/music/tag-explicit-mb.py "/path/to/music/folder" --verbose
  ```
  
  **Note**: The script supports both FLAC (from CD rips) and MP3 (digital purchases) files. EXPLICIT tags are written using format-specific metadata (FLAC: `EXPLICIT` field, MP3: `TXXX:EXPLICIT` ID3 tag). Playlist generation is disabled by default to avoid creating broken playlists when using `--exclude-explicit` sync jobs.

- Sync to a Jellyfin server while excluding explicit and/or unknown tracks
  - Script: `bin/sync/sync-library.py`
  - Exclusion is based on the `EXPLICIT` tag (supports both FLAC and MP3).
  - Missing `EXPLICIT` is treated as `Unknown`.
  - **Automatic cleanup:** Empty directories are removed by default (use `--no-delete` to disable)
  - **Enhanced progress:** Shows detailed transfer progress with `--info=progress2`
  - **Playlist fixing:** Automatically fixes .m3u8 files to replace missing tracks with "(skipped)" placeholders
  - **M3U exclusion:** .m3u8 playlist files are automatically excluded from sync (Jellyfin doesn't need them, but they're kept locally for tag repair)
  ```bash
  # Single sync job
  python3 bin/sync/sync-library.py \
    --src "/Volumes/Data/Media/Library/CDs" \
    --dest "/path/to/jellyfin/music" \
    --exclude-explicit \
    --dry-run
  
  # Multiple sync jobs with global delete mode
  python3 bin/sync/master-sync.py --dry-run
  
  # Shows library sync (no rating filtering yet)
  python3 bin/sync/sync-library.py \
    --src "/Volumes/Data/Media/Library/Shows" \
    --dest "jellyfin@10.0.4.75:/mnt/media/Shows" \
    --media shows \
    --dry-run
  python3 bin/sync/master-sync.py --job clean-library
  
  # Master sync automatically runs explicit tagging before each sync job
  python3 bin/sync/master-sync.py  # Tags new content then syncs all jobs
  python3 bin/sync/master-sync.py --skip-tagging  # Skip tagging phase
  ```

### Master Sync Configuration (bin/sync/)
The `bin/sync/` directory provides orchestration for multiple sync jobs with intelligent delete mode:

**Configuration (sync-config.yaml):**
```yaml
# Global options
global:
  delete: false  # Global delete mode - removes folders that no longer exist in ANY source
  dry_run: false
  print_command: false
  max_flacs: null  # Optional limit for testing

sync_jobs:
  # Clean CD library
  - name: "clean-cd-library"
    src: "/Volumes/Data/Media/Library/CDs"
    dest: "jellyfin@10.0.4.75:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  # Clean digital library
  - name: "clean-digital-library"
    src: "/Volumes/Data/Media/Library/Music"
    dest: "jellyfin@10.0.4.75:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true

  # Clean movies library
  - name: "clean-movies-library"
    src: "/Volumes/Data/Media/Library/Movies"
    dest: "jellyfin@10.0.4.75:/mnt/media/Movies"
    media: "movies"
    max_mpaa: "PG-13"
    exclude_unrated: true
    exclude_unknown: true
```

**Features:**
- **Two-phase sync:** All jobs sync first (without delete), then global cleanup runs
- **Source-aware delete:** Only deletes folders that don't exist in ANY source for that destination
- **Target-specific:** Each destination (Music, Movies) is handled separately
- **Empty folder exclusion:** Automatically skips artist/album folders with no included files
- **Progress tracking:** Enhanced rsync progress with detailed transfer information

**Usage:**
```bash
# List available jobs
python3 bin/sync/master-sync.py --list-jobs

# Dry run all jobs
python3 bin/sync/master-sync.py --dry-run

# Run specific job
python3 bin/sync/master-sync.py --job clean-cd-library

# Run all jobs with global delete enabled
python3 bin/sync/master-sync.py  # Uses global.delete from config

# Skip explicit tagging phase
python3 bin/sync/master-sync.py --skip-tagging
```

- Generate .m3u8 playlists for albums missing them
  ```bash
  # Generate playlists for all albums in a directory
  python3 bin/music/generate-playlists.py "/path/to/music"
  
  # Dry run to see what would be created
  python3 bin/music/generate-playlists.py "/path/to/music" --dry-run
  ```
  Scans for albums containing audio files but no playlist, then creates simple M3U playlists with natural track ordering. Uses album-specific naming (e.g., "Dark Side of the Moon.m3u8") based on metadata or folder name.

- Audit album integrity (cover + playlists)
  ```bash
  python3 bin/music/check_album_integrity.py            # scans ${LIBRARY_ROOT}/CDs recursively
  python3 bin/music/check_album_integrity.py --show-ok  # include OK albums
  python3 bin/music/check_album_integrity.py --albums "Artist/Album"
  ```
  Verifies each album has a 1000×1000 `cover.jpg`, no `_cover.jpg`, and that `.m3u8` playlists match `.flac` files.

- Fix cover art dimensions
  ```bash
  # Preview what would be fixed (non-destructive)
  python3 bin/music/check_album_integrity.py --fix-covers --dry-run
  
  # Actually resize cover.jpg images that aren't 1000x1000
  python3 bin/music/check_album_integrity.py --fix-covers
  
  # Combine with other options
  python3 bin/music/check_album_integrity.py --albums "Artist/Album" --fix-covers --dry-run
  ```
  Uses ImageMagick (preferred) or Pillow to resize cover images to exactly 1000×1000 pixels. The `--dry-run` option shows what would be changed without modifying files.

- Download missing cover art
  ```bash
  # Preview what would be downloaded (non-destructive)
  python3 bin/music/check_album_integrity.py --get-covers --dry-run
  
  # Actually download missing cover.jpg images as _cover.jpg
  python3 bin/music/check_album_integrity.py --get-covers
  
  # Combine with fixing existing covers
  python3 bin/music/check_album_integrity.py --fix-covers --get-covers --dry-run
  ```
  Downloads album covers from MusicBrainz and saves them as `_cover.jpg` when `cover.jpg` is missing or too small for `--fix-covers` to handle. Skips download if `_cover.jpg` already exists or if `cover.jpg` is within `--fix-covers` tolerance. Requires `pip install requests mutagen`.

- Fetch missing cover art only
  - `python3 bin/music/fix_album_covers.py "/path/or/library/root"`
  - Scans for album folders containing FLACs but missing `cover.jpg`, downloads 1000x1000 JPEG.

- Compare two music libraries
  - `python3 bin/music/compare_music.py /old/library /new/library [--threshold 90] [--albums|--artists]`
  - Outputs: either grouped summary to stdout or writes `only_in_old.txt` and `only_in_new.txt`.

- Organize a single loose track
  - `python3 bin/music/fix_track.py /path/to/file.ext --target "${LIBRARY_ROOT}/Music"`
  - Attempts AcoustID+MusicBrainz; falls back to tags/filename; writes to `Artist/Album/NN - Title.ext`.

- Special-case split for a one-file album
  - `python3 bin/music/specialized/prince-lovesexy/split_lovesexy.py /path/to/Lovesexy.flac`
  - Uses fixed timestamps to create track files with safe filenames.

## Notes and caveats
- API keys: `bin/music/fix_track.py` contains a placeholder AcoustID key. Prefer setting via an environment variable; see Improvements.
- Rate limits: MusicBrainz/Cover Art Archive have usage policies. Scripts use `curl`/`jq`; adjust delays if needed.
- Archive folder: `_archive/` contains older or specialized tools; use with caution.

## Legal
These scripts are intended for making personal backups of media you own and for local, personal use only. Respect your jurisdiction’s laws and the terms of the services/APIs used.
