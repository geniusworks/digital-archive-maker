# Disc-to-Digital Roadmap (CDs, DVDs, Blu‑rays)

Goal: Build a reliable, mostly automated pipeline to transfer disc-based media you own (for local, personal use) into clean, well-tagged digital files ready for a future media server.

## Current capabilities (from this repo)
- `.abcde.conf` — solid CD ripping config to FLAC with MusicBrainz lookup, M3U playlists, filename sanitization, and a post-encode eject hook.
- `fix_album.sh` — album-level normalization using MusicBrainz track titles, renames to `NN - Title.flac`, creates playlist, then runs tag + cover-art fixes.
- `fix_album_covers.sh` — fills in missing `cover.jpg` (1000×1000) via Cover Art Archive.
- `fix_metadata.py` — validates and (optionally) fixes `TITLE/ARTIST/ALBUM/TRACKNUMBER` based on `NN - Title.flac` and folder structure.
- `fix_track.py` — organizes a single loose track using tags/AcoustID/MusicBrainz → `Artist/Album/NN - Title.ext`.
- `compare_music.py` — fast fuzz-based comparison of two libraries; can group by artist/album or emit difference files.
- `bin/tag-explicit-mb.py` — per-track explicit tagging (`EXPLICIT=Yes|No|Unknown`) using manual overrides (`explicit_overrides.csv`) + iTunes + MusicBrainz; includes incremental mode and track-search fallback. Note: iTunes data is incomplete for older albums—use overrides for known false negatives.
- `bin/sync-to-jellyfin.py` — rsync-based sync helper that can exclude `EXPLICIT=Yes` and/or `EXPLICIT=Unknown` from a destination library.
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

## Phase 3 — Video discs (DVD/Blu‑ray) ✅ COMPLETED
**Status**: Core workflow implemented and battle-tested.

### Completed features:
- ✅ Unified `bin/rip_video.sh` — MakeMKV + HandBrakeCLI wrapper with:
  - Auto-detection of DVD vs Blu-ray discs (via `drutil` and `makemkvcon`)
  - Title-based or date-based staging folders
  - Automatic organization to `Movies/Title (Year)/` structure
  - Configurable minimum title length filtering (`MINLENGTH`)
- ✅ Audio/subtitle language handling:
  - Interactive prompts for non-English audio (prefer English audio, add English subs, or keep as-is)
  - Policy-based automation via `AUDIO_SUBS_POLICY` (prefer-audio, prefer-subs, prefer-burned, keep)
  - Automatic burn-in of English image-based subtitles (VobSub/PGS) for non-English audio when no soft subs available
  - **Fixed**: HandBrake track numbering calculation (uses sequential position, not stream index)
  - Post-mux of English text-based subtitles (SubRip/ASS/SSA/WebVTT) into MP4
- ✅ Backfill helper (`bin/backfill_subs.sh`) — mux English soft subs from MKV into existing MP4 without re-encoding
- ✅ OCR support for image-based subtitles:
  - Automatic extraction and OCR using Subtitle Edit + Tesseract (when tools available)
  - Manual OCR workflow with `vobsub-to-srt` helper for placeholder SRT creation
- ✅ Makefile integration:
  - `make install-video-deps` — one-command setup for all video tools
  - `make rip-video` / `make rip-movie` — streamlined ripping workflows
  - `make backfill-subs` — subtitle backfilling
- ✅ Comprehensive documentation in `docs/video_ripping_guide.md`

### Remaining enhancements:
- Metadata fetching via TMDb/OMDb (poster/backdrop/`.nfo` files)
- HDR10/SDR tone mapping strategies for UHD content
- TV series episode detection and naming automation

Dependencies (installed via `make install-video-deps`): `makemkv`, `handbrakecli`, `ffmpeg`, `mkvtoolnix`, `jq`, `tesseract`.

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

### Explicit content policy
- Maintain `EXPLICIT=Yes|No|Unknown` tags on the source archive.
- Sync to downstream servers with an explicit policy (e.g., exclude `Yes`, optionally exclude `Unknown`).

## Open technical questions
- Do we prefer embedded artwork in FLACs or external-only? Some servers prefer both.
- What default CRF/resolution for BD vs. DVD? Separate presets for mobile vs. TV playback?
- UHD/HDR handling: tone mapping vs. HDR10 pass-through strategies.
- Handling multi-disc albums, box sets, and bonus materials.

## Legal and usage note
All tools and processes here are for making copies of media you own for local, personal use only. Respect the laws of your jurisdiction, disc decryption rules, and API terms for metadata services.
