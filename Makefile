# Common tasks for the digital library project

SHELL := /bin/sh

.PHONY: help install-deps rip-cd rip-video fix-album fetch-covers fix-track compare

help:
	@echo "Available targets:"
	@echo "  install-deps        Install Homebrew deps and Python packages"
	@echo "  rip-cd              Rip an audio CD using abcde"
	@echo "  rip-video TYPE=...  Rip a video disc (TYPE=dvd|bluray) using bin/rip_video.sh"
	@echo "  fix-album DIR=...   Normalize and complete an album folder"
	@echo "  fetch-covers ROOT=...  Fetch missing cover.jpg under ROOT"
	@echo "  fix-track FILE=... TARGET=...  Organize a single loose track"
	@echo "  compare OLD=... NEW=... [MODE=albums|artists] [THRESHOLD=90] Compare two libraries"

install-deps:
	@echo "Installing Homebrew deps via _install/install_setup_abcde_environment.sh..."
	@bash _install/install_setup_abcde_environment.sh
	@echo "Installing Python deps from requirements.txt..."
	@python3 -m pip install -r requirements.txt

rip-cd:
	@echo "Ripping CD with abcde... (ensure ~/.abcde.conf is configured)"
	@abcde

rip-video:
	@if [ -z "$(TYPE)" ]; then echo "Usage: make rip-video TYPE=dvd|bluray" >&2; exit 1; fi
	@chmod +x bin/rip_video.sh || true
	@bin/rip_video.sh $(TYPE)

fix-album:
	@if [ -z "$(DIR)" ]; then echo "Usage: make fix-album DIR=\"/path/to/Artist/Album\"" >&2; exit 1; fi
	@bash ./fix_album.sh "$(DIR)"

fetch-covers:
	@if [ -z "$(ROOT)" ]; then echo "Usage: make fetch-covers ROOT=\"/path/or/library/root\"" >&2; exit 1; fi
	@bash ./fix_album_covers.sh "$(ROOT)"

fix-track:
	@if [ -z "$(FILE)" ] || [ -z "$(TARGET)" ]; then echo "Usage: make fix-track FILE=\"/path/to/file.ext\" TARGET=\"/Volumes/Data/Media/Rips/Digital\"" >&2; exit 1; fi
	@python3 ./fix_track.py "$(FILE)" --target "$(TARGET)"

compare:
	@if [ -z "$(OLD)" ] || [ -z "$(NEW)" ]; then echo "Usage: make compare OLD=\"/old/library\" NEW=\"/new/library\" [MODE=albums|artists] [THRESHOLD=90]" >&2; exit 1; fi
	@python3 ./compare_music.py $(OLD) $(NEW) $(if $(MODE),--$(MODE),) $(if $(THRESHOLD),--threshold $(THRESHOLD),)
