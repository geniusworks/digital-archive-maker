# Music Collection Guide

Complete guide to processing music from CDs, digital files, and loose tracks into a organized Jellyfin-ready library.

> **Prerequisites:** Follow the [Quick Start Guide](../QUICKSTART.md) for initial setup.  
> **Before running Python scripts:** Activate virtual environment with `source venv/bin/activate`

---

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

**First time only — configure abcde:**
```bash
cp .abcde.conf.sample ~/.abcde.conf
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
```
The Makefile auto-loads `.env` so abcde sees `LIBRARY_ROOT`. Alternative (direct): `set -a; . ./.env; set +a && abcde`

**Output:** `${LIBRARY_ROOT}/CDs/Artist/Album/NN - Title.flac`

> **Notes:** Ensure your drive supports accurate audio extraction. MusicBrainz and Cover Art Archive rate limits apply.

#### Step 2: Fix Missing Metadata (NEW!)
```bash
# Unified CLI (recommended):
dam tag fix-metadata --scan "${LIBRARY_ROOT}/CDs"
dam tag fix-metadata --fix "${LIBRARY_ROOT}/CDs"

# Direct script:
python3 bin/music/fix-missing-metadata.py --scan "${LIBRARY_ROOT}/CDs"
python3 bin/music/fix-missing-metadata.py --fix "${LIBRARY_ROOT}/CDs"
```

#### Step 3: Tag Explicit Content
```bash
# Unified CLI (recommended):
dam tag explicit "${LIBRARY_ROOT}/CDs"

# Direct script:
python3 bin/music/tag-explicit-mb.py "${LIBRARY_ROOT}/CDs"
```

**Output:** Creates definitive list of all explicit tracks in `log/explicit/explicit_tracks_current.csv`

#### Step 4: Download Lyrics (NEW!)
```bash
# Unified CLI (recommended):
dam tag lyrics "${LIBRARY_ROOT}/CDs" --recursive

# Clear all failed lookups (retry everything):
dam tag lyrics "${LIBRARY_ROOT}/CDs" --recursive --clear-failed

# Retry only previously failed tracks (useful after rate limits reset):
dam tag lyrics "${LIBRARY_ROOT}/CDs" --recursive --retry-failed

# Makefile shortcut:
make lyrics

# Direct script:
python3 bin/music/download_lyrics.py "${LIBRARY_ROOT}/CDs" --recursive

# Add a track to permanent skip list (e.g., classical, instrumental):
dam tag lyrics --add-to-skip "Classical Escape" "Brandenburg concerto No1 in F major"

# Force overwrite existing lyrics:
dam tag lyrics "${LIBRARY_ROOT}/CDs" --recursive --force
```

### 🧠 Intelligent Artist Variation System

The lyrics downloader includes advanced artist name matching to maximize success rates:

**Artist Alias Mappings** (reversible):
- **ELO** ↔ `Electric Light Orchestra` ↔ `Jeff Lynne` ↔ `Jeff Lynne's ELO`
- **John Rutter** ↔ `The Cambridge Singers` ↔ `The Cambridge Singers, John Rutter`
- **Rupert's Kitchen Orchestra** ↔ `Ruperts Kitchen Orchestra` ↔ `RUPERTS ☆ KITCHEN ☆ ORCHESTRA`
- **Wendy & Lisa** ↔ `Wendy and Lisa`
- **The Alan Parsons Project** ↔ `Alan Parsons` ↔ `Alan Parsons Project`
- **John Cougar Mellencamp** ↔ `John Mellencamp`
- **Frank Sinatra** ↔ `Frank Sinatra with Billy May and His Orchestra`

**"And" Variant Interchangeability**:
- `Daryl Hall + John Oates` → tries `Daryl Hall and John Oates`, `Daryl Hall & John Oates`
- `Simon & Garfunkel` → tries `Simon and Garfunkel`, `Simon + Garfunkel`

**"Various" Album Artist Support**:
- Extracts real artists from titles like `"Song Title (Artist)"` or `"Song (remix) (Artist)"`
- Filters out remix/version info to find actual artist names
- Examples: `"Encore Une Fois (Original Mix) (Sashi)"` → tries `Sashi - Encore Une Fois`

**Automatic Instrumental Detection**:
- Detects "instrumental" in song titles (case-insensitive)
- Automatically adds to skip list and removes from failed list
- Prevents future lookup attempts on instrumental tracks
**Features:**
- **Album-by-album processing** - One album at a time with 15s cooldowns
- **Smart failure tracking** - Only logs permanent failures when sources confirm songs don't exist
- **Permanent skip list** - Skip tracks forever (e.g., classical, instrumental, foreign language)
- **Intelligent artist variations** - Handles reversible name mappings and "and" variants (+, &, and)
- **"Various" album artist support** - Extracts actual artist from track titles like "Song (Artist)"
- **Automatic instrumental detection** - Detects "instrumental" in titles and auto-skips
- **Rate limit protection** - Exits if entire album fails due to rate limits
- **Progress preservation** - Can resume where left off
- **Retry failed tracks** - `--retry-failed` focuses only on previously failed tracks
- **Detailed statistics** - Shows skips vs failures vs successful downloads
- **Failed track removal** - Successfully retried tracks are automatically removed from failed log
- **Output:** `.lrc` files alongside each audio file for Jellyfin lyrics display

**Understanding the Output:**
- **Files skipped (lyrics already exist)** - Already have .lrc files
- **Files skipped (in skip list)** - Permanent skips (classical, instrumental, etc.)
- **Files skipped (instrumental detected)** - Auto-added to skip list when "instrumental" found in title
- **Files skipped (previously failed)** - In failed log, use `--retry-failed` to retry
- **Files searched but no lyrics found** - Genuine failures (both sources couldn't find them)
- **Albums with new lyrics** - Success! New .lrc files created
- **Albums with no new lyrics** - All tracks either had lyrics or failed

#### Step 5: Sync to Jellyfin
```bash
python3 bin/sync/sync-library.py \
  --src "${LIBRARY_ROOT}/CDs" \
  --dest "jellyfin@server:/mnt/media/Music" \
  --exclude-explicit \
  --delete
```

---

### Source 2: Digital Music Files (Existing Collection)
**Path:** Files → Metadata Fix → Organization → Jellyfin

#### Step 1: Scan and Fix Metadata
```bash
# Scan entire music library:
python3 bin/music/fix-missing-metadata.py --scan "/path/to/music"

# Fix all metadata issues:
python3 bin/music/fix-missing-metadata.py --fix "/path/to/music"
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

**Output:** Creates definitive list of all explicit tracks in `log/explicit/explicit_tracks_current.csv`

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
python3 bin/music/fix_track.py /path/to/loose-track.mp3 --target "${LIBRARY_ROOT}/Music"
```

#### Step 2: Fix Metadata
```bash
python3 bin/music/fix-missing-metadata.py --fix "/path/to/organized/track"
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
python3 bin/video/standardize_music_video_filenames.py "${LIBRARY_ROOT}/Videos/Music"
```

#### Step 3: Fix Metadata
```bash
python3 bin/video/scan_music_video_metadata.py "${LIBRARY_ROOT}/Videos/Music" --fix
```

#### Step 4: Sync to Jellyfin (Videos Section)
```bash
# Music videos sync to Videos/Music, not Music library
python3 bin/sync/sync-library.py \
  --src "${LIBRARY_ROOT}/Videos" \
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
    src: "${LIBRARY_ROOT}/CDs"
    dest: "jellyfin@server:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  # Digital archive to Jellyfin
  - name: "digital-archive-to-jellyfin"
    src: "${LIBRARY_ROOT}/Music"
    dest: "jellyfin@server:/mnt/media/Music"
    exclude_explicit: true
    exclude_unknown: true
    
  # Music videos to Jellyfin Videos
  - name: "music-videos-to-jellyfin"
    src: "${LIBRARY_ROOT}/Videos"
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
python3 bin/music/fix-missing-metadata.py --scan "/path/to/problem/files"
python3 bin/music/fix-missing-metadata.py --fix "/path/to/problem/files"

# Refresh Jellyfin library
```

### Track Titles Displaying Incorrectly
**Cause:** Missing or incorrect title metadata
**Solution:**
```bash
python3 bin/music/fix-missing-metadata.py --scan "/path/to/music"
python3 bin/music/fix-missing-metadata.py --fix "/path/to/music"
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
python3 bin/music/fix-missing-metadata.py --fix "/path/to/music"
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
python3 bin/music/fix-missing-metadata.py --fix "${LIBRARY_ROOT}/Music" --recursive

# Dry run to preview changes
python3 bin/music/fix-missing-metadata.py --fix "/path/to/music" --dry-run --verbose
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
