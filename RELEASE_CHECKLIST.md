# Release Checklist: v1.0.0 Public Release

> **Single source of truth** for everything needed to ship Digital Archive Maker as a polished, delightful, public open-source tool.
>
> Target: a user who "just wants to digitize their physical media and watch it on Jellyfin" — while retaining power-user depth underneath.

---

## Current State (March 2026)

| Area | Status | Notes |
|------|--------|-------|
| **Functionality** | ✅ Complete | CD / DVD / Blu-ray / TV / Music Video / Sync pipelines all working |
| **Legal & Compliance** | ✅ Complete | LICENSE, DISCLAIMER, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, NOTICE |
| **Community Infra** | ✅ Complete | Issue templates, PR template, CI workflow |
| **README / QUICKSTART** | ✅ Solid | Redesigned hero page, badges, Quick Start guide |
| **Documentation** | ✅ Consolidated | 6 docs + 2 server guides — overlap eliminated |
| **Code Quality** | ✅ Complete | Shared library, type hints, comprehensive test suite, clean CI pipeline, professional polish |
| **User Experience** | ✅ Complete | ENTER key support, ASCII spinners, visual progress feedback, celebratory completion |
| **GUI App** | ✅ Complete | Electron wrapper with dashboard, console, settings (runs from repo) |
| **Visual / Delight** | ✅ Complete | ASCII spinners, emoji feedback, professional CLI interface, comprehensive status messages |

---

## A. Repository Hygiene (Do First)

### A1. Root-Level File Cleanup
- [x] Create `CHANGELOG.md` (was referenced by README badge but missing)
- [x] Fix `pyproject.toml` — wrong project name, wrong URLs, wrong author
- [x] Fix `NOTICE` — wrong project name and author
- [x] Consolidate `requirements-lyrics.txt` into `requirements.txt`; add missing `Pillow`
- [x] Fix `QUICKSTART.md` — env vars didn't match `.env.example`
- [x] **Delete `requirements-lyrics.txt`** (now redundant)
- [x] **Delete `TODO.md`** (content absorbed here and into `CHANGELOG.md`)
- [x] **Delete `IMPROVEMENTS.md`** (changelog → `CHANGELOG.md`; capabilities already documented in guides)
- [x] Verify no remaining broken links across all `.md` files
- [ ] Final PII / secrets scan of all tracked files before public push

### A2. Directory Cleanup
- [x] Remove empty `explicit/` directory (no `.gitkeep`, no purpose)
- [x] Verify `_archive/` and `_install/` remain gitignored (local-only; not shipped)
- [x] Add `.gitkeep` to `log/` and `cache/` if not already present
- [x] Confirm `config/` ships only `.gitkeep` (user-specific overrides stay local)

### A3. Dependency & Packaging
- [x] Audit all Python deps for license compatibility (MIT project; all deps should be permissive)
- [x] Reconcile mutagen GPLv2+ licensing conflict (decision: accept GPL, plan split architecture later)
- [x] Update project license from MIT to GPLv2+ in LICENSE and pyproject.toml
- [ ] Bump `pyproject.toml` version to `1.0.0` at release time
- [x] Ensure `make install-deps` + `make install-video-deps` is truly one-command on a fresh Mac
- [ ] Test full clone → install → rip-cd workflow on a clean macOS machine

---

## B. Documentation Consolidation

### B1. Reduce Root Markdown Sprawl
After cleanup, root should contain only **standard GitHub files**:

| File | Purpose | Status |
|------|---------|--------|
| `README.md` | Hero page — what / why / quick start | ✅ Keep |
| `QUICKSTART.md` | 10-minute first-run guide | ✅ Keep |
| `CHANGELOG.md` | Release history | ✅ Created |
| `CONTRIBUTING.md` | How to contribute | ✅ Keep |
| `DISCLAIMER.md` | Legal protections | ✅ Keep |
| `CODE_OF_CONDUCT.md` | Community standards | ✅ Keep |
| `SECURITY.md` | Vulnerability reporting | ✅ Keep |
| `LICENSE` | GPLv2+ license | ✅ Keep |
| `NOTICE` | Third-party attribution | ✅ Keep |
| ~~`TODO.md`~~ | ~~594-line planning doc~~ | ❌ Delete (absorbed here) |
| ~~`IMPROVEMENTS.md`~~ | ~~256-line changelog/roadmap~~ | ❌ Delete (absorbed into CHANGELOG.md) |

### B2. Consolidate `docs/` Guides
Current `docs/` has overlapping files. Target structure:

| File | Purpose | Action |
|------|---------|--------|
| `workflow_overview.md` | High-level Mermaid diagrams of all pipelines | ✅ Keep as-is |
| `music_collection_guide.md` | Complete music pipeline (all sources → Jellyfin) | ✅ Done — absorbed `cd_ripping_guide.md` |
| ~~`cd_ripping_guide.md`~~ | ~~CD-only ripping~~ | ✅ Merged & deleted |
| `video_ripping_guide.md` | Complete DVD/Blu-ray guide + scenario diagrams | ✅ Done — absorbed `video_workflows.md` |
| ~~`video_workflows.md`~~ | ~~Mermaid decision trees~~ | ✅ Merged & deleted |
| `media_server_setup.md` | Server naming conventions, sync, explicit filtering | ✅ Keep |
| `server_setups/` | Hardware-specific guides (BMAX, Jellyfin small box) | ✅ Keep |
| `RELEASE_CHECKLIST.md` | **This file** — the single release plan | ✅ Keep |

**Result:** 6 docs instead of 8, with zero content loss. ✅ Complete.

### B3. Fix Known Doc Bugs
- [x] `media_server_setup.md` lines 86-101: broken/duplicated markdown code block for `metaflac` examples
- [x] Verify all `bin/music/fix_missing_metadata.py` references → actual file is `fix-missing-metadata.py` (kebab-case)
- [x] Ensure every doc links back to QUICKSTART.md for prereqs
- [x] Replace hardcoded `/Volumes/Data/Media/...` paths with `${LIBRARY_ROOT}/...` where possible

---

## C. Script Audit & Consolidation

### C1. Naming Policy
**Decision:** Keep existing filenames (mixed `snake_case` / `kebab-case`) for backward compatibility. New scripts use `snake_case`. Document this in `CONTRIBUTING.md`.

### C2. `bin/music/` — Multiple scripts → classify as Core vs Utility

| Script | Category | Action |
|--------|----------|--------|
| `tag-explicit-mb.py` | **Core** | Keep — explicit content tagging |
| `download_lyrics.py` | **Core** | Keep — lyrics fetching |
| `update-genre-mb.py` | **Core** | Keep — genre tagging |
| `generate-playlists.py` | **Core** | Keep — M3U generation |
| `check_album_integrity.py` | **Core** | Keep — validation |
| `tag-manual-genre.py` | **Core** | Keep — manual genre assignment |
| `update-from-m3u.py` | **Core** | Keep — playlist-driven metadata |
| `compare_music.py` | **Core** | Keep — library comparison |
| `fix_album.py` | **Utility** | Keep — album normalization (documented in guides) |
| `fix_album_covers.py` | **Utility** | Keep — cover art fetching (documented in guides) |
| `fix_track.py` | **Utility** | Keep — single-track organizer (Makefile target) |
| `fix_metadata.py` | **Utility** | Keep — metadata validation |
| `fix-missing-metadata.py` | **Utility** | Keep — MusicBrainz metadata repair |
| `set_explicit.py` | **Utility** | Keep — manual explicit tag setter |
| `fix-single-title.py` | **Utility** | ✅ Keep — generic FLAC title fixer, no personal data |
| `fix-track-numbers.py` | **Utility** | ✅ Keep — generic track number fixer, no personal data |
| `fix-unknown-album.py` | **Utility** | ✅ Keep — album repair with MusicBrainz, no personal data |
| `repair-flac-tags.py` | **Utility** | ✅ Keep — tag repair from playlists, no personal data |
| `specialized/` | **Keep** | Prince Lovesexy splitter — niche but harmless |

### C3. `bin/video/` — Multiple scripts → classify

| Script | Category | Action |
|--------|----------|--------|
| `rip_video.py` | **Core** | Keep — unified ripping pipeline |
| `bluray_to_mp4.zsh` | **Core** | Keep — direct Blu-ray encode |
| `tag-movie-metadata.py` | **Core** | Keep — TMDb/OMDb metadata |
| `tag-movie-ratings.py` | **Core** | Keep — MPAA ratings |
| `backfill_subs.py` | **Core** | Keep — subtitle muxing |
| `vobsub_to_srt.py` | **Core** | Keep — subtitle conversion |
| `language_codes.py` | **Core** | Keep — shared language data |
| `set-movie-imdb-override.py` | **Utility** | Keep — override helper |
| `fix_music_videos.py` | **Utility** | Keep — generic music video organizer |
| `standardize_music_video_filenames.py` | **Utility** | Keep — filename standardizer |
| `scan_music_video_metadata.py` | **Utility** | Keep — metadata scanner |
| `utils/mp4_integrity_checker.py` | **Utility** | Keep — validation |
| `optimize_mp4_streaming.py` | **Utility** | Keep — Jellyfin optimization |
| `embed_thumbnail.py` | **Utility** | ✅ Keep — generic MP4 cover art embedder, no personal data |
| `repair_mp4.sh` | **Utility** | ✅ Keep — generic MP4 streaming compliance fixer, no personal data |
| ~~`fix_music_videos_mapped.py`~~ | **Archived** | ✅ Moved to `_archive/` — 367-entry personal mapping table |
| ~~`fix_music_videos_secondary.py`~~ | **Archived** | ✅ Moved to `_archive/` — hardcoded personal paths + mapping |

### C4. `bin/sync/` — Clean ✅
| Script | Status |
|--------|--------|
| `master-sync.py` | ✅ Keep |
| `sync-library.py` | ✅ Keep |
| `sync-config.yaml` | Gitignored (user-specific); `.example` ships |

### C5. `bin/tv/` — Clean ✅
| Script | Status |
|--------|--------|
| `tag-show-metadata.py` | ✅ Keep |
| `rename_shows_jellyfin.py` | ✅ Keep |

### C6. `bin/utils/` — Clean ✅
| Script | Status |
|--------|--------|
| `clean_playlists.py` | ✅ Keep |
| `clean-redundant-overrides.py` | ✅ Keep |

---

## D. User Experience Improvements

### D1. Unified CLI ✅
*Replace scattered scripts with a single, intuitive entry point.*

- [x] Create unified CLI entry point (`dam` command) using `typer` + `rich`
  - Subcommands: `dam rip cd`, `dam rip video`, `dam tag explicit|genres|lyrics|movie`, `dam sync`, `dam config`, `dam check`
  - `dam check --install` auto-installs missing Homebrew deps
  - `dam config` interactive wizard for library path + API keys
- [x] Feature-driven API onboarding: prompt for keys only when a feature needs them
  - `dam.keys.require_key()` prompts with signup URL and persists to `.env`
  - Scripts call `require_key("TMDB_API_KEY")` on their critical path
- [ ] Goal-oriented batch processing: `dam tag --lyrics --covers --genres` (future)

### D2. Non-Destructive Safety
*Users should feel safe experimenting. Never destroy work without explicit confirmation.*

- [ ] Safe resumption: re-running a command adds new data without disturbing existing metadata
- [ ] Explicit deletion confirmation: `--force-overwrite` flag or typed confirmation
- [ ] Smart sync dry-run: make dry-run the default, require `--confirm` to execute

### D3. "Just Works" Defaults
*Minimize decisions for a perfect result.*

- [ ] Zero-config defaults: sensible FLAC for audio, good Handbrake presets for video
- [ ] Auto-detect media type: `dam rip` detects CD vs DVD vs Blu-ray automatically
- [x] Central path config: `dam config` wizard asks for library root once

### D4. Interactive Conflict Resolution
*Never fail silently, never guess destructively.*

- [ ] Interactive disambiguation for TMDb / MusicBrainz multi-matches
- [ ] Save interactive choices to override files automatically
- [ ] Plain-English video ripping prompts: *"Found 1 Main Feature and 3 Extras. Rip all?"*

### D5. Transparent Retry & Caching
*Network errors shouldn't crash or confuse.*

- [ ] Friendly spinner on rate limits: *"Rate limit reached. Waiting 15s..."*
- [ ] Cache indicators: *"Fetching metadata (using local cache)..."*
- [ ] Graceful degradation: note skipped items in summary instead of crashing

### D6. Interactive Dependency Installation & API Key Onboarding
*Users should never have to hunt for installation commands or signup URLs.*

- [x] `dam check` reports all system tools, Python packages, and API keys with status
- [x] `dam check --install` auto-installs missing Homebrew packages
- [x] `dam config` walks through API key setup with signup URLs and free-tier info
- [x] `dam.keys.require_key()` prompts on the critical path of any script that needs a key
- [ ] Migrate existing scripts to use `dam.deps` for tool checks at startup
- [ ] Migrate existing scripts to use `dam.keys.require_key()` instead of bare `os.getenv()`
- [ ] Add `dam doctor` command: full diagnostic report (tools + versions, Python deps, API keys, disk space, .env sanity)

---

## E. Code Quality & Polish

### E1. Important for Professional Release
- [x] Add `--help` with clear usage examples to every script
- [x] Ensure every script checks for required tools before running → `dam.deps` module + `dam check`
- [x] Add type hints to critical public functions
- [x] Extract shared patterns into `dam/` package (config, deps, keys, console)
- [x] Standardize exit codes across all scripts (0 = success, 1 = error, 2 = partial)

### E2. Testing
- [x] Current tests cover: `backfill_subs`, `clean_playlists`, `fix_album`, `fix_album_covers`, `set_explicit`
- [x] Add tests for: `download_lyrics`, `tag-explicit-mb` (mock-based)
- [ ] Add tests for: `rip_video` (mock-based) - **Priority: Low**
  - Mock makemkvcon output for seamless branching detection
  - Test natural title order vs size sorting logic
  - Test TITLE_INDEX selection and validation
  - Note: Hardware-dependent, complex mocking required
- [x] Target: 70%+ coverage for core scripts (95 tests passing)

### E3. CI / Pre-commit
- [x] Add pre-commit hooks config: `black`, `isort`, `flake8`, trailing whitespace, end-of-file, check-yaml
- [x] Ensure CI runs on PR (already have `.github/workflows/ci.yml`)

---

## F. User Experience & Documentation

### F1. User Stories & Persona Integration
- [x] **Create User Story Inventory**: Document 5 core user stories with complete workflows
- [ ] **Integrate User Stories into README**: Add persona-based narrative showing real use cases
- [ ] **Add User Journey Section**: Show how different personas use specific features
- [ ] **Create Use Case Examples**: Practical scenarios for each media type

### F2. Visual Polish & Delight
- [ ] Create project logo (or refine existing `assets/logo.png`)
- [ ] Add GIF demo of CD ripping workflow (terminal recording)
- [ ] Add terminal screenshots showing beautiful output
- [x] Test README rendering on GitHub before release
- [x] Consistent emoji language across docs (standardized status indicators and feature emojis)

### F3. Workflow Documentation Enhancement
- [ ] **Add Integrated Workflow Flowcharts**: Include finalized flowcharts in `docs/workflow_overview.md`
  - [ ] **Current State Flowcharts**: Show fragmented user journeys with manual script requirements
  - [ ] **Proposed Integrated Flowcharts**: Display "process once, done forever" complete workflows
  - [ ] **Comparative Analysis**: Include integration gap summary and user experience impact
  - [ ] **Implementation Roadmap**: Add phased integration strategy with success metrics
  - [ ] **Technical Considerations**: Document integration challenges and mitigation strategies
  - **Prerequisite**: Complete CLI enhancements identified in CLI Enhancement Review (Section G3)
  - **Goal**: Provide visual documentation of current limitations and future integrated workflows

---

## G. Pre-Release Verification (Run Before EVERY Version Tag)

> **IMPORTANT**: This section applies to ALL releases - v1.0.0, v1.0.1, v1.1.0, v2.0.0, etc.
> Run this complete checklist before tagging any version for public release.

### G1. Quality Assurance Checklist
- [ ] **Code Quality Pipeline**: Run `scripts/test-pipeline.sh` - must pass with 0 errors
- [ ] **All Tests Passing**: All tests must pass (check pytest coverage)
- [ ] **No Critical Linting**: Zero E9/F63/F7/F82 errors
- [ ] **Flake8 Clean**: `./venv/bin/python -m flake8 bin/ tests/ scripts/ dam/ --max-line-length=100` shows acceptable quality:
  - ✅ **Zero critical errors**: No E9/F63/F7/F82 issues
  - ✅ **Zero code quality issues**: No F401/F541/F821/W291/W293/E131/E203 issues  
  - ✅ **Acceptable line length**: E501 issues ≤ 30 (complex cases only)
  - ✅ **Minimal test issues**: F841 issues ≤ 5 (test files only)
  
> **🎯 Quality Baseline Achieved (March 2026)**: Successfully reduced flake8 issues from 71 to 26 (63% improvement) while maintaining all functionality. Current state: 24 E501 + 2 F841 = 26 total issues, all non-critical.
> 
> **🔧 Recent Critical Fixes (March 2026)**:
> - Fixed spinner lifecycle bug where "Ripping with MakeMKV..." persisted through HandBrake encoding
> - Fixed infinite loop in title selection when multiple candidates found
> - Improved title selection UX: shows only candidates with 👉 marker for auto-selected title
- [ ] **Clean Git Status**: No uncommitted changes in working directory
- [ ] **Documentation Links**: Verify all internal links in README and docs work
- [ ] **Environment Variables**: Cross-check `.env.example` with all script requirements
- [ ] **Dependency Audit**: Re-run `pip-audit` on requirements.txt and requirements-test.txt
- [ ] **Documentation Appropriateness**: Review docs/ for user-focused content
  - [ ] Verify docs/video_ripping_guide.md, docs/music_collection_guide.md, docs/workflow_overview.md, and docs/media_server_setup.md contain user workflows, not implementation details
  - [ ] Check docs/server_setups/ files are hardware-specific configuration templates (appropriate location)
  - [ ] Remove any trivialities (ASCII spinners, emoji celebrations, ENTER key prompts) from user-facing docs
  - [ ] Ensure all docs focus on "what users can do" rather than "how the code works"
- [ ] **CD Ripping End-to-End Review**: Test complete CD ripping workflow from start to finish
  - [ ] Verify fresh setup: `cp .abcde.conf.example ~/.abcde.conf` works correctly
  - [ ] Test CD detection and ripping with `dam rip cd` (or `make rip-cd`)
  - [ ] Confirm metadata lookup and album art retrieval working
  - [ ] Verify lyrics download functionality (with/without API key)
  - [ ] Test explicit content tagging workflow
  - [ ] Confirm final file organization in ${LIBRARY_ROOT}/CDs/
  - [ ] Validate M3U playlist generation
  - [ ] Check error handling for missing disc or failed rips

### G1.1. Testing Strategy & Coverage Policy
- [ ] **Smart Testing Approach**: Focus on critical business logic over comprehensive script coverage
- [ ] **Coverage Threshold**: 25% minimum coverage (realistic for complex scripts with external dependencies)
- [ ] **Critical Path Testing**: Ensure core functionality, decision logic, and integration points are tested
- [ ] **Test New Features**: Add focused tests for any new functionality before release
- [ ] **Library vs Script Coverage**: 
  - **Library code** (music, utils): Target 70%+ coverage
  - **Complex scripts** (rip_video.py): Target critical path testing vs. comprehensive coverage
- [ ] **Test Review**: Verify tests cover recent changes and edge cases for new features

### G2. Release Content Preparation
- [ ] **Update CHANGELOG.md**: Add new version section with:
  - New features and improvements
  - Bug fixes
  - Breaking changes (if any)
  - Migration notes (if needed)
- [ ] **Final QUICKSTART.md Review**: After all workflows are fully streamlined, update QUICKSTART.md to reflect final integrated user experience
  - Review all CLI command examples and ensure they match final workflow state
  - Update any remaining manual script references to integrated CLI commands
  - Ensure consistency with any workflow optimizations completed during release prep
  - Verify all examples work with the final integrated user experience
- [ ] **Version Bump**: Update `pyproject.toml` version (X.Y.Z format)
- [ ] **Tag Message**: Prepare release tag description:
  ```bash
  # Example for v1.0.0 - customize for each version
  git tag -a vX.Y.Z -m "Release vX.Y.Z

  Features:
  - Complete CD/DVD/Blu-ray ripping pipeline
  - TV show and music video metadata management
  - Music library sync with explicit tagging
  - Comprehensive test suite (95 tests)
  - Professional code quality standards

  Installation:
  pip install -r requirements.txt
  make install-video-deps  # For DVD/Blu-ray support
  "
  ```

### G3. Final Sanity Checks
- [ ] **Fresh Install Test**: Clone repo to temp directory, run install, test basic workflow
- [ ] **Test with Different Disc Drive**: Verify ripping works with at least one other drive model
- [ ] **README Rendering**: View README on GitHub preview before release
- [ ] **License Compliance**: Verify all deps in requirements.txt have compatible licenses
- [ ] **Security Scan**: Final `gitleaks` or `truffleHog` scan for any missed secrets
- [ ] **Git History**: Review recent commits for any sensitive information
- [ ] **API Key Graceful Failure Testing**: Verify missing API keys don't crash workflows
  - **Spotify API Status Check**: Review recent Spotify API terms changes
    - Verify current API access requirements and rate limits
    - Check if recent policy changes affect explicit content tagging
    - Confirm fallback behavior when Spotify API unavailable
  - **Missing Key Tests**: Test each API-dependent script with no keys configured
    - Genius lyrics API: Should skip gracefully with informative message
    - Spotify explicit API: Should continue without tagging, not crash
    - TMDb/OMDb APIs: Should skip metadata fetch, continue processing
    - MusicBrainz: Should work without API key (rate-limited but functional)
  - **Invalid Key Tests**: Test with malformed/expired API keys
    - Verify clear error messages guide users to fix configuration
    - Confirm scripts continue with reduced functionality when possible
  - **Documentation Review**: Ensure API setup instructions are current
    - Verify all API key acquisition URLs are still valid
    - Check that rate limits and usage policies are accurately documented
- [ ] **Directory Structure and Configuration Review**: Verify standard naming and defaults
  - **Directory Naming Consistency**: Review standard folder names for consistency
    - Check if "Blurays" should be "BDs" to match "DVDs" and "Movies" pattern
    - Verify all target directories are properly named (CDs, Movies, etc.)
    - Ensure consistent capitalization and spelling across all scripts
  - **Directory Placement Verification**: Confirm target folders are in logical locations
    - Verify CDs, Movies, TV Shows directories are properly placed
    - Check that all scripts reference correct directory paths
    - Ensure directory structure matches documentation examples
  - **Configuration Defaults Review**: Verify .env.example has sensible defaults
    - Check LIBRARY_ROOT path is appropriate for typical macOS setups
    - Verify all optional settings have reasonable default values
    - Ensure defaults don't require immediate modification for basic use
    - Confirm API key placeholders are clearly marked as optional
- [ ] **CLI Enhancement Review**: Assess user experience gap between basic CLI and enhanced processing
  - [ ] **"Process Once, Done Forever" Philosophy Review**: Users may only process each disc once - maximize integrated value
    - **Principle**: Every disc processing should include all reasonable enhancements automatically
    - **Goal**: Users should get the "best possible" result from a single command without needing follow-up processing
    - **Standard**: Extra features should be integrated into main workflows, not left as separate manual steps
  - [ ] **Music Workflow Gap**: Review `dam rip cd` vs. manual script requirements
    - Current: Basic ripping with MusicBrainz metadata
    - Gap: Quality validation, metadata repair, organization, lyrics, explicit tagging require manual scripts
    - **Process-Once Analysis**: Should CD ripping automatically include quality checks, metadata repair, and lyrics fetching?
    - Decision: Document current limitation OR integrate key enhancements into `dam rip cd` workflow
  - [ ] **Video Workflow Gap**: Review `dam rip video` vs. metadata enhancement needs
    - Current: Complete ripping pipeline with subtitle handling
    - Gap: Rich metadata, ratings, subtitle backfilling require manual scripts
    - **Process-Once Analysis**: Should video ripping automatically fetch TMDb metadata and ratings during the process?
    - Decision: Document current limitation OR integrate metadata enhancement into `dam rip video` workflow
  - [ ] **TV Workflow Gap**: Review missing CLI integration for TV show processing
    - Current: No CLI wrappers for TV show organization and metadata
    - Gap: Users must run scripts manually for TV show workflow
    - **Process-Once Analysis**: Should TV show processing be a complete workflow with automatic metadata?
    - Decision: Add integrated CLI commands OR document manual workflow clearly
  - [ ] **TV Show Ripping Experience Testing**: Test end-to-end TV show workflow for UX quality
    - **Setup Test**: Create test TV show directory with various naming patterns
    - **Organization Test**: Run `rename_shows_jellyfin.py` with --dry-run and verify planned changes
    - **Metadata Test**: Run `tag-show-metadata.py` and verify proper metadata tagging
    - **Edge Cases Test**: Test with special characters, season directories, flat structures
    - **Error Handling Test**: Verify graceful handling of malformed filenames or missing metadata
    - **Documentation Review**: Ensure TV show workflow is clearly documented for users
  - [ ] **Explicit Lyrics Experience Testing**: Test lyrics download and explicit tagging workflow
    - **Setup Test**: Create test music library with mixed explicit/clean content
    - **Lyrics Download Test**: Run `download_lyrics.py` and verify proper .lrc file creation
    - **Explicit Tagging Test**: Run `tag-explicit-mb.py` and verify accurate explicit detection
    - **Integration Test**: Test lyrics + explicit tagging workflow together
    - **Edge Cases Test**: Test with instrumental tracks, various languages, metadata edge cases
    - **User Choice Test**: Verify user can override automatic explicit detection when needed
    - **Documentation Review**: Ensure explicit content workflow is clearly explained
  - [ ] **Sync Configuration Experience Testing**: Test sync settings configuration before library sync
    - **GUI Configuration Test**: Verify GUI provides clear interface for sync settings
      - MPAA rating filters (G, PG, PG-13, R, NC-17)
      - Explicit content filters (exclude explicit tracks, exclude unknown)
      - Source/destination path configuration
      - Delete mode settings (safe vs. aggressive deletion)
    - **CLI Configuration Test**: Verify sync-config.yaml is clearly documented and editable
      - Test configuration file validation and error messages
      - Test with various filter combinations
      - Test dry-run mode shows what will be filtered
    - **Preview Experience Test**: Test sync preview shows filtering results clearly
      - Verify users can see what content will be excluded before sync
      - Test preview shows file counts and sizes for filtered content
      - Test preview is easy to understand for non-technical users
    - **Override Configuration Test**: Test explicit override configuration (config/explicit_overrides.csv)
      - Verify users can manually override automatic explicit detection
      - Test override file format validation and error handling
      - Test overrides work correctly during sync filtering
    - **Error Handling Test**: Test graceful handling of invalid sync settings
      - Invalid paths, missing directories, permission issues
      - Invalid rating values, malformed filter settings
      - Clear error messages and recovery guidance
    - **Documentation Review**: Ensure sync configuration is clearly documented with examples
  - [ ] **User Experience Documentation**: Update README and guides to clarify:
    - What `dam` commands provide automatically (current state)
    - What enhanced processing requires manual script execution (current gaps)
    - **Process-Once Standard**: Clear guidance on getting the "best possible" result from each disc
    - Step-by-step workflows for complete library processing (if manual steps remain)
  - [ ] **Integration Priority Assessment**: For each workflow gap, evaluate:
    - **User Impact**: How many users would benefit from integrated enhancement?
    - **Technical Complexity**: Feasibility of integrating into main workflow
    - **Processing Time Impact**: Would integration significantly slow down the main workflow?
    - **API Reliability**: Are external services (TMDb, Genius, etc.) reliable enough for automatic integration?
    - **Decision**: Integrate now vs. document for future enhancement vs. leave as manual optional
  - [ ] **User Experience Enhancements**: Consider user engagement and progress tracking features
    - **Disc Ripping Counter**: Track total discs ripped using DAM over time
      - Store counter in user's home directory or config directory
      - Display counter after successful ripping operations
      - Provide simple stats (CDs ripped, movies ripped, total discs)
      - Consider optional milestone celebrations or achievements
      - Ensure counter persists across updates and system reboots
    - **User Value Assessment**: Does tracking progress enhance user motivation and engagement?
    - **Implementation Priority**: Low-effort enhancement with potential user satisfaction benefits
  - [ ] **Rip Time Estimation Enhancement**: Show time estimate based on selected track
    - **Track-Based Estimation**: Use actual main track size/duration for accurate estimates
      - Video: Calculate from selected track's file size or duration
      - CD: Use CD length from disc metadata (74 minutes, etc.)
      - Show: "Come back in ~28 minutes (at 3:47 PM)"
    - **Implementation Approach**:
      - Use information already gathered during title/track selection
      - Simple calculation: track_size ÷ average_processing_rate
      - Display both duration and actual completion time
      - No complex tracking - just use pre-ripping data
    - **User Experience Benefits**:
      - Accurate estimates based on actual content being processed
      - Clear "come back at 3:47 PM" for easy planning
      - Uses data already collected, no extra overhead
      - Helps users plan disc swapping precisely
  - [ ] **Storage Management Enhancement**: Add cleanup script for large intermediate files
    - **MKV Cleanup Script**: Remove large .mkv files after successful MP4 conversion
      - Automatically detect .mkv files that have corresponding working .mp4 files
      - Verify MP4 files are complete and playable before cleanup
      - Calculate space savings and show user before deletion
      - User approval options: yes, no, always, don't ask again
      - Store user preference in config for future runs
    - **Integration Points**: Prompt for cleanup after successful video ripping batches
    - **Safety Considerations**: Verify file integrity before deletion, provide undo option
    - **User Experience Impact**: Significant drive space savings vs. user control over file deletion

> **Versioning Guidelines**:
> - **Patch releases** (X.Y.Z+1): Bug fixes, no breaking changes
> - **Minor releases** (X.Y+1.0): New features, backward compatible
> - **Major releases** (X+1.0.0): Breaking changes, major new features
> - Always run this full checklist regardless of release type

---

## H. Release Execution

### Pre-Release Final Steps
- [x] Complete items in sections A–C above
- [x] Run full PII / secrets scan on all tracked files
- [ ] Test every documented workflow on a clean macOS system
- [ ] Verify README renders correctly on GitHub
- [ ] Bump version to `1.0.0` in `pyproject.toml`
- [ ] Tag release: `git tag v1.0.0`

### Git History (if needed)
If existing git history contains sensitive data, consider a fresh start:
```bash
# Option: Squash to single initial commit
git checkout --orphan fresh-main
git add .
git commit -m "Initial release: Physical media to digital archive automation"
git branch -D main
git branch -m main
```

### Post-Release
- [ ] Monitor issues for first-user feedback
- [ ] Set up GitHub Discussions if community grows
- [ ] Optional: announcement post (HN, Reddit, media server forums)

---

## I. Post-Release Tasks

### I1. Immediate Post-Release
- [ ] Monitor issues for first-user feedback
- [ ] Set up GitHub Discussions if community grows
- [ ] Optional: announcement post (HN, Reddit, media server forums)

### I2. Maintenance Planning
- [ ] Create v1.0.1 milestone for any quick fixes
- [ ] Plan v1.1.0 features based on early feedback
- [ ] Document any known issues in GitHub Issues

### I3. Enhanced Workflow Integration
- [ ] **Integrated Metadata Tagging**: Move metadata fetching and file preparation to end of rip session
  - **Current Gap**: Users must run separate tagging scripts after ripping
  - **Proposed Solution**: Integrate TMDb/Spotify/Genius tagging into main rip workflows
  - **User Benefit**: "Process Once, Done Forever" - single command gets fully prepared files
  - **Implementation**: Add optional tagging phase to `dam rip cd` and `dam rip video` commands
  - **Considerations**: Add API rate limiting, provide skip option for faster ripping

### I4. Enhanced User Experience
- [ ] **Auto-Detect Disc Workflow**: One-shot command that detects disc type and starts appropriate workflow
  - **Current Gap**: Users must run `dam rip cd` vs `dam rip video` based on disc type knowledge
  - **Proposed Solution**: `dam rip auto` command that detects CD/DVD/Blu-ray and runs appropriate workflow
  - **User Benefit**: Simplified interface - just insert disc and run single command
  - **Implementation**: Use existing disc detection logic to determine type and dispatch to correct workflow
  - **Considerations**: Add confirmation prompt before starting, provide manual override option

---

## J. GUI App Polish (Electron)

### J1. App Icon & Branding
- [ ] Create 1024×1024 app icon in `gui/assets/`
  - `gui/assets/icon.icns` (macOS format)
  - `gui/assets/icon.png` (source PNG)
  - Use `electron-icon-builder` or any `.icns` generator from a square PNG
- [ ] Update `gui/package.json` to reference icon for window title bar
- [ ] Test icon displays correctly in Dock and About menu

### J2. Desktop Launcher (Optional)
- [ ] Create a double-clickable launcher script or Automator app
- [ ] Document launcher creation in gui/README.md
- [ ] Consider creating a simple `.command` file for easy double-click launch

### J3. GUI UX Improvements & Reliability Testing
- [ ] Add confirmation dialogs for all destructive operations
  - [ ] Include "Don't ask again" checkbox for frequent operations
  - [ ] Clear messaging about what will happen before execution
- [ ] Eliminate all GUI failures due to missing configuration
  - [ ] Detect missing API keys before operations start
  - [ ] Provide inline help and links to obtain missing keys
  - [ ] Guide users through setup with contextual prompts
- [ ] Implement comprehensive error handling and user guidance
  - [ ] Catch all CLI errors and present user-friendly messages
  - [ ] Provide specific help for each error type
  - [ ] Offer one-click fixes where possible
- [ ] Test GUI reliability under various conditions
  - [ ] Test with missing/invalid configuration
  - [ ] Test with missing dependencies
  - [ ] Test network connectivity issues
  - [ ] Test file permission problems
- [ ] Ensure liquid, predictable user experience
  - [ ] All operations should have clear start/progress/end states
  - [ ] No silent failures or cryptic error messages
  - [ ] Consistent feedback for all user actions

### J4. GUI Critical Features for v1.0
- [ ] **Git History Security**: Clear git history to avoid secrets/PII exposure
  - [ ] Review entire git history for sensitive data
  - [ ] Consider squash-to-single-commit or fresh repository
  - [ ] Document git history cleaning procedure
- [ ] **Operation Cancellation**: Consistent cancel/interrupt functionality
  - [ ] Add cancel button for all long-running operations
  - [ ] Implement graceful shutdown equivalent to CTRL+C
  - [ ] Ensure proper cleanup and user messaging on cancellation
  - [ ] Test cancellation during disc ripping, encoding, and tagging
  - [ ] **Enhanced CLI Ctrl+C Support**: Comprehensive interrupt handling across all workflows
    - [ ] Add top-level try/except wrapper around main() function for graceful Ctrl+C
    - [ ] Ensure Ctrl+C works during all phases: disc detection, ripping, encoding, organization
    - [ ] Implement proper cleanup of temporary files and partial operations on interrupt
    - [ ] Add consistent cancellation messaging across all script entry points
    - [ ] Test Ctrl+C behavior during MakeMKV ripping, HandBrake encoding, and file operations
    - [ ] Verify signal handler integration with subprocess calls and external tools
- [ ] **Workflow Progress Indicators**: Clear position in workflow
  - [ ] Show current step and overall progress for multi-step operations
  - [ ] Display estimated time remaining for long operations
  - [ ] Visual indicators for completed vs. pending steps
  - [ ] Implement after workflow optimization is complete
- [ ] **File/Folder Interaction**: User-friendly source/target selection
  - [ ] Add folder browse buttons instead of manual path entry
  - [ ] Implement file dialogs for source media selection
  - [ ] Add "Open in Finder/Explorer" buttons for target locations
  - [ ] Consider drag-and-drop support for source files/folders
  - [ ] Validate selected paths before operation starts
- [x] **Graceful Degradation**: Handle missing dependencies elegantly
  - [x] Verify graceful handling when MakeMKV is not available
  - [x] Check behavior when HandBrakeCLI is missing
  - [x] Test with missing abcde (CD ripping tool)
  - [x] Verify fallback behavior for missing API keys
  - [x] Ensure clear error messages with installation guidance
  - [x] Provide one-click dependency installation where possible
  - [x] Document which features require which dependencies
- [ ] **Existing Library Enhancement**: Support for improving existing digital collections
  - [ ] Implement non-destructive library analysis (`dam analyze library`)
  - [ ] Create metadata enhancement workflows with backup protection
  - [ ] Develop organization standardization with undo capability
  - [ ] Add quality upgrade identification and batch processing
  - [ ] Ensure preview mode for all enhancement operations
  - [ ] Test safety features (backup, confirmation, rollback)
  - [ ] Document enhancement workflows and safety measures
- [ ] **Community & Support Strategy**: Plan user engagement approach
  - [ ] Decide whether to host own community vs. point to existing forums
  - [ ] Consider recommending established forums (MakeMKV, HandBrake, Jellyfin/Plex)
  - [ ] Evaluate pros/cons of GitHub Discussions vs. existing communities
  - [ ] Plan moderation capacity if hosting own community
  - [ ] Document community guidelines and code of conduct
  - [ ] Consider creating FAQ for common cross-tool questions

### I4. Future Configuration Extensions (Post-v1.0)

#### **🎯 Tier 1: High Impact, Low Complexity**
- [ ] **VIDEO_QUALITY_PROFILE**: Simplified preset system
  - [ ] Add `VIDEO_QUALITY_PROFILE=balanced|quality|speed|storage`
  - [ ] Map presets to HandBrake settings (HB_QUALITY, HB_PRESET, HB_TUNE)
  - [ ] Update documentation with preset descriptions
  - [ ] Test preset combinations for different use cases
- [ ] **AUDIO_OUTPUT_FORMAT**: Audio format flexibility
  - [ ] Add `AUDIO_OUTPUT_FORMAT=flac|mp3|ogg|m4a|wav`
  - [ ] Update .abcde.conf to use environment variable
  - [ ] Test format compatibility across devices
  - [ ] Document storage vs. quality trade-offs
- [ ] **REENCODE_THRESHOLD**: User-controlled compression strategy
  - [ ] Add `REENCODE_THRESHOLD=5GB|10GB|off|auto`
  - [ ] Update logic to use configurable threshold
  - [ ] Test with various file sizes and quality settings
  - [ ] Document impact on storage and quality

#### **🥈 Tier 2: Medium Impact, Medium Complexity**
- [ ] **VIDEO_CONTAINER**: Container choice flexibility
  - [ ] Add `VIDEO_CONTAINER=mp4|mkv|both`
  - [ ] Implement MKV output option for archival users
  - [ ] Add "both" option to generate MP4 + MKV
  - [ ] Update documentation with compatibility notes
- [ ] **VIDEO_RESOLUTION**: Resolution control for storage management
  - [ ] Add `VIDEO_RESOLUTION=source|1080p|720p|480p|auto`
  - [ ] Implement HandBrake resolution settings
  - [ ] Add auto-detection based on source and storage constraints
  - [ ] Test quality impact of resolution reduction
- [ ] **PARALLEL_ENCODING**: Performance optimization
  - [ ] Add `PARALLEL_ENCODING=true|false`
  - [ ] Add `MAX_PARALLEL_JOBS=2|4|auto`
  - [ ] Implement concurrent processing for multiple files
  - [ ] Add CPU usage monitoring and throttling

#### **🥉 Tier 3: High Impact, High Complexity**
- [ ] **VIDEO_CODEC**: Advanced codec options
  - [ ] Add `VIDEO_CODEC=h264|h265|av1|auto`
  - [ ] Implement codec compatibility checking
  - [ ] Add device capability detection
  - [ ] Create fallback strategies for unsupported devices
- [ ] **AUDIO_MULTI_OUTPUT**: Multi-format generation
  - [ ] Add `AUDIO_MULTI_OUTPUT=true|false`
  - [ ] Add `AUDIO_FORMATS=flac,mp3,ogg`
  - [ ] Implement concurrent encoding to multiple formats
  - [ ] Add storage impact calculation and warnings
- [ ] **HDR_PRESERVATION**: Future-proofing for 4K content
  - [ ] Add `VIDEO_HDR_PRESERVE=true|false|auto`
  - [ ] Implement HDR detection and preservation
  - [ ] Add HDR compatibility checking
  - [ ] Document HDR requirements and limitations

#### **🔧 Implementation Strategy**
- [ ] **Phase 1**: Implement Tier 1 extensions (quick wins)
  - [ ] Add environment variables to .env.example
  - [ ] Update configuration loading logic
  - [ ] Add validation and error handling
  - [ ] Update documentation and help text
- [ ] **Phase 2**: Implement Tier 2 extensions (enhanced control)
  - [ ] Extend HandBrake integration for new options
  - [ ] Add parallel processing infrastructure
  - [ ] Implement resolution and container options
  - [ ] Add comprehensive testing suite
- [ ] **Phase 3**: Implement Tier 3 extensions (advanced features)
  - [ ] Add codec compatibility framework
  - [ ] Implement multi-format processing pipelines
  - [ ] Add HDR and advanced video features
  - [ ] Create advanced user documentation

#### **🎯 User Scenario Configurations**
- [ ] **Storage-Constrained User Profile**
  - [ ] Create `AUDIO_OUTPUT_FORMAT=mp3` preset
  - [ ] Create `VIDEO_QUALITY_PROFILE=storage` preset
  - [ ] Create `REENCODE_THRESHOLD=5GB` preset
  - [ ] Add storage usage calculator
- [ ] **Quality Enthusiast Profile**
  - [ ] Create `VIDEO_QUALITY_PROFILE=quality` preset
  - [ ] Create `REENCODE_THRESHOLD=off` preset
  - [ ] Create `VIDEO_CONTAINER=mkv` preset
  - [ ] Add quality verification tools
- [ ] **Speed-Focused User Profile**
  - [ ] Create `VIDEO_QUALITY_PROFILE=speed` preset
  - [ ] Create `PARALLEL_ENCODING=true` preset
  - [ ] Create `REENCODE_THRESHOLD=20GB` preset
  - [ ] Add performance monitoring
- [ ] **Family Setup Profile**
  - [ ] Create `VIDEO_QUALITY_PROFILE=balanced` preset
  - [ ] Create `QUALITY_VERIFICATION=true` preset
  - [ ] Add content filtering options
  - [ ] Add multi-device optimization

#### **📊 Configuration Impact Analysis**
- [ ] **Storage Impact Calculator**
  - [ ] Add tool to estimate storage needs based on settings
  - [ ] Create comparison tables for different configurations
  - [ ] Add recommendations based on available storage
  - [ ] Implement storage usage warnings
- [ ] **Quality Impact Assessment**
  - [ ] Add quality verification tools
  - [ ] Create before/after comparisons
  - [ ] Add quality metrics and thresholds
  - [ ] Implement quality loss detection
- [ ] **Compatibility Matrix**
  - [ ] Create device compatibility database
  - [ ] Add compatibility checking for user configurations
  - [ ] Generate compatibility reports
  - [ ] Add device-specific recommendations

#### **🔮 Future Considerations**
- [ ] **AI-Assisted Configuration**
  - [ ] Analyze user's hardware and storage
  - [ ] Recommend optimal settings automatically
  - [ ] Learn from user preferences over time
  - [ ] Add configuration optimization suggestions
- [ ] **Cloud Configuration Sync**
  - [ ] Allow configuration backup to cloud
  - [ ] Sync settings across multiple installations
  - [ ] Add configuration templates and sharing
  - [ ] Implement configuration versioning

### I5. Storage Management & Cleanup (Post-v1.0)

#### **🗑️ MKV File Cleanup Strategy**
- [ ] **MKV Cleanup Option**: User-controlled removal of original MKV files after successful MP4 encoding
  - [ ] Add `CLEANUP_MKV_AFTER_ENCODING=true|false|prompt` environment variable
  - [ ] Implement validation checks before deletion (MP4 exists, quality verification)
  - [ ] Add user confirmation prompt for safety (default behavior)
  - [ ] Create backup/undo mechanism for accidental deletions
  - [ ] Document storage savings vs. archival flexibility trade-offs

#### **📊 Storage Impact Analysis**
- [ ] **Storage Usage Calculator**: Show users space savings from MKV cleanup
  - [ ] Calculate total MKV storage usage in library
  - [ ] Estimate potential space savings from cleanup
  - [ ] Show before/after storage projections
  - [ ] Add recommendations based on available storage
- [ ] **Storage Monitoring**: Alert users when MKV files consume excessive space
  - [ ] Monitor MKV vs. MP4 ratio in library
  - [ ] Alert when MKV storage exceeds configurable threshold (e.g., 200GB)
  - [ ] Provide cleanup recommendations and storage optimization tips

#### **🔒 Safety & Validation Framework**
- [ ] **Quality Verification**: Ensure MP4 files are valid before MKV deletion
  - [ ] Implement MP4 file integrity checks
  - [ ] Verify audio/video tracks are complete
  - [ ] Check metadata preservation and accuracy
  - [ ] Validate subtitle and chapter information
- [ ] **User Validation Window**: Allow users to review before cleanup
  - [ ] Show list of MKV files proposed for deletion
  - [ ] Display corresponding MP4 files for verification
  - [ ] Allow selective cleanup (delete some, keep others)
  - [ ] Provide preview of storage savings

#### **🎯 User Workflow Integration**
- [ ] **Post-Encoding Cleanup Prompt**: Offer cleanup after successful encoding
  - [ ] Prompt user after each successful video encoding
  - [ ] Show storage impact and recommendations
  - [ ] Allow "remember my choice" for future encodings
  - [ ] Add "cleanup all" option for batch processing
- [ ] **Library Maintenance Mode**: Periodic cleanup recommendations
  - [ ] Add `dam cleanup-mkv` command for manual cleanup
  - [ ] Implement scheduled cleanup reminders
  - [ ] Create storage optimization reports
  - [ ] Add "safe cleanup" vs. "aggressive cleanup" modes

#### **⚙️ Configuration Options**
- [ ] **Cleanup Behavior Settings**
  - [ ] `CLEANUP_MKV_AFTER_ENCODING=prompt|auto|never`
  - [ ] `CLEANUP_MKV_DELAY_DAYS=7` (wait period before deletion)
  - [ ] `CLEANUP_MKV_VERIFY_QUALITY=true` (quality verification before deletion)
  - [ ] `CLEANUP_MKV_BACKUP=false` (create backup before deletion)
- [ ] **Storage Threshold Settings**
  - [ ] `MKV_STORAGE_ALERT_GB=200` (alert when MKV storage exceeds this)
  - [ ] `MKV_STORAGE_RATIO_THRESHOLD=0.5` (alert when MKV:MP4 ratio exceeds this)
  - [ ] `STORAGE_OPTIMIZATION_REMINDERS=true` (periodic cleanup reminders)

#### **🔮 Advanced Cleanup Features**
- [ ] **Smart Cleanup Intelligence**
  - [ ] Analyze user viewing patterns to keep frequently accessed MKVs
  - [ ] Identify MKVs with special features not preserved in MP4
  - [ ] Prioritize cleanup of duplicate or redundant MKV files
  - [ ] Learn from user cleanup preferences over time
- [ **Selective Cleanup Strategies**
  - [ ] Keep MKVs for movies, cleanup for TV episodes
  - [ ] Keep MKVs with multiple audio tracks, cleanup simple ones
  - [ ] Keep MKVs with special features, cleanup basic rips
  - [ ] Allow user-defined cleanup rules and exceptions

#### **📋 Implementation Considerations**
- [ ] **Safety First**: Default to "prompt" mode, never auto-delete without confirmation
- [ ] **Transparency**: Clear communication about what's being deleted and why
- [ **Recoverability**: Provide undo mechanism or backup strategy
- [ ] **User Education**: Explain storage benefits vs. archival trade-offs
- [ ] **Gradual Rollout**: Start with prompts and recommendations, add automation later

### I6. Future Standalone Packaging (Post-v1.0)
- [ ] Research bundling Python environment with Electron app
- [ ] Consider PyInstaller or similar for creating truly standalone app
- [ ] Evaluate trade-offs: bundle size vs. user convenience

### I7. Episodic & Serial Disc Handling (Post-v1.0)

#### **🎯 Problem Statement**
Current video ripping pipeline is optimized for single-feature movie discs. TV show season discs and serial content (multiple episodes per disc) need enhanced handling for:

- **Multi-track ripping**: User may want to rip all qualifying episodes from season discs
- **Naming collision avoidance**: Prevent MP4 filename conflicts when multiple episodes share same title
- **Episode organization**: Proper season/episode naming and metadata integration

#### **🔧 Proposed Enhancements**

##### **Multi-Episode Detection & Handling**
- [ ] **Season Disc Detection**: Automatically identify TV show season discs vs. movie discs
  - [ ] Use disc title patterns (e.g., "Season 1", "Complete Series")
  - [ ] Analyze title durations and quantity (multiple similar-length titles)
  - [ ] Check TMDb for TV show metadata during disc analysis

- [ ] **Batch Episode Ripping**: Enhanced `rip-movie-all` behavior for episodic content
  - [ ] Prompt user: "Detected TV show season disc with X episodes. Rip all episodes?"
  - [ ] Allow selective episode ripping (choose specific episodes)
  - [ ] Maintain current single-episode workflow for movie discs

##### **Enhanced Naming Scheme for Episodes**
- [ ] **Numerical Suffix System**: Prevent MP4 filename collisions
  ```
  Current: Movie Name (Year)/Movie Name (Year).mp4
  Proposed: Show Name/Season 01/Show Name - S01E01 - Episode Title.mp4
  ```

- [ ] **Episode Metadata Integration**: Proper season/episode tagging
  - [ ] Fetch episode-level metadata from TMDb
  - [ ] Add season/episode numbers to filename and metadata
  - [ ] Maintain compatibility with Jellyfin/Plex naming conventions

##### **User Experience Improvements**
- [ ] **Smart Title Handling**: Use provided title as base, add episode identifiers
  - [ ] Example: "Friends (1994)" → "Friends - S01E01 - Pilot.mp4"
  - [ ] Preserve user-provided title in season folder name
  - [ ] Auto-detect episode numbers from disc titles or metadata

- [ ] **Configuration Options**: User control over episodic disc behavior
  - [ ] `EPISODIC_AUTO_DETECT=true|false` - Automatic season disc detection
  - [ ] `EPISODIC_NAMING_PATTERN` - Custom episode naming templates
  - [ ] `EPISODIC_RIP_ALL=true|false|prompt` - Default behavior for multi-episode discs

#### **📋 Implementation Considerations**

##### **Backward Compatibility**
- [ ] **Existing Movie Workflow**: Ensure no breaking changes to current movie disc handling
- [ ] **CLI Flag Addition**: Add `--episodic` flag for explicit episodic disc processing
- [ ] **Graceful Fallback**: Default to current behavior if episodic detection fails

##### **Technical Challenges**
- [ ] **Disc Title Parsing**: Reliable detection of episodic content vs. anthology movies
- [ ] **Episode Number Mapping**: Map disc titles to correct season/episode numbers
- [ ] **Metadata Correlation**: Match disc content with TMDb episode data
- [ ] **File Organization**: Integrate with existing TV show directory structure

##### **User Guidance & Documentation**
- [ ] **Workflow Documentation**: Update video ripping guide for episodic content
- [ ] **CLI Help**: Add episodic options to `dam rip video --help`
- [ ] **Error Messages**: Clear guidance when episodic detection is ambiguous

#### **🎯 Success Criteria**
- [ ] Users can successfully rip entire TV show season discs with proper episode organization
- [ ] No MP4 filename collisions when multiple episodes share base title
- [ ] Enhanced naming integrates seamlessly with existing TV show workflow
- [ ] Backward compatibility maintained for all existing movie disc use cases
- [ ] Clear user guidance for episodic vs. movie disc handling

#### **📊 Priority Assessment**
- **Impact**: High - Addresses common use case for TV show collectors
- **Complexity**: Medium - Builds on existing ripping infrastructure
- **Risk**: Low - Can be implemented as enhancements without breaking changes
- **Timeline**: Post-v1.0 - Not critical for initial release but important for completeness

---

## H. Architecture Reference

```
┌──────────────────────────────────────────────────────────────┐
│                  DIGITAL ARCHIVE MAKER                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────┐  ┌────────┐  ┌──────────┐  ┌────────┐          │
│  │  CDs   │  │  DVDs  │  │ Blu-rays │  │ Files  │          │
│  └───┬────┘  └───┬────┘  └────┬─────┘  └───┬────┘          │
│      │           │            │             │               │
│      ▼           ▼            ▼             ▼               │
│  ┌──────────────────────────────────────────────────┐       │
│  │               INPUT LAYER                        │       │
│  │  abcde (CD)  │  MakeMKV (Video)  │  File Scan   │       │
│  └──────────────────────────────────────────────────┘       │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────┐       │
│  │             PROCESSING LAYER                     │       │
│  │  Encoder    │  Tagger    │  Organizer  │ Checker │       │
│  │  HandBrake  │  MusicBrnz │  Rename     │ Quality │       │
│  └──────────────────────────────────────────────────┘       │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────┐       │
│  │              METADATA LAYER                      │       │
│  │  MusicBrainz │ TMDb │ Spotify │ iTunes │ Genius  │       │
│  └──────────────────────────────────────────────────┘       │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────┐       │
│  │               OUTPUT LAYER                       │       │
│  │  Local Library ──── Sync Engine ──── Media Server│       │
│  │  /Library/         rsync + filter   Jellyfin     │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

*Last updated: March 2026*
*Status: Sections A (hygiene), B (docs), C (script audit), I1-I2 (GUI app) complete. Sections D–H, I3-I4 remain for future work.*