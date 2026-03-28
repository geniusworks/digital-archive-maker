# Tools Guide

Additional utilities and advanced tools for specialized tasks beyond the core `dam` workflow.

---

## 🎵 Music Tools

### **Album Organization**
```bash
# Normalize existing album folders
python bin/music/fix_album.py /path/to/album

# What it does:
# - Renames tracks to NN - Title.flac format
# - Rebuilds playlist files
# - Fixes tags and cover art
# - Standardizes folder structure
```

**Use when**: You have existing albums that need standardization to match Digital Archive Maker conventions.

### **Lyrics Enhancement**
```bash
# Download lyrics for music files
python bin/music/download_lyrics.py /path/to/music

# Alternative to dam command
dam tag lyrics /path/to/music
```

**Features:**
- Fetches lyrics from Genius API (requires `GENIUS_API_TOKEN`)
- Falls back to free sources if no key configured
- Creates synchronized `.lrc` files
- Batch processing support

### **Content Filtering**
```bash
# Tag explicit content
python bin/music/tag-explicit-mb.py /path/to/music

# Alternative to dam command
dam tag explicit /path/to/music
```

**Features:**
- Uses MusicBrainz and Spotify APIs for content identification
- Writes `EXPLICIT=Yes|No|Unknown` tags per track
- Supports FLAC and MP3 files
- Family-friendly filtering preparation

### **Genre Tagging**
```bash
# Add genre tags to music
python bin/music/tag_genres.py /path/to/music

# Alternative to dam command
dam tag genres /path/to/music
```

**Features:**
- Analyzes audio characteristics
- Matches to appropriate genres
- Updates existing genre tags
- Supports multiple genres per track

---

## 🎬 Video Tools

### **Movie Metadata**
```bash
# Add rich movie metadata
python bin/video/tag-movie-metadata.py /path/to/movie

# Alternative to dam command
dam tag movie /path/to/movies
```

**Features:**
- Fetches plot, genres, cast, artwork from TMDb/OMDb
- Creates `.nfo` files for media servers
- Downloads poster and fanart
- Detailed movie information

### **Movie Ratings**
```bash
# Add MPAA ratings to movies
python bin/video/tag-movie-ratings.py /path/to/movies

# Alternative to dam command
dam tag ratings /path/to/movies
```

**Features:**
- Fetches rating tags (`©rat`) via TMDb/OMDb
- Includes overrides and caching for consistency
- Supports international rating systems
- Parental control preparation

### **Subtitle Processing**
```bash
# Extract subtitles from video files
python bin/video/extract_subtitles.py /path/to/video

# Convert subtitle formats
python bin/video/convert_subtitles.py input.srt output.vtt

# OCR image-based subtitles
python bin/video/ocr_subtitles.py /path/to/video
```

**Features:**
- Extract subtitles from MKV/MP4 files
- Convert between subtitle formats (SRT, VTT, ASS)
- OCR for PGS/VOB image subtitles
- Batch processing support

---

## 📺 TV Show Tools

### **Show Organization**
```bash
# Organize TV shows for media servers
python bin/tv/rename_shows_jellyfin.py /path/to/shows

# Output format: .../TV/Show Name/Season 01/Show Name - S01E01 - Episode Title.ext
```

**Features:**
- Normalizes filenames to Jellyfin/Plex conventions
- Handles various input formats automatically
- Detects season and episode numbers
- Creates proper folder structure

### **Show Metadata**
```bash
# Add TV show metadata
python bin/tv/tag-show-metadata.py /path/to/shows

# Alternative to dam command
dam tag show /path/to/shows
```

**Features:**
- Fetches show metadata from TMDb
- Downloads season posters and show artwork
- Creates `.nfo` files for episodes
- Episode-specific metadata

### **Episode Processing**
```bash
# Process TV show episodes
python bin/tv/process_episodes.py /path/to/shows

# What it does:
# - Standardizes episode naming
# - Adds episode metadata
# - Downloads subtitles
# - Organizes by season
```

---

## 🖼️ Image & Cover Art Tools

### **Album Cover Fixing**
```bash
# Fix missing album covers
python bin/music/fix_album_covers.py /path/to/music

# Alternative to dam command
dam fix-covers /path/to/music
```

**Features:**
- Searches MusicBrainz and Cover Art Archive
- Downloads high-resolution artwork
- Updates embedded cover art and folder.jpg
- Supports multiple image formats

### **Image Processing**
```bash
# Resize cover art
python bin/image/resize_covers.py /path/to/images --size 1000x1000

# Convert image formats
python bin/image/convert_images.py /path/to/images --format jpg

# Optimize images for web
python bin/image/optimize_images.py /path/to/images
```

**Features:**
- Batch image processing
- Format conversion (PNG, JPG, WEBP)
- Size optimization
- Quality control

---

## 📁 File Management Tools

### **Library Organization**
```bash
# Organize library structure
python bin/organize/organize_library.py /path/to/library

# What it does:
# - Creates proper folder structure
# - Moves files to correct locations
# - Renames files to conventions
# - Fixes duplicate files
```

### **Duplicate Detection**
```bash
# Find duplicate files
python bin/organize/find_duplicates.py /path/to/library

# Remove duplicates
python bin/organize/remove_duplicates.py /path/to/library --dry-run
```

**Features:**
- Audio fingerprinting for music files
- Video hash comparison
- Image similarity detection
- Safe removal with preview

### **File Validation**
```bash
# Validate music files
python bin/validate/check_music.py /path/to/music

# Validate video files
python bin/validate/check_video.py /path/to/videos

# Check for corruption
python bin/validate/check_integrity.py /path/to/library
```

**Features:**
- File integrity checking
- Metadata validation
- Format compatibility testing
- Corruption detection

---

## 🔧 System Tools

### **Dependency Management**
```bash
# Check all dependencies
python bin/system/check_deps.py

# Install missing dependencies
python bin/system/install_deps.py

# Update tools
python bin/system/update_tools.py
```

### **Configuration Management**
```bash
# Backup configuration
python bin/system/backup_config.py

# Restore configuration
python bin/system/restore_config.py backup.tar.gz

# Validate configuration
python bin/system/validate_config.py
```

### **Performance Monitoring**
```bash
# Monitor system performance
python bin/system/monitor.py

# Check disk space
python bin/system/check_space.py /path/to/library

# Analyze processing performance
python bin/system/analyze_performance.py
```

---

## 🌐 Network & Sync Tools

### **Network Sync**
```bash
# Sync to network storage
python bin/sync/network_sync.py /source /destination

# Alternative to dam command
dam sync --destinations "/network/path"
```

### **Cloud Backup**
```bash
# Backup to cloud storage
python bin/sync/cloud_backup.py /path/to/library

# Supported: AWS S3, Google Drive, Dropbox
# Requires: API keys in .env
```

### **Remote Verification**
```bash
# Verify remote backups
python bin/sync/verify_remote.py /remote/path

# Check sync status
python bin/sync/check_sync.py /source /destination
```

---

## 📊 Analysis & Reporting

### **Library Statistics**
```bash
# Generate library report
python bin/analyze/library_stats.py /path/to/library

# What it includes:
# - File counts by type
# - Storage usage
# - Quality metrics
# - Missing metadata
```

### **Quality Analysis**
```bash
# Analyze audio quality
python bin/analyze/audio_quality.py /path/to/music

# Analyze video quality
python bin/analyze/video_quality.py /path/to/videos

# Generate quality report
python bin/analyze/quality_report.py /path/to/library
```

### **Metadata Reports**
```bash
# Metadata completeness report
python bin/analyze/metadata_report.py /path/to/library

# Missing metadata report
python bin/analyze/missing_metadata.py /path/to/library

# Explicit content report
python bin/analyze/explicit_report.py /path/to/music
```

---

## 🛠️ Development Tools

### **Testing Tools**
```bash
# Test library processing
python bin/test/test_library.py /path/to/library

# Test sync functionality
python bin/test/test_sync.py /source /destination

# Performance testing
python bin/test/performance_test.py
```

### **Debug Tools**
```bash
# Debug processing issues
python bin/debug/trace_processing.py /path/to/problem

# Analyze errors
python bin/debug/analyze_errors.py /path/to/logs

# System diagnostics
python bin/debug/system_diag.py
```

---

## 📋 Usage Examples

### **Complete Music Processing**
```bash
# Step 1: Fix album organization
python bin/music/fix_album.py /path/to/music

# Step 2: Add covers
python bin/music/fix_album_covers.py /path/to/music

# Step 3: Add lyrics
python bin/music/download_lyrics.py /path/to/music

# Step 4: Tag explicit content
python bin/music/tag-explicit-mb.py /path/to/music

# Step 5: Add genres
python bin/music/tag_genres.py /path/to/music
```

### **TV Show Processing**
```bash
# Step 1: Organize files
python bin/tv/rename_shows_jellyfin.py /path/to/shows

# Step 2: Add metadata
python bin/tv/tag-show-metadata.py /path/to/shows

# Step 3: Process episodes
python bin/tv/process_episodes.py /path/to/shows
```

### **Library Maintenance**
```bash
# Step 1: Find duplicates
python bin/organize/find_duplicates.py /path/to/library

# Step 2: Validate files
python bin/validate/check_integrity.py /path/to/library

# Step 3: Generate report
python bin/analyze/library_stats.py /path/to/library

# Step 4: Clean up
python bin/organize/cleanup_library.py /path/to/library
```

---

## 🔧 Integration with dam Commands

### **dam vs Direct Scripts**

| Task | dam Command | Direct Script | When to Use |
|------|-------------|---------------|-------------|
| Rip CD | `dam rip cd` | N/A | Standard CD ripping |
| Fix covers | `dam fix-covers` | `python bin/music/fix_album_covers.py` | Advanced options |
| Tag explicit | `dam tag explicit` | `python bin/music/tag-explicit-mb.py` | Custom processing |
| Sync library | `dam sync` | `python bin/sync/network_sync.py` | Network configurations |
| Process video | `dam rip video` | N/A | Standard video processing |

### **Best Practices**

1. **Use dam commands** for standard workflows
2. **Use direct scripts** for advanced options or custom processing
3. **Combine tools** for complex operations
4. **Preview first** with `--dry-run` when available
5. **Backup before** major operations

---

## 📚 Related Guides

- **[Video Guide](video_guide.md)** - Video processing workflows
- **[Music Guide](music_guide.md)** - Audio processing workflows
- **[Workflow Guide](workflow_guide.md)** - Complete workflow overview
- **[Server Guide](server_guide.md)** - Media server setup

---

## 🤝 Contributing

Want to add new tools? Please:
1. Follow existing code patterns
2. Add proper error handling
3. Include help documentation
4. Add tests for new functionality
5. Update this guide

---

**Happy tooling!** 🛠️✨
