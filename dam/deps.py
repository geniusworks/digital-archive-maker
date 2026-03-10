"""Dependency checker and guided installer.

Checks for required system tools (Homebrew packages, apps) and Python
packages, reports what's missing, and offers to install them.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from dam.console import console, error, heading, info, kv, status_table, success, warning


class DepKind(str, Enum):
    BREW = "brew"
    CASK = "cask"
    APP = "app"          # macOS .app bundle (manual install)
    PYTHON = "python"    # pip package
    LINK = "link"        # symlink from an app bundle into PATH


@dataclass
class Dependency:
    """A single external dependency."""

    name: str
    kind: DepKind
    description: str = ""
    install_hint: str = ""
    check_cmd: Optional[str] = None  # shell command whose exit-0 means present
    brew_name: Optional[str] = None  # override for `brew install <name>`
    app_path: Optional[str] = None   # e.g. /Applications/MakeMKV.app
    url: Optional[str] = None        # download URL for manual installs
    required_for: list[str] = field(default_factory=list)  # e.g. ["music", "video"]
    optional: bool = False

    def is_installed(self) -> bool:
        """Return True if this dependency is available."""
        if self.check_cmd:
            try:
                subprocess.run(
                    self.check_cmd,
                    shell=True,
                    capture_output=True,
                    timeout=10,
                )
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                return False

        if self.kind == DepKind.APP and self.app_path:
            return Path(self.app_path).exists()

        if self.kind in (DepKind.BREW, DepKind.CASK):
            return shutil.which(self.brew_name or self.name) is not None

        if self.kind == DepKind.PYTHON:
            try:
                __import__(self.name)
                return True
            except ImportError:
                return False

        if self.kind == DepKind.LINK:
            return shutil.which(self.name) is not None

        return False


# ---------------------------------------------------------------------------
# Dependency registry
# ---------------------------------------------------------------------------

CORE_DEPS: list[Dependency] = [
    # Homebrew CLI tools — audio pipeline
    Dependency(
        name="abcde",
        kind=DepKind.BREW,
        description="CD ripper with MusicBrainz lookup",
        check_cmd="which abcde",
        required_for=["music"],
    ),
    Dependency(
        name="flac",
        kind=DepKind.BREW,
        description="FLAC encoder/decoder",
        check_cmd="which flac",
        required_for=["music"],
    ),
    Dependency(
        name="imagemagick",
        kind=DepKind.BREW,
        description="Image processing for cover art",
        check_cmd="which convert",
        required_for=["music"],
    ),
    # Homebrew CLI tools — video pipeline
    Dependency(
        name="HandBrakeCLI",
        kind=DepKind.BREW,
        brew_name="handbrake",
        description="Video transcoder",
        check_cmd="which HandBrakeCLI",
        required_for=["video"],
    ),
    Dependency(
        name="ffmpeg",
        kind=DepKind.BREW,
        description="Media toolkit (also provides ffprobe)",
        check_cmd="which ffmpeg",
        required_for=["video", "music"],
    ),
    Dependency(
        name="jq",
        kind=DepKind.BREW,
        description="JSON processor",
        check_cmd="which jq",
        required_for=["video"],
    ),
    Dependency(
        name="tesseract",
        kind=DepKind.BREW,
        description="OCR for image-based subtitles",
        check_cmd="which tesseract",
        required_for=["video"],
        optional=True,
    ),
    Dependency(
        name="mkvtoolnix",
        kind=DepKind.BREW,
        description="MKV muxing tools (mkvmerge, mkvextract)",
        check_cmd="which mkvmerge",
        required_for=["video"],
    ),
    Dependency(
        name="ccextractor",
        kind=DepKind.BREW,
        description="Closed-caption extraction",
        check_cmd="which ccextractor",
        required_for=["video"],
        optional=True,
    ),
    Dependency(
        name="libdvdcss",
        kind=DepKind.BREW,
        description="DVD decryption library",
        check_cmd="brew list libdvdcss >/dev/null 2>&1",
        required_for=["video"],
        optional=True,
    ),
    # macOS application — manual install
    Dependency(
        name="MakeMKV",
        kind=DepKind.APP,
        description="Disc ripper (DVD/Blu-ray → MKV)",
        app_path="/Applications/MakeMKV.app",
        url="https://www.makemkv.com/download/",
        install_hint="Download from https://www.makemkv.com/download/ and drag to Applications",
        required_for=["video"],
    ),
    # Symlink from MakeMKV bundle
    Dependency(
        name="makemkvcon",
        kind=DepKind.LINK,
        description="MakeMKV CLI (linked from app bundle)",
        check_cmd="which makemkvcon",
        install_hint="Run: sudo ln -sf /Applications/MakeMKV.app/Contents/MacOS/makemkvcon /usr/local/bin/makemkvcon",
        required_for=["video"],
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_all(
    scope: Optional[str] = None,
    verbose: bool = False,
) -> tuple[list[Dependency], list[Dependency]]:
    """Check all dependencies. Returns (installed, missing).

    Args:
        scope: Limit to "music", "video", or None for all.
        verbose: Print status while checking.
    """
    deps = CORE_DEPS
    if scope:
        deps = [d for d in deps if scope in d.required_for]

    installed: list[Dependency] = []
    missing: list[Dependency] = []

    if verbose:
        heading("Checking system dependencies")

    for dep in deps:
        ok = dep.is_installed()
        if ok:
            installed.append(dep)
        else:
            missing.append(dep)

    if verbose:
        rows = []
        for dep in deps:
            is_ok = dep in installed
            status = "✅" if is_ok else ("⚠️" if dep.optional else "❌")
            detail = dep.description
            if not is_ok and dep.optional:
                detail += " (optional)"
            rows.append((dep.name, status, detail))
        status_table(rows)

    return installed, missing


def install_missing(
    missing: list[Dependency],
    dry_run: bool = False,
) -> tuple[int, int]:
    """Attempt to install missing Homebrew dependencies.

    Returns (installed_count, skipped_count).
    Manual-install deps (apps) are printed as instructions.
    """
    brew_deps = [d for d in missing if d.kind in (DepKind.BREW, DepKind.CASK)]
    manual_deps = [d for d in missing if d.kind in (DepKind.APP, DepKind.LINK)]

    installed_count = 0
    skipped_count = 0

    if brew_deps:
        heading("Installing via Homebrew")
        for dep in brew_deps:
            pkg = dep.brew_name or dep.name
            opt_label = " (optional)" if dep.optional else ""
            if dry_run:
                info(f"Would install: brew install {pkg}{opt_label}")
                installed_count += 1
                continue
            try:
                info(f"Installing {pkg}{opt_label}...")
                subprocess.run(
                    ["brew", "install", pkg],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                success(f"Installed {pkg}")
                installed_count += 1
            except subprocess.CalledProcessError as exc:
                warning(f"Failed to install {pkg}: {exc.stderr.strip()}")
                skipped_count += 1

    if manual_deps:
        heading("Manual installation required")
        for dep in manual_deps:
            hint = dep.install_hint or dep.url or "See project documentation"
            console.print(f"  [key]{dep.name}[/]: {hint}")
            skipped_count += 1

    return installed_count, skipped_count


def check_python_deps() -> list[str]:
    """Return list of missing Python packages from requirements.txt."""
    from dam.config import REPO_ROOT

    req_file = REPO_ROOT / "requirements.txt"
    if not req_file.exists():
        return []

    missing = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Extract package name (before any version specifier)
        pkg = line.split(">=")[0].split("==")[0].split("<")[0].split("[")[0].strip()
        # Map common PyPI names → import names
        import_map = {
            "python-dotenv": "dotenv",
            "pyyaml": "yaml",
            "pyacoustid": "acoustid",
            "rapidfuzz": "rapidfuzz",
            "pillow": "PIL",
            "lyricsgenius": "lyricsgenius",
        }
        import_name = import_map.get(pkg.lower(), pkg.lower().replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    return missing


def ensure_venv() -> bool:
    """Check whether we're running inside the project venv."""
    venv_marker = sys.prefix != sys.base_prefix
    return venv_marker
