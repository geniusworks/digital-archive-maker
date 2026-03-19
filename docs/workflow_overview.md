# Workflow Overview (Physical Media → Digital Archive)

Digital Archive Maker provides a simple command-line tool (`dam`) for two main workflows:

- **🎵 Audio CDs → FLAC library → tagging → sync to media server (optional)**
- **🎬 Movie discs → MP4 library → subtitles/organization → sync to media server (optional)**

Each step uses the simple `dam` command.

---

## 🏛️ Two-Stage Approach: Archive Locally, Share Selectively

### Stage 1: Your Perfect Local Archive
Your **LIBRARY_ROOT** becomes your complete digital collection:
- **Everything preserved**: No content filtering - keep all your media in high quality
- **Rich metadata**: Automatic tagging from MusicBrainz, TMDb, Spotify, and more
- **Perfect organization**: Files organized by artist, album, movie, TV show
- **Your master copy**: The single source of truth for your entire collection

### Stage 2: Filtered Server Sync
**`dam sync`** prepares content for your media server:
- **Smart filtering**: Skip explicit content, unknown ratings, or files you choose
- **Family-friendly options**: Different rules for different audiences
- **Multiple destinations**: Sync to Jellyfin, Plex, or backup drives
- **Your choice**: What gets shared is up to you

### How It Works
```
Physical Media → [RIP + TAG] → Your Complete Library
                                   ↓
                               [SYNC + FILTERS]
                                   ↓
                            Media Server (selective)
```

**Result**: Keep everything perfect locally, share only what you want with your media server.

---

## System Overview

```mermaid
flowchart TB
    subgraph INPUT["📀 Physical Media"]
        CD[Audio CD]
        DVD[DVD]
        BR[Blu-ray]
    end

    subgraph PROCESS["⚙️ Processing"]
        RIP[Rip & Encode]
        TAG[Tag Metadata]
        ORG[Organize Files]
        QA[Quality Check]
    end

    subgraph METADATA["🏷️ Metadata Sources"]
        MB[MusicBrainz]
        TMDB[TMDb]
        OMDB[OMDb]
        SPOT[Spotify]
        ITUNES[iTunes]
    end

    subgraph OUTPUT["📁 Local Library"]
        MUSIC["/Library/CDs"]
        MOVIES["/Library/Movies"]
        SHOWS["/Library/Shows"]
        VIDEOS["/Library/Videos"]
    end

    subgraph SERVER["🖥️ Media Server"]
        JELLY[Jellyfin/Plex]
    end

    CD --> RIP
    DVD --> RIP
    BR --> RIP

    RIP --> TAG
    TAG --> ORG
    ORG --> QA

    MB -.-> TAG
    TMDB -.-> TAG
    OMDB -.-> TAG
    SPOT -.-> TAG
    ITUNES -.-> TAG

    QA --> MUSIC
    QA --> MOVIES
    QA --> SHOWS
    QA --> VIDEOS

    MUSIC -->|rsync + filter| JELLY
    MOVIES -->|rsync + filter| JELLY
    SHOWS -->|rsync + filter| JELLY
    VIDEOS -->|rsync + filter| JELLY
```

---

## Workflow A: CDs → FLACs → tagging → sync

```mermaid
flowchart LR
    A[🎵 Audio CD] --> B[abcde + MusicBrainz]
    B --> C[FLAC + cover.jpg + .m3u8]
    C --> D[Enhance Metadata]
    D --> E[Tag Explicit Content]
    E --> F[Download Lyrics]
    F --> G{Sync?}
    G -->|exclude explicit| H[🖥️ Family Server]
    G -->|all content| I[🖥️ Full Server]
```

### A1) Rip CD to FLAC (MusicBrainz + cover + playlist)
- Guide: `docs/music_collection_guide.md` (Source 1: Audio CDs)
- Commands:
  - `dam rip cd` (unified CLI)
  - `make rip-cd` (Makefile shortcut)

Output (default):
- `${LIBRARY_ROOT}/CDs/Artist/Album/NN - Title.flac`
- `cover.jpg`
- `Album.m3u8`

### A2) Normalize/fix an existing album folder (optional)
- Commands:
  - `dam tag fix-album` (unified CLI)
  - `bin/music/fix_album.py` (direct script)
  - Renames tracks to `NN - Title.flac`
  - Rebuilds playlist
  - Fixes tags and cover art

### A3) Download lyrics (optional)
- Commands:
  - `dam tag lyrics` (unified CLI)
  - `bin/music/download_lyrics.py` (direct script)
- Fetches lyrics from Genius API (falls back to free sources if no key)

### A4) Tag explicit content (optional)
- Commands:
  - `dam tag explicit` (unified CLI)
  - `bin/music/tag-explicit-mb.py` (direct script)
- Writes per-track tag: `EXPLICIT=Yes|No|Unknown`

### A5) Sync to a destination server while excluding explicit/unknown (optional)
- Commands:
  - `dam sync` (unified CLI)
  - `bin/sync/sync-library.py` (direct script)
- Excludes are driven by the `EXPLICIT` tag:
  - `--exclude-explicit` skips `EXPLICIT=Yes`
  - `--exclude-unknown` skips `EXPLICIT=Unknown` and missing tags

---

## Workflow B: Movie discs → MP4s → organize/subtitles → server

```mermaid
flowchart LR
    A[📀 Movie disc] --> B[MakeMKV Scan]
    B --> C[Interactive Prompt]
    C --> D[Rip MKV]
    D --> E[HandBrakeCLI]
    E --> F[MP4 + subtitles]
    F --> G[Tag Metadata]
    G --> H[Tag Ratings]
    H --> I{Rating Filter}
    I -->|≤PG-13| J[🖥️ Family Server]
    I -->|all ratings| K[🖥️ Full Server]
```

### B1) Rip discs to staging (MKV/MP4)
- Guide: `docs/video_ripping_guide.md`
- Commands:
  - `dam rip video` (unified CLI)
  - `make rip-video` (staging)
  - `make rip-movie TITLE="Movie Name" YEAR=1999` (organize main feature)
- Features: Automatic disc scanning, interactive subtitle processing prompt before ripping, automatic compression for large MKVs.
- **MakeMKV is optional for DVDs**: If MakeMKV is not installed, the script will automatically use HandBrake CLI directly for DVD ripping. Blu-ray ripping still requires MakeMKV due to encryption.

### B2) Organize into a server-friendly layout
- Guide: `docs/media_server_setup.md`
- Recommended:
  - Movies: `.../Movies/Movie Name (Year)/Movie Name (Year).mp4`
  - TV: `.../TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.mp4`

### B3) Ensure subtitles are present (optional)
- Video guide covers:
  - English subtitle selection/burn-in policies
  - Backfilling English soft subs into existing MP4s

### B4) Tag movie metadata and ratings (optional)
- Commands:
  - `dam tag metadata` (unified CLI)
  - `dam tag ratings` (unified CLI)
  - `bin/video/tag-movie-metadata.py` — rich metadata (plot/genres/cast/artwork) via TMDb/OMDb
  - `bin/video/tag-movie-ratings.py` — MPAA rating tag (`©rat`) via TMDb/OMDb + overrides/cache

---

## Workflow C: TV Shows → organize → metadata → server

```mermaid
flowchart LR
    A[📺 TV Shows] --> B[rename_shows_jellyfin.py]
    B --> C[Jellyfin Format]
    C --> D[tag-show-metadata.py]
    D --> E[TMDb Metadata]
    E --> F[🖥️ Media Server]
```

### C1) Organize TV shows into Jellyfin-compatible format
- Commands:
  - `bin/tv/rename_shows_jellyfin.py` (direct script)
- Output: `.../TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.ext`
- Handles various input formats and normalizes to Jellyfin naming conventions

### C2) Tag TV show metadata (optional)
- Commands:
  - `bin/tv/tag-show-metadata.py` (direct script)
- Fetches show metadata from TMDb
- Adds proper series/season/episode metadata

