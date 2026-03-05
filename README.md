<p align="center">
  <img src="assets/logo.png" alt="Digital Library Logo" width="320" />
</p>

<p align="center">
Transform physical media into a streaming-ready digital archive — CDs, DVDs, and Blu-rays, organized and tagged automatically.
</p>

<div align="center">

[![License](https://img.shields.io/github/license/geniusworks/digital-library?style=for-the-badge&label=License&labelColor=444444&color=007ec6)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/github/v/release/geniusworks/digital-library?style=for-the-badge&label=Version&labelColor=444444&color=ED7B00)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg?style=for-the-badge&label=Platform&labelColor=444444&color=999999)](https://www.apple.com/macos/)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg?style=for-the-badge&label=Python&labelColor=444444&color=3776AB)](https://www.python.org/downloads/)

</div>

<p align="center">
  <a href="QUICKSTART.md">Quick Start</a> ·
  <a href="docs/">Documentation</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="DISCLAIMER.md">Disclaimer</a> ·
  <a href="SECURITY.md">Security</a>
</p>

---

## About

**Digital Library** transforms your physical media collection — CDs, DVDs, and Blu-rays — into a perfectly organized digital archive ready for Jellyfin, Plex, or any media server.

**What it provides:**
- 🎵 **CD Ripping** — Automatic metadata from MusicBrainz, cover art fetching, FLAC lossless
- 📀 **DVD/Blu-ray Archiving** — MakeMKV + HandBrake with intelligent subtitle handling
- 🏷️ **Smart Tagging** — Explicit content flags, genre normalization, lyrics fetching
- 🔄 **Multi-destination Sync** — rsync with content filtering (explicit, ratings)
- 📱 **Media Server Ready** — Outputs organized files with proper metadata for Jellyfin/Plex

Perfect for anyone with a growing pile of physical media who wants to preserve their collection in a modern, streaming-ready format — while keeping full control of their data on their own hardware.

---

## Getting Started

**Step 1: Clone and install dependencies**
```bash
git clone https://github.com/geniusworks/digital-library.git
cd digital-library
make install-deps
source venv/bin/activate
```

**Step 2: Configure**
```bash
cp .env.sample .env
# Edit .env with your paths and optional API keys
```

**Step 3: Rip a CD**
```bash
make rip-cd
```

**Step 4: Rip a DVD/Blu-ray**
```bash
make rip-video
```

**Step 5: Sync to your media server**
```bash
python bin/sync/master-sync.py
```

📖 **[Full Quick Start Guide →](QUICKSTART.md)**

---

## Core Features

### 🎵 Music Pipeline
| Feature | Description |
|---------|-------------|
| **CD Ripping** | `abcde` with MusicBrainz lookup, FLAC output |
| **Cover Art** | Automatic fetch from Cover Art Archive |
| **Explicit Tagging** | Waterfall: Spotify → iTunes → MusicBrainz |
| **Genre Tagging** | Curated whitelist with 100+ genres |
| **Metadata Fixer** | Comprehensive MusicBrainz-based repair |
| **Lyrics Download** | Genius API + lyrics.ovh fallback |

### 📀 Video Pipeline
| Feature | Description |
|---------|-------------|
| **Disc Ripping** | MakeMKV extraction + HandBrake encoding |
| **Subtitle Handling** | Auto-detect, burn-in, or soft-sub muxing |
| **Language Detection** | Intelligent audio/subtitle selection |
| **Music Videos** | Organize with artist/title metadata |

### 🔄 Library Management
| Feature | Description |
|---------|-------------|
| **Multi-destination Sync** | YAML-configured rsync with filters |
| **Content Filtering** | Exclude explicit/adult content per destination |
| **Playlist Generation** | Auto-create `.m3u8` playlists |

---

## Command Reference

```bash
# Rip media
make rip-cd              # Rip audio CD to FLAC
make rip-video           # Rip DVD/Blu-ray to MP4/MKV

# Tag and organize
python bin/music/tag-explicit-mb.py --path /path/to/music
python bin/music/download_lyrics.py --path /path/to/music --recursive
python bin/music/update-genre-mb.py --path /path/to/music

# Sync library
python bin/sync/master-sync.py
python bin/sync/sync-library.py --config sync-config.yaml

# Quality checks
python bin/music/check_album_integrity.py --path /path/to/music
```

For more commands, see [Documentation](docs/).

---

## System Requirements

**macOS requirements:**
- macOS with Homebrew
- Python 3.9+

**External tools (installed via `make install-deps`):**
- `abcde` — CD ripping
- `flac` — Audio encoding
- `ffmpeg` — Media processing
- `HandBrakeCLI` — Video encoding
- `MakeMKV` — Disc decryption (installed separately)

**Optional API keys for enhanced metadata:**
| Service | Purpose | Get Key |
|---------|---------|---------|
| Spotify | Explicit detection | [developer.spotify.com](https://developer.spotify.com/) |
| TMDb | Movie/TV metadata | [themoviedb.org](https://www.themoviedb.org/documentation/api) |
| Genius | Lyrics fetching | [genius.com/developers](https://genius.com/developers) |
| AcoustID | Audio fingerprinting | [acoustid.org](https://acoustid.org/) |

---

## Documentation

| Guide | Description |
|-------|-------------|
| **[Quick Start](QUICKSTART.md)** | Get running in 10 minutes |
| **[Workflow Overview](docs/workflow_overview.md)** | High-level pipelines |
| **[Music Collection](docs/music_collection_guide.md)** | Complete CD-to-Jellyfin guide |
| **[Video Ripping](docs/video_ripping_guide.md)** | DVD/Blu-ray workflow |
| **[Media Server Setup](docs/media_server_setup.md)** | Jellyfin/Plex configuration |
| **[Server Setups](docs/server_setups/)** | Hardware-specific guides |

---

## Project Structure

```
digital-library/
├── bin/
│   ├── music/          # CD ripping, tagging, metadata
│   ├── video/          # DVD/Blu-ray ripping, subtitles
│   ├── sync/           # Library sync and filtering
│   ├── tv/             # TV show metadata
│   └── utils/          # Playlist tools, helpers
├── docs/               # Detailed guides
├── config/             # Configuration templates
├── cache/              # Runtime cache
├── tests/              # Test suite
└── Makefile            # Common tasks
```

---

## Troubleshooting

**"Command not found: abcde"**
```bash
brew install abcde
```

**"MakeMKV not found"**
Download from [makemkv.com](https://www.makemkv.com/) and install.

**"No disc found"**
Ensure your disc is inserted and mounted. External drives may need a moment.

**API errors**
Check that your `.env` file has valid API keys and that you haven't exceeded rate limits.

Need more help? Check [docs/](docs/) or open an issue.

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Disclaimer

This software is for **personal backup of media you legally own**. Users are solely responsible for compliance with applicable copyright laws in their jurisdiction.

- **No decryption code is included** — External tools (MakeMKV) must be obtained and licensed separately
- **No copyrighted content is downloaded** — Metadata lookups use authorized public APIs
- **For personal use only** — See [DISCLAIMER.md](DISCLAIMER.md) for full terms

---

## Author

Made by Martin Herd
