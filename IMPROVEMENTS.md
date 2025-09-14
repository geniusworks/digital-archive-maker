# Disc-to-Digital Roadmap (CDs, DVDs, Blu‑rays)

Goal: Build a reliable, mostly automated pipeline to transfer disc-based media you own (for local, personal use) into clean, well-tagged digital files ready for a future media server.

## Current capabilities (from this repo)
- `.abcde.conf` — solid CD ripping config to FLAC with MusicBrainz lookup, M3U playlists, filename sanitization, and a post-encode eject hook.
- `fix_album.sh` — album-level normalization using MusicBrainz track titles, renames to `NN - Title.flac`, creates playlist, then runs tag + cover-art fixes.
- `fix_album_covers.sh` — fills in missing `cover.jpg` (1000×1000) via Cover Art Archive.
- `fix_metadata.py` — validates and (optionally) fixes `TITLE/ARTIST/ALBUM/TRACKNUMBER` based on `NN - Title.flac` and folder structure.
- `fix_track.py` — organizes a single loose track using tags/AcoustID/MusicBrainz → `Artist/Album/NN - Title.ext`.
- `compare_music.py` — fast fuzz-based comparison of two libraries; can group by artist/album or emit difference files.
- `_install/` — installers to set up core dependencies and fix a known abcde issue on macOS.
- `prince-lovesexy/split_lovesexy.sh` — example special-case splitter for a single-file album.

## Phase 1 — Harden the CD pipeline
- ReplayGain and loudness:
  - Keep using `USERPLAYGAIN=y` for tagging. Consider an optional step to write album/track ReplayGain tags for consistent playback.
- Accurate ripping and verification:
  - Ensure secure reading with `cdparanoia` settings in `.abcde.conf`.
  - Save abcde and cdparanoia logs per album for auditability.
  - Generate per-album checksums (`SHA256SUMS`) after rip and after any metadata changes.
- Metadata fidelity:
  - Persist the chosen MusicBrainz release ID (e.g., write `MUSICBRAINZ_ALBUMID` / `MUSICBRAINZ_RELEASEGROUPID`) so re-runs are deterministic.
  - Add `DISCTOTAL`/`DISCNUMBER` where applicable; improve handling of `Various Artists`.
- Cover art:
  - Standardize external `cover.jpg` at 1000×1000.
  - Optional: embed the cover into each FLAC (`metaflac --import-picture-from`) while also keeping `cover.jpg` for media servers.
- Logging and observability:
  - Central `logs/` with timestamped runs, plus a summary CSV per session (albums processed, errors, durations).
- Safety/keys:
  - Move API keys and toggles to environment variables (`.env` pattern) and reference them in scripts.

Deliverables:
- `generate_checksums.sh` — writes/verifies `SHA256SUMS` in each album folder.
- `embed_cover_art.py` — embeds `cover.jpg` into FLACs (idempotent).
- Add env support to scripts and document `.env.sample`.

## Phase 2 — Library health and dedup
- Health checks:
  - Walk the library and validate: tag completeness, presence of `cover.jpg`, filename conformity, playlist freshness.
  - Report-only mode vs. `--fix` mode.
- Deduplication:
  - Duplicate detection via normalized path+tags; optionally via acoustic fingerprinting (`fpcalc`/Chromaprint) for FLACs.
- Unicode/FS normalization:
  - Enforce NFC normalization on filenames; unify whitespace and dash conventions.

Deliverables:
- `audit_library.py` — generates a HTML/CSV report (missing tags/covers, nonconforming names, duplicates).
- `dedupe_library.py` — identifies (& optionally resolves) duplicates safely.

## Phase 3 — Add video discs (DVD/Blu‑ray)
- Ripping strategy:
  - Use MakeMKV to decrypt/remux to MKV (preserve quality, chapters, multiple audio tracks, forced subs).
  - Optionally transcode with HandBrakeCLI (`H.264`/`H.265`) using device-friendly presets; keep originals or maintain a mezzanine tier.
- Subtitles and audio:
  - Extract and tag forced subtitles.
  - Pass-through key audio (e.g., AC-3, DTS) and add an AAC stereo downmix for compatibility.
- Naming & metadata for media servers (Plex/Jellyfin/Emby):
  - Movies: `Movies/Movie Name (Year)/Movie Name (Year).mkv`
  - TV: `TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.mkv`
  - Fetch metadata/poster via TMDb/OMDb; respect API terms and rate limits.

Deliverables:
- `rip_bluray.sh` / `rip_dvd.sh` — MakeMKV wrappers with title selection, language filters, logging.
- `transcode_video.sh` — HandBrakeCLI presets for Movies/TV; HDR10/SDR considerations.
- `fetch_video_metadata.py` — pulls TMDb/OMDb data and writes poster/backdrop and optional `.nfo` files.

Dependencies (macOS/Homebrew examples): `makemkv`, `handbrakecli`, `ffmpeg`, `mkvtoolnix`, `mediainfo`.

## Phase 4 — Orchestration and UX
- Unified CLI:
  - `media_cli.py` — a single entrypoint to run rip/normalize/audit/compare flows with subcommands.
- Config management:
  - `media.yml` config for paths, quality presets, account keys; environment overrides.
- Queues and parallelization:
  - Batch mode for multiple discs/albums; parallel cover downloads; safe concurrency controls.

## Phase 5 — Media server readiness
- Target servers: Plex, Jellyfin, Emby (select later).
- Library layout under a common root, e.g., `/Volumes/Data/Media/`:
  - `Music/Artist/Album/NN - Title.flac`
  - `Movies/Movie Name (Year)/Movie Name (Year).mkv`
  - `TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.mkv`
- Integrity and backup:
  - Maintain checksums and a backup plan (local + offsite).
  - Periodic re-scan jobs and health reports.

## Open technical questions
- Do we prefer embedded artwork in FLACs or external-only? Some servers prefer both.
- What default CRF/resolution for BD vs. DVD? Separate presets for mobile vs. TV playback?
- UHD/HDR handling: tone mapping vs. HDR10 pass-through strategies.
- Handling multi-disc albums, box sets, and bonus materials.

## Legal and usage note
All tools and processes here are for making copies of media you own for local, personal use only. Respect the laws of your jurisdiction, disc decryption rules, and API terms for metadata services.
