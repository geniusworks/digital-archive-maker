#!/usr/bin/env python3
"""
Master sync script for running multiple library sync jobs.
Reads sync-config.yaml and executes sync-library.py for each job.
"""

import os
import sys
import subprocess
import argparse
import time
import re
import tempfile
import shutil
import signal
from pathlib import Path


_RSYNC_PROGRESS_RE = re.compile(r"^\s*\d+(?:\.\d+)?[KMG]?\s+\d+%")


def _stream_process_output(process, *, quiet=False, label=None):
    """Stream a subprocess' stdout (and optionally filtered stderr) to console.

    In quiet mode:
    - Suppresses extremely noisy progress-bar output (tqdm) and repetitive no-op lines.
    - Collapses rsync-style progress lines into a single updating row.
    """

    def _should_print(line):
        if not quiet:
            return True

        stripped = line.strip()
        if not stripped:
            return False

        # tqdm progress lines are handled separately (single-row updates).
        if stripped.startswith("Tagging audio files:"):
            return False

        # Suppress high-volume no-op chatter from taggers.
        if stripped.startswith("Processing:") and "No changes needed" not in stripped:
            # Allow the tagger to show the file being processed only in non-quiet.
            return False
        if stripped.endswith("No changes needed"):
            return False

        return True

    last_was_progress = False
    suppressed_processing = 0
    for line in process.stdout:
        if quiet and line.strip().startswith("Tagging audio files:"):
            # Collapse tqdm progress into a single updating row.
            sys.stdout.write("\r" + line.rstrip("\n"))
            sys.stdout.flush()
            last_was_progress = True
            continue

        if quiet and line.strip().startswith("Processing:"):
            # Many taggers print one line per file. In quiet mode, suppress the spam
            # but keep a heartbeat so long runs don't look hung.
            suppressed_processing += 1
            if suppressed_processing % 50 == 0:
                sys.stdout.write(f"\rProcessing... {suppressed_processing}")
                sys.stdout.flush()
                last_was_progress = True
            continue

        if quiet and _RSYNC_PROGRESS_RE.match(line):
            # Update in-place (single row) for rsync progress lines.
            sys.stdout.write("\r" + line.rstrip("\n"))
            sys.stdout.flush()
            last_was_progress = True
            continue

        if last_was_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()
            last_was_progress = False

        if _should_print(line):
            print(line, end="", flush=True)

    if last_was_progress:
        sys.stdout.write("\n")
        sys.stdout.flush()


def _require_python_deps():
    missing = []

    try:
        import yaml  # noqa: F401
    except Exception:
        missing.append("PyYAML")

    try:
        import dotenv  # noqa: F401
    except Exception:
        missing.append("python-dotenv")

    try:
        import requests  # noqa: F401
    except Exception:
        missing.append("requests")

    try:
        import mutagen  # noqa: F401
    except Exception:
        missing.append("mutagen")

    try:
        import musicbrainzngs  # noqa: F401
    except Exception:
        missing.append("musicbrainzngs")

    try:
        import rapidfuzz  # noqa: F401
    except Exception:
        missing.append("rapidfuzz")

    try:
        import tqdm  # noqa: F401
    except Exception:
        missing.append("tqdm")

    if missing:
        print("Error: Missing required Python dependencies:")
        for name in missing:
            print(f"  - {name}")
        print("\nInstall the repo requirements using the SAME python interpreter you are running:")
        print(f"  {sys.executable} -m pip install -r requirements.txt")
        sys.exit(1)


def _parse_int(value):
    if value is None:
        return 0
    return int(str(value).replace(",", "").strip())


def _format_bytes(num_bytes):
    try:
        n = float(num_bytes)
    except Exception:
        n = 0.0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    i = 0
    while n >= 1024.0 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.2f} {units[i]}"


def _format_duration(seconds):
    try:
        total = int(round(float(seconds)))
    except Exception:
        total = 0
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _resolve_rsync_bin():
    override = os.environ.get("RSYNC_BIN")
    if override:
        return override

    for candidate in ("/opt/homebrew/bin/rsync", "/usr/local/bin/rsync"):
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return shutil.which("rsync") or "rsync"


def parse_rsync_stats(output_text):
    stats = {
        "files_copied": 0,
        "bytes_transferred": 0,
        "bytes_sent": 0,
        "bytes_received": 0,
    }

    if not output_text:
        return stats

    m = re.search(r"^Number of regular files transferred:\s+([0-9,]+)\s*$", output_text, flags=re.MULTILINE)
    if not m:
        m = re.search(r"^Number of files transferred:\s+([0-9,]+)\s*$", output_text, flags=re.MULTILINE)
    if m:
        stats["files_copied"] = _parse_int(m.group(1))

    m = re.search(r"^Total transferred file size:\s+([0-9,]+)\s+bytes\s*$", output_text, flags=re.MULTILINE)
    if m:
        stats["bytes_transferred"] = _parse_int(m.group(1))

    m_sent = re.search(r"^Total bytes sent:\s+([0-9,]+)\s*$", output_text, flags=re.MULTILINE)
    m_recv = re.search(r"^Total bytes received:\s+([0-9,]+)\s*$", output_text, flags=re.MULTILINE)
    if m_sent:
        stats["bytes_sent"] = _parse_int(m_sent.group(1))
    if m_recv:
        stats["bytes_received"] = _parse_int(m_recv.group(1))

    if not (m_sent and m_recv):
        m = re.search(r"sent\s+([0-9,]+)\s+bytes\s+received\s+([0-9,]+)\s+bytes", output_text)
        if m:
            stats["bytes_sent"] = _parse_int(m.group(1))
            stats["bytes_received"] = _parse_int(m.group(2))

    return stats


def load_config(config_path):
    """Load sync configuration from YAML file."""
    import yaml
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)


def build_sync_command(job, sync_script_path, global_opts):
    """Build the sync-library.py command for a given job."""
    cmd = [
        sys.executable,  # Use current python interpreter
        sync_script_path,
        "--src", job["src"],
        "--dest", job["dest"]
    ]
    
    media = job.get("media", "music")
    cli_media = media
    if media == "cartoons":
        cli_media = "shows"
    if cli_media in {"music", "movies", "shows"}:
        cmd.extend(["--media", cli_media])

    # Add optional flags
    if media == "music":
        if job.get("exclude_explicit", False):
            cmd.append("--exclude-explicit")
        if job.get("exclude_unknown", False):
            cmd.append("--exclude-unknown")
    elif media == "movies":
        max_mpaa = job.get("max_mpaa")
        if not max_mpaa:
            max_mpaa = "PG-13"
        cmd.extend(["--max-mpaa", str(max_mpaa)])

        exclude_unknown = job.get("exclude_unknown")
        if exclude_unknown is None:
            exclude_unknown = True
        if exclude_unknown:
            cmd.append("--exclude-unknown")

        exclude_unrated = job.get("exclude_unrated")
        if exclude_unrated is None:
            exclude_unrated = True
        if exclude_unrated:
            cmd.append("--exclude-unrated")
    elif media == "shows":
        # Shows sync - no special filtering for now
        # Could add TV rating filters here in the future
        pass

    # Note: delete is now handled globally, not per-job
    
    if job.get("dry_run", False) or global_opts.get("dry_run", False):
        cmd.append("--dry-run")
    if job.get("ssh"):
        cmd.extend(["--ssh", job["ssh"]])
    
    # Add global options
    if global_opts.get("print_command", False):
        cmd.append("--print-command")
    if global_opts.get("max_flacs"):
        cmd.extend(["--max-flacs", str(global_opts["max_flacs"])])
    
    # For all sync jobs, use --no-delete to avoid cross-library deletion
    cmd.append("--no-delete")
    
    return cmd


def run_explicit_tagging(source_path, dry_run=False, quiet=False):
    """Run explicit tagging on source path before sync."""
    if not quiet:
        print(f"\n{'='*60}")
        print(f"Running explicit tagging on: {source_path}")
        print(f"{'='*60}")
    
    # Get the directory of this script to find repo root
    repo_root = Path(__file__).parent.parent
    tag_script = repo_root / "bin" / "tag-explicit-mb.py"
    
    cmd = [
        sys.executable,  # Use current python interpreter
        str(tag_script),
        source_path,
        "--dry-run" if dry_run else ""
    ]
    
    # Remove empty string from args
    cmd = [arg for arg in cmd if arg]
    
    if dry_run:
        print("DRY RUN - Would execute explicit tagging:")
        print(" ".join(cmd))
        return True
    
    process = None
    try:
        if not quiet:
            print("Running explicit tagging to detect new content...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        _stream_process_output(process, quiet=quiet)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, "", "")
        return True
    except KeyboardInterrupt:
        print("\n\nTagging interrupted by user. Cleaning up...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("Tagging aborted.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running explicit tagging on '{source_path}':")
        print(f"Exit code: {e.returncode}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def run_movie_rating_tagging(source_path, dry_run=False, quiet=False):
    """Run movie rating tagging on source path before sync."""
    if not quiet:
        print(f"\n{'='*60}")
        print(f"Running movie rating tagging on: {source_path}")
        print(f"{'='*60}")

    repo_root = Path(__file__).parent.parent
    tag_script = repo_root / "bin" / "tag-movie-ratings.py"

    cmd = [
        sys.executable,
        str(tag_script),
        source_path,
        "--dry-run" if dry_run else "",
    ]

    cmd = [arg for arg in cmd if arg]

    if dry_run:
        print("DRY RUN - Would execute movie rating tagging:")
        print(" ".join(cmd))
        return True

    process = None
    try:
        if not quiet:
            print("Running movie rating tagging to detect new content...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        _stream_process_output(process, quiet=quiet)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, "", "")
        return True
    except KeyboardInterrupt:
        print("\n\nTagging interrupted by user. Cleaning up...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("Tagging aborted.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running movie rating tagging on '{source_path}':")
        print(f"Exit code: {e.returncode}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def run_movie_metadata_tagging(source_path, dry_run=False, quiet=False):
    if not quiet:
        print(f"\n{'='*60}")
        print(f"Running movie metadata tagging on: {source_path}")
        print(f"{'='*60}")

    repo_root = Path(__file__).parent.parent
    tag_script = repo_root / "bin" / "tag-movie-metadata.py"

    cmd = [
        sys.executable,
        str(tag_script),
        source_path,
        "--recursive",
        "--dry-run" if dry_run else "",
    ]

    cmd = [arg for arg in cmd if arg]

    if dry_run:
        print("DRY RUN - Would execute movie metadata tagging:")
        print(" ".join(cmd))
        return True

    process = None
    try:
        if not quiet:
            print("Running movie metadata tagging to detect/fill missing metadata...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        _stream_process_output(process, quiet=quiet)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, "", "")
        return True
    except KeyboardInterrupt:
        print("\n\nTagging interrupted by user. Cleaning up...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("Tagging aborted.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running movie metadata tagging on '{source_path}':")
        print(f"Exit code: {e.returncode}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def run_show_metadata_tagging(source_path, dry_run=False, quiet=False):
    if not quiet:
        print(f"\n{'='*60}")
        print(f"Running show metadata tagging on: {source_path}")
        print(f"{'='*60}")

    repo_root = Path(__file__).parent.parent
    tag_script = repo_root / "bin" / "tag-show-metadata.py"

    cmd = [
        sys.executable,
        str(tag_script),
        source_path,
        "--recursive",
        "--dry-run" if dry_run else "",
    ]

    cmd = [arg for arg in cmd if arg]

    if dry_run:
        print("DRY RUN - Would execute show metadata tagging:")
        print(" ".join(cmd))
        return True

    process = None
    try:
        if not quiet:
            print("Running show metadata tagging to detect/fill missing metadata...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )
        _stream_process_output(process, quiet=quiet)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, "", "")
        return True
    except KeyboardInterrupt:
        print("\n\nTagging interrupted by user. Cleaning up...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("Tagging aborted.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running show metadata tagging on '{source_path}':")
        print(f"Exit code: {e.returncode}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def run_sync_job(job, sync_script_path, global_opts, dry_run=False, skip_tagging=False, quiet=False):
    """Run a single sync job and return statistics."""
    if not quiet:
        print(f"\n{'='*60}")
        print(f"Running sync job: {job['name']}")
        print(f"Source: {job['src']}")
        print(f"Destination: {job['dest']}")
        print(f"{'='*60}")
    
    media = job.get("media", "music")
    
    job_stats = {
        'name': job['name'],
        'media_type': media,
        'start_time': time.time(),
        'end_time': None,
        'elapsed_seconds': 0,
        'files_copied': 0,
        'bytes_transferred': 0,
        'bytes_sent': 0,
        'bytes_received': 0,
        'success': False
    }

    effective_dry_run = bool(dry_run or job.get("dry_run", False) or global_opts.get("dry_run", False))

    # Run tagging first unless skipped
    if not skip_tagging and not effective_dry_run:
        tag_metadata = job.get("tag_metadata")
        if tag_metadata is None:
            tag_metadata = media in {"movies", "shows", "cartoons"}

        if media == "movies":
            if tag_metadata:
                if not run_movie_metadata_tagging(job["src"], dry_run=False, quiet=quiet):
                    print("Warning: Movie metadata tagging failed, proceeding with sync anyway")
            if not run_movie_rating_tagging(job["src"], dry_run=False, quiet=quiet):
                print("Warning: Movie rating tagging failed, proceeding with sync anyway")
        elif media == "shows":
            if tag_metadata:
                if not run_show_metadata_tagging(job["src"], dry_run=False, quiet=quiet):
                    print("Warning: Show metadata tagging failed, proceeding with sync anyway")
            else:
                print("Shows sync - skipping metadata tagging")
        elif media == "cartoons":
            if tag_metadata:
                if not run_movie_metadata_tagging(job["src"], dry_run=False, quiet=quiet):
                    print("Warning: Movie metadata tagging failed, proceeding with sync anyway")
            else:
                print("Cartoons sync - skipping metadata tagging")
        elif media == "music":
            if not run_explicit_tagging(job["src"], dry_run=False, quiet=quiet):
                print("Warning: Explicit tagging failed, proceeding with sync anyway")
        else:
            if not run_explicit_tagging(job["src"], dry_run=False, quiet=quiet):
                print("Warning: Explicit tagging failed, proceeding with sync anyway")
    
    cmd = build_sync_command(job, sync_script_path, global_opts)
    
    if effective_dry_run:
        print("DRY RUN - Would execute:")
        print(" ".join(cmd))
        job_stats['end_time'] = time.time()
        job_stats['elapsed_seconds'] = job_stats['end_time'] - job_stats['start_time']
        job_stats['success'] = True
        return job_stats
    
    process = None
    try:
        # Stream output in real-time while collecting for stats parsing
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1  # Line buffered
        )
        
        stdout_lines = []
        # Read stdout line by line and print in real-time
        last_was_progress = False
        for line in process.stdout:
            stdout_lines.append(line)

            if quiet and _RSYNC_PROGRESS_RE.match(line):
                sys.stdout.write("\r" + line.rstrip("\n"))
                sys.stdout.flush()
                last_was_progress = True
                continue

            if last_was_progress:
                sys.stdout.write("\n")
                sys.stdout.flush()
                last_was_progress = False

            if quiet:
                stripped = line.strip()
                if not stripped:
                    continue
                # Keep rsync's summary-ish lines, but drop the verbose file list.
                if stripped in {"sending incremental file list", "./"}:
                    continue
                # Drop directory listing spam (e.g. "Foo/"), keep file transfer stats/progress.
                if stripped.endswith("/") and not stripped.startswith("Number of"):
                    continue

            print(line, end='', flush=True)

        if last_was_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()
        
        # Wait for process to complete and get stderr
        _, stderr = process.communicate()
        
        if stderr and process.returncode != 0:
            print("STDERR:", stderr)
        
        stdout_text = ''.join(stdout_lines)
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, stdout_text, stderr)
        
        job_stats.update(parse_rsync_stats(stdout_text))
        job_stats['success'] = True
        job_stats['end_time'] = time.time()
        job_stats['elapsed_seconds'] = job_stats['end_time'] - job_stats['start_time']
        
        return job_stats
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user. Cleaning up...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        job_stats['success'] = False
        job_stats['end_time'] = time.time()
        job_stats['elapsed_seconds'] = job_stats['end_time'] - job_stats['start_time']
        print("Sync aborted.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running sync job '{job['name']}':")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        job_stats['success'] = False
        job_stats['end_time'] = time.time()
        job_stats['elapsed_seconds'] = job_stats['end_time'] - job_stats['start_time']
        return job_stats


def run_global_cleanup(jobs, sync_script_path, global_opts, dry_run=False):
    """Run global cleanup to remove folders that no longer exist in any source."""
    if not global_opts.get("delete", False):
        return True
    
    print(f"\n{'='*60}")
    print("Running global cleanup (delete mode)")
    print(f"{'='*60}")
    
    # Group jobs by destination
    dest_groups = {}
    for job in jobs:
        dest = job["dest"]
        if dest not in dest_groups:
            dest_groups[dest] = []
        dest_groups[dest].append(job)
    
    cleanup_success = True
    
    for dest, dest_jobs in dest_groups.items():
        print(f"\nCleaning destination: {dest}")

        keep_set = set()
        ssh_cmd = None
        for job in dest_jobs:
            if job.get("ssh"):
                ssh_cmd = job.get("ssh")
                break

        for job in dest_jobs:
            media = job.get("media", "music")
            cli_media = media
            if media == "cartoons":
                cli_media = "shows"
            keep_file = f"/tmp/keep_{hash(dest)}_{hash(job.get('name', job.get('src', '')))}.txt"
            exclude_file = f"/tmp/exclude_{hash(dest)}_{hash(job.get('name', job.get('src', '')))}.txt"

            cmd = [
                sys.executable,
                sync_script_path,
                "--src",
                job["src"],
                "--dest",
                dest,
                "--media",
                cli_media,
                "--no-delete",
                "--scan-only",
                "--keep-file",
                keep_file,
                "--exclude-file",
                exclude_file,
            ]

            if media == "music":
                if job.get("exclude_explicit", False):
                    cmd.append("--exclude-explicit")
                if job.get("exclude_unknown", False):
                    cmd.append("--exclude-unknown")
            elif media == "movies":
                max_mpaa = job.get("max_mpaa")
                if not max_mpaa:
                    max_mpaa = "PG-13"
                cmd.extend(["--max-mpaa", str(max_mpaa)])

                exclude_unknown = job.get("exclude_unknown")
                if exclude_unknown is None:
                    exclude_unknown = True
                if exclude_unknown:
                    cmd.append("--exclude-unknown")

                exclude_unrated = job.get("exclude_unrated")
                if exclude_unrated is None:
                    exclude_unrated = True
                if exclude_unrated:
                    cmd.append("--exclude-unrated")
            elif media in {"shows", "cartoons"}:
                # Shows sync - no special filtering for now
                pass

            if job.get("ssh"):
                cmd.extend(["--ssh", job["ssh"]])

            if global_opts.get("print_command", False):
                cmd.append("--print-command")

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
            except subprocess.CalledProcessError as e:
                print(f"Error building keep list for job '{job.get('name', '')}' (dest={dest}):")
                print(f"Exit code: {e.returncode}")
                print(f"STDOUT: {e.stdout}")
                print(f"STDERR: {e.stderr}")
                cleanup_success = False
                continue

            try:
                with open(keep_file, "r", encoding="utf-8") as f:
                    for line in f:
                        p = line.strip().replace("\\", "/")
                        if p:
                            keep_set.add(p)
            except FileNotFoundError:
                pass
            finally:
                try:
                    os.remove(keep_file)
                except Exception:
                    pass
                try:
                    os.remove(exclude_file)
                except Exception:
                    pass

        filter_file = f"/tmp/cleanup_filter_{hash(dest)}.txt"
        with open(filter_file, "w", encoding="utf-8", newline="\n") as f:
            # Always protect Playlists folder in music destinations
            if "/Music" in dest:
                f.write("P /Playlists/\n")
            
            # Add all files from keep set
            for p in sorted(keep_set):
                f.write(f"P /{p}\n")

        dest_arg = dest
        if not dest_arg.endswith("/"):
            dest_arg = dest_arg + "/"

        with tempfile.TemporaryDirectory(prefix="master_sync_empty_") as empty_dir:
            src_arg = empty_dir.rstrip(os.sep) + os.sep
            rsync_bin = _resolve_rsync_bin()
            rsync_cmd = [
                rsync_bin,
                "-a",
                "--delete",
                "--filter",
                f"merge {filter_file}",
                src_arg,
                dest_arg,
            ]

            if ssh_cmd:
                rsync_cmd.extend(["-e", ssh_cmd])

            if dry_run:
                rsync_cmd.append("--dry-run")

            if global_opts.get("print_command", False):
                print("Cleanup rsync command:")
                print(" ".join(rsync_cmd))

            process = None
            try:
                print("Running cleanup...")
                # Stream output in real-time
                process = subprocess.Popen(
                    rsync_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1
                )
                for line in process.stdout:
                    print(line, end='', flush=True)
                _, stderr = process.communicate()
                if stderr:
                    print("STDERR:", stderr)
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, rsync_cmd, "", stderr)
            except KeyboardInterrupt:
                print("\n\nCleanup interrupted by user. Cleaning up...")
                if process:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                print("Cleanup aborted.")
                cleanup_success = False
            except subprocess.CalledProcessError as e:
                print(f"Error running cleanup for {dest}:")
                print(f"Exit code: {e.returncode}")
                if e.stderr:
                    print(f"STDERR: {e.stderr}")
                cleanup_success = False

        try:
            os.remove(filter_file)
        except Exception:
            pass
    
    return cleanup_success


def main():
    _require_python_deps()
    parser = argparse.ArgumentParser(description="Run multiple library sync jobs")
    parser.add_argument(
        "--config", 
        default="sync-config.yaml",
        help="Path to sync configuration file"
    )
    parser.add_argument(
        "--job", 
        help="Run only specific job (by name)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be executed without running"
    )
    parser.add_argument(
        "--list-jobs", 
        action="store_true",
        help="List available jobs and exit"
    )
    parser.add_argument(
        "--skip-tagging", 
        action="store_true",
        help="Skip explicit tagging before sync"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose console output (disables quiet mode)"
    )
    
    args = parser.parse_args()
    
    # Get paths
    script_dir = Path(__file__).parent
    config_path = script_dir / args.config
    repo_root = script_dir.parent
    sync_script_path = repo_root / "bin" / "sync-library.py"
    
    # Load configuration
    config = load_config(config_path)
    
    # List jobs if requested
    if args.list_jobs:
        print("Available sync jobs:")
        for job in config.get("sync_jobs", []):
            print(f"  - {job['name']}: {job['src']} -> {job['dest']}")
        return 0
    
    # Check if sync script exists
    if not sync_script_path.exists():
        print(f"Error: sync-library.py not found at {sync_script_path}")
        return 1
    
    # Get global options
    global_opts = config.get("global", {})  # Changed from "global_options" to "global"
    
    # Override with command line args
    if args.dry_run:
        global_opts["dry_run"] = True
    
    # Filter jobs if specific job requested
    jobs = config.get("sync_jobs", [])
    if args.job:
        jobs = [job for job in jobs if job["name"] == args.job]
        if not jobs:
            print(f"Error: Job '{args.job}' not found in configuration")
            return 1
    
    run_start = time.time()
    success_count = 0
    total_count = len(jobs)
    job_stats_list = []
    
    quiet = not bool(args.verbose)

    for job in jobs:
        stats = run_sync_job(
            job,
            str(sync_script_path),
            global_opts,
            args.dry_run,
            args.skip_tagging,
            quiet=quiet,
        )
        job_stats_list.append(stats)
        if stats.get("success"):
            success_count += 1
    
    # Run global cleanup if enabled
    cleanup_success = run_global_cleanup(jobs, str(sync_script_path), global_opts, args.dry_run)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Sync Summary:")
    print(f"  Total jobs: {total_count}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {total_count - success_count}")
    print(f"  Cleanup: {'Success' if cleanup_success else 'Failed'}")

    run_elapsed = time.time() - run_start
    per_media = {}
    for s in job_stats_list:
        media = s.get("media_type") or "unknown"
        bucket = per_media.setdefault(
            media,
            {
                "jobs": 0,
                "failed": 0,
                "files_copied": 0,
                "bytes_transferred": 0,
                "bytes_sent": 0,
                "bytes_received": 0,
                "elapsed_seconds": 0,
            },
        )
        bucket["jobs"] += 1
        if not s.get("success"):
            bucket["failed"] += 1
        bucket["files_copied"] += int(s.get("files_copied") or 0)
        bucket["bytes_transferred"] += int(s.get("bytes_transferred") or 0)
        bucket["bytes_sent"] += int(s.get("bytes_sent") or 0)
        bucket["bytes_received"] += int(s.get("bytes_received") or 0)
        bucket["elapsed_seconds"] += float(s.get("elapsed_seconds") or 0)

    if job_stats_list:
        print("\nStats by media type:")
        for media in sorted(per_media.keys()):
            b = per_media[media]
            print(f"  {media}:")
            print(f"    Jobs: {b['jobs']} (failed: {b['failed']})")
            print(f"    Files copied: {b['files_copied']}")
            print(f"    Data transferred: {_format_bytes(b['bytes_transferred'])}")
            if b["bytes_sent"] or b["bytes_received"]:
                print(f"    Network: sent {_format_bytes(b['bytes_sent'])}, received {_format_bytes(b['bytes_received'])}")
            print(f"    Job time: {_format_duration(b['elapsed_seconds'])}")

        total_files = sum(int(s.get("files_copied") or 0) for s in job_stats_list)
        total_bytes = sum(int(s.get("bytes_transferred") or 0) for s in job_stats_list)
        total_sent = sum(int(s.get("bytes_sent") or 0) for s in job_stats_list)
        total_recv = sum(int(s.get("bytes_received") or 0) for s in job_stats_list)
        print("\nOverall stats:")
        print(f"  Total files copied: {total_files}")
        print(f"  Total data transferred: {_format_bytes(total_bytes)}")
        if total_sent or total_recv:
            print(f"  Total network: sent {_format_bytes(total_sent)}, received {_format_bytes(total_recv)}")
        print(f"  Wall time: {_format_duration(run_elapsed)}")

    print(f"{'='*60}")
    
    return 0 if (success_count == total_count and cleanup_success) else 1


if __name__ == "__main__":
    sys.exit(main())