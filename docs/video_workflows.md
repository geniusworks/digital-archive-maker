# Video Processing Workflows

Complete guide to all video processing scenarios and workflows in the digital library system.

> **Updated:** February 2026 - Unified MP4 + External SRT approach for all content

---

## 🎬 Quick Reference

| Scenario | Command | Output | Subtitles |
|----------|---------|--------|-----------|
| **English DVD/Blu-ray** | `make rip-movie TITLE="Film" YEAR=2023 TYPE=bluray` | MP4 + SRT | External SRT |
| **Foreign Film** | `BURN_SUBTITLES=true make rip-movie TITLE="Film" YEAR=2023 TYPE=bluray` | MP4 (burned) + SRT | Burned + External |
| **Existing MKV** | `make rip-movie TITLE="Film" YEAR=2023 TYPE=bluray` | MP4 + SRT | External SRT |
| **Large MKV** | `make rip-movie TITLE="Film" YEAR=2023 TYPE=bluray` | Compressed MP4 + SRT | External SRT |

---

## 📊 Scenario Matrix

| Scenario | Input | Output | Subtitles | Container | Use Case |
|----------|-------|--------|-----------|-----------|----------|
| **English DVD** | DVD disc | MP4 + SRT | External SRT | MP4 | English DVDs |
| **English Blu-ray** | Blu-ray disc | MP4 + SRT | External SRT | MP4 | English Blu-rays |
| **Foreign DVD** | DVD disc | MP4 (burned) + SRT | Burned + External | MP4 | Foreign DVDs |
| **Foreign Blu-ray** | Blu-ray disc | MP4 (burned) + SRT | Burned + External | MP4 | Foreign Blu-rays |
| **Existing MKV** | MKV file | MP4 + SRT | External SRT | MP4 | Already ripped |
| **Large MKV** | Uncompressed MKV | Compressed MP4 + SRT | External SRT | MP4 | Re-compression needed |

---

## 🔄 Detailed Workflows

### 1. English Film Processing

```mermaid
graph TD
    A[Start: make rip-movie] --> B{MKV files exist in Blurays/DVDs folder?}
    B -->|Yes| C[Process existing MKV]
    B -->|No| D[Rip from disc]
    D --> E[Create MKV files]
    E --> C
    C --> F[HandBrake Encode]
    F --> G[MP4 File ~2-3GB]
    G --> H{English subtitles available?}
    H -->|Yes| I[Extract SRT Subtitles]
    H -->|No| J[No subtitle extraction]
    I --> K[Organize to Movies/]
    J --> K
    K --> L[Movies/Title (Year)/]
    L --> M[Title (Year).mp4]
    L --> N[Title (Year).en.srt if available]
```

**Command:**
```bash
make rip-movie TITLE="The Goonies" YEAR=1985 TYPE=bluray
```

**Expected Output:**
```
Found 1 existing MKV files, skipping disc rip...
→ Using MP4 container (Jellyfin compatible)
Processing: The Goonies (1985).mkv (18.4GB)
→ Encoding to MP4...
✓ Encoding complete: The Goonies (1985).mp4
✓ Extracted 1 subtitle file(s)
✓ Streaming optimization applied
Done: /Users/martin/Movies/Rips/Movies/The Goonies (1985)
```

**Final Organization:**
```
/Users/martin/Movies/Rips/
├── Blurays/The Goonies (1985)/          # Source folder
│   └── The Goonies (1985).mkv           # Original (18.4GB)
└── Movies/The Goonies (1985)/           # Destination folder
    ├── The Goonies (1985).mp4           # Compressed (2.3GB)
    └── The Goonies (1985).en.srt        # External subs (if available)
```

### 2. Foreign Film Processing

```mermaid
graph TD
    A[Start: BURN_SUBTITLES=true make rip-movie] --> B{MKV files exist in Blurays/DVDs folder?}
    B -->|Yes| C[Process existing MKV]
    B -->|No| D[Rip from disc]
    D --> E[Create MKV files]
    E --> C
    C --> F{Foreign audio detected?}
    F -->|No| G[Standard MP4 encoding]
    F -->|Yes| H{English subtitles available?}
    H -->|Yes| I[HandBrake + Burn Subs]
    H -->|No| J[Standard MP4 + warning]
    I --> K[MP4 with burned subs]
    J --> L[MP4 no burned subs]
    G --> M[Extract SRT if available]
    K --> M
    L --> M
    M --> N[Organize to Movies/]
    N --> O[Movies/Title (Year)/]
    O --> P[Title (Year).mp4]
    O --> Q[Title (Year).en.srt if available]
```

**Command:**
```bash
BURN_SUBTITLES=true make rip-movie TITLE="Amélie" YEAR=2001 TYPE=bluray
```

**Expected Output (with English subs):**
```
⚠️  BURNING English text subtitles (foreign language audio)
→ Encoding to MP4...
✓ Encoding complete: Amélie (2001).mp4
✓ Extracted 1 subtitle file(s)
✓ Streaming optimization applied
Done: /Users/martin/Movies/Rips/Movies/Amélie (2001)
```

**Expected Output (no English subs):**
```
⚠️  Foreign language audio detected but no English subtitles available
⚠️  Cannot burn subtitles - will extract external subs if found
→ Encoding to MP4...
✓ Encoding complete: Foreign Film (2023).mp4
✓ Streaming optimization applied
Done: /Users/martin/Movies/Rips/Movies/Foreign Film (2023)
```

### 3. Existing File Processing

```mermaid
graph TD
    A[Start: make rip-movie] --> B{MKV files exist in Blurays/DVDs folder?}
    B -->|Yes| C{File Size Check}
    B -->|No| D[Rip from disc]
    D --> E[Create MKV files]
    E --> C
    C -->|< 10GB| F[Already Compressed - Skip]
    C -->|> 10GB| G[Re-encode Needed]
    G --> H[HandBrake Encode]
    H --> I[Compressed MP4]
    F --> J[Extract SRT if available]
    I --> J
    J --> K[Organize to Movies/]
    K --> L[Movies/Title (Year)/]
    L --> M[Title (Year).mp4]
    L --> N[Title (Year).en.srt if available]
```

**Command:**
```bash
make rip-movie TITLE="Silent Running" YEAR=1972 TYPE=bluray
```

**Expected Output (large file):**
```
Found 1 existing MKV files, skipping disc rip...
⚠️  Found large file (21.1GB) - re-encoding to compress...
→ Using temporary output: Silent Running (1972)_compressed.mp4
→ Encoding to MP4...
✓ Encoding complete: Silent Running (1972)_compressed.mp4
✓ Extracted 1 subtitle file(s)
✓ Streaming optimization applied
Done: /Users/martin/Movies/Rips/Movies/Silent Running (1972)
```

---

## 🎯 Master Decision Tree

```mermaid
graph TD
    A[Start: make rip-movie] --> B{MKV files exist in Blurays/DVDs folder?}
    B -->|Yes| C{Files compressed?}
    B -->|No| D{Disc present?}
    
    C -->|< 10GB| E[Skip encoding - already done]
    C -->|> 10GB| F[Re-encode to compress]
    
    D -->|No| G[Error: No disc found]
    D -->|Yes| H[Rip from disc]
    
    F --> I[HandBrake encode]
    H --> I
    E --> J[Extract SRT if available]
    I --> J
    
    J --> K{Foreign audio?}
    K -->|No| L[External SRT only]
    K -->|Yes + BURN_SUBTITLES| M{English subs exist?}
    K -->|Yes + no flag| N[External SRT only]
    
    M -->|Yes| O[Burn + External SRT]
    M -->|No| P[External SRT only + Warning]
    
    L --> Q[Organize to Movies/]
    O --> Q
    N --> Q
    P --> Q
    
    E --> Q
    G --> R[Exit with error]
```

---

## 🚨 Error Handling Workflows

### No Disc + No Files

```mermaid
graph TD
    A[make rip-movie] --> B{Disc in Drive?}
    B -->|No| C{MKV Files Exist?}
    C -->|No| D[Error Message]
    C -->|Yes| E[Process Files]
    B -->|Yes| F[Rip from Disc]
    
    D --> G["❌ No Blu-ray/DVD disc found in drive"]
    G --> H["💡 Please insert a disc and try again"]
    H --> I[Exit - No folders created]
```

### Problematic Disc

```mermaid
graph TD
    A[Disc Read Error] --> B[MakeMKV Direct Rip]
    B --> C{Rip Success?}
    C -->|No| D[MakeMKV Backup Method]
    D --> E[Copy Disc to Disk]
    E --> F[Rip from Backup]
    F --> G{Success?}
    G -->|Yes| H[Continue Processing]
    G -->|No| I[Clear Error Message]
    C -->|Yes| H
```

---

## 📁 File Organization Patterns

### ✅ Correct Success Pattern: English Film
```
/Users/martin/Movies/Rips/
├── Blurays/The Goonies (1985)/          # Source folder (MKV only)
│   └── The Goonies (1985).mkv           # Original rip (20GB)
└── Movies/The Goonies (1985)/           # Destination folder (MP4 + SRT only)
    ├── The Goonies (1985).mp4           # Compressed (2GB)
    └── The Goonies (1985).en.srt        # External subs (if available)
```

### ✅ Correct Success Pattern: Foreign Film
```
/Users/martin/Movies/Rips/
├── Blurays/Amélie (2001)/               # Source folder (MKV only)
│   └── Amélie (2001).mkv                # Original rip (15GB)
└── Movies/Amélie (2001)/                # Destination folder (MP4 + SRT only)
    ├── Amélie (2001).mp4                # Compressed + burned subs (2GB)
    └── Amélie (2001).en.srt             # External subs backup
```

### ❌ Incorrect Pattern (Never Should Happen)
```
/Users/martin/Movies/Rips/
└── Movies/Title (Year)/                 # Should NEVER contain MKV files
    ├── Title (Year).mkv                  # ❌ WRONG - MKV in Movies folder
    └── Title (Year).mp4                  # ❌ CONFUSING - Mixed file types
```

### ✅ Error Pattern: No Disc
```
/Users/martin/Movies/Rips/
├── Blurays/                             # No empty folders created
└── Movies/                              # No empty folders created
```

---

## 📂 Folder Structure Rules

### 🎯 **Source Folders (Blurays/DVDs)**
- **Purpose:** Store original MKV rips from discs
- **Files:** Only `.mkv` files
- **Location:** `/Blurays/Title (Year)/` or `/DVDs/Title (Year)/`
- **Size:** Large uncompressed files (10-50GB)

### 🎯 **Destination Folders (Movies)**
- **Purpose:** Store final processed media
- **Files:** Only `.mp4` and `.en.srt` files
- **Location:** `/Movies/Title (Year)/`
- **Size:** Compressed MP4 (1-3GB) + small SRT files

### 🚫 **Strict Rules:**
- **NEVER** put MKV files in Movies folder
- **NEVER** put MP4 files in Blurays/DVDs folders
- **ALWAYS** keep original MKV in source folder
- **ALWAYS** create final MP4 in destination folder

### 🔄 **Workflow:**
```
Blurays/DVDs (Source) → Processing → Movies (Destination)
     MKV files                           MP4 + SRT files
```

---

## 🎛️ Control Variables

| Variable | Values | Effect |
|----------|--------|--------|
| `TYPE` | `dvd` | `bluray` | Disc type detection |
| `BURN_SUBTITLES` | `true` | `false` (default) | Burn subs for foreign films |
| `FORCE_ALL_TRACKS` | `true` | `false` (default) | Rip all titles vs main feature |
| `STREAMING_OPTIMIZE` | `true` (default) | `false` | Apply web optimization |

---

## 🎬 Key Features & Benefits

### ✅ Universal Compatibility
- **MP4 format** works on all devices and players
- **External SRT** files auto-detected by Jellyfin
- **Web streaming** optimized for all clients

### ✅ Intelligent Processing
- **Smart compression** - only re-encode when necessary
- **Foreign film support** - burns subtitles when available
- **Error resilience** - graceful handling of missing discs

### ✅ Jellyfin Integration
- **Automatic subtitle detection** - `.en.srt` files found automatically
- **Proper metadata** - titles and years organized correctly
- **Streaming ready** - optimized for web playback

### ✅ User Control
- **Explicit subtitle burning** - only when `BURN_SUBTITLES=true`
- **Flexible workflows** - works with existing files or fresh rips
- **Clear messaging** - tells user exactly what's happening

---

## 🚀 Quick Start Examples

### Basic English Film
```bash
make rip-movie TITLE="The Goonies" YEAR=1985 TYPE=bluray
```

### Foreign Film with Subtitle Burning
```bash
BURN_SUBTITLES=true make rip-movie TITLE="Amélie" YEAR=2001 TYPE=bluray
```

### Process All Tracks (Special Features)
```bash
FORCE_ALL_TRACKS=true make rip-movie TITLE="Special Film" YEAR=2023 TYPE=dvd
```

### Disable Streaming Optimization
```bash
STREAMING_OPTIMIZE=false make rip-movie TITLE="Film" YEAR=2023 TYPE=bluray
```

---

## 📞 Troubleshooting

### Common Issues
- **"No disc found"** - Insert disc or check MKV files in correct location
- **"Silent HandBrake failure"** - Check file permissions and disk space
- **"No subtitles extracted"** - Source may not have English subtitle tracks
- **"File too large"** - Script will automatically re-compress files >10GB

### Getting Help
- Check the log output for specific error messages
- Ensure all prerequisites are installed: `make install-video-deps`
- Verify MakeMKV is properly installed in `/Applications/`

This unified approach handles all your video processing needs with maximum compatibility and user control! 🎬✨
