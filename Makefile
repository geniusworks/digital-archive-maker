# Common tasks for the digital library project

SHELL := /bin/sh

# Load .env if present and export variables (centralized config)
ifneq (,$(wildcard .env))
include .env
export $(shell sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .env)
endif

.PHONY: help install-deps rip-cd rip-video rip-movie fix-album fetch-covers fix-track compare backfill-subs

help:
	@echo "Available targets:"
	@echo "  install-deps        Install Homebrew deps and Python packages"
	@echo "  rip-cd              Rip an audio CD using abcde"
	@echo "  rip-video TYPE=...  Rip a video disc (TYPE=dvd|bluray) using bin/rip_video.sh"
	@echo "  rip-movie TYPE=... TITLE=... YEAR=...  Rip and organize a movie into Movies/Title (Year)/Title (Year).mp4"
	@echo "  fix-album DIR=...   Normalize and complete an album folder"
	@echo "  fetch-covers ROOT=...  Fetch missing cover.jpg under ROOT"
	@echo "  fix-track FILE=... TARGET=...  Organize a single loose track"
	@echo "  compare OLD=... NEW=... [MODE=albums|artists] [THRESHOLD=90] Compare two libraries"
	@echo "  backfill-subs SRC_DIR=... DST_DIR=... [INPLACE=yes]  Mux English soft subs from MKV into existing MP4"

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
	@TITLE="$(TITLE)" YEAR="$(YEAR)" bin/rip_video.sh $(TYPE)

rip-movie:
	@if [ -z "$(TYPE)" ] || [ -z "$(TITLE)" ] || [ -z "$(YEAR)" ]; then \
	  echo "Usage: make rip-movie TYPE=dvd|bluray TITLE=\"Movie Name\" YEAR=1999" >&2; exit 1; \
	fi
	@chmod +x bin/rip_video.sh || true
	@TITLE="$(TITLE)" YEAR="$(YEAR)" bin/rip_video.sh $(TYPE)

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

backfill-subs:
	@if [ -z "$(SRC_DIR)" ] || [ -z "$(DST_DIR)" ]; then \
	  echo "Usage: make backfill-subs SRC_DIR=\"/path/to/source_mkv_dir\" DST_DIR=\"/path/to/target_mp4_dir\" [INPLACE=yes]" >&2; exit 1; \
	fi
	@chmod +x bin/backfill_subs.sh || true
	@INPLACE="$(INPLACE)" bin/backfill_subs.sh "$(SRC_DIR)" "$(DST_DIR)"
