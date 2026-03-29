# Video Guide

Complete workflow for processing video content - movies, TV shows, and existing files - to high-quality MP4 with proper metadata and organization.

> **Prerequisites:** Follow the [Quick Start Guide](../QUICKSTART.md) for initial setup.  
> **Before running Python scripts:** Activate virtual environment with `source venv/bin/activate`

---

## 🎬 Quick Start

**For all video processing, use the unified CLI:**

```bash
# Movies
dam rip video --title "Movie Title" --year 2023
make rip-movie TITLE="Movie Title" YEAR=2023

# TV Shows (all episodes)
dam rip video --title "Show Name" --year 2023 --episodes
make rip-episodes TITLE="Show Name" YEAR=2023

# Foreign language content
dam rip video --title "Foreign Film" --year 2023 --burn-subtitles
BURN_SUBTITLES=true make rip-movie TITLE="Foreign Film" YEAR=2023

# Existing files
dam rip video --title "Movie Title" --year 2023 --type file
```

---

## 📺 Content Types

### 🎥 Movies
**Perfect for:** Feature films, standalone movies, documentaries

**Workflow:**
1. **Main feature detection** - Automatically finds the longest track
2. **High-quality encoding** - H.264 with optimal compression
3. **Subtitle processing** - External SRT or burned subtitles
4. **Movie organization** - `/Movies/Movie Title (Year)/Movie Title (Year).mp4`

**Commands:**
```bash
dam rip video --title "Movie Name" --year 2023
make rip-movie TITLE="Movie Name" YEAR=2023
```

### 📺 TV Shows
**Perfect for:** TV series, episodic content, multi-episode discs

**Workflow:**
1. **Episode detection** - Finds all episode tracks on disc
2. **Individual ripping** - Rips each episode separately
3. **Continuous numbering** - Maintains episode order across discs
4. **Season organization** - `/Shows/Show Name (Year)/Season X/`

**Commands:**
```bash
dam rip video --title "Show Name" --year 2023 --episodes
make rip-episodes TITLE="Show Name" YEAR=2023
```

### 📁 Existing Files
**Perfect for:** Already-ripped MKV files, re-encoding, subtitle extraction

**Workflow:**
1. **Skip disc scanning** - Work directly with existing files
2. **Smart compression** - Only re-encode if needed (>10GB)
3. **Subtitle extraction** - Add subtitles to existing MP4s
4. **Resume capability** - Re-encode without re-ripping

**Commands:**
```bash
dam rip video --title "Movie Title" --year 2023 --type file
```

---

## 🎯 Scenario Matrix

| Scenario | Input | Output | Subtitles | Use Case |
|----------|-------|--------|-----------|----------|
| **My Language DVD** | DVD disc | MP4 + SRT | External SRT | DVDs with your preferred audio language |
| **My Language Blu-ray** | Blu-ray disc | MP4 + SRT | External SRT | Blu-rays with your preferred audio language |
| **Other Language DVD** | DVD disc | MP4 (burned) + SRT | Burned + External | DVDs with non-preferred audio language |
| **Other Language Blu-ray** | Blu-ray disc | MP4 (burned) + SRT | Burned + External | Blu-rays with non-preferred audio language |
| **TV Show Episodes** | TV disc | Multiple MP4 + SRT | External SRT | Complete season/episode ripping |
| **Existing MKV** | MKV file | MP4 + SRT | External SRT | Already ripped files |
| **Large MKV** | Uncompressed MKV | Compressed MP4 + SRT | External SRT | Re-compression needed |

---

## ⚙️ Prerequisites

### **System Requirements**
- **macOS** (Catalina or newer)
- **8GB+ RAM** recommended for video processing
- **50GB+ free storage** for temporary files

### **Hardware**
- **CD, DVD, and/or Blu-ray drive** (internal or USB)

### **Software Installation**
```bash
# Install all video tools with one command
make install-video-deps
```

This installs: HandBrakeCLI, ffmpeg/ffprobe, jq, tesseract, mkvtoolnix, and links makemkvcon.

### **MakeMKV Setup**
- **Not required for DVDs**: Automatic HandBrake fallback
- **Required for Blu-rays**: Due to encryption
- **Manual installation**: Download from https://www.makemkv.com/download/
- **CLI linking**: `make install-video-deps` handles automatically

---

## 🎛️ Configuration

### **Environment Variables (.env)**
```bash
# Language preferences
LANG_AUDIO=en          # Preferred audio track language
LANG_SUBTITLES=en      # Preferred subtitle track language

# Video quality settings
HB_QUALITY=28           # HandBrake quality (lower = better)
HB_PRESET="Apple 1080p30 Surround"  # Encoding preset
HB_TUNE=                # Optional tuning parameter

# TV show specific
MINLENGTH=300          # Minimum episode duration for TV shows
FORCE_ALL_TRACKS=true   # Force all tracks for TV shows

# Streaming optimization
STREAMING_OPTIMIZE=true # Optimize for streaming
```

### **MakeMKV Configuration**
The script automatically configures MakeMKV to extract all subtitles:
```
app_DefaultSelectionString="+sel:all,-sel:(core)"
```

---

## 🌟 Key Features

### ✅ **Complete Pipeline**
- **Disc to digital**: DVD/Blu-ray → MP4 with metadata
- **File processing**: Existing MKV → optimized MP4
- **Smart compression**: Only re-encode when needed
- **Automatic organization**: Media-server friendly structure

### ✅ **Intelligent Processing**
- **Main feature detection**: Automatically finds movies
- **Episode detection**: Finds all TV show episodes
- **Seamless branching**: Handles multi-language discs
- **Size-based fallback**: Distinguishes main features from extras

### ✅ **Advanced Subtitle Support**
- **Interactive selection**: Choose processing method
- **English content**: Auto-extract soft subtitles
- **Foreign content**: Burn or extract as needed
- **Format support**: PGS, VOB, text subtitles
- **OCR capability**: Image-based subtitle conversion

### ✅ **Flexible Workflows**
- **Disc ripping**: Direct from physical media
- **File processing**: Work with existing files
- **Smart selective ripping**: Only rip missing episodes (TV shows)
- **Resume capability**: Continue interrupted work
- **Subtitle backfill**: Add subs to existing files

### 🎯 **Smart TV Show Ripping**
For TV shows (`--episodes`), the script intelligently handles partial rips:

```bash
# Always scans disc, but only rips missing episodes
dam rip video --title "Show Name" --year 2023 --episodes

# Behavior:
# 🔍 Scans disc for all episodes
# ✓ Skips episodes that already exist (MKV or MP4)
# 🎬 Only rips missing episodes
# 📁 Perfect for interrupted rips or adding missing episodes
```

---

## 🔧 Advanced Features

### **Title Selection**
```bash
# Specific title (for seamless branching discs)
TITLE_INDEX=0 make rip-movie TITLE="Movie" YEAR=2023

# Force all tracks (bypass filtering)
FORCE_ALL_TRACKS=true make rip-episodes TITLE="Show" YEAR=2023
```

### **Encoding Options**
```bash
# Higher quality (lower number)
HB_QUALITY=20 make rip-movie TITLE="Movie" YEAR=2023

# Different preset
HB_PRESET="Fast 1080p30" make rip-movie TITLE="Movie" YEAR=2023
```

### **Subtitle Control**
```bash
# Burn subtitles for foreign films
BURN_SUBTITLES=true make rip-movie TITLE="Foreign" YEAR=2023

# Disable subtitles
LANG_SUBTITLES=none make rip-movie TITLE="Movie" YEAR=2023
```

---

## 📁 Output Organization

### **Movies**
```
/Movies/
└── Movie Title (Year)/
    ├── Movie Title (Year).mp4
    ├── Movie Title (Year).srt
    └── Movie Title (Year).nfo  (metadata)
```

### **TV Shows**
```
/Shows/
└── Show Name (Year)/
    └── Season 1/
        ├── Show Name (Year) - S01E01.mp4
        ├── Show Name (Year) - S01E01.srt
        ├── Show Name (Year) - S01E02.mp4
        └── Show Name (Year) - S01E02.srt
```

### **Continuous Episode Numbering**
- Episode numbers continue across multiple discs
- Automatic detection of existing episodes
- Proper season organization

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **"No tracks detected"**
- Clean the disc and retry
- Verify MakeMKV installation: `which makemkvcon`
- Check disc compatibility and damage

#### **"HandBrake failed"**
- Ensure HandBrakeCLI installed: `make install-video-deps`
- Check available disk space (need 2-3x disc size)
- Verify disc not copy-protected

#### **Subtitle issues**
- Check language preferences in `.env`
- Verify subtitle tracks exist on source
- Try different subtitle processing options

#### **Encoding problems**
- Check available RAM and disk space
- Verify source file integrity
- Try different quality settings

### **Debug Commands**
```bash
# Check tool installations
dam check

# Test MakeMKV detection
makemkvcon info disc:0 --minlength=300

# Test HandBrake
HandBrakeCLI --version

# Check file structure
ls -la /Movies/
ls -la /Shows/
```

### **Performance Tips**
- **SSD storage**: Faster processing for temporary files
- **RAM allocation**: More RAM helps with encoding
- **Disc quality**: Clean discs prevent read errors
- **Background processing**: Run overnight for large collections

---

## 📚 Examples

### **Movie Examples**
```bash
# Standard movie
dam rip video --title "The Matrix" --year 1999

# Foreign language film
dam rip video --title "Amélie" --year 2001 --burn-subtitles

# Specific title for seamless branching
TITLE_INDEX=2 dam rip video --title "Blade Runner" --year 1982
```

### **TV Show Examples**
```bash
# TV series season
make rip-episodes TITLE="Breaking Bad Season 1" YEAR=2008

# Multi-disc series
make rip-episodes TITLE="Game of Thrones Season 1" YEAR=2011
# (run again for disc 2, numbering continues)
```

### **File Processing Examples**
```bash
# Re-encode existing MKV
dam rip video --title "Existing Movie" --year 2020 --type file

# Add subtitles to existing MP4
dam rip video --title "Movie with Subs" --year 2020 --type file
```

---

## 🔄 Integration

### **Media Server Sync**
```bash
# Sync to media server
dam sync

# Preview sync
dam sync --dry-run

# Quiet sync
dam sync --quiet
```

### **Library Management**
- **Movies**: Organized in `/Movies/` folder
- **TV Shows**: Organized in `/Shows/` folder with seasons
- **Metadata**: Automatic NFO files for media servers
- **Compatibility**: Works with Plex, Jellyfin, Emby

---

## 📖 Related Guides

- **[Music Guide](music_guide.md)** - Audio CD processing
- **[Server Guide](server_guide.md)** - Media server setup
- **[Workflow Guide](workflow_guide.md)** - High-level overview
- **[Quick Start](../QUICKSTART.md)** - Initial setup

---

## 🤝 Contributing

Found an issue with video processing? Please:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create an issue with details about source and error messages

---

**Happy video archiving!** 🎬✨
