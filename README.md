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
- `make rip-cd` — run `abcde` using your `~/.abcde.conf`
- `make rip-video TYPE=dvd|bluray` — call `bin/rip_video.sh` for video discs
- `make rip-movie TYPE=dvd|bluray TITLE="Movie Name" YEAR=1999` — rip and organize the main feature to `Movies/Title (Year)/Title (Year).mp4`
- Notes: you can set `MINLENGTH=1800` to skip short titles and `DEST_CATEGORY=Films` to change the destination category from `Movies`.
- `make fix-album DIR="/path/to/Artist/Album"` — normalize, tag, covers, playlist
- `make fetch-covers ROOT="/path/or/library"` — fetch missing `cover.jpg`
- `make fix-track FILE="/path/file.ext" TARGET="${RIPS_ROOT}/Digital"` — organize a single track
- `make compare OLD="/old" NEW="/new" [MODE=albums|artists] [THRESHOLD=90]` — compare two libraries

## Typical workflows
- Rip a CD to FLAC
  1. Insert disc; run `abcde` (uses `.abcde.conf`).
  2. Result at `${RIPS_ROOT}/CDs/Artist/Album/NN - Title.flac` with `cover.jpg` and playlist.

- Rip and organize a DVD/Blu-ray
  - Staging only:
    - `make rip-video TYPE=dvd` (or `TYPE=bluray`). In an interactive terminal, the script can prompt to name the staging folder and optionally organize afterward.
  - Rip + organize in one step:
    - `make rip-movie TYPE=dvd TITLE="Movie Name" YEAR=1999`
    - Moves the largest MP4 to `${RIPS_ROOT}/Movies/Movie Name (1999)/Movie Name (1999).mp4`; keeps MKVs (and any extras) under `${RIPS_ROOT}/DVDs/` or `${RIPS_ROOT}/Blurays/`.

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
