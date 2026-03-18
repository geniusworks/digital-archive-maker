"""Interactive API key onboarding and validation.

When a script hits a code path that needs an API key, it calls
``require_key("TMDB_API_KEY")`` which will:
1. Return the key if already configured.
2. Prompt the user to enter it interactively (with signup URL).
3. Optionally persist it to .env so they're only asked once.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from dam.console import console, info, success, warning

# Human-friendly metadata for each key
_KEY_INFO: dict[str, dict[str, str]] = {
    "ACOUSTID_API_KEY": {
        "service": "AcoustID",
        "purpose": "audio fingerprint lookups",
        "signup_url": "https://acoustid.org/api-key",
        "free": "yes",
    },
    "GENIUS_API_TOKEN": {
        "service": "Genius",
        "purpose": "song lyrics downloads",
        "signup_url": "https://genius.com/api-clients",
        "free": "yes",
    },
    "SPOTIFY_CLIENT_ID": {
        "service": "Spotify",
        "purpose": "explicit content detection & metadata",
        "signup_url": "https://developer.spotify.com/dashboard",
        "free": "yes",
    },
    "SPOTIFY_CLIENT_SECRET": {
        "service": "Spotify",
        "purpose": "explicit content detection & metadata",
        "signup_url": "https://developer.spotify.com/dashboard",
        "free": "yes",
    },
    "TMDB_API_KEY": {
        "service": "TMDb",
        "purpose": "movie & TV metadata, posters, descriptions",
        "signup_url": "https://www.themoviedb.org/settings/api",
        "free": "yes",
    },
    "OMDB_API_KEY": {
        "service": "OMDb",
        "purpose": "movie ratings (MPAA, IMDB scores)",
        "signup_url": "https://www.omdbapi.com/apikey.aspx",
        "free": "yes (1,000 requests/day)",
    },
}


def require_key(
    key_name: str,
    *,
    prompt: bool = True,
    persist: bool = True,
) -> Optional[str]:
    """Return the API key value, prompting the user if missing.

    Args:
        key_name: Environment variable name (e.g. "TMDB_API_KEY").
        prompt: If True and key is missing, ask the user interactively.
        persist: If True and the user provides a key, save it to .env.

    Returns:
        The key string, or None if the user declines to provide one.
    """
    from dam.config import get_api_key, REPO_ROOT

    # Already configured?
    existing = get_api_key(key_name)
    if existing:
        return existing

    if not prompt:
        return None

    # Get human-friendly info
    meta = _KEY_INFO.get(key_name, {})
    service = meta.get("service", key_name)
    purpose = meta.get("purpose", "enhanced functionality")
    signup_url = meta.get("signup_url", "")
    free = meta.get("free", "unknown")

    console.print()
    console.print(f"[heading]🔑 API key needed: {service}[/]")
    console.print(f"   [muted]Used for:[/] {purpose}")
    if signup_url:
        console.print(f"   [muted]Get a free key at:[/] [link={signup_url}]{signup_url}[/]")
    if free:
        console.print(f"   [muted]Free?[/] {free}")
    console.print()

    value = console.input(
        f"  Paste your [key]{key_name}[/] here (or press Enter to skip): "
    ).strip()

    if not value:
        warning(f"Skipping {service} — features that need it will be unavailable.")
        return None

    # Basic sanity check
    if len(value) < 8:
        warning(
            "That looks too short for an API key. Saving anyway — you can fix it in .env later."
        )

    # Set in current process
    os.environ[key_name] = value

    # Persist to .env
    if persist:
        _save_key_to_env(key_name, value, REPO_ROOT / ".env")

    success(f"{service} key saved.")
    return value


def onboard_keys(scope: Optional[str] = None) -> None:
    """Walk the user through all missing API keys for a given scope.

    Args:
        scope: Optional scope ('music' or 'video') to limit which keys are prompted.

    Prompts for all missing keys in the given scope, or all keys if no scope.
    """
    from dam.console import heading
    from dam.config import missing_api_keys

    scope_keys: dict[str, list[str]] = {
        "music": [
            "ACOUSTID_API_KEY",
            "GENIUS_API_TOKEN",
            "SPOTIFY_CLIENT_ID",
            "SPOTIFY_CLIENT_SECRET",
        ],
        "video": [
            "TMDB_API_KEY",
            "OMDB_API_KEY",
        ],
    }

    if scope:
        relevant = scope_keys.get(scope, [])
    else:
        relevant = list(_KEY_INFO.keys())

    missing = [k for k in relevant if k in missing_api_keys()]

    console.print()
    if not missing:
        info("All API keys for this workflow are already configured.")
        update = console.input("  Update an existing key? (y/N): ").strip().lower()
        if update not in ("y", "yes"):
            return
        # Show existing values and prompt for updates
        from dam.config import get
        console.print()
        heading("Update API Keys")
        console.print()
        console.print("  Press Enter to keep existing value, or enter new key to update.")
        for key_name in relevant:
            current_value = get(key_name, "")
            if current_value:
                # Mask API keys for security
                masked = current_value[:4] + "*" * (len(current_value) - 8) + current_value[-4:] if len(current_value) > 8 else "*" * len(current_value)
                console.print(f"\n  {key_name}: {masked}")
                new_value = console.input(f"  New value (or press Enter to keep): ").strip()
                if new_value and new_value != current_value:
                    from dam.config import REPO_ROOT
                    env_path = REPO_ROOT / ".env"
                    _save_key_to_env(key_name, new_value, env_path)
                    success(f"Updated {key_name}")
                else:
                    info(f"Kept existing {key_name}")
            else:
                # This shouldn't happen if we're in the "all configured" branch, but handle it
                require_key(key_name, prompt=True, persist=True)
        return

    console.print(
        f"[heading]API Key Setup[/] — {len(missing)} key{'s' if len(missing) != 1 else ''} "
        f"not yet configured."
    )
    console.print("[muted]These are optional but recommended for the best results.[/]")

    for key_name in missing:
        require_key(key_name, prompt=True, persist=True)


def _save_key_to_env(key_name: str, value: str, env_path: Path) -> None:
    """Append or update a key in the .env file."""
    if not env_path.exists():
        # Create from sample if available
        sample = env_path.parent / ".env.example"
        if sample.exists():
            import shutil

            shutil.copy2(sample, env_path)
            info("Created .env from .env.example")
        else:
            env_path.touch()

    content = env_path.read_text()

    # Check if key already exists (possibly commented or placeholder)
    pattern = re.compile(rf"^{re.escape(key_name)}\s*=.*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f'{key_name}="{value}"', content)
    else:
        # Append
        if not content.endswith("\n"):
            content += "\n"
        content += f'{key_name}="{value}"\n'

    env_path.write_text(content)
