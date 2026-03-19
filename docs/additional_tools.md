# Additional Scripts and Optional Tools

This document covers scripts that provide additional functionality beyond the core `dam` workflow. These are optional tools for specific use cases or advanced users.

## 🎵 Music Scripts

### Album Organization
- **`bin/music/fix_album.py`** - Normalize existing album folders
  - Renames tracks to `NN - Title.flac` format
  - Rebuilds playlist files
  - Fixes tags and cover art
  - Use when you have existing albums that need standardization

### Lyrics Enhancement
- **`bin/music/download_lyrics.py`** - Download lyrics for music files
  - Fetches lyrics from Genius API (requires API key)
  - Falls back to free sources if no key configured
  - Alternative to `dam tag lyrics` for direct script usage

### Content Filtering
- **`bin/music/tag-explicit-mb.py`** - Tag explicit content in music files
  - Uses MusicBrainz and Spotify APIs for content identification
  - Writes `EXPLICIT=Yes|No|Unknown` tags per track
  - Alternative to `dam tag explicit` for direct script usage

## 🎬 Video Scripts

### Movie Metadata
- **`bin/video/tag-movie-metadata.py`** - Add rich movie metadata
  - Fetches plot, genres, cast, artwork from TMDb/OMDb
  - Alternative to `dam tag metadata` for direct script usage
  - Use when you need detailed movie information

### Movie Ratings
- **`bin/video/tag-movie-ratings.py`** - Add MPAA ratings to movies
  - Fetches rating tags (`©rat`) via TMDb/OMDb
  - Includes overrides and caching for consistency
  - Alternative to `dam tag ratings` for direct script usage

## 📺 TV Show Scripts

### Show Organization
- **`bin/tv/rename_shows_jellyfin.py`** - Organize TV shows for Jellyfin
  - Normalizes filenames to Jellyfin conventions
  - Output: `.../TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.ext`
  - Handles various input formats automatically

### Show Metadata
- **`bin/tv/tag-show-metadata.py`** - Add TV show metadata
  - Fetches show metadata from TMDb
  - Adds proper series/season/episode information
  - Use for comprehensive TV show libraries

## 🔄 Sync Scripts

### Library Sync
- **`bin/sync/sync-library.py`** - Sync library to media servers
  - Alternative to `dam sync` for direct script usage
  - Supports filtering options (explicit, unknown ratings)
  - Use when you need custom sync configurations

## 📝 When to Use These Scripts

### Use the `dam` commands for:
- **Standard workflows** - ripping, tagging, syncing
- **Automated processing** - uses your configured API keys
- **Simple operations** - one-command workflows

### Use these scripts for:
- **Manual control** - when you want to override defaults
- **Specific fixes** - repairing existing disorganized libraries
- **Advanced features** - functionality beyond core workflows
- **Direct access** - when you prefer script usage over CLI

## 🔧 Configuration

Most scripts respect the same environment variables as the `dam` commands:
- `LIBRARY_ROOT` - Your media library path
- API keys for MusicBrainz, Spotify, TMDb, etc.
- Configure once with `dam config` and both `dam` commands and scripts will work

---

**Note**: For most users, the `dam` commands provide all the functionality needed for a complete digital archive workflow. These scripts are available for power users and special cases.
