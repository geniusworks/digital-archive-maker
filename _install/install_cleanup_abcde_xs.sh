#!/bin/bash
# cleanup_abcde_xs.sh

set -e

# Locate the old DiscID.bundle inside the abcde cellar path
OLD_DISC_ID="/opt/homebrew/Cellar/abcde"/*/libexec/lib/perl5/darwin-thread-multi-2level/auto/MusicBrainz/DiscID/DiscID.bundle

if [ -f "$OLD_DISC_ID" ]; then
  echo "Removing old incompatible DiscID.bundle:"
  echo "  $OLD_DISC_ID"
  rm "$OLD_DISC_ID"
  echo "Cleanup complete."
else
  echo "No old DiscID.bundle found to clean."
fi

