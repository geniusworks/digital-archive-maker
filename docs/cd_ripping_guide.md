# CD Ripping Guide (abcde)

This guide describes a consistent, reliable workflow for ripping audio CDs to FLAC on macOS using `abcde`, matching the configuration documented in this repository.

See also: `docs/workflow_overview.md` for the full end-to-end pipeline (CDs → FLACs → explicit tagging → sync).

---

## Prerequisites
- macOS with Homebrew
- Core tools: `abcde`, `flac` (metaflac), `imagemagick` (`convert`/`magick`), `jq`, `curl`, `wget`, `ffmpeg`
- Python 3 (optional, for helper scripts) with packages from `requirements.txt`

Tip: Use `_install/install_setup_abcde_environment.sh` to verify/install common packages.

---

## Setup
1. Create and load environment config (centralized):
   ```bash
   cp .env.sample .env   # at repo root
   # Option A: let the Makefile load .env automatically (recommended)
   # Option B: source it in your shell profile so abcde sees RIPS_ROOT
   #   echo 'set -a; . /path/to/repo/.env; set +a' >> ~/.zshrc
   ```

2. Copy the sample abcde configuration into place and adjust as needed:
   ```bash
   cp ./.abcde.conf.sample ~/.abcde.conf
   ```
3. Open `~/.abcde.conf` and verify the key settings:
   - `OUTPUTDIR="${RIPS_ROOT}/CDs"` (defaults to `/Volumes/Data/Media/Rips/CDs` if `RIPS_ROOT` is unset)
   - `OUTPUTFORMAT='${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}'`
   - `ACTIONS=cddb,getalbumart,encode,tag,move,playlist,clean`
   - `COVERFILE="cover.jpg"`
   - `PLAYLISTS=y` and playlist format ending in `.m3u8`
   - Disc eject after encode via `EJECTCD=y`

Note: `~/.abcde.conf` uses `RIPS_ROOT` from the environment (defined in `.env`) to set `OUTPUTDIR`. When you run `make rip-cd`, the Makefile auto-loads `.env` so `abcde` sees `RIPS_ROOT`.

---

## Rip a CD to FLAC
1. Insert a CD.
2. Run (standard):
   ```bash
   make rip-cd
   ```
   Alternative (direct):
   ```bash
   # ensure your shell has loaded ./.env so RIPS_ROOT is available
   set -a; . ./.env; set +a
   abcde
   ```
3. Resulting structure (example):
   ```
   ${RIPS_ROOT}/CDs/
     Artist/
       Album/
         01 - First Track.flac
         02 - Second Track.flac
         ...
         cover.jpg
         Album.m3u8
   ```

`abcde` will look up metadata from MusicBrainz, fetch cover art, write a playlist, sanitize filenames, and eject the disc when done (per the provided config).

---

## Post-processing helpers (optional)
- Normalize/complete an album folder:
  ```bash
  ./fix_album.sh "/path/to/Artist/Album"
  ```
- Fetch missing cover art only:
  ```bash
  ./fix_album_covers.sh "/path/or/library/root"
  ```
- Organize a single loose track:
  ```bash
  ./fix_track.py /path/to/file.ext --target "${RIPS_ROOT}/Digital"
  ```

---

## Notes
- Ensure your drive supports accurate audio extraction.
- Prefer changing `RIPS_ROOT` in `.env` to relocate outputs for all workflows; or override `OUTPUTDIR` in `~/.abcde.conf` if needed.
- API usage policies (MusicBrainz, Cover Art Archive) apply; consider rate limits.

---

## Legal
This workflow is intended for creating personal backups of media you own, for local personal use only. Respect your jurisdiction’s laws and the terms of the services/APIs used.
