#!/usr/bin/env python3
"""
Check and optionally fix FLAC metadata.

Usage:
    python flac_metadata_checker.py --path . --dry-run --verbose
    python flac_metadata_checker.py --path . --fix --verbose
    python flac_metadata_checker.py --path . --fix --force

Arguments:
    --path     Root directory to scan (default: current directory)
    --dry-run  Show what would be changed, don't write anything (default behavior if --fix not specified)
    --trial    Alias for --dry-run
    --fix      Update mismatched metadata
    --force    Overwrite all tags with derived values
    --verbose  Print detailed info per file
"""

# Run in virtual environment:
#   python3 -m venv ~/mutagen-env
#   source ~/mutagen-env/bin/activate
#
# Examples:
#
#   Dry run on current directory
#   ./fix_flac_metadata.py
#
#   Dry run on target directory
#   ./fix_flac_metadata.py /your/path
#
#   Additional options
#     --fix   (fixes metdata identified as incomplete)
#     --force (forces update)
#     --verbose|--trial (detailed dry run)

import argparse
import os
import re
import sys

import mutagen.flac


# Normalize both values for comparison (ignore illegal filename characters)
def normalize_string_for_compare(s):
    if not s:
        return ""
    s = s.lower()
    # Normalize common replacements from filename sanitization
    s = s.replace("_", " ")
    s = s.replace("/", " ")
    s = s.replace(":", " ")
    s = re.sub(r'[\\:*?"<>|]', "", s)  # remove other illegal filesystem chars
    s = re.sub(r"\s+", "", s)  # collapse all whitespace
    return s


# Determine if current tag differs from desired value meaningfully
def needs_update(current, desired):
    return normalize_string_for_compare(current) != normalize_string_for_compare(desired)


def derive_metadata_from_path(path):
    filename = os.path.basename(path)
    parent = os.path.basename(os.path.dirname(path))
    grandparent = os.path.basename(os.path.dirname(os.path.dirname(path)))

    match = re.match(r"(\d{2}) - (.+)\.flac$", filename, re.IGNORECASE)
    if not match:
        return None

    tracknumber, title = match.groups()
    return {
        "TRACKNUMBER": tracknumber,
        "TITLE": title.strip(),
        "ALBUM": parent.strip(),
        "ARTIST": grandparent.strip(),
    }


def normalize_string(s):
    return s.strip().lower().replace("_", ":").replace(" ", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pos_path", nargs="?", help="Optional positional path")
    parser.add_argument(
        "--path",
        dest="kwarg_path",
        help="Named path (overrides positional)",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing changes",
    )
    parser.add_argument("--trial", action="store_true", help="Alias for --dry-run")
    parser.add_argument("--fix", action="store_true", help="Apply changes to files")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite all tags, even if present",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed info per file")

    args = parser.parse_args()
    path = args.kwarg_path or args.pos_path or "."

    dry_run = args.dry_run or args.trial
    fix = args.fix
    force = args.force
    verbose = args.verbose

    if not fix:
        dry_run = True

    dot_count = 0

    for root, dirs, files in os.walk(path):
        for f in sorted(files):
            if not f.lower().endswith(".flac"):
                continue
            fullpath = os.path.join(root, f)

            print(".", end="", flush=True)
            dot_count += 1
            if dot_count % 60 == 0:
                print()

            meta = derive_metadata_from_path(fullpath)
            if not meta:
                if verbose:
                    print(f"\nSkipping {fullpath} (filename pattern not matched)")
                continue

            try:
                audio = mutagen.flac.FLAC(fullpath)
            except Exception as e:
                if verbose:
                    print(f"\nError reading {fullpath}: {e}")
                continue

            changed = False

            if force:
                audio.clear()

            for tag, value in meta.items():
                current = audio.get(tag, [""])[0]
                if force or needs_update(current, value):
                    if dry_run:
                        print(f"[DRY RUN] {fullpath} would update {tag}: '{current}' → '{value}'")
                    else:
                        audio[tag] = value
                        changed = True
                        if verbose:
                            print(f"[UPDATED] {fullpath} set {tag}: '{current}' → '{value}'")

            if changed and not dry_run:
                try:
                    audio.save()
                except Exception as e:
                    print(f"\nError saving {fullpath}: {e}", file=sys.stderr)

    if dot_count % 60 != 0:
        print()

    print("Done.")


if __name__ == "__main__":
    main()
