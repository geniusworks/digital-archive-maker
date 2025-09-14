# CD Ripping Guide (abcde)

This guide describes a consistent, reliable workflow for ripping audio CDs to FLAC on macOS using `abcde`, matching the configuration documented in this repository.

---

## Prerequisites
- macOS with Homebrew
- Core tools: `abcde`, `flac` (metaflac), `imagemagick` (`convert`/`magick`), `jq`, `curl`, `wget`, `ffmpeg`
- Python 3 (optional, for helper scripts) with packages from `requirements.txt`

Tip: Use `_install/install_setup_abcde_environment.sh` to verify/install common packages.

---

## Setup
1. Copy the sample configuration into place and adjust as needed:
   ```bash
   cp ./.abcde.conf.sample ~/.abcde.conf
   ```
2. Open `~/.abcde.conf` and verify the key settings:
   - `OUTPUTDIR="/Volumes/Data/Media/Rips/CDs"`
   - `OUTPUTFORMAT='${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}'`
   - `CDDBMETHOD=musicbrainz`
   - `GETALBUMART=y` and `COVERARTFILE="cover.jpg"`
   - Playlists enabled and disc eject after encode via `abcde_post_encode()`

---

## Rip a CD to FLAC
1. Insert a CD.
2. Run:
   ```bash
   abcde
   ```
3. Resulting structure (example):
   ```
   /Volumes/Data/Media/Rips/CDs/
     Artist/
       Album/
         01 - First Track.flac
         02 - Second Track.flac
         ...
         cover.jpg
         Album.m3u
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
  ./fix_track.py /path/to/file.ext --target "/Volumes/Data/Media/Rips/Digital"
  ```

---

## Notes
- Ensure your drive supports accurate audio extraction.
- If your mount point differs, update `OUTPUTDIR` in `~/.abcde.conf`.
- API usage policies (MusicBrainz, Cover Art Archive) apply; consider rate limits.

---

## Legal
This workflow is intended for creating personal backups of media you own, for local personal use only. Respect your jurisdiction’s laws and the terms of the services/APIs used.
