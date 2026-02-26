# Open Source Release: User Experience & Polish Checklist

This document outlines the roadmap to transform this project from a collection of powerful power-user scripts into a cohesive, delightful, and user-friendly toolkit. The target audience includes unsophisticated users who "just want to digitize their physical media and use Jellyfin to view it," while retaining the accuracy and granular control that power users expect.

## 1. Unified CLI & Stepwise Implementation
*Goal: Replace scattered scripts with a single, intuitive entry point that guides the user step-by-step based on their goals.*

- [ ] **Create a Unified Entry Point (`dl` or `digitize` command)**
  - Implement a modern CLI (using `click`, `typer`, or `rich`) with clear subcommands: `dl rip`, `dl tag`, `dl sync`, `dl config`.
- [ ] **Goal-Oriented "A La Carte" Processing**
  - Allow users to specify exactly what they want to achieve.
  - E.g., `dl tag --music --lyrics --covers` vs `dl tag --music --basic-only`.
  - Introduce interactive prompts if run without flags: "What would you like to refine today? [ ] Basic Tags [ ] Lyrics [ ] High-Res Covers [ ] Explicit Ratings"
- [ ] **Feature-Driven API Onboarding**
  - Instead of demanding all API keys upfront, prompt for them *only* when a user requests a feature that requires them.
  - E.g., If they select "Lyrics", prompt: *"To fetch lyrics, you need a free Genius API key. Go to [URL] to get one, and paste it here: "*
  - Save provided keys securely to the central configuration.

## 2. Non-Destructive Idempotency & Workflow Safety
*Goal: Users should feel safe experimenting. The system should never destroy existing work unless explicitly instructed.*

- [ ] **Safe Resumption & Additive Processing**
  - If a user re-runs a command with new requirements (e.g., adding lyrics to an already-tagged library), the system must *add* the new data without disturbing or deleting the existing metadata.
- [ ] **Explicit Deletion Confirmation**
  - Require a double-confirmation (e.g., typing out the folder name or adding a `--force-overwrite` flag) before replacing, overwriting, or deleting existing files or high-quality artwork.
- [ ] **Smart Sync Dry-Run**
  - Make `dl sync --dry-run` the default behavior if no flags are provided, showing exactly what will be copied, deleted, or skipped.
  - Require a `--confirm` or `-y` flag to actually execute the sync, preventing accidental deletions.

## 3. Workflow Optimization (The "Just Work" Philosophy)
*Goal: Minimize the number of decisions a user has to make to get a perfect result.*

- [ ] **Zero-Configuration Defaults**
  - Provide sensible defaults for ripping (e.g., standard FLAC for audio, high-quality Handbrake presets for video) that don't require tweaking.
- [ ] **Auto-Detection of Media**
  - `dl rip` should automatically detect if a CD, DVD, or Blu-ray is inserted and launch the correct underlying pipeline.
- [ ] **Automated Path Management**
  - Abstract away the need to define exact source and destination paths for every command. Use a central `dl config` wizard to ask for the "Media Library folder" once.

## 4. User-Friendly Prompting & Interactive Conflict Resolution
*Goal: Never fail silently, and never make a destructive guess without asking.*

- [ ] **Interactive Disambiguation**
  - When TMDB, OMDB, or MusicBrainz returns multiple close matches for a movie or album, pause and present a numbered list: 
    *"Found multiple matches for 'Dune'. Which is correct?"*
    *[1] Dune (1984) - Directed by David Lynch*
    *[2] Dune: Part One (2021) - Directed by Denis Villeneuve*
- [ ] **Smart Overrides**
  - When the user resolves a conflict interactively, automatically save that choice to the respective `config/` override files so they never have to answer the same question twice.
- [ ] **Interactive Video Ripping Options**
  - Read disc contents and ask in plain English: *"Found 1 Main Feature (1h 45m) and 3 Extras. Rip all, or just the Main Feature?"*
  - Ask about subtitles simply: *"This is a foreign language film. Do you want English subtitles burned in? (Y/n)"*

## 5. Transparent Retry Logic & Smart Caching
*Goal: Network errors and API limits shouldn't crash the program or confuse the user.*

- [ ] **Transparent Exponential Backoff**
  - Instead of hanging or throwing an exception when an API rate limit is hit (e.g., Genius or TMDB), show a friendly spinner: *"Rate limit reached for Genius API. Waiting 15 seconds before retrying..."*
- [ ] **Clear Cache Indicators**
  - When running a tagger, indicate if data is being pulled from cache to explain why it's running so fast: *"Fetching movie metadata (using local cache)..."*
- [ ] **Graceful Degradation**
  - If a specific non-critical API is down (e.g., lyrics.ovh), note it cleanly in the summary rather than failing the whole tagging run: *"Skipped lyrics for 5 tracks (API currently unreachable)."*

## 6. Repository Cleanup: Solidifying the Core
*Goal: Scour the repo to consolidate permanent features and remove or deprecate transitory "fixer" scripts that complicate the codebase.*

- [ ] **Consolidate the `music` Pipeline**
  - **Core Features to Keep:** `tag-explicit-mb.py` (explicit tagging), `download_lyrics.py` (lyrics fetching), `update-genre-mb.py` (genre tagging), `generate-playlists.py` (M3U generation), `check_album_integrity.py` (validation).
  - **Transitory/Fixer Scripts to Deprecate or Move to `utils/`:** `fix-missing-metadata.py`, `fix-single-title.py`, `fix-track-numbers.py`, `fix-unknown-album.py`, `fix_album.py`, `fix_album_covers.py`, `fix_metadata.py`, `fix_track.py`, `repair-flac-tags.py`, `set_explicit.py`. These were likely written to fix specific historical library issues and confuse new users.
- [ ] **Consolidate the `video` Pipeline**
  - **Core Features to Keep:** `rip_video.py` / `bluray_to_mp4.zsh` (ripping), `tag-movie-metadata.py` (metadata), `tag-movie-ratings.py` (ratings), `vobsub_to_srt.py` / `backfill_subs.py` (subtitles).
  - **Transitory/Fixer Scripts to Deprecate or Move to `utils/`:** `repair_mp4.sh`, `optimize_mp4_streaming.py`, `embed_thumbnail.py`, `fix_music_videos_mapped.py`, `fix_music_videos_secondary.py`.
  - **Optional Enhancements to Add:**
    - **PGS to SRT OCR Conversion:** Add support for converting Blu-ray PGS (image-based) subtitles to SRT text files using Tesseract OCR. This would extract subtitles from discs like "Silent Running" that only have image-based subtitles, improving subtitle coverage across more Blu-ray releases.
- [ ] **Consolidate the `tv` Pipeline**
  - **Core Features to Keep:** `tag-show-metadata.py`, `rename_shows_jellyfin.py`.
- [ ] **Consolidate the `sync` Pipeline**
  - **Core Features to Keep:** `master-sync.py`, `sync-library.py`, `sync-config.yaml`.

## 7. Documentation & Onboarding
*Goal: A user should feel confident and excited after reading the README.*

- [ ] **"Zero to Jellyfin" Visual Guide**
  - Step-by-step Markdown guide with terminal screenshots and Jellyfin UI screenshots showing the exact workflow from inserting a physical disc to watching it.
- [ ] **Architecture Map**
  - A simple diagram for contributors explaining how the ripping, tagging, caching, and syncing modules interact.