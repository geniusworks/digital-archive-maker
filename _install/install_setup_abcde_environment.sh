#!/bin/bash
set -e

echo "Checking required tools for abcde ripping and tagging..."

# Homebrew install command
install_if_missing() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Installing $1..."
        brew install "$2"
    else
        echo "$1 is already installed."
    fi
}

# Core tools
install_if_missing abcde abcde
install_if_missing eyeD3 eye-d3
install_if_missing metaflac flac
install_if_missing convert imagemagick
install_if_missing wget wget
install_if_missing curl curl

# Optional: create a cleanup script for later
CLEAN_SCRIPT="/usr/local/bin/abcde-cleanup"
if [ ! -f "$CLEAN_SCRIPT" ]; then
    echo "Creating cleanup script at $CLEAN_SCRIPT..."
    cat <<'EOF' > "$CLEAN_SCRIPT"
#!/bin/bash
# Example cleanup script after ripping

find /Volumes/Data/Media/Library/CDs -type f -name '*.flac' -exec metaflac --remove --block-type=PICTURE {} \;
echo "Removed embedded album art from all FLACs in ripped CD folder (if needed)."
EOF
    chmod +x "$CLEAN_SCRIPT"
else
    echo "Cleanup script already exists at $CLEAN_SCRIPT."
fi

echo "Setup complete. You can now use abcde with embedded album art and automated tagging."

