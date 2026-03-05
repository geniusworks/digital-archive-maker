<p align="center">
  <img src="assets/logo.png" alt="Digital Archive Maker Logo" width="320" />
</p>

<p align="center">
Turn your CDs, DVDs, and Blu-rays into a convenient digital library you can access from anywhere.
</p>

<div align="center">

[![License](https://img.shields.io/github/license/geniusworks/digital-archive-maker?style=for-the-badge&label=License&labelColor=444444&color=007ec6)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/github/v/release/geniusworks/digital-archive-maker?style=for-the-badge&label=Version&labelColor=444444&color=ED7B00)](CHANGELOG.md)
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

**Digital Archive Maker** does the heavy lifting for you — just insert a disc, and it handles the ripping, tagging, and organizing automatically. Your music and movies appear in your library with proper titles, album art, and descriptions — no manual typing required.

**What it does:**
- 🎵 **Rips your CDs** — Saves as high-quality FLAC with album art and metadata
- 📀 **Archives DVDs & Blu-rays** — Preserves your movies with the right subtitles and language tracks
- 🏷️ **Adds all the details** — Album names, artist info, movie descriptions, genre tags
- 🔄 **Syncs everywhere** — Keeps your library in sync across your devices
- 📱 **Works with your media server** — Send your collection to Jellyfin, Plex, or Emby with one command

Whether you're preserving a decades-old CD collection or archiving your favorite movies, this tool handles the tedious work so you can enjoy your library on any device — all stored on your own hardware, with no monthly fees.

---

## Getting Started

**Step 1: Clone and install dependencies**
```bash
git clone https://github.com/geniusworks/digital-archive-maker.git
cd digital-archive-maker
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

### 🎵 Music
| What it does | How it works |
|--------------|-------------|
| **Rips CDs** | Saves as FLAC (lossless quality) with album art |
| **Finds metadata** | Looks up album names, track titles, artists automatically |
| **Tags explicit content** | Marks songs that may not be family-friendly |
| **Adds genres** | Organizes by genre (rock, jazz, classical, etc.) |
| **Fetches lyrics** | Downloads song lyrics when available |
| **Fixes missing info** | Fills in gaps if something's missing |

### 📀 Video
| What it does | How it works |
|--------------|-------------|
| **Rips DVDs & Blu-rays** | Extracts video while preserving quality |
| **Handles subtitles** | Detects and includes the right language |
| **Burns in subtitles** | Embeds subtitles permanently if needed |
| **Organizes movies** | Names files and adds descriptions automatically |
| **Handles TV shows** | Groups episodes by season |

### 🔄 Library Management
| What it does | How it works |
|--------------|-------------|
| **Syncs your library** | Keeps multiple copies in sync |
| **Filters content** | Can exclude explicit content for family-friendly devices |
| **Creates playlists** | Auto-generates playlists for easy browsing |

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

## What You Need

**Just a Mac** — This runs on any Mac with macOS. You'll need Homebrew (free package manager) installed.

**Optional tools:**
- **MakeMKV** — Required for ripping DVDs/Blu-rays. The free trial works indefinitely for this purpose.
- **API keys** — Optional but recommended for better results:

| Service | Why | How to get it |
|---------|-----|---------------|
| Spotify | More accurate explicit content detection | Free at developer.spotify.com |
| TMDb | Better movie/TV descriptions | Free at themoviedb.org |
| Genius | Song lyrics when available | Free at genius.com/developers |

Everything else installs automatically with one command.

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
digital-archive-maker/
├── bin/
│   ├── music/          # CD ripping and tagging scripts
│   ├── video/          # DVD/Blu-ray ripping scripts
│   ├── sync/           # Library sync scripts
│   ├── tv/             # TV show handling
│   └── utils/          # Helper tools
├── docs/               # Detailed guides
├── config/             # Configuration templates
├── cache/              # Temporary data
├── tests/              # Tests
└── Makefile            # Common commands
```

---

## Common Issues

**"abcde not found"**
```bash
brew install abcde
```

**"MakeMKV not found"**
Download from [makemkv.com](https://www.makemkv.com/) and install the app.

**"No disc found"**
Make sure the disc is inserted. If using an external drive, give it a moment to mount.

**"API errors"**
If you added API keys, check that they're correct in your `.env` file.

Still stuck? Check the [docs](docs/) or open an issue.

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

Made by Martin Diekhoff
