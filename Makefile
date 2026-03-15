# Common tasks for Digital Archive Maker

SHELL := /bin/sh

# Load .env if present and export variables (centralized config)
ifneq (,$(wildcard .env))
include .env
export $(shell sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .env)
endif

.PHONY: help install-deps install-video-deps rip-cd rip-video rip-movie rip-movie-all optimize-mp4 fix-album fetch-covers fix-track compare backfill-subs vobsub-to-srt test test-unit test-integration test-all test-pipeline

help:
	@echo "Available targets:"
	@echo "  install-deps        Install Homebrew deps and Python packages"
	@echo "  install-video-deps  Install HandBrakeCLI, ffmpeg/ffprobe, jq, tesseract, mkvtoolnix, ccextractor, libdvdcss; link makemkvcon"
	@echo "  rip-cd              Rip an audio CD using abcde"
	@echo "  rip-video [TYPE=...]  Rip a video disc (TYPE=dvd|bluray; auto-detect if omitted) using bin/video/rip_video.py"
	@echo "  rip-movie [TYPE=...] TITLE=... YEAR=...  Rip and organize a movie into Movies/Title (Year)/Title (Year).mp4 (auto-detect if TYPE omitted)"
	@echo "  rip-movie-all [TYPE=...] TITLE=... YEAR=...  Same as rip-movie but processes ALL tracks (not just main feature)"
	@echo "  optimize-mp4 DIR=...  Optimize existing MP4 files for streaming (Jellyfin/Plex)"
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
	@echo "  test-coverage       Run tests with coverage report"
	@echo "  test-pipeline       Run local CI pipeline test (mirrors GitHub Actions)"
	@echo "  install-test-deps  Install test dependencies"

install-deps:
	@echo ""
	@./venv/bin/python scripts/show_banner.py
	@echo ""
	@echo "Installing tools..."
	@if command -v brew >/dev/null 2>&1; then \
		brew bundle --quiet; \
	else \
		echo "Homebrew not found. Installing..." && \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
		brew bundle --quiet; \
	fi
	@echo "Installing GUI npm packages..."
	@cd gui && npm install --silent
	@echo "✓ GUI dependencies installed (including Electron)"
	@echo "Installing Python deps from requirements.txt..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Configuring virtual environment for modern Python (PEP 668 compatibility)..."
	@echo "[global]" > venv/pip.conf
	@echo "break-system-packages = true" >> venv/pip.conf
	@echo "Activating virtual environment and installing packages..."
	@printf "  → Upgrading pip... " && \
	./venv/bin/python -m pip install --upgrade pip --quiet && \
	echo "✓" && \
	printf "  → Installing requirements... " && \
	./venv/bin/python -m pip install -r requirements.txt --quiet && \
	echo "✓" && \
	printf "  → Installing digital-archive-maker... " && \
	./venv/bin/python -m pip install -e . --quiet && \
	echo "✓" && \
	echo "" && \
	echo "Virtual environment ready. Activate with: source venv/bin/activate" && \
	echo "Package installed as 'dam' command. Running setup check..." && \
	echo "" && \
	./venv/bin/python -m dam.cli check

install-video-deps:
	@echo "Installing video tools via Homebrew... (installing individually to avoid aborts)"
	@for p in handbrake ffmpeg jq tesseract mkvtoolnix ccextractor libdvdcss; do \
		if ! brew list $$p >/dev/null 2>&1; then \
		  echo "brew install $$p"; brew install $$p || true; \
		else \
		  echo "Already installed: $$p"; \
		fi; \
	  done
	@echo "Fixing HandBrakeCLI dependencies..."
	@brew reinstall libvpx handbrake || echo "HandBrake dependency fix completed"
	@echo "Attempting to link makemkvcon if MakeMKV is installed..."
	@([ -x /Applications/MakeMKV.app/Contents/MacOS/makemkvcon ] && \
		sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/makemkvcon /usr/local/bin/makemkvcon && \
		echo "Linked makemkvcon to /usr/local/bin/makemkvcon") || \
		echo "Note: Install MakeMKV from https://www.makemkv.com/download/ then rerun this target to link makemkvcon."
	@echo "Linking MakeMKV mmgplsrv service..."
	@([ -x /Applications/MakeMKV.app/Contents/MacOS/mmgplsrv ] && \
		sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/mmgplsrv /usr/local/bin/mmgplsrv && \
		echo "Linked mmgplsrv to /usr/local/bin/mmgplsrv") || \
		echo "Note: mmgplsrv not found, MakeMKV may not be properly installed."
	@echo "Creating MakeMKV ccextractor symlink..."
	@([ -x /opt/homebrew/bin/ccextractor ] && \
		sudo ln -sf /opt/homebrew/bin/ccextractor /usr/local/bin/mmccextr && \
		echo "Linked ccextractor to /usr/local/bin/mmccextr for MakeMKV") || \
		echo "Note: ccextractor not found, install with: brew install ccextractor"
	@echo "If 'mkvmerge' is still not found, ensure Homebrew bin is in PATH (e.g., export PATH=\"$$(brew --prefix)/bin:$$PATH\")."
	@echo ""
	@echo "For OCR of image-based subtitles (VobSub/PGS), consider:"
	@echo "  - Subtitle Edit (GUI): https://www.nikse.dk/subtitleedit (recommended)"
	@echo "  - vobsub2srt: brew install vobsub2srt (if available)"
	@echo "  - Use the vobsub-to-srt helper for placeholder SRT creation"

rip-cd:
	@echo "Ripping CD with abcde..."
	@abcde

rip-video:
	@TITLE="$(TITLE)" YEAR="$(YEAR)" ./venv/bin/python bin/video/rip_video.py $(if $(TYPE),$(TYPE),auto)

rip-movie:
	@if [ -z "$(TITLE)" ] || [ -z "$(YEAR)" ]; then \
	  echo "Usage: make rip-movie [TYPE=dvd|bluray] TITLE=\"Movie Name\" YEAR=1999 [TITLE_INDEX=0]" >&2; exit 1; \
	fi
	@TITLE="$(TITLE)" YEAR="$(YEAR)" ./venv/bin/python bin/video/rip_video.py $(if $(TITLE_INDEX),--title-index $(TITLE_INDEX),) $(if $(TYPE),$(TYPE),auto)

rip-movie-all:
	@if [ -z "$(TITLE)" ] || [ -z "$(YEAR)" ]; then \
	  echo "Usage: make rip-movie-all [TYPE=dvd|bluray] TITLE=\"Movie Name\" YEAR=1999" >&2; exit 1; \
	fi
	@TITLE="$(TITLE)" YEAR="$(YEAR)" ./venv/bin/python bin/video/rip_video.py --force-all-tracks $(if $(TYPE),$(TYPE),auto)

optimize-mp4:
	@if [ -z "$(DIR)" ]; then echo "Usage: make optimize-mp4 DIR=\"/path/to/movies\"" >&2; exit 1; fi
	@python3 bin/video/optimize_mp4_streaming.py "$(DIR)"

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
	@python3 bin/music/compare_music.py $(OLD) $(NEW) $(if $(MODE),--$(MODE),) $(if $(THRESHOLD),--threshold $(THRESHOLD),)

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
	@python3 bin/music/set_explicit.py "$(PATH)" "$(VALUE)" $(if $(ALBUM),--album,)

clean-playlists:
	@python3 bin/utils/clean_playlists.py "$(ROOT)" $(if $(REPLACE),--replace,)

install-test-deps:
	@echo "Installing test dependencies..."
	@./venv/bin/python -m pip install -r requirements-test.txt

uninstall:
	@echo "Removing Digital Archive Maker..."
	@if [ -d "venv" ]; then \
		echo "  • Uninstalling Python package..."; \
		./venv/bin/pip uninstall -y digital-archive-maker 2>/dev/null || true; \
		echo "  • Removing virtual environment..."; \
		rm -rf venv; \
		echo "✓ Uninstall complete"; \
		echo ""; \
		echo "Optional cleanup:"; \
		echo "  • Remove Homebrew packages: brew uninstall handbrake ffmpeg jq tesseract mkvtoolnix ccextractor libdvdcss"; \
		echo "  • Remove cache directory: rm -rf cache/"; \
		echo "  • Remove log directory: rm -rf log/"; \
		echo "  • Keep your .env file and media library"; \
	else \
		echo "  • No virtual environment found"; \
		echo "  • Nothing to uninstall"; \
	fi

test:
	@echo ""
	@echo "Running all tests..."
	@./venv/bin/python scripts/run_tests.py

test-unit:
	@echo "Running unit tests..."
	@./venv/bin/python -m pytest tests/ -m unit -v

test-integration:
	@echo "Running integration tests..."
	@./venv/bin/python -m pytest tests/ -m integration -v

test-coverage:
	@echo "Running tests with coverage..."
	@./venv/bin/python -m pytest tests/ --cov=bin --cov-report=term-missing --cov-report=html --cov-fail-under=25

test-pipeline:
	@echo "Running local pipeline test (mirrors GitHub Actions CI)..."
	@./scripts/test-pipeline.sh
