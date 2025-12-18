# Media Server Setup and Naming Conventions (Plex/Jellyfin/Emby)

This guide outlines recommended folder structures and filenames so your media server (Plex/Jellyfin/Emby) can automatically match metadata.

---

## Library roots
- Music library root: `/Volumes/Data/Media/Rips/CDs`
- Video library root (examples):
  - Movies: `/Volumes/Data/Media/Rips/Movies`
  - TV: `/Volumes/Data/Media/Rips/TV`
  - Disc backups (raw MKV/MP4 by title or date): `${RIPS_ROOT:-/Volumes/Data/Media/Rips}/DVDs` and `${RIPS_ROOT:-/Volumes/Data/Media/Rips}/Blurays`

Note: `RIPS_ROOT` is centralized in `.env` (see `.env.sample`). Make targets auto-load `.env`.

Use the title-named (preferred when Title/Year are known) or date-based folders under `${RIPS_ROOT}` for staging. After verification/renaming, move items into the long-term library roots for your media server.

---

## Music naming (albums)
Recommended structure (matches `abcde` config in this repo):
```
/Volumes/Data/Media/Rips/CDs/
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
This repo supports explicit content tagging via per-track FLAC metadata, which can later drive sync policies (e.g., skip explicit content on a destination Jellyfin server).

### Tagging
- Script: `bin/tag-explicit-mb.py`
- Writes a per-track tag: `EXPLICIT=Yes|No|Unknown`
- Output files (repo-local):
  - `./log/explicit_tagging.log`
  - `./log/explicit_tagging_errors.log`
  - `./log/explicit_tagging_cache.json`
- Also writes a playlist file at the music library root:
  - `/Volumes/Data/Media/Rips/CDs/Explicit.m3u8`

### Syncing to a Jellyfin server (optional)
If your source archive contains both explicit and non-explicit content, you can sync to a destination server while excluding content based on the `EXPLICIT` tag.

- Script: `bin/sync-to-jellyfin.py`
- Options:
  - `--exclude-explicit` skips `EXPLICIT=Yes`
  - `--exclude-unknown` skips `EXPLICIT=Unknown` and missing tags
  - `--dry-run` previews the copy plan

Example:
```
python3 bin/sync-to-jellyfin.py \
  --src "/Volumes/Data/Media/Rips/CDs" \
  --dest "/path/to/jellyfin/music" \
  --exclude-explicit \
  --dry-run
```

---

## Movie naming
Follow Plex/Jellyfin recommendations:
```
/Volumes/Data/Media/Rips/Movies/
  Movie Name (Year)/
    Movie Name (Year).mp4
    Movie Name (Year).nfo   # optional
```

- Avoid extra text in filenames; prefer the title and year only.
- Keep one movie per folder named exactly as the file.

---

## TV series naming
```
/Volumes/Data/Media/Rips/TV/
  Show Name/
    Season 01/
      Show Name - S01E01 - Episode Title.mp4
      Show Name - S01E02 - Episode Title.mp4
```

- Specials: `Season 00` with `S00EXX` numbering.
- Multi-episode files: `S01E01E02`.

---

## Moving from staging to library
- Ripping guides output to title-named folders when Title/Year are provided or prompted (e.g., `${RIPS_ROOT}/DVDs/Movie Name (1999)`), otherwise to date-based folders (e.g., `${RIPS_ROOT}/DVDs/2025-09-13`). Verify, then rename/move into library roots as needed.
- Tools such as FileBot or tinyMediaManager can speed up renaming based on online databases.

### Backfilling English subtitles into existing MP4s
If your MP4 is missing English soft subtitles but the archival MKV has them (as text subs), you can mux them in without re-encoding:

```
make backfill-subs \
  SRC_DIR="${RIPS_ROOT}/DVDs/Movie Name (Year)" \
  DST_DIR="${RIPS_ROOT}/Movies/Movie Name (Year)" \
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
