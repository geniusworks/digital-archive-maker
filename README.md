<div align="center">

# 📀 Digital Library

**Physical Media → Digital Archive → Streaming Server**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

[Quick Start](QUICKSTART.md) •
[Documentation](docs/) •
[Contributing](CONTRIBUTING.md)

</div>

---

> 🎵 **Rip CDs** to FLAC with MusicBrainz metadata and cover art  
> 📀 **Archive DVDs/Blu-rays** with proper subtitles and organization  
> 🏷️ **Tag everything** automatically from MusicBrainz, TMDb, Spotify, iTunes  
> 🔄 **Sync to Jellyfin/Plex** with content filtering (explicit, ratings)

## Why This Exists

| Problem | Solution |
|---------|----------|
| CDs piling up, no organization | One command: rip, tag, organize, done |
| DVDs with wrong subtitles | Intelligent language detection and burn-in |
| Manual metadata entry is tedious | Automatic lookups from 5+ sources |
| Explicit content on family server | Filter by EXPLICIT tag or MPAA rating |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/digital-library.git
cd digital-library
make install-deps
pip install -r requirements.txt

# Configure
cp .env.sample .env
# Edit .env with your paths and API keys

# Rip a CD
make rip-cd

# Rip a DVD/Blu-ray
make rip-video

# (Optional) Add convenience aliases - see QUICKSTART.md for "media" command
```

📖 **[Full Quick Start Guide →](QUICKSTART.md)**

## Features

### 🎵 Music Pipeline
- **CD Ripping** — `abcde` + MusicBrainz for accurate metadata
- **Cover Art** — Automatic fetch from Cover Art Archive
- **Explicit Tagging** — Waterfall lookup: Spotify → iTunes → MusicBrainz
- **Genre Tagging** — Curated whitelist with 100+ genres
- **Library Comparison** — Fuzzy matching to find duplicates/missing albums

### 📀 Video Pipeline  
- **DVD/Blu-ray Ripping** — MakeMKV extraction + HandBrake encoding
- **Subtitle Handling** — Auto-detect, burn-in, or soft-sub muxing
- **Music Videos** — Organize and tag with artist/title metadata

### 🔄 Library Management
- **Multi-destination Sync** — YAML-configured rsync with filters
- **Content Filtering** — Exclude explicit/adult content per destination
- **Playlist Generation** — Auto-create `.m3u8` playlists

## Documentation

| Guide | Description |
|-------|-------------|
| **[Quick Start](QUICKSTART.md)** | Get running in 10 minutes |
| **[Workflow Overview](docs/workflow_overview.md)** | High-level pipelines |
| **[Music Collection](docs/music_collection_guide.md)** | Complete CD-to-Jellyfin guide |
| **[CD Ripping](docs/cd_ripping_guide.md)** | Detailed `abcde` setup |
| **[Video Ripping](docs/video_ripping_guide.md)** | DVD/Blu-ray workflow |
| **[Media Server Setup](docs/media_server_setup.md)** | Jellyfin/Plex configuration |

## Project Structure

```
digital-library/
├── bin/
│   ├── music/          # CD ripping, tagging, metadata
│   ├── video/          # DVD/Blu-ray ripping, subtitles
│   ├── sync/           # Library sync and filtering
│   └── utils/          # Playlist tools, helpers
├── docs/               # Detailed guides
├── tests/              # Test suite
└── Makefile            # Common tasks
```

## Requirements

- **macOS** with Homebrew
- **Python 3.9+**
- **External tools**: `abcde`, `flac`, `ffmpeg`, `HandBrakeCLI`, `MakeMKV`

All dependencies install via:
```bash
make install-deps
pip install -r requirements.txt
```

## API Keys (Optional but Recommended)

Enhanced metadata requires free API keys:

| Service | Purpose | Get Key |
|---------|---------|---------|
| Spotify | Explicit detection | [developer.spotify.com](https://developer.spotify.com/) |
| TMDb | Movie/TV metadata | [themoviedb.org](https://www.themoviedb.org/documentation/api) |
| AcoustID | Audio fingerprinting | [acoustid.org](https://acoustid.org/) |

Configure in `.env` — see `.env.sample` for all options.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Legal

This software is for **personal backup of media you legally own**. See [DISCLAIMER.md](DISCLAIMER.md) for full terms.

**No decryption code is included.** External tools (MakeMKV) must be obtained and licensed separately.

---

<div align="center">

**[⬆ Back to Top](#-digital-library)**

</div>

