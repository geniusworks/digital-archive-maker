# Home Ripping Guide for CDs, DVDs, and Blu-rays (Non-DMCA Protected)

> Note: This combined guide is kept for reference. For up-to-date, focused workflows see:
> - `docs/cd_ripping_guide.md` (CDs with abcde)
> - `docs/video_ripping_guide.md` (DVD/Blu-ray with MakeMKV + HandBrakeCLI)

This guide outlines how to set up and automate the ripping of non-DMCA-protected CDs, DVDs, and Blu-ray discs on macOS using a USB Blu-ray drive.

---

## 🧰 Prerequisites

### Hardware:
- macOS system (Intel or Apple Silicon)
- USB Blu-ray drive (e.g., LG WH16NS40, Pioneer BDR-XD08)

### Software:
Install the following tools via Homebrew or manually:

```bash
brew install abcde id3v2 cd-discid cdrdao lame flac opus-tools handbrake
```

Install MakeMKV manually:
- Download: https://www.makemkv.com/download/
- Install to `/Applications`
- Enable CLI:
```bash
sudo ln -s /Applications/MakeMKV.app/Contents/MacOS/makemkvcon /usr/local/bin/makemkvcon
```

---

## 📀 Ripping Audio CDs with `abcde`

### 1. Create config file `~/.abcde.conf`:
```bash
OUTPUTDIR="$HOME/Rips/CDs"
OUTPUTTYPE="flac"
PADTRACKS=y
MAXPROCS=2
CDDBMETHOD=musicbrainz
```

### 2. Rip the CD:
```bash
abcde -x
```

This will:
- Look up metadata (MusicBrainz)
- Rip to FLAC
- Save to `~/Rips/CDs/Artist/Album/Track.flac`

---

## 📀 Ripping DVDs and Blu-rays with MakeMKV and HandBrakeCLI

### 1. Insert Disc and Create Output Folder:
```bash
DISCTYPE=dvd   # or 'bluray'
# Map DISCTYPE to a stable directory name without relying on Bash 4+ features
case "$DISCTYPE" in
  dvd) DISCDIR="DVDs" ;;
  bluray) DISCDIR="Blurays" ;;
  *) echo "Unknown DISCTYPE: $DISCTYPE" >&2; exit 1 ;;
esac
TITLE=$(date "+%Y-%m-%d")
OUTDIR="$HOME/Rips/$DISCDIR/$TITLE"
mkdir -p "$OUTDIR"
```

### 2. Rip to MKV with MakeMKV:
```bash
makemkvcon mkv disc:0 all "$OUTDIR"
```

### 3. Transcode to MP4 with HandBrakeCLI:
```bash
for file in "$OUTDIR"/*.mkv; do
  BASENAME=$(basename "$file" .mkv)
  HandBrakeCLI -i "$file" -o "$OUTDIR/${BASENAME}.mp4" -e x264 -q 22 -B 160 --optimize
done
```

---

## 🧪 Notes on Metadata
- Audio CDs: metadata is pulled from MusicBrainz via `abcde`
- DVDs/Blu-rays: No automatic metadata; consider manual renaming or use FileBot for post-process tagging

---

## ⚙️ Optional: Automation Script
Save the following as `~/rip_and_encode.sh`:

```bash
#!/bin/bash

set -e
echo "Insert disc and choose type:"
select disc_type in "CD" "DVD" "Blu-ray" "Quit"; do
    case $disc_type in
        "CD")
            abcde -x
            break;;
        "DVD"|"Blu-ray")
            title=$(date "+%Y-%m-%d")
            outdir="$HOME/Rips/${disc_type//-/}/$title"
            mkdir -p "$outdir"
            makemkvcon mkv disc:0 all "$outdir"
            for f in "$outdir"/*.mkv; do
                name=$(basename "$f" .mkv)
                HandBrakeCLI -i "$f" -o "$outdir/${name}.mp4" -e x264 -q 22 -B 160 --optimize
            done
            break;;
        "Quit")
            break;;
        *)
            echo "Invalid option.";;
    esac
done
```

Make executable:
```bash
chmod +x ~/rip_and_encode.sh
```

Run with:
```bash
~/rip_and_encode.sh
```

---

## 📌 Summary
- FLAC is ideal for archival; MP3 is better for space-constrained playback
- Ripped files are stored by type/date in:
  - `~/Rips/CDs/`
  - `~/Rips/DVDs/`
  - `~/Rips/Blurays/`
- Transcoded video is `.mp4` H.264 encoded

Use this guide to build a consistent, reliable personal media archive.
