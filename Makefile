# Common tasks for the digital library project

SHELL := /bin/sh

# Load .env if present and export variables (centralized config)
ifneq (,$(wildcard .env))
include .env
export $(shell sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .env)
endif

.PHONY: help install-deps install-video-deps rip-cd rip-video rip-movie fix-album fetch-covers fix-track compare backfill-subs vobsub-to-srt test test-unit test-integration test-all

help:
	@echo "Available targets:"
	@echo "  install-deps        Install Homebrew deps and Python packages"
	@echo "  install-video-deps  Install HandBrakeCLI, ffmpeg/ffprobe, jq, sub2srt, tesseract, mkvtoolnix; link makemkvcon"
	@echo "  rip-cd              Rip an audio CD using abcde"
	@echo "  rip-video [TYPE=...]  Rip a video disc (TYPE=dvd|bluray; auto-detect if omitted) using bin/video/rip_video.py"
	@echo "  rip-movie [TYPE=...] TITLE=... YEAR=...  Rip and organize a movie into Movies/Title (Year)/Title (Year).mp4 (auto-detect if TYPE omitted)"
	@echo "  fix-album DIR=...   Normalize and complete an album folder"
	@echo "  fetch-covers ROOT=...  Fetch missing cover.jpg under ROOT"
	@echo "  fix-track FILE=... TARGET=...  Organize a single loose track"
	@echo "  compare OLD=... NEW=... [MODE=albums|artists] [THRESHOLD=90] Compare two libraries"
	@echo "  backfill-subs SRC_DIR=... DST_DIR=... [INPLACE=yes]  Mux English soft subs from MKV into existing MP4"
	@echo "  vobsub-to-srt FILE=...  Convert VobSub (.idx) to placeholder SRT for muxing"
	@echo "  set-explicit PATH=... VALUE=... [--album]  Set EXPLICIT tag for FLAC files"
	@echo "  clean-playlists [ROOT=...] [--replace]  Clean and normalize M3U playlists"
	@echo "  test                Run all tests"
	@echo "  test-unit           Run unit tests only"
	@echo "  test-integration    Run integration tests only"
	@echo "  install-test-deps  Install test dependencies"

install-deps:
	@echo "Installing Homebrew deps via _install/install_setup_abcde_environment.sh..."
	@bash _install/install_setup_abcde_environment.sh
	@echo "Installing Python deps from requirements.txt..."
	@python3 -m pip install -r requirements.txt

install-video-deps:
	@echo "Installing video tools via Homebrew... (installing individually to avoid aborts)"
	@for p in handbrake ffmpeg jq tesseract mkvtoolnix; do \
		if ! brew list $$p >/dev/null 2>&1; then \
		  echo "brew install $$p"; brew install $$p || true; \
		else \
		  echo "Already installed: $$p"; \
		fi; \
	  done
	@echo "Attempting to link makemkvcon if MakeMKV is installed..."
	@([ -x /Applications/MakeMKV.app/Contents/MacOS/makemkvcon ] && \
		sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/makemkvcon /usr/local/bin/makemkvcon && \
		echo "Linked makemkvcon to /usr/local/bin/makemkvcon") || \
		echo "Note: Install MakeMKV from https://www.makemkv.com/download/ then rerun this target to link makemkvcon."
	@echo "If 'mkvmerge' is still not found, ensure Homebrew bin is in PATH (e.g., export PATH=\"$$(brew --prefix)/bin:$$PATH\")."
	@echo ""
	@echo "For OCR of image-based subtitles (VobSub/PGS), consider:"
	@echo "  - Subtitle Edit (GUI): https://www.nikse.dk/subtitleedit (recommended)"
	@echo "  - vobsub2srt: brew install vobsub2srt (if available)"
	@echo "  - Use the vobsub-to-srt helper for placeholder SRT creation"

rip-cd:
	@echo "Ripping CD with abcde... (ensure ~/.abcde.conf is configured)"
	@abcde

rip-video:
	@TITLE="$(TITLE)" YEAR="$(YEAR)" python3 bin/video/rip_video.py $(if $(TYPE),$(TYPE),auto)

rip-movie:
	@if [ -z "$(TITLE)" ] || [ -z "$(YEAR)" ]; then \
	  echo "Usage: make rip-movie [TYPE=dvd|bluray] TITLE=\"Movie Name\" YEAR=1999" >&2; exit 1; \
	fi
	@TITLE="$(TITLE)" YEAR="$(YEAR)" python3 bin/video/rip_video.py $(if $(TYPE),$(TYPE),auto)

fix-album:
	@if [ -z "$(DIR)" ]; then echo "Usage: make fix-album DIR=\"/path/to/Artist/Album\"" >&2; exit 1; fi
	@python3 bin/music/fix_album.py "$(DIR)"

fetch-covers:
	@if [ -z "$(ROOT)" ]; then echo "Usage: make fetch-covers ROOT=\"/path/or/library/root\"" >&2; exit 1; fi
	@python3 bin/music/fix_album_covers.py "$(ROOT)"

fix-track:
	@if [ -z "$(FILE)" ] || [ -z "$(TARGET)" ]; then echo "Usage: make fix-track FILE=\"/path/to/file.ext\" TARGET=\"/Volumes/Data/Media/Library/Music\"" >&2; exit 1; fi
	@python3 bin/music/fix_track.py "$(FILE)" --target "$(TARGET)"

compare:
	@if [ -z "$(OLD)" ] || [ -z "$(NEW)" ]; then echo "Usage: make compare OLD=\"/old/library\" NEW=\"/new/library\" [MODE=albums|artists] [THRESHOLD=90]" >&2; exit 1; fi
	@python3 bin/sync/compare_music.py $(OLD) $(NEW) $(if $(MODE),--$(MODE),) $(if $(THRESHOLD),--threshold $(THRESHOLD),)

backfill-subs:
	@if [ -z "$(SRC_DIR)" ] || [ -z "$(DST_DIR)" ]; then \
	  echo "Usage: make backfill-subs SRC_DIR=\"/path/to/source_mkv_dir\" DST_DIR=\"/path/to/target_mp4_dir\" [INPLACE=yes]" >&2; exit 1; \
	fi
	@python3 bin/video/backfill_subs.py "$(SRC_DIR)" "$(DST_DIR)" $(if $(INPLACE),--inplace,)

vobsub-to-srt:
	@if [ -z "$(FILE)" ]; then \
	  echo "Usage: make vobsub-to-srt FILE=\"/path/to/subtitle.idx\"" >&2; \
	  echo "Example: make vobsub-to-srt FILE=\".backfill_ocr_12345.idx\"" >&2; \
	  echo "Creates a placeholder SRT file for muxing. Use Subtitle Edit for full OCR." >&2; \
	  exit 1; \
	fi
	@python3 bin/video/vobsub_to_srt.py "$(FILE)"

set-explicit:
	@if [ -z "$(PATH)" ] || [ -z "$(VALUE)" ]; then \
	  echo "Usage: make set-explicit PATH=\"/path/to/file.or.album\" VALUE=\"Yes|No|Unknown\" [--album]" >&2; exit 1; \
	fi
	@python3 bin/metadata/set_explicit.py "$(PATH)" "$(VALUE)" $(if $(ALBUM),--album,)

clean-playlists:
	@python3 bin/utils/clean_playlists.py "$(ROOT)" $(if $(REPLACE),--replace,)

install-test-deps:
	@echo "Installing test dependencies..."
	@python3 -m pip install -r requirements-test.txt

test:
	@echo "Running all tests..."
	@python3 run_tests.py

test-unit:
	@echo "Running unit tests..."
	@python3 -m pytest tests/ -m unit -v

test-integration:
	@echo "Running integration tests..."
	@python3 -m pytest tests/ -m integration -v

test-coverage:
	@echo "Running tests with coverage..."
	@python3 -m pytest tests/ --cov=bin --cov-report=term-missing --cov-report=html --cov-fail-under=70
