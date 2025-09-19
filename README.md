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
  - `install_setup_abcde_environment.sh` — checks/installs Homebrew deps (abcde, eye-d3, flac, imagemagick, wget, curl) and creates an example cleanup helper.
  - `install_cleanup_abcde_xs.sh` — removes an incompatible `DiscID.bundle` in some abcde installs.
- `_archive/` (kept for reference)
  - `backup_cover_art.sh` — finds `cover.jpg`, logs dimensions, renames non-1000x1000 covers to `_cover.jpg`.
  - `check_flac_metadata.py` — compares FLAC tags to MusicBrainz; respects a skip list in `check_flac_metadata.skip`.
- `fix_album.sh` — given an album folder, fetches track titles from MusicBrainz, renames `*.flac` to `NN - Title.flac`, makes an `.m3u`, runs `fix_metadata.py --fix`, then `fix_album_covers.sh`.
- `fix_album_covers.sh` — finds albums missing `cover.jpg` and downloads a 1000x1000 front cover from Cover Art Archive (via MusicBrainz).
- `fix_metadata.py` — checks/updates FLAC tags (TITLE, ARTIST, ALBUM, TRACKNUMBER) based on the path/filename pattern `NN - Title.flac`.
- `fix_track.py` — organizes a single loose track into `Artist/Album/NN - Title.ext`. Attempts metadata from tags, AcoustID, MusicBrainz; falls back to filename parsing.
- `compare_music.py` — fast fuzzy comparison of two library roots; can group differences by album/artist.
- `compare_music 2025-08-30.py` — earlier implementation of compare tool (kept for reference).
- `prince-lovesexy/split_lovesexy.sh` — example special-case splitter for a single-file album (`ffmpeg`-based).
- `.abcde.conf.sample` — sample abcde configuration matching this repo's defaults.
- `.env.sample` — example environment variables (e.g., `ACOUSTID_API_KEY`).
- `disc_ripping_guide.md` — earlier combined guide for CDs/DVDs/Blu-rays (kept for reference).

## Prerequisites
- macOS with Homebrew.
- Core tools: `abcde`, `flac` (metaflac), `imagemagick` (`convert`/`magick`), `jq`, `curl`, `wget`, `ffmpeg`.
  - Use `_install/install_setup_abcde_environment.sh` to verify/install common packages.
- Python 3 with packages:
  - `mutagen`, `rapidfuzz`, `musicbrainzngs`, `acoustid`
  - Install via `requirements.txt`:
    - Create venv: `python3 -m venv ~/venvs/media && source ~/venvs/media/bin/activate`
    - Install deps: `pip install -r requirements.txt`
  - Example manual install: `pip install mutagen rapidfuzz musicbrainzngs pyacoustid`
- Accounts/keys (optional but recommended):
  - AcoustID API key for `fix_track.py`.
    - Set in your shell: `export ACOUSTID_API_KEY=...`
    - Or copy `.env.sample` to `.env` and load it via your shell init or a tool like `direnv`.

## Guides
- CD ripping: see `docs/cd_ripping_guide.md`.
- DVD/Blu-ray ripping: see `docs/video_ripping_guide.md`.
- Media server setup: see `docs/media_server_setup.md`.

## Configuration: `.abcde.conf`
- Output: `FLAC` to `${RIPS_ROOT}/CDs` (defaults to `/Volumes/Data/Media/Rips/CDs`) using format `${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}`.
- Uses MusicBrainz for album/track lookup and `getalbumart` in the `ACTIONS` chain.
- Playlists enabled (`.m3u`).
- Ejects the disc after encoding via `abcde_post_encode` using `drutil` (currently `EJECTCD=n` but eject occurs in the hook).
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
- `make rip-video [TYPE=dvd|bluray]` — call `bin/rip_video.sh` for video discs (auto-detects disc type if TYPE omitted)
- `make rip-movie [TYPE=dvd|bluray] TITLE="Movie Name" YEAR=1999` — rip and organize the main feature to `Movies/Title (Year)/Title (Year).mp4` (auto-detects disc type if TYPE omitted)
- Notes: you can set `MINLENGTH=1800` to skip short titles and `DEST_CATEGORY=Films` to change the destination category from `Movies`.
- `make fix-album DIR="/path/to/Artist/Album"` — normalize, tag, covers, playlist
- `make fetch-covers ROOT="/path/or/library"` — fetch missing `cover.jpg`
- `make fix-track FILE="/path/file.ext" TARGET="${RIPS_ROOT}/Digital"` — organize a single track
- `make compare OLD="/old" NEW="/new" [MODE=albums|artists] [THRESHOLD=90]` — compare two libraries
- `make backfill-subs SRC_DIR="/path/to/source_mkv_dir" DST_DIR="/path/to/target_mp4_dir" [INPLACE=yes] [DEFAULT=yes]` — mux English soft subs from MKV into existing MP4
- `make vobsub-to-srt FILE="/path/to/subtitle.idx"` — convert VobSub files to placeholder SRT for muxing

## Typical workflows
- Rip a CD to FLAC
  1. Insert disc; run `abcde` (uses `.abcde.conf`).
  2. Result at `${RIPS_ROOT}/CDs/Artist/Album/NN - Title.flac` with `cover.jpg` and playlist.

- Rip and organize a DVD/Blu-ray
  - Staging only:
    - `make rip-video` (auto-detects disc type). In an interactive terminal, the script can prompt to name the staging folder and optionally organize afterward.
  - Rip + organize in one step:
    - `make rip-movie TITLE="Movie Name" YEAR=1999` (auto-detects disc type)
    - Moves the largest MP4 to `${RIPS_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`; keeps MKVs (and any extras) under `${RIPS_ROOT}/DVDs/` or `${RIPS_ROOT}/Blurays/`.
  - Auto-detection: The script now automatically detects DVD vs Blu-ray discs. You can still override with `TYPE=dvd` or `TYPE=bluray` if needed.

- Backfill English subtitles into an existing MP4
  - Create a new MP4 with subs next to the original:
    ```bash
    make backfill-subs \
      SRC_DIR="${RIPS_ROOT}/DVDs/Movie Name (Year)" \
      DST_DIR="${RIPS_ROOT}/Movies/Movie Name (Year)"
    ```
  - Replace the original in-place and mark subs default:
    ```bash
    make backfill-subs \
      SRC_DIR="${RIPS_ROOT}/DVDs/Movie Name (Year)" \
      DST_DIR="${RIPS_ROOT}/Movies/Movie Name (Year)" \
      INPLACE=yes DEFAULT=yes
    ```
  - For image-based subtitles (VobSub/PGS): The script will extract subtitle files and provide guidance for manual OCR using tools like Subtitle Edit.

- Convert VobSub to SRT (for manual OCR workflow)
  ```bash
  make vobsub-to-srt FILE=".backfill_ocr_12345.idx"
  ```
  Creates a placeholder SRT file for immediate muxing. For full OCR, use Subtitle Edit GUI with the corresponding .sub file.

- Normalize and complete an album folder
  1. `./fix_album.sh "/path/to/Artist/Album"`
  2. Script fetches MusicBrainz release, renames files to track order, writes `Album.m3u`, fixes tags, and fetches `cover.jpg` if missing.

- Fetch missing cover art only
  - `./fix_album_covers.sh "/path/or/library/root"`
  - Scans for album folders containing FLACs but missing `cover.jpg`, downloads 1000x1000 JPEG.

- Compare two music libraries
  - Fast tool: `./compare_music.py /old/library /new/library [--threshold 90] [--albums|--artists]`
  - Outputs: either grouped summary to stdout or writes `only_in_old.txt` and `only_in_new.txt`.

- Organize a single loose track
  - `./fix_track.py /path/to/file.ext --target "${RIPS_ROOT}/Digital"`
  - Attempts AcoustID+MusicBrainz; falls back to tags/filename; writes to `Artist/Album/NN - Title.ext`.

- Special-case split for a one-file album
  - `./prince-lovesexy/split_lovesexy.sh /path/to/Lovesexy.flac`
  - Uses fixed timestamps to create track files with safe filenames.

## Notes and caveats
- API keys: `fix_track.py` contains a placeholder AcoustID key. Prefer setting via an environment variable; see Improvements.
- Rate limits: MusicBrainz/Cover Art Archive have usage policies. Scripts use `curl`/`jq`; adjust delays if needed.
- Archive folder: `_archive/` contains older or specialized tools; use with caution.

## Legal
These scripts are intended for making personal backups of media you own and for local, personal use only. Respect your jurisdiction’s laws and the terms of the services/APIs used.
