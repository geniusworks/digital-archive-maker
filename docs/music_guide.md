# Music Guide

Complete guide to processing music from CDs, digital files, and loose tracks into an organized, media-server-ready library.

> **Prerequisites:** Follow the [Quick Start Guide](../QUICKSTART.md) for initial setup.  
> **Before running Python scripts:** Activate virtual environment with `source venv/bin/activate`

---

## 🎯 Target Result

**Music Library** with:
- ✅ Complete metadata (artist, album, title, track numbers)
- ✅ Proper folder structure (`Artist/Album/NN - Title.ext`)
- ✅ High-quality audio (FLAC preferred, MP3 supported)
- ✅ Explicit content tagging for family-safe filtering
- ✅ Cover art for all albums
- ✅ **Lyrics files (.lrc) for synchronized display**
- ✅ Consistent naming and organization

---

## 🎵 Quick Start

```bash
# Rip audio CD
dam rip cd
make rip-cd

# Process existing music files
dam tag genres /path/to/music
dam tag explicit /path/to/music
dam tag lyrics /path/to/music

# Fix album covers
dam fix-covers /path/to/music
```

---

## 🌊 Music Sources Pipeline

### 📀 Audio CDs (Physical Media)
**Path:** CD Disc → FLAC → Metadata → Library

#### Step 1: Rip CD to FLAC

**First time only — configure abcde:**
```bash
cp .abcde.conf.example ~/.abcde.conf
```

Verify key settings in `~/.abcde.conf`:
- `OUTPUTDIR="${LIBRARY_ROOT}/CDs"` — uses `LIBRARY_ROOT` from `.env`
- `OUTPUTFORMAT='${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}'`
- `ACTIONS=cddb,getalbumart,encode,tag,move,playlist,clean`
- `EJECTCD=y` — ejects disc when done

**Rip:**
```bash
# Insert CD and run:
make rip-cd
dam rip cd
```

**Output:** `${LIBRARY_ROOT}/CDs/Artist/Album/NN - Title.flac`

> **Notes:** Ensure your drive supports accurate audio extraction. MusicBrainz and Cover Art Archive rate limits apply.

#### Step 2: Fix Missing Metadata
```bash
# Fix missing metadata, covers, and add lyrics
make process-cds
```

### 📁 Digital Files (Existing Collection)
**Path:** Digital Files → Metadata → Organization → Library

#### Supported Formats
- **Audio:** FLAC, MP3, WAV, ALAC, M4A, OGG
- **Metadata:** ID3 tags, Vorbis comments, MP4 tags

#### Processing Workflow
```bash
# Add genre tags
dam tag genres /path/to/music

# Tag explicit content
dam tag explicit /path/to/music

# Download lyrics
dam tag lyrics /path/to/music

# Fix album covers
dam fix-covers /path/to/music
```

---

## 🛠️ Music Processing Tools

### 🎨 Album Cover Fixing
```bash
# Fix missing album covers
dam fix-covers /path/to/music

# Preview changes without writing
dam fix-covers /path/to/music --dry-run

# Process single album
dam fix-covers /path/to/Artist/Album
```

**Features:**
- Searches MusicBrainz and Cover Art Archive
- Downloads high-resolution artwork
- Supports multiple image formats
- Updates embedded cover art and folder.jpg

### 🏷️ Metadata Tagging

#### Explicit Content Tagging
```bash
# Tag explicit content
dam tag explicit /path/to/music

# Preview without changes
dam tag explicit /path/to/music --dry-run

# Check specific directory
dam tag explicit /path/to/Artist/Album
```

**What it does:**
- Analyzes lyrics for explicit content
- Tags files for parental controls
- Works with existing metadata
- Family-safe filtering support

#### Genre Tagging
```bash
# Add genre tags
dam tag genres /path/to/music

# Preview changes
dam tag genres /path/to/music --dry-run
```

**Features:**
- Analyzes audio characteristics
- Matches to appropriate genres
- Updates existing genre tags
- Supports multiple genres

#### Lyrics Download
```bash
# Download synchronized lyrics
dam tag lyrics /path/to/music

# Process single directory (non-recursive)
dam tag lyrics /path/to/music --no-recursive
```

**Sources:**
- Genius API (requires GENIUS_API_TOKEN)
- Multiple lyrics providers
- Synchronized LRC format
- Automatic language detection

---

## 📁 Library Organization

### **Folder Structure**
```
${LIBRARY_ROOT}/
├── CDs/                    # Ripped from physical media
│   ├── Artist Name/
│   │   └── Album Name/
│   │       ├── 01 - Track Title.flac
│   │       ├── 02 - Track Title.flac
│   │       ├── cover.jpg
│   │       └── folder.jpg
└── Music/                  # Existing digital files
    ├── Artist Name/
    │   └── Album Name/
    │       ├── 01 - Track Title.mp3
    │       ├── 01 - Track Title.lrc
    │       └── cover.jpg
```

### **File Naming**
- **Audio:** `NN - Track Title.ext`
- **Lyrics:** `NN - Track Title.lrc`
- **Artwork:** `cover.jpg`, `folder.jpg`
- **Playlists:** `Album Name.m3u`

---

## ⚙️ Configuration

### **Environment Variables (.env)**
```bash
# Required
LIBRARY_ROOT="/path/to/your/media/library"

# Optional API keys (enhanced features)
TMDB_API_KEY="your_tmdb_key"              # Movie metadata
SPOTIFY_CLIENT_ID="your_spotify_client_id"
SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
GENIUS_API_TOKEN="your_genius_token"      # Lyrics download

# Music processing preferences
MUSICBRAINZ_USER="your_username"           # MusicBrainz account
MUSICBRAINZ_PASS="your_password"
```

### **Audio Quality Settings**
```bash
# abcde configuration (~/.abcde.conf)
OUTPUTFORMAT='${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}'
OUTPUTTYPE="flac"                          # FLAC output
CDROMREADERSYNTAX=cdparanoia
CDPARANOIAOPTS="-Z"                       # Error correction
```

---

## 🌟 Advanced Features

### **Batch Processing**
```bash
# Process entire library
make process-cds
dam tag explicit ${LIBRARY_ROOT}/Music
dam tag genres ${LIBRARY_ROOT}/Music
dam tag lyrics ${LIBRARY_ROOT}/Music
dam fix-covers ${LIBRARY_ROOT}/Music
```

### **Selective Processing**
```bash
# Process specific genres
find ${LIBRARY_ROOT}/Music -name "*Rock*" -exec dam tag genres {} \;

# Process specific artists
dam tag explicit ${LIBRARY_ROOT}/Music/"The Beatles"
```

### **Quality Control**
```bash
# Check for missing metadata
find ${LIBRARY_ROOT}/Music -name "*.flac" -exec metaflac --show-tag=TITLE {} \; | grep -c "^$"

# Verify cover art
find ${LIBRARY_ROOT}/Music -name "cover.jpg" | wc -l

# Check lyrics files
find ${LIBRARY_ROOT}/Music -name "*.lrc" | wc -l
```

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **CD Ripping Problems**
```bash
# Check cdparanoia installation
which cdparanoia
cdparanoia -V

# Test abcde configuration
abcde -d /dev/cd2 -1  # Test first track

# Check drive permissions
ls -la /dev/cd*
```

#### **Metadata Issues**
```bash
# Check audio file metadata
metaflac --list file.flac
mp3info file.mp3
ffprobe file.wav

# Test MusicBrainz connection
curl -s "https://musicbrainz.org/ws/2/release/?query=artist:Beatles"
```

#### **Cover Art Problems**
```bash
# Check Cover Art Archive
curl -s "https://coverartarchive.org/release/mbid/front"

# Test image processing
file cover.jpg
identify cover.jpg
```

#### **Lyrics Download Issues**
```bash
# Test Genius API
curl -H "Authorization: Bearer ${GENIUS_API_TOKEN}" \
     "https://api.genius.com/search?q=Beatles"

# Check lyrics files
head -5 song.lrc
```

### **Performance Tips**
- **Parallel processing**: Run multiple tools simultaneously
- **Batch operations**: Process entire library at once
- **SSD storage**: Faster file processing
- **Network storage**: Consider bandwidth for large libraries

---

## 📚 Examples

### **Complete CD Processing**
```bash
# Rip CD
make rip-cd

# Process new rips
make process-cds

# Verify results
ls -la ${LIBRARY_ROOT}/CDs/
```

### **Existing Library Processing**
```bash
# Step 1: Fix covers
dam fix-covers ${LIBRARY_ROOT}/Music

# Step 2: Add genres
dam tag genres ${LIBRARY_ROOT}/Music

# Step 3: Tag explicit content
dam tag explicit ${LIBRARY_ROOT}/Music

# Step 4: Add lyrics
dam tag lyrics ${LIBRARY_ROOT}/Music
```

### **Selective Processing**
```bash
# Process specific genre
find ${LIBRARY_ROOT}/Music -iname "*jazz*" -exec dam tag genres {} \;

# Fix specific album
dam fix-covers ${LIBRARY_ROOT}/Music/"Miles Davis"/"Kind of Blue"

# Add lyrics to specific artist
dam tag lyrics ${LIBRARY_ROOT}/Music/"Bob Dylan"
```

---

## 🔄 Integration

### **Media Server Sync**
```bash
# Sync to media server
dam sync

# Preview sync
dam sync --dry-run

# Music-specific sync
dam sync --include-music
```

### **Library Management**
- **Automatic organization**: Proper folder structure
- **Metadata consistency**: Standardized tagging
- **Quality control**: Missing file detection
- **Backup ready**: Consistent naming

---

## 📖 Related Guides

- **[Video Guide](video_guide.md)** - Movie and TV show processing
- **[Server Guide](server_guide.md)** - Media server setup
- **[Workflow Guide](workflow_guide.md)** - High-level overview
- **[Quick Start](../QUICKSTART.md)** - Initial setup

---

## 🤝 Contributing

Found an issue with music processing? Please:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create an issue with details about source files and error messages

---

**Happy music archiving!** 🎵✨
