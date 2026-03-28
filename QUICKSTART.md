# Digital Archive Maker - Quick Start Guide

Get from zero to ripping your first disc in under 10 minutes.

---

## Prerequisites

**macOS** with [Homebrew](https://brew.sh/) installed.

## 1. Clone & Install Dependencies

```bash
git clone https://github.com/geniusworks/digital-archive-maker.git
cd digital-archive-maker

# Install system dependencies (audio/CD tools) — this creates the venv
make install-deps

# Install video ripping dependencies (movie disc support)
make install-video-deps

# Note: MakeMKV is not required for DVD ripping - the script will use HandBrake fallback
# For full functionality, install MakeMKV from https://www.makemkv.com/download/
# After installing MakeMKV, run 'make install-video-deps' again to link makemkvcon

# Activate the virtual environment (shown in Next steps after install)
source venv/bin/activate
```


## 2. Configure Environment

**Option A: Interactive wizard** (recommended)
```bash
dam config
```
This walks you through setting your library path and API keys interactively.

**Option B: Manual setup**
```bash
cp .env.example .env
```

Edit `.env` with your paths and preferences:

```bash
# Required: Where your media library lives
LIBRARY_ROOT="/path/to/your/media/library"

# Optional: Language preferences for video ripping
# Use 2-letter ISO 639-1 codes (e.g., "en", "fr", "es", "de", "ja")
LANG_AUDIO=en          # Preferred audio track language
LANG_SUBTITLES=en      # Preferred subtitle track language

# Optional: API keys for enhanced metadata (add these as you need them)
TMDB_API_KEY="your_tmdb_key"
SPOTIFY_CLIENT_ID="your_spotify_client_id"
SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
GENIUS_API_TOKEN="your_genius_token"
```

### Verify your setup
```bash
dam check                 # shows status of all tools, packages, and API keys
```

### MakeMKV Configuration (Important for Subtitles)
The `rip_video.py` script will automatically configure MakeMKV to extract all subtitles by adding this to `~/.MakeMKV/settings.conf`:
```
app_DefaultSelectionString="+sel:all,-sel:(core)"
```
This ensures movie disc rips contain the necessary subtitle streams.

## 3. Rip Your First CD

Insert a CD, then:

```bash
dam rip cd
```

## 4. Rip Your First Movie Disc

```bash
dam rip video
```

Follow the prompts to select title and configure encoding.

## 5. Rip TV Show Episodes

```bash
dam rip video --title "Show Name" --year 2024 --episodes
```

Or use the Makefile shortcut:
```bash
make rip-episodes TITLE="Show Name" YEAR=2024
```

This automatically detects and rips all episode tracks from TV show discs.

---

## What's Next?

- **`dam --help`** — See all available commands
- **[GUI Desktop App](gui/README.md)** — Graphical interface for all workflows
- **[Full Documentation](docs/)** — Detailed guides for each workflow
- **[Music Guide](docs/music_guide.md)** — Complete CD pipeline
- **[Video Guide](docs/video_guide.md)** — Movie and TV show workflows
- **[Server Guide](docs/server_guide.md)** — Media server configuration
- **[README](README.md)** — Full feature overview
