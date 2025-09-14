# Media Server Setup and Naming Conventions (Plex/Jellyfin/Emby)

This guide outlines recommended folder structures and filenames so your media server (Plex/Jellyfin/Emby) can automatically match metadata.

---

## Library roots
- Music library root: `/Volumes/Data/Media/Rips/CDs`
- Video library root (examples):
  - Movies: `/Volumes/Data/Media/Rips/Movies`
  - TV: `/Volumes/Data/Media/Rips/TV`
  - Disc backups (raw MKV/MP4 by date): `/Users/<you>/Rips/DVDs` and `/Users/<you>/Rips/Blurays`

Use the date-based folders under your home dir (as in ripping guides) for staging. After verification/renaming, move items into the long-term library roots for your media server.

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
      Album.m3u
```

Notes:
- Various Artists: consider `Various/Album/NN - Artist - Title.flac` (see `VAOUTPUTFORMAT` in `.abcde.conf.sample`).
- Multi-disc albums: either separate as `Album (Disc 1)` / `Album (Disc 2)` or subfolders within the album.
- Keep `cover.jpg` at 1000x1000 for best compatibility with many clients.

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
- Ripping guides output to date-based folders (e.g., `~/Rips/DVDs/2025-09-13`). Verify, then rename/move into library roots.
- Tools such as FileBot or tinyMediaManager can speed up renaming based on online databases.

---

## Tips for scrapers
- Use the official names and years from The Movie Database (TMDb) or The TV Database (TVDb) for best matches.
- Avoid extra tags (e.g., `1080p`, `x264`) in filenames; put those into folder names or leave them out.
- Keep one show per top-level directory, one movie per directory.

---

## Legal
This setup is intended for personal backups of media you own, for local personal use only.
