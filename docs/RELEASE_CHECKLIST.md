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
| **Code Quality** | 🟡 Needs polish | Naming inconsistency, no shared library, some stale scripts |
| **User Experience** | 🟡 Needs work | No unified CLI, scattered entry points, API keys demanded upfront |
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
- [ ] Add `.gitkeep` to `log/` and `cache/` if not already present
- [ ] Confirm `config/` ships only `.gitkeep` (user-specific overrides stay local)

### A3. Dependency & Packaging
- [ ] Audit all Python deps for license compatibility (MIT project; all deps should be permissive)
- [ ] Bump `pyproject.toml` version to `1.0.0` at release time
- [ ] Ensure `make install-deps` + `make install-video-deps` is truly one-command on a fresh Mac
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
| `LICENSE` | MIT license | ✅ Keep |
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
- [ ] Ensure every doc links back to QUICKSTART.md for prereqs
- [ ] Replace hardcoded `/Volumes/Data/Media/...` paths with `${LIBRARY_ROOT}/...` where possible

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

### D1. Unified CLI (Major Feature — Post-1.0 or 1.0)
*Replace scattered scripts with a single, intuitive entry point.*

- [ ] Create unified CLI entry point (`dam` or `archive` command) using `typer` or `click` + `rich`
  - Subcommands: `dam rip`, `dam tag`, `dam sync`, `dam config`
  - Interactive prompts if run without flags
- [ ] Goal-oriented processing: `dam tag --lyrics --covers --genres`
- [ ] Feature-driven API onboarding: prompt for keys only when a feature needs them
  - *"To fetch lyrics, you need a free Genius API key. Get one at [URL], paste it here:"*
  - Save keys to `.env` automatically

### D2. Non-Destructive Safety
*Users should feel safe experimenting. Never destroy work without explicit confirmation.*

- [ ] Safe resumption: re-running a command adds new data without disturbing existing metadata
- [ ] Explicit deletion confirmation: `--force-overwrite` flag or typed confirmation
- [ ] Smart sync dry-run: make dry-run the default, require `--confirm` to execute

### D3. "Just Works" Defaults
*Minimize decisions for a perfect result.*

- [ ] Zero-config defaults: sensible FLAC for audio, good Handbrake presets for video
- [ ] Auto-detect media type: `dam rip` detects CD vs DVD vs Blu-ray automatically
- [ ] Central path config: `dam config` wizard asks for library root once

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

---

## E. Code Quality & Polish

### E1. Important for Professional Release
- [ ] Add `--help` with clear usage examples to every script
- [ ] Ensure every script checks for required tools before running (e.g., `makemkvcon`, `HandBrakeCLI`)
- [ ] Add type hints to critical public functions
- [ ] Extract shared patterns into a `lib/` or `digitallibrary/core/` module (config, logging, API clients)
- [ ] Standardize exit codes across all scripts (0 = success, 1 = error, 2 = partial)

### E2. Testing
- [ ] Current tests cover: `backfill_subs`, `clean_playlists`, `fix_album`, `fix_album_covers`, `set_explicit`
- [ ] Add tests for: `download_lyrics`, `tag-explicit-mb`, `rip_video` (mock-based)
- [ ] Target: 70%+ coverage for core scripts

### E3. CI / Pre-commit
- [ ] Add pre-commit hooks config: `black`, `isort`, `flake8`
- [ ] Ensure CI runs on PR (already have `.github/workflows/ci.yml`)

---

## F. Visual Polish & Delight

- [ ] Create project logo (or refine existing `assets/logo.png`)
- [ ] Add GIF demo of CD ripping workflow (terminal recording)
- [ ] Add terminal screenshots showing beautiful output
- [ ] Test README rendering on GitHub before release
- [ ] Consistent emoji language across docs (already partially done)

---

## G. Release Execution

### Pre-Release Final Steps
- [ ] Complete items in sections A–C above
- [ ] Run full PII / secrets scan on all tracked files
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

## H. Architecture Reference

```
┌──────────────────────────────────────────────────────────────┐
│                  DIGITAL ARCHIVE MAKER                       │
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
*Status: Sections A (hygiene), B (docs), C (script audit) complete. Sections D–G remain for future work.*