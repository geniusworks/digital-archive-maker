# Quick Start Guide

Get from zero to ripping your first CD in under 10 minutes.

---

## Prerequisites

**macOS** with [Homebrew](https://brew.sh/) installed.

## 1. Clone & Install Dependencies

```bash
git clone https://github.com/yourusername/digital-library.git
cd digital-library

# Install system dependencies
make install-deps

# Install Python dependencies
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
cp .env.sample .env
```

Edit `.env` with your paths:

```bash
# Required: Where your media library lives
LIBRARY_ROOT="/Volumes/Data/Media/Library"
RIPS_ROOT="/Volumes/Data/Media/Rips"

# Optional: API keys for enhanced metadata
MUSICBRAINZ_USER_AGENT="YourApp/1.0 (your@email.com)"
TMDB_API_KEY="your_tmdb_key"
SPOTIFY_CLIENT_ID="your_spotify_client_id"
SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
```

## 3. Rip Your First CD

Insert a CD, then:

```bash
make rip-cd
```

This will:
1. Detect the disc and look up metadata on MusicBrainz
2. Rip to FLAC with proper tags
3. Fetch cover art
4. Organize into your library

## 4. Rip Your First DVD/Blu-ray

```bash
make rip-video
```

Follow the prompts to select title and configure encoding.

---

## What's Next?

- **[Full Documentation](docs/)** — Detailed guides for each workflow
- **[Music Collection Guide](docs/music_collection_guide.md)** — Complete CD pipeline
- **[Video Disc Guide](docs/video_disc_guide.md)** — DVD/Blu-ray workflow
- **[README](README.md)** — Full feature overview

---

## Troubleshooting

### "Command not found: abcde"
```bash
brew install abcde
```

### "MakeMKV not found"
Download from [makemkv.com](https://www.makemkv.com/) and install.

### "No disc found"
Ensure your disc is inserted and mounted. External drives may need a moment.

### API errors
Check that your `.env` file has valid API keys and that you haven't exceeded rate limits.
