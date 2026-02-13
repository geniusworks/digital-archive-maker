# Music Collection Guide: Complete Guide from All Sources to Jellyfin

This guide provides the complete end-to-end pipeline for getting music from **all sources** into a **Jellyfin-ready library** with proper metadata, organization, and content filtering.

## 🎯 Target Result
**Jellyfin Music Library** at `/mnt/media/Music` with:
- ✅ Complete metadata (artist, album, title, track numbers)
- ✅ Proper folder structure (`Artist/Album/NN - Title.ext`)
- ✅ High-quality audio (FLAC preferred, MP3 supported)
- ✅ Explicit content tagging for family-safe filtering
- ✅ Cover art for all albums
- ✅ **Lyrics files (.lrc) for synchronized display in Jellyfin**
- ✅ Consistent naming and organization

---

## 🌊 Music Sources Pipeline

### Source 1: Audio CDs (Physical Media)
**Path:** CD Disc → FLAC → Metadata → Jellyfin

#### Step 1: Rip CD to FLAC
```bash
# Insert CD and run:
make rip-cd
```
**Output:** `/Volumes/Data/Media/Library/CDs/Artist/Album/NN - Title.flac`

#### Step 2: Fix Missing Metadata (NEW!)
```bash
# Scan for metadata issues:
python3 bin/music/fix_missing_metadata.py --scan "/Volumes/Data/Media/Library/CDs"

# Fix all issues:
python3 bin/music/fix_missing_metadata.py --fix "/Volumes/Data/Media/Library/CDs"
```

#### Step 3: Tag Explicit Content
```bash
python3 bin/music/tag-explicit-mb.py "/Volumes/Data/Media/Library/CDs"
```

#### Step 4: Download Lyrics (NEW!)
```bash
# Smart album-by-album processing (recommended):
media lyrics "/Volumes/Data/Media/Library/CDs" --recursive

# Clear all failed lookups (retry everything):
media lyrics "/Volumes/Data/Media/Library/CDs" --recursive --clear-failed

# Retry only previously failed tracks (useful after rate limits reset):
media lyrics "/Volumes/Data/Media/Library/CDs" --recursive --retry-failed

# Add a track to permanent skip list (e.g., classical, instrumental):
media lyrics --add-to-skip "Classical Escape" "Brandenburg concerto No1 in F major"

# Force overwrite existing lyrics:
media lyrics "/Volumes/Data/Media/Library/CDs" --recursive --force

# Or use the script directly:
python3 bin/music/download_lyrics.py "/Volumes/Data/Media/Library/CDs" --recursive
```
**Features:**
- **Album-by-album processing** - One album at a time with 15s cooldowns
- **Smart failure tracking** - Only logs permanent failures when sources confirm songs don't exist
- **Permanent skip list** - Skip tracks forever (e.g., classical, instrumental, foreign language)
- **Rate limit protection** - Exits if entire album fails due to rate limits
- **Progress preservation** - Can resume where left off
- **Retry failed tracks** - `--retry-failed` focuses only on previously failed tracks
- **Detailed statistics** - Shows skips vs failures vs successful downloads
- **Failed track removal** - Successfully retried tracks are automatically removed from failed log
- **Output:** `.lrc` files alongside each audio file for Jellyfin lyrics display

**Understanding the Output:**
- **Files skipped (lyrics already exist)** - Already have .lrc files
- **Files skipped (in skip list)** - Permanent skips (classical, instrumental, etc.)
- **Files skipped (previously failed)** - In failed log, use `--retry-failed` to retry
- **Files searched but no lyrics found** - Genuine failures (both sources couldn't find them)
- **Albums with new lyrics** - Success! New .lrc files created
- **Albums with no new lyrics** - All tracks either had lyrics or failed

#### Step 5: Sync to Jellyfin
```bash
python3 bin/sync/sync-library.py \
  --src "/Volumes/Data/Media/Library/CDs" \
  --dest "jellyfin@server:/mnt/media/Music" \
  --exclude-explicit \
  --exclude-unknown
```

---

### Source 2: Digital Music Files (Existing Collection)
**Path:** Files → Metadata Fix → Organization → Jellyfin

#### Step 1: Scan and Fix Metadata
```bash
# Scan entire music library:
python3 bin/music/fix_missing_metadata.py --scan "/path/to/music"

# Fix all metadata issues:
python3 bin/music/fix_missing_metadata.py --fix "/path/to/music"
```

#### Step 2: Normalize Album Organization
```bash
# For each album that needs organization:
python3 bin/music/fix_album.py "/path/to/Artist/Album"
```

#### Step 3: Add Missing Cover Art
```bash
python3 bin/music/fix_album_covers.py "/path/to/music"
```

#### Step 4: Tag Explicit Content
```bash
python3 bin/music/tag-explicit-mb.py "/path/to/music"
```

#### Step 5: Download Lyrics (NEW!)
```bash
# Smart album-by-album processing (recommended):
media lyrics "/path/to/music" --recursive

# Clear all failed lookups (retry everything):
media lyrics "/path/to/music" --recursive --clear-failed

# Or use the script directly:
python3 bin/music/download_lyrics.py "/path/to/music" --recursive
```
**Features:**
- **Album-by-album processing** - One album at a time with 15s cooldowns
- **Smart failure tracking** - Only logs permanent failures when sources confirm songs don't exist
- **Rate limit protection** - Exits if entire album fails due to rate limits
- **Progress preservation** - Can resume where left off
- **Output:** `.lrc` files alongside each audio file for Jellyfin lyrics display

#### Step 6: Sync to Jellyfin
```bash
python3 bin/sync/sync-library.py \
  --src "/path/to/music" \
  --dest "jellyfin@server:/mnt/media/Music" \
  --exclude-explicit \
  --exclude-unknown
```

---

### Source 3: Loose Tracks (Single Files)
**Path:** Single File → Identify → Organize → Metadata → Jellyfin

#### Step 1: Identify and Organize Track
```bash
python3 bin/music/fix_track.py /path/to/loose-track.mp3 --target "/Volumes/Data/Media/Library/Music"
```

#### Step 2: Fix Metadata
```bash
python3 bin/music/fix_missing_metadata.py --fix "/path/to/organized/track"
```

#### Step 3: Sync to Jellyfin
```bash
# File will be included in regular sync operations
```

---

### Source 4: Music Videos
**Path:** Video Files → Metadata → Organization → Jellyfin (Videos)

#### Step 1: Organize Music Videos
```bash
python3 bin/video/fix_music_videos_mapped.py "/path/to/music/videos"
```

#### Step 2: Standardize Filenames
```bash
python3 bin/video/standardize_music_video_filenames.py "/Volumes/Data/Media/Library/Videos/Music"
```

#### Step 3: Fix Metadata
```bash
python3 bin/video/scan_music_video_metadata.py "/Volumes/Data/Media/Library/Videos/Music" --fix
```

#### Step 4: Sync to Jellyfin (Videos Section)
```bash
# Music videos sync to Videos/Music, not Music library
python3 bin/sync/sync-library.py \
  --src "/Volumes/Data/Media/Library/Videos" \
  --dest "jellyfin@server:/mnt/media/Videos"
```

---

## 🔄 Complete Automation (Master Sync)

### Run Everything with Master Sync
```bash
python3 bin/sync/master-sync.py
```

**Configuration:** `bin/sync/sync-config.yaml`
```yaml
sync_jobs:
  # Clean CD library to Jellyfin
  - name: "cd-library-to-jellyfin"
    src: "/Volumes/Data/Media/Library/CDs"
    dest: "jellyfin@server:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  # Digital library to Jellyfin
  - name: "digital-library-to-jellyfin"
    src: "/Volumes/Data/Media/Library/Music"
    dest: "jellyfin@server:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  # Music videos to Jellyfin Videos
  - name: "music-videos-to-jellyfin"
    src: "/Volumes/Data/Media/Library/Videos"
    dest: "jellyfin@server:/mnt/media/Videos"
    media: "videos"
```

---

## 🎵 Music Quality Pipeline

### Audio Format Priority
1. **FLAC** (Lossless) - Preferred for CD rips and archival
2. **MP3** (320kbps) - Acceptable for existing collections
3. **MP4/M4A** - Supported, automatically handled

### Metadata Standards
- **Artist:** Clean, properly capitalized
- **Album:** Complete album title from MusicBrainz
- **Title:** Complete track title
- **Genre:** Curated whitelist (via `update-genre-mb.py`)
- **Explicit:** `Yes|No|Unknown` for content filtering

### File Organization
```
/mnt/media/Music/
  Artist Name/
    Album Name/
      01 - First Track.flac
      02 - Second Track.flac
      ...
      cover.jpg
```

---

## 🛠️ Troubleshooting Common Issues

### Files Not Showing in Jellyfin
**Cause:** Missing or incorrect metadata
**Solution:**
```bash
# Rescan and fix metadata
python3 bin/music/fix_missing_metadata.py --scan "/path/to/problem/files"
python3 bin/music/fix_missing_metadata.py --fix "/path/to/problem/files"

# Refresh Jellyfin library
```

### Track Titles Displaying Incorrectly
**Cause:** Missing or incorrect title metadata
**Solution:**
```bash
python3 bin/music/fix_missing_metadata.py --scan "/path/to/music"
python3 bin/music/fix_missing_metadata.py --fix "/path/to/music"
# This populates missing title metadata using MusicBrainz
```

### Missing Cover Art
**Cause:** No cover.jpg in album folder
**Solution:**
```bash
python3 bin/music/fix_album_covers.py "/path/to/music"
```

### Wrong Artist/Album Information
**Cause:** Poor metadata from file names or tags
**Solution:**
```bash
# Force MusicBrainz lookup
python3 bin/music/fix_missing_metadata.py --fix "/path/to/music"
```

---

## 📊 Quality Assurance Checklist

### Before Sync to Jellyfin
- [ ] All files have complete metadata (artist, album, title, track)
- [ ] All albums have cover.jpg
- [ ] Explicit content is properly tagged
- [ ] File structure follows `Artist/Album/NN - Title.ext`
- [ ] No duplicate files or albums

### After Sync to Jellyfin
- [ ] Jellyfin library scan completes successfully
- [ ] All albums show cover art
- [ ] Track titles display correctly
- [ ] Explicit content filtering works as expected
- [ ] Music plays without issues

---

## 🚀 Advanced Features

### Bulk Operations
```bash
# Process entire library at once
python3 bin/music/fix_missing_metadata.py --fix "/Volumes/Data/Media/Library/Music" --recursive

# Dry run to preview changes
python3 bin/music/fix_missing_metadata.py --fix "/path/to/music" --dry-run --verbose
```

### Content Filtering
```bash
# Family-safe sync (no explicit content)
python3 bin/sync/sync-library.py --src ... --dest ... --exclude-explicit --exclude-unknown

# Complete sync (including explicit content)
python3 bin/sync/sync-library.py --src ... --dest ...
```

### Genre Enhancement
```bash
# Add proper genres to all music
python3 bin/music/update-genre-mb.py "/path/to/music"
```

---

## 📚 Related Documentation

- **CD Ripping:** `docs/cd_ripping_guide.md`
- **Video Processing:** `docs/video_ripping_guide.md`
- **Media Server Setup:** `docs/media_server_setup.md`
- **Workflow Overview:** `docs/workflow_overview.md`
- **Individual Scripts:** `README.md` (tool descriptions)

---

## 🎯 Success Metrics

When the collection guide is complete, you should have:
- **100%** of files with complete metadata
- **100%** of albums with cover art
- **Proper** explicit content filtering
- **Clean** Jellyfin library with proper organization
- **Family-safe** media server environment
