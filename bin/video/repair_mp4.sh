#!/usr/bin/env zsh
set -euo pipefail

# MP4 Compliance Repair Script
# ==========================
# 
# This script checks and repairs MP4 files for streaming compliance:
# - Fixes missing/invalid timestamps
# - Adds faststart flag for web streaming
# - Ensures proper MP4 container structure
#
# USAGE:
#   ./repair_mp4.sh "movie.mp4"
#   ./repair_mp4.sh "/path/to/movie.mp4"
#
# OUTPUT:
#   - Repaired MP4 file (replaces original if successful)
#   - Backup of original if repair fails

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <mp4_file>"
  exit 1
fi

INPUT_FILE="$1"

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "❌ File not found: $INPUT_FILE"
  exit 1
fi

if [[ "${INPUT_FILE##*.}" != "mp4" ]]; then
  echo "❌ Not an MP4 file: $INPUT_FILE"
  exit 1
fi

echo "🔍 Checking MP4 compliance: $(basename "$INPUT_FILE")"

# Check for common MP4 compliance issues
COMPLIANCE_CHECK=$(ffmpeg -i "$INPUT_FILE" -v quiet -f null - 2>&1 | grep -E "(non-monotonic|missing timestamps|Invalid frame)" || true)

# Also check if faststart is present
FASTSTART_CHECK=$(ffmpeg -i "$INPUT_FILE" -v quiet -movflags +faststart -f null - 2>&1 | grep -E "(faststart|moov atom)" || true)

if [[ -n "$COMPLIANCE_CHECK" ]] || [[ -z "$FASTSTART_CHECK" ]]; then
  echo "🔧 Issues detected, repairing MP4..."
  
  # Create backup
  BACKUP_FILE="${INPUT_FILE%.mp4}.backup.mp4"
  echo "📋 Creating backup: $(basename "$BACKUP_FILE")"
  cp "$INPUT_FILE" "$BACKUP_FILE"
  
  # Repair the file
  REPAIRED_FILE="${INPUT_FILE%.mp4}.repair.mp4"
  
  echo "⚙️  Running repair process..."
  
  if ffmpeg -fflags +genpts \
    -i "$INPUT_FILE" \
    -map 0 \
    -c copy \
    -movflags +faststart \
    -avoid_negative_ts make_zero \
    -write_colours 1 \
    "$REPAIRED_FILE" 2>/dev/null; then
    
    echo "✅ Repair completed successfully"
    
    # Verify the repaired file
    echo "🔍 Verifying repaired file..."
    VERIFY_CHECK=$(ffmpeg -i "$REPAIRED_FILE" -v quiet -f null - 2>&1 | grep -E "(non-monotonic|missing timestamps|Invalid frame)" || true)
    
    if [[ -n "$VERIFY_CHECK" ]]; then
      echo "⚠️  Repaired file still has issues:"
      echo "$VERIFY_CHECK"
      echo "📋 Keeping original file and backup"
      rm -f "$REPAIRED_FILE"
    else
      # Replace original with repaired version
      echo "🔄 Replacing original with repaired version"
      mv "$REPAIRED_FILE" "$INPUT_FILE"
      
      # Check file size to ensure it's reasonable
      ORIGINAL_SIZE=$(stat -f%z "$BACKUP_FILE")
      REPAIRED_SIZE=$(stat -f%z "$INPUT_FILE")
      
      if [[ $REPAIRED_SIZE -lt $((ORIGINAL_SIZE / 10)) ]]; then
        echo "⚠️  Repaired file seems too small, restoring backup"
        mv "$BACKUP_FILE" "$INPUT_FILE"
      else
        echo "🗑️  Removing backup (repair successful)"
        rm -f "$BACKUP_FILE"
      fi
    fi
  else
    echo "❌ Repair failed, keeping original"
    rm -f "$REPAIRED_FILE"
  fi
else
  echo "✅ MP4 is already streaming compliant"
fi

# Final verification
echo ""
echo "📊 Final file info:"
ffprobe -v quiet -show_format -show_streams "$INPUT_FILE" | grep -E "(duration|size|codec_name)" | head -10

echo ""
echo "✅ Repair process completed for: $(basename "$INPUT_FILE")"
