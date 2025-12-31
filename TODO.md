# TODO: Repository Improvements & Pipeline Optimization

## 📋 Overview
This document outlines improvements needed to make this repository more organized, better documented, and more efficient for users preparing media files for Jellyfin/media server ingestion.

---

## 🗂️ Organization & Structure

### Current Structure Analysis
```
digital-library/
├── README.md                    # Comprehensive main guide ✅
├── IMPROVEMENTS.md              # Detailed changelog ✅
├── TODO.md                      # This file ✅
├── requirements.txt             # Python dependencies ✅
├── .env.example                 # Environment template ✅
├── Makefile                     # Build automation ✅
├── .abcde.conf*                 # CD ripping config
├── bin/                         # Main scripts directory ✅
│   ├── Music Scripts:
│   │   ├── update-genre-mb.py
│   │   ├── tag-manual-genre.py
│   │   ├── tag-explicit-mb.py
│   │   └── check_album_integrity.py
│   ├── Video Scripts:
│   │   ├── rip_video.sh
│   │   ├── tag-movie-metadata.py
│   │   ├── tag-movie-ratings.py
│   │   └── backfill_subs.sh
│   ├── TV Scripts:
│   │   ├── tag-show-metadata.py
│   │   └── rename_shows_jellyfin.py
│   ├── Utility Scripts:
│   │   ├── sync-library.py
│   │   ├── repair-flac-tags.py
│   │   ├── generate-playlists.py
│   │   └── fix-*.py (various fix scripts)
├── docs/                        # Documentation ✅
│   ├── cd_ripping_guide.md
│   ├── video_ripping_guide.md
│   ├── media_server_setup.md
│   └── workflow_overview.md
├── log/                         # Logs and cache ✅
├── _archive/                    # Archived files
├── _install/                    # Installation files
├── custom-sync/                 # Custom sync scripts
└── Root-level scripts:          # SCATTERED - needs consolidation
    ├── fix_album.sh
    ├── fix_album_covers.sh
    ├── fix_metadata.py
    ├── fix_track.py
    ├── compare_music.py
    └── disc_ripping_guide.md
```

### Current Issues
- **Script organization inconsistency** - Some scripts in `bin/`, others in root
- **Naming convention conflicts** - Mix of `kebab-case` and `snake_case`
- **No clear categorization** - Scripts mixed without clear purpose grouping
- **Redundant functionality** - Multiple scripts doing similar operations
- **Root-level clutter** - Utility scripts should be organized better

### Proposed Structure
```
digital-library/
├── README.md                    # Main getting started guide
├── TODO.md                      # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── Makefile                     # Build automation
├── config/                      # NEW: Configuration files
│   ├── media.yml               # Unified configuration
│   └── genres.yml              # Genre configuration
├── scripts/                     # RENAMED: All scripts consolidated
│   ├── music/
│   │   ├── update-genre-mb.py
│   │   ├── tag-manual-genre.py
│   │   ├── tag-explicit-mb.py
│   │   ├── check_album_integrity.py
│   │   └── fix_album.py        # MOVED from root
│   ├── video/
│   │   ├── rip_video.sh
│   │   ├── tag-movie-metadata.py
│   │   ├── tag-movie-ratings.py
│   │   └── backfill_subs.sh
│   ├── tv/
│   │   ├── tag-show-metadata.py
│   │   └── rename_shows_jellyfin.py
│   ├── utils/
│   │   ├── sync-library.py
│   │   ├── repair-flac-tags.py
│   │   ├── generate-playlists.py
│   │   ├── fix_metadata.py     # MOVED from root
│   │   ├── fix_track.py        # MOVED from root
│   │   └── compare_music.py    # MOVED from root
│   └── legacy/                  # DEPRECATED: Old scripts for reference
├── docs/                        # Enhanced documentation
│   ├── getting-started.md       # NEW
│   ├── configuration.md         # NEW
│   ├── music-workflow.md        # NEW
│   ├── video-workflow.md        # ENHANCED
│   ├── troubleshooting.md        # NEW
│   ├── cd_ripping_guide.md
│   ├── video_ripping_guide.md
│   ├── media_server_setup.md
│   └── workflow_overview.md
├── log/                         # Logs and cache
├── _archive/                    # Archived files
└── _install/                    # Installation files
```

---

## 📚 Documentation Improvements

### Missing Documentation
- [ ] **Getting Started Guide** - Step-by-step setup for new users (partially in README.md)
- [ ] **Configuration Guide** - How to set up `.env` and config files (scattered across docs)
- [ ] **Workflow Guides** - End-to-end examples for each media type (exists but fragmented)
- [ ] **Troubleshooting Guide** - Common issues and solutions (missing)
- [ ] **API Setup Guide** - MusicBrainz, TMDb, OMDb, Spotify setup (partially in docs)

### Current Documentation Assets
✅ **README.md** - Comprehensive 35KB main guide with all workflows
✅ **IMPROVEMENTS.md** - Detailed changelog and feature documentation  
✅ **docs/video_ripping_guide.md** - 16KB comprehensive video guide
✅ **docs/media_server_setup.md** - Jellyfin/Plex setup instructions
✅ **docs/cd_ripping_guide.md** - CD ripping workflow
✅ **docs/workflow_overview.md** - High-level overview
✅ **requirements.txt** - Dependencies listed
✅ **.env.sample** - Environment template

### Documentation Standards Needed
- [ ] **Consistent formatting** across all documentation
- [ ] **Code examples** for every major feature
- [ ] **Prerequisites** clearly listed for each script
- [ ] **Migration guides** when making breaking changes
- [ ] **Index/Navigation** - Better way to find relevant documentation

---

## 🔧 Configuration Management

### Current Configuration Assets
✅ **.env** - Environment variables for API keys and paths
✅ **.env.sample** - Template for new users
✅ **.abcde.conf** - CD ripping configuration
✅ **Makefile** - Build automation and dependency installation

### Current Problems
- **Environment variables scattered** - Some scripts have hardcoded paths
- **No unified configuration** - Each script manages its own config
- **No validation** of configuration on startup
- **Configuration fragmentation** - Settings spread across multiple files

### Proposed Solution
```yaml
# config/media.yml - NEW: Unified configuration
paths:
  music_library: "/Volumes/Data/Media/Rips"
  video_library: "/Volumes/Data/Media/Videos"
  log_dir: "./log"

api_keys:
  musicbrainz: ""
  tmdb: ""
  omdb: ""
  spotify_client_id: ""
  spotify_client_secret: ""

genres:
  whitelist_file: "config/genres.yml"
  enable_transformers: true
  enable_christmas_detection: true

processing:
  parallel_downloads: 4
  api_timeout: 15
  max_retries: 4
```

---

## 🚀 Pipeline Efficiency Improvements

### Current Pipeline Strengths
✅ **Music pipeline** - Comprehensive genre tagging with MusicBrainz integration
✅ **Video pipeline** - Complete DVD/Blu-ray ripping with HandBrake integration
✅ **TV pipeline** - Show metadata with TMDb/IMDb fallback
✅ **Explicit content detection** - Automatic tagging with multiple sources
✅ **Real-time logging** - Unresolved files and rejected genres tracking

### Current Pipeline Issues
- **Sequential processing** - No parallel operations for large libraries
- **No resume capability** - Interrupted operations start from scratch
- **Limited progress tracking** - Basic progress bars, no ETA calculations
- **No batch operations** - Must run scripts manually for each folder
- **No health monitoring** - No way to monitor library health over time

### Proposed Improvements
- [ ] **Parallel processing** - Process multiple albums/movies simultaneously
- [ ] **Batch operations** - Process entire library in one run
- [ ] **Progress tracking** - Better progress bars and ETA calculations
- [ ] **Resume capability** - Resume interrupted processing from last checkpoint
- [ ] **Smart caching** - Cache artist-level lookups to reduce API calls
- [ ] **Health monitoring** - Track library quality and completeness over time

---

## 🛠️ Technical Improvements

### Current Technical Assets
✅ **Python scripts** - Well-structured with error handling
✅ **Bash scripts** - Robust video ripping pipeline
✅ **Signal handling** - Proper Ctrl+C handling in update-genre-mb.py
✅ **Caching system** - Genre cache and API call optimization
✅ **Logging system** - Real-time unresolved and rejected genre tracking

### Technical Debt
- [ ] **Type hints** - Missing from most Python scripts
- [ ] **Consistent error handling** - Different patterns across scripts
- [ ] **Structured logging** - Basic print statements instead of proper logging
- [ ] **Testing framework** - No unit tests for core functions
- [ ] **Code linting** - Inconsistent formatting and style
- [ ] **Async operations** - No asyncio for I/O bound operations

### Performance Optimizations
- [ ] **Connection pooling** - Reuse HTTP connections for API calls
- [ ] **Memory optimization** - Better memory usage for large libraries
- [ ] **Caching layers** - Multiple caching strategies for different data types
- [ ] **Batch API calls** - Reduce round trips to external APIs

---

## 🎯 Media Server Readiness

### Current Server Integration
✅ **Jellyfin naming conventions** - Follows proper folder/file naming
✅ **Metadata standards** - Compatible with Jellyfin/Plex expectations
✅ **NFO generation potential** - Scripts have metadata needed for NFO files
✅ **Artwork handling** - Cover art embedding and management

### Missing Server Features
- [ ] **NFO generation** - Generate NFO files for Jellyfin/Plex
- [ ] **Artwork optimization** - Optimize cover art for server consumption
- [ ] **Format validation** - Ensure files meet server requirements
- [ ] **Quality assurance** - Validate files before server ingestion
- [ ] **Library health checks** - Ensure server-compatible library structure

---

## � Workflow Automation

### Current Workflow Strengths
✅ **End-to-end music processing** - From CD ripping to genre tagging
✅ **Complete video pipeline** - From disc to server-ready files
✅ **Manual tagging tools** - tag-manual-genre.py for problematic files
✅ **Real-time feedback** - Unresolved files logged immediately

### Automation Gaps
- [ ] **One-command ripping** - From disc to server-ready media
- [ ] **Watched folders** - Automatically process new files
- [ ] **Scheduled maintenance** - Regular library health checks
- [ ] **Notification system** - Alert on completion or errors
- [ ] **CLI wizard** - Guided setup for new users

---

## 📦 Distribution & Deployment

### Current Distribution
✅ **Makefile** - Dependency installation and setup
✅ **requirements.txt** - Python dependencies listed
✅ **Environment template** - .env.sample for configuration
✅ **Comprehensive documentation** - Multiple guides and references

### Deployment Improvements
- [ ] **Setup script** - Automated setup for new users
- [ ] **Docker support** - Containerized deployment option
- [ ] **Cross-platform compatibility** - Windows/Linux support
- [ ] **Update mechanism** - Easy way to update scripts
- [ ] **Backup/restore** - Backup configuration and data

---

## 🎨 User Experience & Branding

### Current User Experience
✅ **Comprehensive documentation** - 35KB README with detailed workflows
✅ **Practical error messages** - Clear feedback in most scripts
✅ **Real-time progress feedback** - Progress bars and status updates
✅ **Manual override tools** - tag-manual-genre.py for problematic files
✅ **Signal handling** - Proper Ctrl+C behavior with graceful shutdown

### User Experience Gaps
- **No unified CLI** - Users must know which script to run for each task
- **Technical naming** - Script names are functional but not user-friendly
- **No friendly branding** - Generic "digital-library" name
- **Limited onboarding** - No guided setup for new users
- **No visual feedback** - Text-only interface, no progress visualization

### Proposed Branding & Identity

#### **Project Name Ideas:**
- **MediaFlow** - Suggests smooth media processing pipeline
- **Librarian** - Evokes organization and curation
- **MediaCurator** - Professional media management
- **DigitalVault** - Secure, organized media storage
- **StreamReady** - Focus on server-ready output
- **MediaForge** - Crafting perfect media libraries
- **ArchiveCraft** - Artful media archiving

#### **Recommended Name: `MediaFlow`**
- **Memorable and professional**
- **Suggests pipeline/flow concept**
- **Easy to say and type**
- **Available domain likely**
- **Evokes efficiency and organization**

### User Experience Enhancements

#### **Friendly CLI Interface**
```bash
# Current: Multiple script names
python3 bin/update-genre-mb.py --recursive --force-missing
python3 bin/tag-manual-genre.py --genre "jazz"
python3 bin/rip_video.sh

# Proposed: Unified CLI
mediaflow music tag --recursive --force-missing
mediaflow music manual --genre "jazz"
mediaflow video rip
mediaflow tv metadata
mediaflow library health
mediaflow library organize
```

#### **Interactive Setup Wizard**
```bash
$ mediaflow setup
🎵 Welcome to MediaFlow! Let's set up your media library.

📁 Where is your music library? [/Volumes/Data/Media/Rips]: 
🎬 Where is your video library? [/Volumes/Data/Media/Videos]:
🔑 Do you have API keys? (MusicBrainz, TMDb) [y/N]: y
🎯 What's your primary media server? [Jellyfin/Plex/Emby]: Jellyfin

✅ Setup complete! Ready to process your media.
🚀 Try: mediaflow music scan --help
```

#### **Friendly Logging & Progress**
```bash
$ mediaflow music tag --recursive

🎵 MediaFlow Music Tagger v1.0
📁 Scanning: /Volumes/Data/Media/Rips (6,543 files found)
⚡ Processing: 1,234/6,543 (18.9%) • ETA: 3m 24s
🎼 Last processed: The Beatles - Abbey Road • Genre: rock
📊 Statistics: 1,200 tagged • 34 skipped • 0 errors

🎯 Current file: Pink Floyd - The Dark Side of the Moon
🔍 Looking up: Pink Floyd → Progressive rock → ✅ rock
💾 Saved: Pink Floyd - The Dark Side of the Moon (rock)
```

#### **Visual Progress Indicators**
- **Progress bars** with percentage and ETA
- **Real-time statistics** (tagged, skipped, errors)
- **Current file display** with artist/album info
- **Genre lookup visualization** showing transformation process
- **Success/failure indicators** with emojis/colors

#### **Smart Error Handling**
```bash
❌ Error processing file:
📁 File: /path/to/problem.flac
🎵 Artist: Unknown Artist
💬 Issue: No metadata found
💡 Suggestion: Try manual tagging with --force flag
🔧 Command: mediaflow music manual --genre "genre" /path/to/problem.flac
```

### Onboarding Experience

#### **Quick Start Guide**
```bash
# One-command setup
curl -sSL https://mediaflow.dev/install | bash

# Interactive configuration
mediaflow setup

# First scan
mediaflow music scan --quick

# Health check
mediaflow library health --report
```

#### **Contextual Help System**
```bash
$ mediaflow --help
🎵 MediaFlow - Your Digital Library Toolkit

Commands:
  music    🎼 Organize and tag your music collection
  video    🎬 Rip and process videos
  tv       📺 Manage TV show metadata
  library  📚 Library health and organization
  setup    ⚙️  Configure MediaFlow
  doctor   🔍 Diagnose and fix issues

Get help: mediaflow <command> --help
Docs: https://mediaflow.dev/docs
```

### Accessibility & Inclusivity

#### **Multi-language Support**
- **Internationalized error messages**
- **Unicode genre handling** (already good with guaguancó example)
- **Cultural genre awareness** (world music, regional genres)
- **Accessibility features** for screen readers

#### **Skill Level Adaptation**
```bash
# Beginner mode
mediaflow music scan --easy

# Advanced mode
mediaflow music tag --transformers --cache-bypass --parallel 8

# Expert mode
mediaflow config --edit raw
```

---

## 🚨 Priority Items

### High Priority (This Week)
1. **Consolidate root-level scripts** - Move fix_*.py scripts to scripts/utils/
2. **Create unified configuration system** - config/media.yml
3. **Add structured logging** - Replace print statements with proper logging
4. **Script organization cleanup** - Consistent naming and categorization
5. **🎨 DESIGN BRANDING** - Choose project name and create friendly CLI interface

### Medium Priority (This Month)
1. **Parallel processing for music pipeline** - Process multiple albums
2. **Resume capability** - Checkpoint and resume interrupted operations
3. **Health monitoring system** - Track library quality over time
4. **NFO generation** - Generate Jellyfin-compatible metadata files
5. **🎯 UNIFIED CLI** - Implement mediaflow command with subcommands

### Low Priority (Future)
1. **Web interface development** - Optional web UI for management
2. **Docker containerization** - Portable deployment option
3. **Advanced analytics** - Library statistics and reporting
4. **Mobile app development** - Remote monitoring and control
5. **🌟 PREMIUM FEATURES** - Advanced automation and AI-powered suggestions

---

## 📝 Implementation Notes

### Immediate Actions Required
1. **Script consolidation** - Move root-level scripts to appropriate subdirectories
2. **Configuration unification** - Create config/media.yml and migrate settings
3. **Documentation reorganization** - Create better navigation in docs/
4. **Naming standardization** - Choose consistent naming convention
5. **🎨 BRAND IDENTITY** - Select final name and design logo/color scheme

### User Experience Strategy
- **Progressive disclosure** - Simple interface that reveals advanced features
- **Visual feedback** - Progress bars, emojis, and clear status indicators
- **Contextual help** - Right help at the right time
- **Error recovery** - Clear paths forward when things go wrong
- **Success celebration** - Acknowledge completed tasks with positive feedback

### Migration to Unified CLI
```bash
# Phase 1: Keep existing scripts, add mediaflow wrapper
# Phase 2: Deprecate individual scripts with warnings
# Phase 3: Remove old scripts after transition period
```

---

## 🎯 Success Metrics

### Organization Metrics
- [ ] Zero scripts in root directory (except README.md, TODO.md)
- [ ] All scripts follow consistent naming convention
- [ ] Clear categorization of all scripts by purpose
- [ ] Unified configuration system for all scripts

### Performance Metrics
- [ ] Process 1000 tracks in under 10 minutes (with parallel processing)
- [ ] Resume capability saves 90% of progress on interruption
- [ ] Library health checks complete in under 5 minutes
- [ ] 99% successful processing rate with proper error handling

### User Experience Metrics
- [ ] Setup time under 30 minutes for new users
- [ ] One-command processing for common workflows
- [ ] Clear error messages with recovery suggestions
- [ ] Comprehensive documentation with examples
- [ ] **🎨 FRIENDLY INTERFACE** - Users describe it as "delightful" and "intuitive"
- [ ] **🎯 BRAND RECOGNITION** - Users recognize and recommend "MediaFlow"

---

*Last updated: December 30, 2025*
*Current Status: Well-documented but needs organization and performance improvements*
*Next Steps: Script consolidation, configuration unification, and user experience transformation*
*🎨 VISION: Transform from technical toolkit to user-friendly "MediaFlow" digital library assistant*
