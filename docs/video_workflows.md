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
    A[English DVD/Blu-ray Disc] --> B[MakeMKV Rip]
    B --> C[MKV File ~20GB]
    C --> D[HandBrake Encode]
    D --> E[MP4 File ~2-3GB]
    E --> F[Extract SRT Subtitles]
    F --> G[Organize to Movies/]
    
    G --> H[Movies/Title (Year)/]
    H --> I[Title (Year).mp4]
    H --> J[Title (Year).en.srt]
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
├── Blurays/The Goonies (1985)/          # Source
│   └── The Goonies (1985).mkv           # Original (18.4GB)
└── Movies/The Goonies (1985)/           # Destination
    ├── The Goonies (1985).mp4           # Compressed (2.3GB)
    └── The Goonies (1985).en.srt        # External subs
```

### 2. Foreign Film Processing

```mermaid
graph TD
    A[Foreign DVD/Blu-ray Disc] --> B[MakeMKV Rip]
    B --> C[MKV File ~15GB]
    C --> D{English Subtitles Available?}
    D -->|Yes| E[HandBrake + Burn Subs]
    D -->|No| F[HandBrake Only]
    E --> G[MP4 with Burned Subs]
    F --> H[MP4 No Subs]
    G --> I[Extract External SRT]
    H --> I
    I --> J[Organize to Movies/]
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
    A[Existing MKV File] --> B{File Size Check}
    B -->|< 10GB| C[Already Compressed - Skip]
    B -->|> 10GB| D[Re-encode Needed]
    D --> E[HandBrake Encode]
    E --> F[Compressed MP4]
    C --> G[Extract SRT]
    F --> G
    G --> H[Organize to Movies/]
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
    A[Start: make rip-movie] --> B{MKV files exist?}
    B -->|Yes| C{Files compressed?}
    B -->|No| D{Disc present?}
    
    C -->|< 10GB| E[Skip encoding - already done]
    C -->|> 10GB| F[Re-encode to compress]
    
    D -->|No| G[Error: No disc found]
    D -->|Yes| H[Rip from disc]
    
    F --> I[HandBrake encode]
    H --> I
    E --> J[Extract SRT]
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

### Success: English Film
```
/Users/martin/Movies/Rips/
├── Blurays/The Goonies (1985)/          # Source
│   └── The Goonies (1985).mkv           # Original (20GB)
└── Movies/The Goonies (1985)/           # Destination
    ├── The Goonies (1985).mp4           # Compressed (2GB)
    └── The Goonies (1985).en.srt        # External subs
```

### Success: Foreign Film
```
/Users/martin/Movies/Rips/
├── Blurays/Amélie (2001)/               # Source
│   └── Amélie (2001).mkv                # Original (15GB)
└── Movies/Amélie (2001)/                # Destination
    ├── Amélie (2001).mp4                # Compressed + burned subs (2GB)
    └── Amélie (2001).en.srt             # External subs backup
```

### Error: No Disc
```
/Users/martin/Movies/Rips/
├── Blurays/                             # No empty folders created
└── Movies/                              # No empty folders created
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
