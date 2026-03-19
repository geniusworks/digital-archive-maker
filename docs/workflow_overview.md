# Physical Media → Digital Archive workflow

Digital Archive Maker provides a simple command-line tool (`dam`) for two main workflows:

- **🎵 Audio CDs → FLAC library → tagging → sync to media server (optional)**
- **🎬 Movie discs → MP4 library → subtitles/organization → sync to media server (optional)**

Each step uses the simple `dam` command.

---

## 🏛️ Archive Locally, Share Selectively

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

## Workflow A: CDs → FLACs → sync

```mermaid
flowchart LR
    A[🎵 Audio CD] --> B[dam rip cd]
    B --> C[FLAC + Metadata]
    C --> D[dam sync]
    D --> E[🖥️ Media Server]
```

### A1) Rip CD to digital library
- **Command**: `dam rip cd`
- **What it does**: 
  - Rips audio CD to high-quality FLAC files
  - Automatically fetches album art and metadata from MusicBrainz
  - Creates playlist and organizes files by artist/album
- **Output**: `${LIBRARY_ROOT}/CDs/Artist/Album/NN - Title.flac`

### A2) Sync to media server (optional)
- **Command**: `dam sync`
- **What it does**: 
  - Syncs your music library to Jellyfin/Plex
  - Applies rating and explicit content filters (if set in config)
  - Maintains perfect organization on your media server

**Setup required**: Run `dam config` first to set up your library path and API keys

---

## Workflow B: Movie discs → MP4s → sync

```mermaid
flowchart LR
    A[📀 Movie disc] --> B[dam rip video]
    B --> C[MP4 + Subtitles + Metadata]
    C --> D[dam sync]
    D --> E[🖥️ Media Server]
```

### B1) Rip movie disc to digital library
- **Command**: `dam rip video`
- **What it does**:
  - Scans disc and shows interactive subtitle options
  - Rips DVD/Blu-ray to high-quality MP4 files
  - Automatically fetches movie metadata and ratings from TMDb
  - Handles both MakeMKV and HandBrake as needed
- **Output**: Organized MP4 files with optional subtitles and rich metadata

### B2) Sync to media server (optional)
- **Command**: `dam sync`
- **What it does**:
  - Syncs your movie library to Jellyfin/Plex
  - Applies rating and explicit content filters (if set in config)
  - Maintains perfect server-ready organization

**Setup required**: Run `dam config` first to set up your library path and API keys

---

## 📚 Additional Tools

For advanced users and special cases, see **`docs/additional_tools.md`** for:
- Manual organization scripts
- Enhanced metadata tools
- TV show processing utilities
- Custom sync options

These scripts provide additional functionality beyond the core `dam` workflows.

