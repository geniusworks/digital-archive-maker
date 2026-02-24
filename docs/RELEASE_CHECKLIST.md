# Open Source Release: User Experience & Polish Checklist

This document outlines the roadmap to transform this project from a collection of powerful power-user scripts into a cohesive, delightful, and user-friendly toolkit. The target audience includes unsophisticated users who "just want to digitize their physical media and use Jellyfin to view it," while retaining the accuracy and granular control that power users expect.

## 1. Unified CLI & Stepwise Implementation
*Goal: Replace scattered scripts with a single, intuitive entry point that guides the user step-by-step based on their goals.*

- [ ] **Create a Unified Entry Point (`dl` or `digitize` command)**
  - Implement a modern CLI (using `click` or `typer` or `rich`) with clear subcommands: `dl rip`, `dl tag`, `dl sync`, `dl config`.
- [ ] **Goal-Oriented "A La Carte" Processing**
  - Allow users to specify exactly what they want to achieve.
  - E.g., `dl tag --music --lyrics --covers` vs `dl tag --music --basic-only`.
  - Introduce interactive prompts if run without flags: "What would you like to refine today? [ ] Basic Tags [ ] Lyrics [ ] High-Res Covers [ ] Explicit Ratings"
- [ ] **Smart Resumption & Idempotency**
  - If a user cancels a long process (like lyric fetching), the CLI should know exactly where it left off on the next run without requiring complex flags.

## 2. Workflow Optimization (The "Just Work" Philosophy)
*Goal: Minimize the number of decisions a user has to make to get a perfect result.*

- [ ] **Zero-Configuration Defaults**
  - Provide sensible defaults for ripping (e.g., standard FLAC for audio, high-quality Handbrake presets for video) that don't require tweaking.
- [ ] **Auto-Detection of Media**
  - `dl rip` should automatically detect if a CD, DVD, or Blu-ray is inserted and launch the correct underlying pipeline.
- [ ] **Seamless Pipeline Execution**
  - Allow a single command like `dl auto` that rips the inserted disc, fetches all metadata/lyrics/art, and syncs it to the Jellyfin directory in one smooth workflow.
- [ ] **Automated Path Management**
  - Abstract away the need to define exact source and destination paths for every command. Use a central `dl config` wizard to ask for the "Media Library folder" once.

## 3. User-Friendly Prompting & Interactive Conflict Resolution
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

## 4. Transparent Retry Logic & Smart Caching
*Goal: Network errors and API limits shouldn't crash the program or confuse the user.*

- [ ] **Transparent Exponential Backoff**
  - Instead of hanging or throwing an exception when an API rate limit is hit (e.g., Genius or TMDB), show a friendly spinner: *"Rate limit reached for Genius API. Waiting 15 seconds before retrying..."*
- [ ] **Clear Cache Indicators**
  - When running a tagger, indicate if data is being pulled from cache to explain why it's running so fast: *"Fetching movie metadata (using local cache)..."*
- [ ] **Graceful Degradation**
  - If a specific non-critical API is down (e.g., lyrics.ovh), note it cleanly in the summary rather than failing the whole tagging run: *"Skipped lyrics for 5 tracks (API currently unreachable)."*

## 5. Robust Error Handling & Actionable Advice
*Goal: Eliminate stack traces for expected user errors (like missing dependencies or API keys).*

- [ ] **Pre-Flight Dependency Checks**
  - Run a quick check before a command starts to ensure `ffmpeg`, `HandBrakeCLI`, `abcde`, etc., are installed. If missing, provide the exact command to install them (e.g., *"Please run `brew install handbrake`"*).
- [ ] **Actionable API Key Errors**
  - If TMDB lookup fails due to authentication, print: *"❌ TMDB API Key is missing or invalid. Please get an API key from TMDB and run `dl config` to set it."*
- [ ] **Beautiful Progress & Output Formatting**
  - Use `rich` for Python terminal output to provide clean tables, progress bars, and color-coded success/warning/error messages.

## 6. Code Simplification & Modularization
*Goal: Make the codebase welcoming for open-source contributors.*

- [ ] **Consolidate Duplicate Logic**
  - Move shared logic (like API rate limiting, cache loading/saving, and override parsing) into a central `dl_core/` Python package.
- [ ] **Standardize Configuration**
  - Move away from mixed `.env` variables and hardcoded paths toward a single `config.toml` or `config.yaml` managed via the CLI.
- [ ] **Decouple Shell and Python**
  - Where possible, rewrite complex bash scripts (like `rip_video.sh`) in Python using `subprocess`, enabling better cross-platform compatibility and richer interactive prompts.

## 7. Documentation & Onboarding
*Goal: A user should feel confident and excited after reading the README.*

- [ ] **Interactive Setup Wizard (`setup.py`)**
  - A friendly script that runs on first clone to initialize directories, check dependencies, and set up API keys.
- [ ] **"Zero to Jellyfin" Visual Guide**
  - Step-by-step Markdown guide with terminal screenshots and Jellyfin UI screenshots showing the exact workflow from inserting a physical disc to watching it.
- [ ] **Architecture Map**
  - A simple diagram for contributors explaining how the ripping, tagging, caching, and syncing modules interact.