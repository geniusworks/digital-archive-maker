# Quick Start Guide

Get from zero to ripping your first CD in under 10 minutes.

---

## Prerequisites

**macOS** with [Homebrew](https://brew.sh/) installed.

## 1. Clone & Install Dependencies

```bash
git clone https://github.com/geniusworks/digital-library.git
cd digital-library

# Install system dependencies (audio/CD tools)
make install-deps

# Install video ripping dependencies (DVD/Blu-ray support)
make install-video-deps

# Note: MakeMKV requires manual installation from https://www.makemkv.com/download/
# After installing MakeMKV, run 'make install-video-deps' again to link makemkvcon

# Activate virtual environment for Python scripts
source venv/bin/activate
```

## 2. Configure Environment

```bash
cp .env.sample .env
```

Edit `.env` with your paths and preferences:

```bash
# Required paths
MOVIES_ROOT="/path/to/your/movies"
TV_ROOT="/path/to/your/tv"
MUSIC_ROOT="/path/to/your/music"

# Optional: Language preferences for video ripping
# Use 2-letter ISO 639-1 codes (e.g., "en", "fr", "es", "de", "ja")
LANG_AUDIO=en          # Preferred audio track language
LANG_SUBTITLES=en      # Preferred subtitle track language
```

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

### MakeMKV Configuration (Important for Subtitles)
The `rip_video.py` script will automatically configure MakeMKV to extract all subtitles (including Blu-ray PGS subtitles) by adding this to `~/.MakeMKV/settings.conf`:
```
app_DefaultSelectionString="+sel:all,-sel:(core)"
```
This ensures both DVD and Blu-ray rips contain the necessary subtitle streams.

## 3. Rip Your First CD

Insert a CD, then:

```bash
make rip-cd
```

## 4. (Optional) Add Convenience Aliases

For seamless media management, add this function to your `~/.zshrc`:

```bash
media() {
    local VENV_PATH="$HOME/venvs/media"
    local REPO_PATH="$HOME/Herd/digital-library"
    
    case "${1:-help}" in
        "sync"|"master-sync")
            source "$VENV_PATH/bin/activate"
            python3 "$REPO_PATH/bin/sync/master-sync.py"
            ;;
        "bluray")
            shift
            "$REPO_PATH/bin/video/bluray_to_mp4.zsh" "$@"
            ;;
        "repair")
            shift
            "$REPO_PATH/bin/video/repair_mp4.sh" "$@"
            ;;
        "lyrics")
            shift
            source "$VENV_PATH/bin/activate"
            python3 "$REPO_PATH/bin/music/download_lyrics.py" "$@"
            ;;
        "help"|*)
            echo "Media Management Commands:"
            echo "  media sync          - Run master sync"
            echo "  media bluray <args> - Run Blu-ray rip"
            echo "  media repair <file> - Repair MP4 file"
            echo "  media lyrics <path> - Download lyrics for music (smart processing)"
            echo "  media help          - Show this help"
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

# Rip a Blu-ray with custom output
media bluray "Movie Title" 2024 "/path/to/output"

# Repair an MP4 file
media repair "movie.mp4"

# Download lyrics for music library (smart processing)
media lyrics "/path/to/music" --recursive

# Clear all failed lookups (retry everything)
media lyrics "/path/to/music" --recursive --clear-failed
```

This will:
1. Detect the disc and look up metadata on MusicBrainz
2. Rip to FLAC with proper tags
3. Fetch cover art
4. Organize into your library

## 5. Rip Your First DVD/Blu-ray

```bash
make rip-video
```

Follow the prompts to select title and configure encoding.

---

## What's Next?

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
