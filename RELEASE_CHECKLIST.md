# Release Checklist: v1.0.0 Public Release

> **Single source of truth** for everything needed to ship Media Archive Maker as a polished, delightful, public open-source tool.
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
| **Code Quality** | ✅ Complete | Shared library, type hints, 95 tests passing, clean CI pipeline, professional polish |
| **User Experience** | 🟡 Needs work | No unified CLI, scattered entry points, API keys demanded upfront |
| **GUI App** | ✅ Complete | Electron wrapper with dashboard, console, settings (runs from repo) |
| **Visual / Delight** | 🟡 Needs work | No GIF demos, no terminal screenshots, no CHANGELOG until now |

---

## A. Repository Hygiene (Do First)

### A1. Root-Level File Cleanup
- [x] Create `CHANGELOG.md` (was referenced by README badge but missing)
- [x] Fix `pyproject.toml` — wrong project name, wrong URLs, wrong author
- [x] Fix `NOTICE` — wrong project name and author
- [x] Consolidate `requirements-lyrics.txt` into `requirements.txt`; add missing `Pillow`
- [x] Fix `QUICKSTART.md` — env vars didn't match `.env.sample`
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

### C2. `bin/music/` — 19 scripts → classify as Core vs Utility

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

### C3. `bin/video/` — 17 scripts → classify

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

---

## G. Pre-Release Verification (Run Before EVERY Version Tag)

> **IMPORTANT**: This section applies to ALL releases - v1.0.0, v1.0.1, v1.1.0, v2.0.0, etc.
> Run this complete checklist before tagging any version for public release.

### G1. Quality Assurance Checklist
- [ ] **Code Quality Pipeline**: Run `scripts/test-pipeline.sh` - must pass with 0 errors
- [ ] **All Tests Passing**: 95+ tests must pass (check pytest coverage)
- [ ] **No Critical Linting**: Zero E9/F63/F7/F82 errors
- [ ] **Clean Git Status**: No uncommitted changes in working directory
- [ ] **Documentation Links**: Verify all internal links in README and docs work
- [ ] **Environment Variables**: Cross-check `.env.sample` with all script requirements
- [ ] **Dependency Audit**: Re-run `pip-audit` on requirements.txt and requirements-test.txt

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
- [ ] **README Rendering**: View README on GitHub preview before release
- [ ] **License Compliance**: Verify all deps in requirements.txt have compatible licenses
- [ ] **Security Scan**: Final `gitleaks` or `truffleHog` scan for any missed secrets
- [ ] **Git History**: Review recent commits for any sensitive information

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
- [ ] **Graceful Degradation**: Handle missing dependencies elegantly
  - [ ] Verify graceful handling when MakeMKV is not available
  - [ ] Check behavior when HandBrakeCLI is missing
  - [ ] Test with missing abcde (CD ripping tool)
  - [ ] Verify fallback behavior for missing API keys
  - [ ] Ensure clear error messages with installation guidance
  - [ ] Provide one-click dependency installation where possible
  - [ ] Document which features require which dependencies
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

### I4. Future Standalone Packaging (Post-v1.0)
- [ ] Research bundling Python environment with Electron app
- [ ] Consider PyInstaller or similar for creating truly standalone app
- [ ] Evaluate trade-offs: bundle size vs. user convenience

---

## H. Architecture Reference

```
┌──────────────────────────────────────────────────────────────┐
│                  MEDIA ARCHIVE MAKER                         │
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