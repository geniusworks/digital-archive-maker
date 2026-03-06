"""Centralised configuration loader.

Reads settings from (in priority order):
1. Environment variables
2. .env file in the repo root
3. Built-in defaults

Other modules import ``cfg`` and call ``cfg.get(key)`` or ``cfg.library_root``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains pyproject.toml)."""
    candidate = Path(__file__).resolve().parent.parent
    while candidate != candidate.parent:
        if (candidate / "pyproject.toml").exists():
            return candidate
        candidate = candidate.parent
    # Fallback: assume parent of dam/
    return Path(__file__).resolve().parent.parent


REPO_ROOT: Path = _find_repo_root()

# Default values — overridden by .env / env vars
_DEFAULTS: dict[str, str] = {
    "LIBRARY_ROOT": "/Volumes/Data/Media/Library",
    "LANG_AUDIO": "en",
    "LANG_SUBTITLES": "en",
}

# Keys that represent optional API credentials
API_KEYS: list[str] = [
    "ACOUSTID_API_KEY",
    "GENIUS_API_TOKEN",
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "TMDB_API_KEY",
    "OMDB_API_KEY",
]


def _load_dotenv() -> None:
    """Load .env without requiring python-dotenv at import time."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        # Minimal fallback parser
        with open(env_path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    os.environ.setdefault(key, value)


_load_dotenv()


def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return a config value from env → .env → built-in defaults."""
    return os.environ.get(key, _DEFAULTS.get(key, default))


@property
def library_root() -> Path:
    """Resolved library root path."""
    return Path(get("LIBRARY_ROOT", _DEFAULTS["LIBRARY_ROOT"]))


def env_file_exists() -> bool:
    return (REPO_ROOT / ".env").exists()


def get_api_key(name: str) -> Optional[str]:
    """Return an API key value, or None if not set / placeholder."""
    val = get(name)
    if not val:
        return None
    # Treat obvious placeholders as unset
    placeholders = {"your_", "changeme", "xxx", "TODO", "REPLACE"}
    if any(val.lower().startswith(p.lower()) for p in placeholders):
        return None
    return val


def missing_api_keys() -> list[str]:
    """Return names of API keys that are not configured."""
    return [k for k in API_KEYS if get_api_key(k) is None]
