#!/usr/bin/env python3
"""
Master sync script for running multiple library sync jobs.
Reads sync-config.yaml and executes sync-library.py for each job.
"""

import argparse
import subprocess
import sys
import os
import yaml
from pathlib import Path


def load_config(config_path):
    """Load sync configuration from YAML file."""
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
    if media in {"music", "movies"}:
        cmd.extend(["--media", media])

    # Add optional flags
    if media == "music":
        if job.get("exclude_explicit", False):
            cmd.append("--exclude-explicit")
        if job.get("exclude_unknown", False):
            cmd.append("--exclude-unknown")
    else:
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

    if job.get("delete", False):
        cmd.append("--delete")
    if job.get("dry_run", False):
        cmd.append("--dry-run")
    if job.get("ssh"):
        cmd.extend(["--ssh", job["ssh"]])
    
    # Add global options
    if global_opts.get("print_command", False):
        cmd.append("--print-command")
    if global_opts.get("max_flacs", 0) > 0:
        cmd.extend(["--max-flacs", str(global_opts["max_flacs"])])
    
    return cmd


def run_explicit_tagging(source_path, dry_run=False):
    """Run explicit tagging on source path before sync."""
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
    
    try:
        print("Running explicit tagging to detect new content...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running explicit tagging on '{source_path}':")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def run_movie_rating_tagging(source_path, dry_run=False):
    """Run movie rating tagging on source path before sync."""
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

    try:
        print("Running movie rating tagging to detect new content...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running movie rating tagging on '{source_path}':")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def run_sync_job(job, sync_script_path, global_opts, dry_run=False, skip_tagging=False):
    """Run a single sync job."""
    print(f"\n{'='*60}")
    print(f"Running sync job: {job['name']}")
    print(f"Source: {job['src']}")
    print(f"Destination: {job['dest']}")
    print(f"{'='*60}")
    
    media = job.get("media", "music")

    # Run tagging first unless skipped
    if not skip_tagging and not dry_run:
        if media == "movies":
            if not run_movie_rating_tagging(job["src"], dry_run=False):
                print("Warning: Movie rating tagging failed, proceeding with sync anyway")
        else:
            if not run_explicit_tagging(job["src"], dry_run=False):
                print("Warning: Explicit tagging failed, proceeding with sync anyway")
    
    cmd = build_sync_command(job, sync_script_path, global_opts)
    
    if dry_run or job.get("dry_run", False):
        print("DRY RUN - Would execute:")
        print(" ".join(cmd))
        return True
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running sync job '{job['name']}':")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
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
    global_opts = config.get("global_options", {})
    
    # Filter jobs if specific job requested
    jobs = config.get("sync_jobs", [])
    if args.job:
        jobs = [job for job in jobs if job["name"] == args.job]
        if not jobs:
            print(f"Error: Job '{args.job}' not found in configuration")
            return 1
    
    # Run jobs
    success_count = 0
    total_count = len(jobs)
    
    for job in jobs:
        if run_sync_job(job, str(sync_script_path), global_opts, args.dry_run, args.skip_tagging):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Sync Summary:")
    print(f"  Total jobs: {total_count}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {total_count - success_count}")
    print(f"{'='*60}")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())