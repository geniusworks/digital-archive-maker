# Copyright (c) 2026 Martin Diekhoff
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unified CLI for Digital Archive Maker.

Usage:
    dam check          Check system dependencies and API keys
    dam config         Interactive first-run configuration wizard
    dam rip cd         Rip an audio CD to FLAC
    dam rip video      Rip a DVD or Blu-ray to MP4
    dam tag <cmd>      Tag media (explicit, genres, lyrics, metadata)
    dam sync           Sync library to media server
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.prompt import Confirm

from dam import __version__
from dam.config import REPO_ROOT, env_file_exists, get, missing_api_keys
from dam.console import banner, console, error, heading, info, kv, success, warning
from dam.deps import check_all, check_python_deps, ensure_venv, install_missing
from dam.keys import onboard_keys

app = typer.Typer(
    name="dam",
    help="Digital Archive Maker — physical media to digital library automation.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ── Subcommand groups ──────────────────────────────────────────────────────

rip_app = typer.Typer(help="Rip physical media to digital files.")
app.add_typer(rip_app, name="rip")

tag_app = typer.Typer(help="Tag and enrich media metadata.")
app.add_typer(tag_app, name="tag")


# ── dam check ──────────────────────────────────────────────────────────────


@app.command()
def check(
    scope: Optional[str] = typer.Argument(
        None,
        help="Limit check to 'music' or 'video' scope.",
    ),
    install: bool = typer.Option(False, "--install", "-i", help="Install missing Homebrew deps."),
):
    """Check that all required tools, Python packages, and API keys are present."""
    banner()

    # System deps
    installed, missing = check_all(scope=scope, verbose=True)

    # Python deps
    heading("Python packages")
    py_missing = check_python_deps()
    if py_missing:
        warning(f"Missing Python packages: {', '.join(py_missing)}")
        info("Run: pip install -r requirements.txt")
    else:
        success("All Python packages installed.")

    # Virtual env
    heading("Environment")
    if ensure_venv():
        success("Running inside a virtual environment.")
    else:
        warning("Not running in a virtual environment. Run: source venv/bin/activate")

    if env_file_exists():
        success(".env file found.")
    else:
        warning(".env not found. Run: cp .env.sample .env")

    # Summary - After dependency checks are complete
    console.print()
    required_missing = [d for d in missing if not d.optional]
    if not required_missing and not py_missing:
        console.print("[success]All required dependencies are satisfied![/]")

    # API keys
    heading("API keys (highly recommended)")
    api_missing = missing_api_keys()
    all_api_keys = ["ACOUSTID_API_KEY", "GENIUS_API_TOKEN", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "TMDB_API_KEY", "OMDB_API_KEY"]
    
    for k in all_api_keys:
        if k in api_missing:
            console.print(f" ⚠️ {k} (not configured yet)")
        else:
            console.print(f" ✅ {k}")
    
    if not api_missing:
        success("All API keys configured.")
    
    # Next steps - After all checks are complete
    console.print()
    if not required_missing and not py_missing:
        console.print("💡 Next steps:")
        console.print("   • Activate virtual environment: 'source venv/bin/activate'")
        console.print("   • Run 'dam config' to set up API keys interactively")
        console.print("   • CLI: Use 'dam' commands for media processing (try 'dam --help')")
        console.print("   • GUI: Run 'cd gui && npm start' for desktop app")
        console.print()
    else:
        total = len(required_missing) + len(py_missing)
        console.print(f"[warning]{total} required item(s) missing.[/]")
        console.print()

    # Offer to install
    if install and missing:
        console.print()
        n_installed, n_skipped = install_missing(missing)
        if n_installed:
            success(f"Installed {n_installed} package(s).")
        if n_skipped:
            info(f"{n_skipped} item(s) need manual installation (see above).")
        console.print()


# ── dam config ─────────────────────────────────────────────────────────────


@app.command()
def config(
    scope: Optional[str] = typer.Argument(
        None,
        help="Limit to 'music' or 'video' scope.",
    ),
):
    """Interactive first-run configuration wizard.

    Creates .env if needed, sets LIBRARY_ROOT, and walks through API key setup.
    """
    banner()
    heading("Configuration wizard")

    # .env file
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        sample = REPO_ROOT / ".env.sample"
        if sample.exists():
            import shutil

            shutil.copy2(sample, env_path)
            success("Created .env from .env.sample")
        else:
            env_path.touch()
            success("Created empty .env")

    # Library root
    current_root = get("LIBRARY_ROOT", "/Volumes/Data/Media/Library")
    console.print(f"\n  Current library root: [key]{current_root}[/]")
    new_root = console.input(
        "  Enter new library root (or press Enter to keep current): "
    ).strip()
    if new_root and new_root != current_root:
        _update_env_value(env_path, "LIBRARY_ROOT", new_root)
        success(f"Library root set to {new_root}")
    else:
        info(f"Keeping library root: {current_root}")

    # API keys
    console.print()
    onboard_keys(scope=scope)

    console.print()
    success("Configuration complete! Run [bold]dam check[/] to verify everything.")


# ── dam rip cd ─────────────────────────────────────────────────────────────


@rip_app.command("cd")
def rip_cd():
    """Rip an audio CD to FLAC using abcde."""
    banner()
    _ensure_deps(["abcde", "flac"])
    
    # Check for abcde configuration
    import os
    import shutil
    abcde_config = os.path.expanduser("~/.abcde.conf")
    sample_config = os.path.join(os.getcwd(), ".abcde.conf.sample")
    
    if not os.path.exists(abcde_config):
        if os.path.exists(sample_config):
            info("Setting up abcde configuration...")
            
            # Read MusicBrainz setting from user's .env (default to enabled)
            from dam.config import get
            musicbrainz_setting = get("MUSICBRAINZ_LOOKUP", "true").lower()
            
            # Read sample config
            with open(sample_config, 'r') as f:
                config_content = f.read()
            
            # Set MusicBrainz based on user's .env configuration
            if musicbrainz_setting in ("true", "1", "yes"):
                # User has MusicBrainz enabled (default)
                config_content = config_content.replace("MUSICBRAINZ_LOOKUP=y", "MUSICBRAINZ_LOOKUP=y")
                success_msg = "✓ Created ~/.abcde.conf"
                info_msg = "  • MusicBrainz lookup enabled (per your MUSICBRAINZ_LOOKUP setting)"
            else:
                # User explicitly disabled MusicBrainz
                config_content = config_content.replace("MUSICBRAINZ_LOOKUP=y", "MUSICBRAINZ_LOOKUP=n")
                success_msg = "✓ Created ~/.abcde.conf"
                info_msg = "  • MusicBrainz lookup disabled (per your MUSICBRAINZ_LOOKUP setting)"
            
            # Write the customized config
            with open(abcde_config, 'w') as f:
                f.write(config_content)
            
            success(success_msg)
            info(info_msg)
            info("  • Using LIBRARY_ROOT from your .env file")
            info("  • Edit ~/.abcde.conf to customize settings")
        else:
            warning("abcde configuration sample not found:")
            warning(f"  • {sample_config}")
            warning("\nContinuing with abcde defaults...")
    
    # Check for CD and prompt user to insert if needed
    import subprocess
    import time
    
    heading("Ripping CD")
    
    # Check if any CD/DVD is inserted
    try:
        result = subprocess.run(
            r"diskutil list | grep -E 'CD_partition_scheme|CD_DA|DVD_partition_scheme|DVD_ROM' | grep -v 'Virtual'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            warning("No CD detected in drive")
            info("Please insert a CD and press ENTER to continue...")
            info("(Waiting 30 seconds for CD detection...)")
            
            # Countdown with periodic checks and ENTER detection
            import select
            import sys
            
            for i in range(30, 0, -1):
                try:
                    check_result = subprocess.run(
                        r"diskutil list | grep -E 'CD_partition_scheme|CD_DA|DVD_partition_scheme|DVD_ROM' | grep -v 'Virtual'",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if check_result.returncode == 0 and check_result.stdout.strip():
                        success(f"✓ CD detected!")
                        break
                except:
                    pass
                
                # Show countdown
                if i % 5 == 0 or i <= 5:
                    info(f"  {i} seconds remaining...")
                
                # Check for ENTER key press (wait 1 second max)
                if select.select([sys.stdin], [], [], 1)[0]:
                    sys.stdin.readline()
                    info("  Continuing anyway...")
                    break
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
            else:
                # After 30 seconds, check one more time
                final_check = subprocess.run(
                    r"diskutil list | grep -E 'CD_partition_scheme|CD_DA|DVD_partition_scheme|DVD_ROM' | grep -v 'Virtual'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if final_check.returncode != 0 or not final_check.stdout.strip():
                    error("No CD detected after 30 seconds")
                    info("Please insert a CD and try again")
                    return
        else:
            success("✓ CD detected in drive")
            
    except Exception:
        # If disk detection fails, just proceed anyway
        warning("Could not check for CD - proceeding anyway")
    
    info("Running abcde...")
    try:
        _run_script_or_make("rip-cd")
    except (SystemExit, typer.Exit) as e:
        exit_code = getattr(e, 'exit_code', getattr(e, 'code', 1))
        if exit_code == 2:  # abcde failed, likely due to MusicBrainz issues
            # MusicBrainz is mandatory - provide immediate guidance
            error("MusicBrainz compatibility issue detected")
            error("MusicBrainz is required for CD ripping")
            info("")
            info("This is a known issue with the old Audio::CD Perl module.")
            info("The module is incompatible with modern macOS/Perl versions.")
            info("")
            info("Workaround options:")
            info("  1. Use system Perl (may work better):")
            info("     /usr/bin/perl -MCPAN -e 'install Audio::CD'")
            info("  2. Try manual compilation:")
            info("     cd /tmp && cpan -g Audio::CD && cd Audio-CD-*")
            info("     perl Makefile.PL && make && make install")
            info("  3. Alternative: Use cd-paranoia directly:")
            info("     abcde can work without MusicBrainz if needed")
            info("")
            info("Note: This is a legacy compatibility issue with Perl modules.")
            info("")
            info("After fixing, run: dam rip cd")
            raise typer.Exit(code=2)
        else:
            raise


# ── dam rip video ──────────────────────────────────────────────────────────


@rip_app.command("video")
def rip_video(
    title: str = typer.Option("", "--title", "-t", help="Movie or show title."),
    year: str = typer.Option("", "--year", "-y", help="Release year."),
    disc_type: str = typer.Option(
        "auto",
        "--type",
        help="Disc type: dvd, bluray, or auto.",
    ),
    burn_subs: bool = typer.Option(False, "--burn-subs", help="Burn subtitles into video."),
):
    """Rip a DVD or Blu-ray to MP4."""
    banner()
    _ensure_deps(["makemkvcon", "HandBrakeCLI", "ffmpeg", "mkvmerge"])

    heading("Ripping video disc")
    cmd_parts = ["make"]
    if title and year:
        cmd_parts += ["rip-movie", f'TITLE="{title}"', f'YEAR={year}']
    else:
        cmd_parts.append("rip-video")

    if disc_type != "auto":
        cmd_parts.append(f"TYPE={disc_type}")

    env = {}
    if burn_subs:
        env["BURN_SUBTITLES"] = "true"

    info(f"Running: {' '.join(cmd_parts)}")
    _run_make(cmd_parts[1:], extra_env=env)


# ── dam tag <subcommands> ─────────────────────────────────────────────────


@tag_app.command("explicit")
def tag_explicit(
    path: str = typer.Argument(..., help="Path to music library or album."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without writing."),
):
    """Tag explicit content using MusicBrainz + Spotify."""
    banner()
    from dam.keys import require_key

    require_key("SPOTIFY_CLIENT_ID")
    require_key("SPOTIFY_CLIENT_SECRET")

    heading("Tagging explicit content")
    script = REPO_ROOT / "bin" / "music" / "tag-explicit-mb.py"
    args = [sys.executable, str(script), "--path", path]
    if dry_run:
        args.append("--dry-run")
    _run(args)


@tag_app.command("genres")
def tag_genres(
    path: str = typer.Argument(..., help="Path to music library or album."),
):
    """Add genre tags via MusicBrainz."""
    banner()
    heading("Updating genres")
    script = REPO_ROOT / "bin" / "music" / "update-genre-mb.py"
    _run([sys.executable, str(script), path])


@tag_app.command("lyrics")
def tag_lyrics(
    path: str = typer.Argument(..., help="Path to music library."),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Process subdirectories."),
):
    """Download song lyrics via Genius."""
    banner()
    from dam.keys import require_key

    require_key("GENIUS_API_TOKEN")

    heading("Downloading lyrics")
    script = REPO_ROOT / "bin" / "music" / "download_lyrics.py"
    args = [sys.executable, str(script), "--path", path]
    if recursive:
        args.append("--recursive")
    _run(args)


@tag_app.command("movie")
def tag_movie(
    path: str = typer.Argument(..., help="Path to movie file or directory."),
):
    """Add movie metadata via TMDb/OMDb."""
    banner()
    from dam.keys import require_key

    require_key("TMDB_API_KEY")

    heading("Tagging movie metadata")
    script = REPO_ROOT / "bin" / "video" / "tag-movie-metadata.py"
    _run([sys.executable, str(script), path])


# ── dam sync ───────────────────────────────────────────────────────────────


@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview sync without executing."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output."),
):
    """Sync media library to configured destinations."""
    banner()
    heading("Library sync")
    script = REPO_ROOT / "bin" / "sync" / "master-sync.py"
    args = [sys.executable, str(script)]
    if dry_run:
        args.append("--dry-run")
    if quiet:
        args.append("--quiet")
    _run(args)


# ── dam version ────────────────────────────────────────────────────────────


@app.command()
def version():
    """Show the current version."""
    console.print(f"Digital Archive Maker [bold]{__version__}[/]")


# ── Helpers ────────────────────────────────────────────────────────────────


def _ensure_deps(names: list[str]) -> None:
    """Warn if specific tools are missing (non-blocking)."""
    import shutil

    for name in names:
        if not shutil.which(name):
            warning(f"{name} not found. Run [bold]dam check --install[/] to set up dependencies.")


def _run(args: list[str]) -> None:
    """Run a subprocess, streaming output."""
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as exc:
        error(f"Command failed with exit code {exc.returncode}")
        raise typer.Exit(code=exc.returncode)
    except FileNotFoundError:
        error(f"Command not found: {args[0]}")
        raise typer.Exit(code=1)


def _run_make(targets: list[str], extra_env: Optional[dict] = None) -> None:
    """Run a Makefile target from the repo root."""
    import os

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    args = ["make", "-C", str(REPO_ROOT)] + targets
    try:
        subprocess.run(args, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        error(f"make failed with exit code {exc.returncode}")
        raise typer.Exit(code=exc.returncode)


def _run_script_or_make(target: str) -> None:
    """Run a Makefile target."""
    _run_make([target])


def _update_env_value(env_path: Path, key: str, value: str) -> None:
    """Update or add a key in .env."""
    import re

    content = env_path.read_text() if env_path.exists() else ""
    pattern = re.compile(rf'^{re.escape(key)}\s*=.*$', re.MULTILINE)
    replacement = f'{key}="{value}"'

    if pattern.search(content):
        content = pattern.sub(replacement, content)
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += replacement + "\n"

    env_path.write_text(content)


def main() -> None:
    """Entry point for the ``dam`` command."""
    app()


if __name__ == "__main__":
    main()
