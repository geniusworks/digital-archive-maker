<p align="center">
  <img src="assets/logo.png" alt="Media Archive Maker Logo" width="320" />
</p>

<p align="center">
Turn your CDs, DVDs, and Blu-rays into a convenient digital library you can access from anywhere.
</p>

<div align="center">

[![License](https://img.shields.io/github/license/geniusworks/media-archive-maker?style=for-the-badge&label=License&labelColor=444444&color=007ec6)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/github/v/release/geniusworks/media-archive-maker?style=for-the-badge&label=Version&labelColor=444444&color=ED7B00)](CHANGELOG.md)
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

**Digital Archive Maker** transforms your physical media collection into a organized digital library. 

**The Problem:** Your CDs, DVDs, and Blu-rays sit on shelves, collecting dust. They're difficult to browse, can't be searched, and only work when you have the physical disc and player. Your favorite music and movies are trapped in plastic boxes.

**The Solution:** Digital Archive Maker liberates your media by:
- **Extracting** perfect digital copies from physical discs
- **Organizing** everything with proper names, metadata, and artwork  
- **Tagging** each item with rich details from online databases
- **Structuring** files in a way that media servers understand
- **Syncing** your entire library to devices you actually use

**What it does:**
- 🎵 **Digitizes CDs** — Creates lossless FLAC files with complete album info and cover art
- 📀 **Preserves DVDs & Blu-rays** — Extracts movies with correct audio tracks and subtitles
- 🏷️ **Enriches metadata** — Adds artist bios, movie descriptions, genre tags, and ratings
- �️ **Organizes everything** — Creates a browsable, searchable library structure
- 📱 **Integrates with media servers** — Works seamlessly with Jellyfin, Plex, and Emby

The result: Your entire media collection becomes instantly accessible from any device, searchable by any criteria, and safely backed up on your own hardware—no subscriptions required.

---

## Getting Started

**Step 1: Clone and install**
```bash
git clone https://github.com/geniusworks/digital-archive-maker.git
cd digital-archive-maker
make install-deps        # creates venv, auto-configures pip, installs everything
source venv/bin/activate  # activate the virtual environment
```

*The `make install-deps` command now handles PEP 668 compatibility automatically by configuring the virtual environment.*

*If you prefer not to use `make`, create the venv manually:*
```bash
python3 -m venv venv
echo "break-system-packages = true" > venv/pip.conf  # Configure for modern Python
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

**Step 2: Configure** (interactive wizard)
```bash
dam config                # sets library path, walks you through API keys
```

Or manually:
```bash
cp .env.sample .env
# Edit .env with your paths and optional API keys
```

**Step 3: Check your setup**
```bash
dam check                 # verifies tools, Python packages, and API keys
dam check --install       # auto-installs missing Homebrew dependencies
```

**Step 4: Rip a CD**
```bash
dam rip cd
```

**Step 5: Rip a DVD/Blu-ray**
```bash
dam rip video
```

**Step 6: Sync to your media server**
```bash
dam sync
```

**GUI Option:** For a graphical interface, launch the desktop app:
```bash
cd gui && npm start
```

## Verify Installation

Optional: Run the test suite to confirm everything works:
```bash
make test  # Runs all 81 tests
```

See [Contributing](CONTRIBUTING.md#running-tests) for more testing options.

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
# Setup & configuration
dam check                # Verify all dependencies and API keys
dam check --install      # Auto-install missing Homebrew packages
dam config               # Interactive first-run wizard (library path, API keys)

# Rip media
dam rip cd               # Rip audio CD to FLAC
dam rip video             # Rip DVD/Blu-ray to MP4
dam rip video --title "Movie" --year 2024   # With metadata

# Tag and organize
dam tag explicit /path/to/music    # Tag explicit content
dam tag genres /path/to/music      # Add genre tags
dam tag lyrics /path/to/music      # Download lyrics
dam tag movie /path/to/movies      # Add movie metadata

# Sync library
dam sync                 # Sync to media server
dam sync --dry-run       # Preview without changes
```

The `dam` CLI wraps the underlying scripts and handles dependency checks and API key
onboarding automatically. You can still use `make` targets and individual scripts directly —
see [Documentation](docs/) for details.

---

## What You Need

**Just a Mac** — This runs on any Mac with macOS. You'll need Homebrew (free package manager) installed.

Run `dam check --install` and the tool will install everything it can automatically. For the rest:

- **MakeMKV** — Required for ripping DVDs/Blu-rays. Download from [makemkv.com](https://www.makemkv.com/).
- **API keys** — Optional but recommended. Run `dam config` and you'll be walked through each one:

| Service | Why | How to get it |
|---------|-----|---------------|
| Spotify | More accurate explicit content detection | Free at developer.spotify.com |
| TMDb | Better movie/TV descriptions | Free at themoviedb.org |
| Genius | Song lyrics when available | Free at genius.com/developers |

API keys are requested only when you use a feature that needs them — you're never blocked upfront.

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
media-archive-maker/
├── dam/                # Shared library & unified CLI
│   ├── cli.py          #   `dam` command entry point
│   ├── config.py       #   Centralised configuration loader
│   ├── deps.py         #   Dependency checker & installer
│   ├── keys.py         #   Interactive API key onboarding
│   └── console.py      #   Rich terminal output helpers
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
└── Makefile            # Make targets (also usable directly)
```

---

## Common Issues

**"abcde not found" / "HandBrakeCLI not found"**
```bash
dam check --install      # auto-installs all Homebrew dependencies
```

**"MakeMKV not found"**
Download from [makemkv.com](https://www.makemkv.com/) and install the app, then run `dam check`.

**"No disc found"**
Make sure the disc is inserted. If using an external drive, give it a moment to mount.

**"API errors"**
Run `dam config` to re-enter your API keys, or check `.env` directly.

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
