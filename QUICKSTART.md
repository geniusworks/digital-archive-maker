# Digital Archive Maker - Quick Start Guide

Get from zero to ripping your first CD in under 10 minutes.

---

## Prerequisites

**macOS** with [Homebrew](https://brew.sh/) installed.

## 1. Clone & Install Dependencies

```bash
git clone https://github.com/geniusworks/digital-archive-maker.git
cd digital-archive-maker

# Install system dependencies (audio/CD tools) — this creates the venv
make install-deps

# Install video ripping dependencies (DVD/Blu-ray support)
make install-video-deps

# Note: MakeMKV is optional for DVD ripping - the script will use HandBrake fallback
# For full functionality (including Blu-ray), install MakeMKV from https://www.makemkv.com/download/
# After installing MakeMKV, run 'make install-video-deps' again to link makemkvcon

# Activate the virtual environment (shown in Next steps after install)
source venv/bin/activate
```

*If you prefer not to use `make`, create the venv manually:*
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 2. Configure Environment

**Option A: Interactive wizard** (recommended)
```bash
dam config
```
This walks you through setting your library path and API keys interactively.

**Option B: Manual setup**
```bash
cp .env.sample .env
```

Edit `.env` with your paths and preferences:

```bash
# Required: Where your media library lives
LIBRARY_ROOT="/Volumes/Data/Media/Library"

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
The `rip_video.py` script will automatically configure MakeMKV to extract all subtitles (including Blu-ray PGS subtitles) by adding this to `~/.MakeMKV/settings.conf`:
```
app_DefaultSelectionString="+sel:all,-sel:(core)"
```
This ensures both DVD and Blu-ray rips contain the necessary subtitle streams.

## 3. Rip Your First CD

Insert a CD, then:

```bash
dam rip cd
# or: make rip-cd
```

## 4. (Optional) Add Convenience Aliases

For seamless media management, add this function to your `~/.zshrc`:

```bash
media() {
    local VENV_PATH="$HOME/venvs/digital-archive"
    local REPO_PATH="${LIBRARY_ROOT:-$HOME/digital-archive-maker}"
    
    case "${1:-help}" in
        "sync")
            source "$VENV_PATH/bin/activate"
            dam sync
            ;;
        "cd")
            source "$VENV_PATH/bin/activate"
            dam rip cd
            ;;
        "video")
            source "$VENV_PATH/bin/activate"
            dam rip video
            ;;
        "lyrics")
            shift
            source "$VENV_PATH/bin/activate"
            python3 "$REPO_PATH/bin/music/download_lyrics.py" "$@"
            ;;
        "help"|*)
            echo "Media Management Commands:"
            echo "  media sync    - Sync media library"
            echo "  media cd     - Rip a CD"
            echo "  media video  - Rip DVD/Blu-ray"
            echo "  media lyrics - Download lyrics for music"
            echo "  media help   - Show this help"
            ;;
    esac
}
```

Then reload your shell:

```bash
source ~/.zshrc
```

Now you can use simple commands:

```bash
# Sync your media library
media sync

# Rip a CD
media cd

# Rip a DVD/Blu-ray
media video

# Download lyrics for music library
media lyrics "/path/to/music" --recursive
```

This will:
1. Detect the disc and look up metadata on MusicBrainz
2. Rip to FLAC with proper tags
3. Fetch cover art
4. Organize into your library

## 5. Rip Your First DVD/Blu-ray

```bash
dam rip video
# or: make rip-video
```

Follow the prompts to select title and configure encoding.

## 6. (Optional) Run Tests

Verify your installation with the test suite:
```bash
make test  # Should show "All tests passed!"
```

See [Contributing](CONTRIBUTING.md#running-tests) for detailed testing options.

---

## What's Next?

- **`dam --help`** — See all available commands
- **[GUI Desktop App](gui/README.md)** — Graphical interface for all workflows
- **[Full Documentation](docs/)** — Detailed guides for each workflow
- **[Music Collection Guide](docs/music_collection_guide.md)** — Complete CD pipeline
- **[Video Ripping Guide](docs/video_ripping_guide.md)** — DVD/Blu-ray workflow
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
