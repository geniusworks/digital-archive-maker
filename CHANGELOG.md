# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Lyrics downloader** (`bin/music/download_lyrics.py`) — Comprehensive lyrics fetching with Genius API + lyrics.ovh fallback, Jellyfin-compatible `.lrc` output, smart rate limiting, and album-by-album processing
- **Metadata fixer** (`bin/music/fix-missing-metadata.py`) — MusicBrainz-first metadata repair for FLAC, MP3, and MP4/M4A files with cached lookups and dry-run support
- **Manual genre tagger** (`bin/music/tag-manual-genre.py`) — Whitelist-validated manual genre assignment with bulk operations
- **Music video filename standardizer** (`bin/video/standardize_music_video_filenames.py`) — Enforces `{Artist} - {Title}.mp4` naming with metadata-based fallback
- **Music video metadata scanner** (`bin/video/scan_music_video_metadata.py`) — Finds and fills missing metadata using filename parsing
- **M3U8 playlist processor** (`bin/music/update-from-m3u.py`) — Updates filenames and metadata from M3U8 playlists with smart parsing
- **MP4 integrity checker** (`bin/video/utils/mp4_integrity_checker.py`) — Validates MP4 files for corruption
- **Playlist cleaner** (`bin/utils/clean_playlists.py`) — Normalizes and cleans M3U playlists
- Quick Start guide (`QUICKSTART.md`)
- Legal documentation: `DISCLAIMER.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- GitHub issue templates, PR template, and CI workflow
- Project logo and README badges

### Changed
- **Genre tagging system** (`bin/music/update-genre-mb.py`) — Complete rewrite with 100+ curated genres, Christmas auto-detection, genre transformers, and improved API reliability
- **TV show metadata** (`bin/tv/tag-show-metadata.py`) — Added manual TMDb/IMDb overrides, automatic override persistence, and IMDb fallback via OMDb
- **Video ripping** (`bin/video/rip_video.py`) — Unified DVD/Blu-ray pipeline with auto-detection, interactive subtitle handling, language policies, and automatic organization
- **Sync engine** (`bin/sync/master-sync.py`) — Two-phase sync with intelligent global delete mode and automatic explicit tagging before sync
- Music videos relocated from `/Music Videos/` to `/Videos/Music/` for better organization
- Dual-level Ctrl+C handling across all long-running scripts (graceful first, force second)
- README redesigned as concise hero page with feature tables

### Fixed
- HandBrake track numbering calculation (uses sequential position, not stream index)
- macOS colon-to-dash conversion in TV episode titles
- Genre transformer properly normalizes R&B, classical, and Latin variants
- Rejected genres log no longer accumulates duplicates across runs

## [0.1.0] - 2025-01-01

### Added
- Initial CD ripping pipeline with `abcde` + MusicBrainz
- Explicit content tagging via iTunes + MusicBrainz + Spotify
- Album integrity checker
- Cover art fetcher via Cover Art Archive
- Video ripping with MakeMKV + HandBrakeCLI
- Movie metadata tagging via TMDb/OMDb
- Movie ratings tagging with MPAA ratings
- Subtitle backfilling and VobSub-to-SRT conversion
- Library sync with explicit content filtering
- TV show renaming and metadata tagging

[Unreleased]: https://github.com/geniusworks/digital-archive-maker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/geniusworks/digital-archive-maker/releases/tag/v0.1.0
