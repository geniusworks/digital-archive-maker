# Server Guide

Complete guide to setting up and configuring media servers (Plex, Jellyfin, Emby) with your Digital Archive Maker library.

> **Prerequisites:** Follow the [Quick Start Guide](../QUICKSTART.md) for initial setup.  
> **Before running Python scripts:** Activate virtual environment with `source venv/bin/activate`

---

## 🎯 Quick Start

```bash
# Sync library to media server
dam sync

# Preview sync without changes
dam sync --dry-run

# Check server compatibility
dam check
```

---

## 🏗️ Library Structure

### **Root Organization**
```
${LIBRARY_ROOT}/
├── CDs/                    # Audio CD rips
├── Music/                  # Digital music files
├── Movies/                 # Movie files
├── Shows/                  # TV show episodes
├── DVDs/                   # DVD disc backups
├── Blurays/                # Blu-ray disc backups
└── Backups/                # Sync destinations
```

### **Media Server Libraries**
- **Music Library**: `${LIBRARY_ROOT}/CDs` and `${LIBRARY_ROOT}/Music`
- **Movies Library**: `${LIBRARY_ROOT}/Movies`
- **TV Shows Library**: `${LIBRARY_ROOT}/Shows`
- **Other Media**: `${LIBRARY_ROOT}/DVDs`, `${LIBRARY_ROOT}/Blurays`

---

## 🎵 Music Library Setup

### **Folder Structure**
```
${LIBRARY_ROOT}/CDs/
└── Artist Name/
    └── Album Name/
        ├── 01 - Track Title.flac
        ├── 02 - Track Title.flac
        ├── 01 - Track Title.lrc
        ├── cover.jpg
        └── folder.jpg

${LIBRARY_ROOT}/Music/
└── Artist Name/
    └── Album Name/
        ├── 01 - Track Title.mp3
        ├── 01 - Track Title.lrc
        └── cover.jpg
```

### **Server Configuration**

#### **Jellyfin**
```bash
# Library Type: Music
# Folders: ${LIBRARY_ROOT}/CDs, ${LIBRARY_ROOT}/Music
# Metadata: None (uses embedded tags)
# Lyrics: Enabled (reads .lrc files)
```

#### **Plex**
```bash
# Library Type: Music
# Agent: Plex Music
# Folders: ${LIBRARY_ROOT}/CDs, ${LIBRARY_ROOT}/Music
# Lyrics: Enabled
```

#### **Emby**
```bash
# Library Type: Music
# Folders: ${LIBRARY_ROOT}/CDs, ${LIBRARY_ROOT}/Music
# Metadata: Embedded tags
# Lyrics: Enabled
```

---

## 🎬 Movies Library Setup

### **Folder Structure**
```
${LIBRARY_ROOT}/Movies/
└── Movie Title (Year)/
    ├── Movie Title (Year).mp4
    ├── Movie Title (Year).srt
    ├── Movie Title (Year).nfo
    └── poster.jpg
```

### **Server Configuration**

#### **Jellyfin**
```bash
# Library Type: Movies
# Folder: ${LIBRARY_ROOT}/Movies
# Metadata: None (uses .nfo files)
# Subtitles: Enabled (reads .srt files)
```

#### **Plex**
```bash
# Library Type: Movies
# Agent: The Movie Database
# Folder: ${LIBRARY_ROOT}/Movies
# Subtitles: Enabled
```

#### **Emby**
```bash
# Library Type: Movies
# Folder: ${LIBRARY_ROOT}/Movies
# Metadata: Embedded + .nfo files
# Subtitles: Enabled
```

---

## 📺 TV Shows Library Setup

### **Folder Structure**
```
${LIBRARY_ROOT}/Shows/
└── Show Name (Year)/
    └── Season 1/
        ├── Show Name (Year) - S01E01.mp4
        ├── Show Name (Year) - S01E01.srt
        ├── Show Name (Year) - S01E02.mp4
        └── Show Name (Year) - S01E02.srt
```

### **Server Configuration**

#### **Jellyfin**
```bash
# Library Type: TV Shows
# Folder: ${LIBRARY_ROOT}/Shows
# Metadata: None (uses embedded metadata)
# Subtitles: Enabled
```

#### **Plex**
```bash
# Library Type: TV Shows
# Agent: TheTVDB
# Folder: ${LIBRARY_ROOT}/Shows
# Subtitles: Enabled
```

#### **Emby**
```bash
# Library Type: TV Shows
# Folder: ${LIBRARY_ROOT}/Shows
# Metadata: Embedded
# Subtitles: Enabled
```

---

## 🔄 Sync Configuration

### **Environment Variables (.env)**
```bash
# Sync destinations
SYNC_DESTINATIONS="/path/to/server1,/path/to/server2"

# Content filtering
EXPLICIT_CONTENT_FILTER=true    # Skip explicit content
FAMILY_FRIENDLY_ONLY=false      # Include all content

# Sync options
SYNC_DELETE=false               # Don't delete from destination
SYNC_COPY=true                  # Copy instead of move
SYNC_COMPRESS=false             # Don't compress during sync
```

### **Sync Commands**
```bash
# Full sync
dam sync

# Dry run (preview)
dam sync --dry-run

# Quiet sync
dam sync --quiet

# Specific destinations
dam sync --destinations "/path/to/server"

# Content filtering
dam sync --family-friendly
dam sync --include-explicit
```

---

## 🛠️ Server Setup Guides

### **Jellyfin Setup**

#### **Installation**
```bash
# macOS
brew install jellyfin

# Start service
brew services start jellyfin

# Access web interface
open http://localhost:8096
```

#### **Library Configuration**
1. **Add Libraries**: Dashboard → Libraries → + Add Library
2. **Music**: Type "Music", folders `${LIBRARY_ROOT}/CDs` and `${LIBRARY_ROOT}/Music`
3. **Movies**: Type "Movies", folder `${LIBRARY_ROOT}/Movies`
4. **TV Shows**: Type "TV Shows", folder `${LIBRARY_ROOT}/Shows`
5. **Metadata**: Set to "None" (uses embedded tags and .nfo files)
6. **Subtitles**: Enable subtitle support

#### **Advanced Settings**
```bash
# Enable lyrics display
Dashboard → Playback → Enable lyric display

# Subtitle preferences
Dashboard → Playback → Subtitle settings

# Transcoding settings
Dashboard → Playback → Transcoding
```

### **Plex Setup**

#### **Installation**
```bash
# macOS
brew install --cask plex-media-server

# Start service
brew services start plex-media-server

# Access web interface
open http://localhost:32400/web
```

#### **Library Configuration**
1. **Add Libraries**: Settings → Manage → Libraries → Add Library
2. **Music**: Type "Music", agent "Plex Music", folders `${LIBRARY_ROOT}/CDs` and `${LIBRARY_ROOT}/Music`
3. **Movies**: Type "Movies", agent "The Movie Database", folder `${LIBRARY_ROOT}/Movies`
4. **TV Shows**: Type "TV Shows", agent "TheTVDB", folder `${LIBRARY_ROOT}/Shows`
5. **Advanced**: Enable subtitles, lyrics, and metadata extraction

#### **Advanced Settings**
```bash
# Settings → Server → Library
# Enable: "Generate video thumbnail thumbs"
# Enable: "Generate intro video markers"
# Enable: "Generate BIF thumbs"

# Settings → Server → Transcoder
# Set: "Allow hardware encoding"
# Set: "Transcoder quality"
```

### **Emby Setup**

#### **Installation**
```bash
# macOS
brew install emby-server

# Start service
brew services start emby-server

# Access web interface
open http://localhost:8096
```

#### **Library Configuration**
1. **Add Libraries**: Dashboard → Media Library + Add Media Library
2. **Music**: Type "Music", folders `${LIBRARY_ROOT}/CDs` and `${LIBRARY_ROOT}/Music`
3. **Movies**: Type "Movies", folder `${LIBRARY_ROOT}/Movies`
4. **TV Shows**: Type "TV Shows", folder `${LIBRARY_ROOT}/Shows`
5. **Metadata**: Enable embedded metadata and .nfo files

---

## 🔧 Advanced Configuration

### **Content Filtering**

#### **Explicit Content Filtering**
```bash
# Tag explicit content
dam tag explicit /path/to/music

# Sync with filtering
dam sync --family-friendly

# Check explicit tags
ffprobe -v error -show_entries format_tags=explicit file.mp3
```

#### **Family-Friendly Sync**
```bash
# Environment variable
EXPLICIT_CONTENT_FILTER=true

# Command line
dam sync --family-friendly

# Preview filtered content
dam sync --dry-run --family-friendly
```

### **Performance Optimization**

#### **Transcoding Settings**
```bash
# Jellyfin
Dashboard → Playback → Transcoding
- Enable hardware acceleration
- Set quality presets
- Configure codec preferences

# Plex
Settings → Server → Transcoder
- Enable hardware encoding
- Set transcoder quality
- Configure throttle settings

# Emby
Dashboard → Transcoding
- Enable hardware acceleration
- Set quality profiles
- Configure bandwidth limits
```

#### **Storage Optimization**
```bash
# Network storage
# Use NFS/SMB for media libraries
# Configure appropriate mount options

# Local storage
# Use SSD for frequently accessed content
# Use HDD for archive storage

# Backup storage
# Configure RAID for redundancy
# Use off-site backup for critical content
```

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **Library Not Scanning**
```bash
# Check file permissions
ls -la ${LIBRARY_ROOT}/

# Check server logs
# Jellyfin: /var/log/jellyfin/
# Plex: /Library/Application Support/Plex Media Server/Logs/
# Emby: /var/log/emby/

# Test file access
curl -I http://localhost:8096/web/index.html
```

#### **Metadata Not Loading**
```bash
# Check file metadata
ffprobe -v quiet -print_format json -show_format file.mp4
metaflac --list file.flac

# Verify .nfo files
cat "${LIBRARY_ROOT}/Movies/Movie Title (Year)/Movie Title (Year).nfo"

# Check folder structure
find ${LIBRARY_ROOT}/Movies -type f -name "*.nfo" | head -5
```

#### **Subtitle Issues**
```bash
# Check subtitle files
ls -la "${LIBRARY_ROOT}/Movies/Movie Title (Year)/"*.srt
file "${LIBRARY_ROOT}/Movies/Movie Title (Year)/"*.srt

# Test subtitle content
head -5 "${LIBRARY_ROOT}/Movies/Movie Title (Year)/"*.srt

# Verify encoding
file -bi "${LIBRARY_ROOT}/Movies/Movie Title (Year)/"*.srt
```

#### **Sync Problems**
```bash
# Check sync configuration
dam check

# Test sync dry run
dam sync --dry-run --verbose

# Check destination permissions
ls -la /path/to/destination/

# Verify network connectivity
ping server-address
ssh server-address "ls /path/to/media"
```

### **Performance Issues**

#### **Slow Scanning**
```bash
# Check disk I/O
iostat -w 1

# Check network bandwidth
iftop -i en0

# Optimize library size
find ${LIBRARY_ROOT} -name "*.tmp" -delete
find ${LIBRARY_ROOT} -name "*.log" -delete
```

#### **Transcoding Issues**
```bash
# Check hardware acceleration
ffmpeg -hwaccels

# Test transcoding
ffmpeg -i input.mp4 -c:v libx264 -preset fast output.mp4

# Monitor system resources
top -o cpu
top -o mem
```

---

## 📚 Examples

### **Complete Setup**
```bash
# 1. Process media
make rip-cd
make process-cds
dam rip video --title "Movie" --year 2023
dam rip video --title "Show" --year 2023 --episodes

# 2. Tag and organize
dam tag explicit ${LIBRARY_ROOT}/Music
dam fix-covers ${LIBRARY_ROOT}/Music
dam tag lyrics ${LIBRARY_ROOT}/Music

# 3. Sync to server
dam sync --dry-run
dam sync
```

### **Server Migration**
```bash
# Export library configuration
# Jellyfin: Dashboard → Plugins → Backup
# Plex: Settings → Server → Backup
# Emby: Dashboard → Advanced → Backup

# Sync to new location
SYNC_DESTINATIONS="/new/server/path" dam sync

# Update server library paths
# Reconfigure libraries with new paths
```

### **Content Filtering**
```bash
# Tag explicit content
dam tag explicit ${LIBRARY_ROOT}/Music

# Create family-friendly sync
EXPLICIT_CONTENT_FILTER=true dam sync --destinations "/family/server"

# Create full-content sync
dam sync --destinations "/adult/server"
```

---

## 📖 Related Guides

- **[Video Guide](video_guide.md)** - Movie and TV show processing
- **[Music Guide](music_guide.md)** - Audio CD and file processing
- **[Workflow Guide](workflow_guide.md)** - High-level overview
- **[Quick Start](../QUICKSTART.md)** - Initial setup

---

## 🤝 Contributing

Found an issue with server setup? Please:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create an issue with server type and configuration details

---

**Happy media serving!** 🖥️✨
