<p align="center">
  <img src="assets/logo.png" alt="Digital Archive Maker Logo" width="320" />
</p>

<p align="center">
Transform CDs, DVDs, and Blu-rays into a perfectly organized, media server-ready digital library.
</p>

<div align="center">

[![License](https://img.shields.io/badge/license-GPLv2+-007ec6?style=for-the-badge&label=License&labelColor=444444)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/geniusworks/digital-archive-maker?include_prereleases&style=for-the-badge&label=Version&labelColor=444444&color=ED7B00)](https://github.com/geniusworks/digital-archive-maker/releases)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg?style=for-the-badge&label=Platform&labelColor=444444&color=999999)](https://www.apple.com/macos/)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg?style=for-the-badge&label=Python&labelColor=444444&color=3776AB)](https://www.python.org/downloads/)

</div>

<p align="center">
  <a href="QUICKSTART.md">Quick Start</a> ·
  <a href="docs/">Documentation</a> ·
  <a href="ROADMAP.md">Roadmap</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="DISCLAIMER.md">Disclaimer</a> ·
  <a href="SECURITY.md">Security</a>
</p>

---

## About

**Digital Archive Maker** converts your physical disc collection into a rich digital archive you can use anywhere.

**The Challenge:** Your media collection sits on shelves—difficult to browse, search, access, and enjoy. Many transfer tools are difficult to orchestrate, lossy, or lock you into closed systems.

**The Gap:** Creating a perfect digital library requires dozens of uncoordinated tools for ripping, tagging, organizing, and delivery.

**Digital Archive Maker handles it all:**
- 📀 **Reads** any disc (CD, DVD, Blu-ray)
- 💻 **Extracts** archival quality digital files
- 🏷️ **Enriches** with artwork, subtitles, and metadata
- 📁 **Organizes** a browsable, searchable collection
- 🔄 **Syncs** to your device or media server

**Result:** Your physical collection becomes a searchable, accessible digital library—stored on your hardware, no subscriptions required.

---

## Development Status

**Current Version: 0.9.0-beta** - Pre-release, actively developed

### ✅ What's Working
- **Complete media pipelines** for CDs, DVDs, Blu-rays, and TV show discs
- **Advanced subtitle processing** with language preferences and OCR support
- **Unified CLI** (`dam`) with comprehensive commands including `make rip-episodes`
- **Rich metadata integration** (MusicBrainz, TMDb, Spotify, Genius)
- **Comprehensive documentation** and user guides
- **Comprehensive testing** and automated quality checks

### 🎯 Roadmap to 1.0.0
- **TV show workflow validation** (ripping complete, organization verification needed)
- **DAM workflow validation and optimization** for all main features
- **API key graceful failure** handling improvements
- **GUI application testing** and refinement
- **Hardware compatibility testing** for different drives
- **Documentation & Onboarding**
  - Troubleshooting guide for common issues
  - Video tutorials for key workflows
  - Examples gallery with sample configurations
- **Final documentation polish** and examples

### 🤝 Community Status
- **Open for feedback** and feature requests
- **Contributions welcome** - see CONTRIBUTING.md
- **Issue tracking** active on GitHub
- **Discussions** enabled for community input

---

## Requirements

### 🖥️ What You Need
- **macOS** (Catalina or newer)
- **8GB+ RAM** recommended for video processing
- **50GB+ free storage** for temporary files

### 💿 Hardware (for ripping)
- **CD, DVD, and/or Blu-ray drive** (internal or USB)

### 📦 Software
- **Optional**: MakeMKV (for DVD/Blu-ray) requires manual download from makemkv.com (free beta available)
- **Everything else is installed automatically** by `make install-deps`

---

## Getting Started

**Step 1: Clone and install**
```bash
git clone https://github.com/geniusworks/digital-archive-maker.git
cd digital-archive-maker
make install-deps
```

**Step 2: Configure** (choose one)
```bash
# interactive wizard (recommended)
dam config
```

Or manually:
```bash
cp .env.example .env
# Edit .env with your paths and optional API keys
```

**GUI Option:** For a graphical interface (alpha quality - CLI preferred during beta):
```bash
cd gui && npm start
```

**Step 3: Rip a CD**
```bash
dam rip cd
```

**Step 4: Rip a movie disc**
```bash
dam rip video
```

**Step 5: Rip TV show episodes**
```bash
dam rip video --title "Show Name" --year 2024 --episodes
```

**Step 6: Sync to your media server**
```bash
dam sync
```

**[Full Quick Start Guide →](QUICKSTART.md)**

---

## Core Features

### **Music**
| Feature | How it works |
|:---------|:------------|
| **CD ripping** | Saves as FLAC with album art |
| **Metadata** | Automatic album/track/artist lookup |
| **Content tags** | Marks explicit content (optional) |
| **Genres** | Organizes by musical style |
| **Lyrics** | Downloads when available |
| **Gap filling** | Fixes missing information |

### **Video**
| Feature | How it works |
|:---------|:------------|
| **Movie discs** | Extracts high-quality video |
| **TV show episodes** | Detects and rips all episodes from TV show discs |
| **Subtitles** | Includes your preferred language |
| **Subtitle burning** | Embeds subtitles when needed |
| **Movie organization** | Names files and adds descriptions |
| **TV show organization** | Groups episodes by season with continuous numbering |

### **Library Management**
| Feature | How it works |
|:---------|:------------|
| **Library sync** | Syncs library to media servers and backups with content filtering |
| **Content filtering** | Excludes explicit content for family devices (optional) |
| **Playlists** | Creates album playlists and fixes missing metadata |

---

## Command Reference

```bash
# Setup & configuration
dam check                # Verify all dependencies and API keys
dam check --install      # Auto-install missing Homebrew packages
dam config               # Interactive first-run wizard (library path, API keys)
dam version              # Show current version

# Rip media
dam rip cd                                              # Rip audio CD to FLAC
dam rip video                                           # Rip movie disc to MP4
dam rip video --title "Movie" --year 2024               # With metadata
dam rip video --title "Show" --year 2024 --episodes     # TV show disc
dam rip video --title "Show" --year 2024 --episodes --skip-disc  # Process existing MKV files

# TV show episodes (Makefile targets)
make rip-episodes TITLE="Show Name" YEAR=2024           # Rip TV show disc
make rip-movie TITLE="Movie Name" YEAR=2024             # Rip movie disc
make rip-movie-all TITLE="Movie Name" YEAR=2024         # Rip all tracks

# Tag and organize
dam tag explicit /path/to/music                 # Tag explicit content
dam tag explicit /path/to/music --dry-run       # Preview without writing
dam tag genres /path/to/music                   # Add genre tags
dam tag lyrics /path/to/music                   # Download lyrics
dam tag lyrics /path/to/music --no-recursive    # Process single directory
dam tag movie /path/to/movies                   # Add movie metadata

# Sync library
dam sync                 # Sync to media server
dam sync --dry-run       # Preview without changes
dam sync --quiet         # Minimal output
```

The `dam` command provides easy access to all features with automatic setup. You can also use individual scripts directly — see [Documentation](docs/) for details.

---

## Documentation

| Guide | Description |
|:------|:------------|
| **[Quick Start](QUICKSTART.md)** | Get running in 10 minutes |
| **[Workflow Guide](docs/workflow_guide.md)** | High-level pipelines |
| **[Music Guide](docs/music_guide.md)** | Complete CD-to-library guide |
| **[Video Guide](docs/video_guide.md)** | Movie and TV show disc workflows |
| **[Server Guide](docs/server_guide.md)** | Jellyfin/Plex configuration |
| **[Tools Guide](docs/tools_guide.md)** | Additional utilities |
| **[Server Setups](docs/server_setups/)** | Hardware-specific guides |

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Disclaimer

This software is for **personal backup of media you legally own**. Users are solely responsible for compliance with applicable copyright laws in their jurisdiction.

- **No decryption code is included** — External tools (MakeMKV) must be obtained and licensed separately
- **Metadata uses authorized APIs** — Song lyrics may be downloaded when available
- **For personal use only** — See [DISCLAIMER.md](DISCLAIMER.md) for full terms

---

## Uninstall

To remove Digital Archive Maker:
```bash
make uninstall  # Removes Python package and virtual environment
```

Optional cleanup (run manually if needed):
```bash
brew uninstall handbrake ffmpeg jq tesseract mkvtoolnix libdvdcss
rm -rf cache/ log/  # Remove cache and log directories
```

## Development

For development setup and testing guidelines, see [Contributing](CONTRIBUTING.md).

## Author

Made by Martin Diekhoff
