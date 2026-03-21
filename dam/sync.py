#!/usr/bin/env python3
# Copyright (c) 2026 Martin Diekhoff
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Sync module for Digital Archive Maker.

This module provides the sync functionality for the dam CLI by calling
the master-sync.py script which reads sync-config.yaml and runs all jobs.
"""

import subprocess
import sys
from pathlib import Path


def main(dry_run: bool = False, quiet: bool = False):
    """Sync media library to configured destinations."""
    # Get the path to master-sync.py
    repo_root = Path(__file__).parent.parent
    master_sync = repo_root / "bin" / "sync" / "master-sync.py"
    
    if not master_sync.exists():
        print(f"Error: master-sync.py not found at {master_sync}")
        return 1
    
    # Build command arguments
    cmd = [sys.executable, str(master_sync)]
    
    if dry_run:
        cmd.append('--dry-run')
    if quiet:
        cmd.append('--quiet')
    
    # Run the master sync script
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Sync failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print(f"Error: Cannot execute {sys.executable}")
        return 1
