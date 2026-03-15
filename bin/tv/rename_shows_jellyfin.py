#!/usr/bin/env python3
"""
Rename show episodes to Jellyfin naming convention.
Use --dry-run to preview; run without flags to apply changes.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from mutagen.mp4 import MP4

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def _desired_ordering_tags(season, episode, show_name, year=None):
    desired = {
        "tvsh": [show_name],
        "tvsn": [int(season)],
        "tves": [int(episode)],
    }
    if year:
        desired["\xa9day"] = [str(year)]
    return desired


def needs_episode_metadata_update(file_path, season, episode, show_name, year=None):
    if not MUTAGEN_AVAILABLE:
        return None

    try:
        mp4 = MP4(file_path)
        desired = _desired_ordering_tags(season, episode, show_name, year=year)
        for k, v in desired.items():
            if mp4.get(k) != v:
                return True
        return False
    except Exception:
        return None


def set_episode_metadata(file_path, season, episode, show_name, year=None):
    """Set TV episode metadata in MP4 file."""
    if not MUTAGEN_AVAILABLE:
        print(f"Warning: mutagen not available, skipping metadata for {file_path.name}")
        return False

    try:
        mp4 = MP4(file_path)

        desired = _desired_ordering_tags(season, episode, show_name, year=year)

        changed = False
        for k, v in desired.items():
            existing = mp4.get(k)
            if existing == v:
                continue
            mp4[k] = v
            changed = True

        if not changed:
            return False

        mp4.save()
        return True
    except Exception as e:
        print(f"Error setting metadata for {file_path.name}: {e}")
        return False


def parse_episode_number(filename):
    """Extract leading episode number from filename."""
    match = re.match(r"^(\d{1,2})\s+(.+)", filename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, filename


def parse_show_folder(folder_name):
    m = re.match(r"^(.+?)\s*\((\d{4})\)\s*$", folder_name)
    if m:
        return m.group(1).strip(), m.group(2)
    return folder_name.strip(), None


def _extract_order_index(stem):
    patterns = [
        r"^\(?\s*(\d{1,3})\s*\)?\s*[-_. ]+(.+)$",  # (01) Title / 01 Title / 01-Title
        r"^Session\s+(\d{1,3})\s*[-:.]+\s*(.+)$",
        r"^Episode\s+(\d{1,3})\s*[-:.]+\s*(.+)$",
        r"^Part\s+(\d{1,3})\s*[-:.]+\s*(.+)$",
        r"^(.+?)\s+-\s+Part\s+(\d{1,3})\s*(?:\(\d{4}\))?$",
        r"^(.+?)\s+Part\s+(\d{1,3})$",
        r"^(.+?)\s+Part\s+(\d{1,3})\s*[-:.]+\s*(.+)$",
        r"^(.+?)\s+(\d{1,3})\s*(?:\(\d{4}\))?$",
    ]

    for pat in patterns:
        m = re.match(pat, stem, flags=re.IGNORECASE)
        if not m:
            continue

        if pat.startswith(r"^\(?"):
            try:
                return int(m.group(1)), m.group(2).strip()
            except Exception:
                return None, stem

        if (
            pat.lower().startswith("^session")
            or pat.lower().startswith("^episode")
            or pat.lower().startswith("^part")
        ):
            try:
                return int(m.group(1)), m.group(2).strip()
            except Exception:
                return None, stem

        # Suffix "Part N" or "... - Part N"
        if "Part" in pat and pat.startswith(r"^(.+?)") and m.lastindex in (2, 3):
            if m.lastindex == 2:
                base = (m.group(1) or "").strip()
                try:
                    idx = int(m.group(2))
                except Exception:
                    return None, stem
                return idx, base
            if m.lastindex == 3:
                base = (m.group(3) or "").strip()
                try:
                    idx = int(m.group(2))
                except Exception:
                    return None, stem
                return idx, base

        # Suffix "Title 1" or "Title 1 (2002)"
        if pat == r"^(.+?)\s+(\d{1,3})\s*(?:\(\d{4}\))?$" and m.lastindex == 2:
            base = (m.group(1) or "").strip()
            try:
                idx = int(m.group(2))
            except Exception:
                return None, stem
            return idx, base

    return None, stem


def _strip_trailing_year_if_matches(title, year_str):
    if not year_str:
        return title
    t = title.strip()
    if t.endswith(f"({year_str})"):
        return t[: -len(f"({year_str})")].rstrip()
    return t


def _extract_year_from_text(text):
    if not text:
        return None
    m = re.search(r"\((\d{4})\)", text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _strip_leading_show_prefix(title, show_title):
    t = (title or "").strip()
    if not show_title:
        return t
    st = show_title.strip()
    if not st:
        return t
    if t.lower().startswith(st.lower()):
        rest = t[len(st) :]
        rest = re.sub(r"^[\s\-–—:._]+", "", rest)
        return rest.strip() or t
    return t


def _parse_existing_jellyfin_name(show_title, filename_stem):
    m = re.match(
        rf"^{re.escape(show_title)}\s+-\s+S(\d{{2}})E(\d{{2}})\s+-\s+(.+)$",
        filename_stem,
    )
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), m.group(3).strip()


def _iter_video_files(dir_path):
    for p in sorted(dir_path.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() not in (".mp4", ".m4v"):
            continue
        yield p


def plan_show(show_dir, strip_years=False):
    show_title, show_year = parse_show_folder(show_dir.name)

    # If the show already has Jellyfin-style filenames, prefer that exact show title
    # (avoids repeated renames due to case/punctuation differences vs folder name).
    existing_titles = {}
    try:
        for p in show_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".mp4", ".m4v"):
                continue
            m = re.match(r"^(.+?)\s+-\s+S\d{2}E\d{2}\s+-\s+.+$", p.stem)
            if not m:
                continue
            t = (m.group(1) or "").strip()
            if t:
                existing_titles[t] = existing_titles.get(t, 0) + 1
    except Exception:
        existing_titles = {}

    if existing_titles:
        show_title = max(existing_titles.items(), key=lambda kv: kv[1])[0]

    # Determine structure
    season_dirs = sorted(
        [
            d
            for d in show_dir.iterdir()
            if d.is_dir() and re.match(r"^Season\s+\d{1,2}$", d.name, re.IGNORECASE)
        ]
    )
    specials_dir = next(
        (d for d in show_dir.iterdir() if d.is_dir() and d.name.lower() == "specials"),
        None,
    )

    operations = []

    def _plan_episode(src_path, dest_dir, season_num, episode_num, raw_title):
        ext = src_path.suffix
        ep_year = _extract_year_from_text(raw_title) or (int(show_year) if show_year else None)
        clean_title = _strip_leading_show_prefix(raw_title, show_title)
        if strip_years:
            clean_title = _strip_trailing_year_if_matches(clean_title, show_year)
        dest_name = f"{show_title} - S{season_num:02d}E{episode_num:02d} - {clean_title}{ext}"
        dest_path = dest_dir / dest_name
        operations.append((src_path, dest_path, show_title, season_num, episode_num, ep_year))

    # If no season dirs and no specials dir, treat as flat => Season 01
    if not season_dirs and specials_dir is None:
        season_dirs = [show_dir]

    for sd in season_dirs:
        season_num = 1
        m = re.match(r"^Season\s+(\d{1,2})$", sd.name, re.IGNORECASE)
        if m:
            season_num = int(m.group(1))

        # Where files should end up
        dest_dir = show_dir / f"Season {season_num:02d}"

        files = list(_iter_video_files(sd))
        if not files:
            continue

        # Build ordering
        extracted = []
        for f in files:
            existing = _parse_existing_jellyfin_name(show_title, f.stem)
            if existing:
                s_existing, e_existing, _t_existing = existing
                extracted.append((f, e_existing, _t_existing, True))
                continue
            idx, title = _extract_order_index(f.stem)
            if idx is not None:
                extracted.append((f, idx, title, False))
            else:
                extracted.append((f, None, f.stem, False))

        # If all have explicit indexes, sort by that; otherwise by name
        if all(i is not None for (_f, i, _t, _e) in extracted):
            extracted.sort(key=lambda x: x[1])
        else:
            extracted.sort(key=lambda x: x[0].name.lower())

        # Assign sequential episode numbers if any are missing or if coming from non-jellyfin names
        ep = 1
        for f, idx, title, already_named in extracted:
            if already_named:
                # Keep the episode number embedded in filename
                _plan_episode(f, f.parent, season_num, idx, title)
            else:
                _plan_episode(f, dest_dir, season_num, ep, title)
                ep += 1

    if specials_dir is not None:
        dest_dir = specials_dir
        files = list(_iter_video_files(specials_dir))
        extracted = []
        for f in files:
            existing = _parse_existing_jellyfin_name(show_title, f.stem)
            if existing:
                s_existing, e_existing, t_existing = existing
                extracted.append((f, e_existing, t_existing, True))
                continue
            idx, title = _extract_order_index(f.stem)
            if idx is not None:
                extracted.append((f, idx, title, False))
            else:
                extracted.append((f, None, f.stem, False))

        if all(i is not None for (_f, i, _t, _e) in extracted):
            extracted.sort(key=lambda x: x[1])
        else:
            extracted.sort(key=lambda x: x[0].name.lower())

        ep = 1
        for f, idx, title, already_named in extracted:
            if already_named:
                _plan_episode(f, f.parent, 0, idx, title)
            else:
                _plan_episode(f, dest_dir, 0, ep, title)
                ep += 1

    return show_title, operations


def main():
    parser = argparse.ArgumentParser(
        description="Rename shows under the Shows folder to Jellyfin naming convention"
    )
    parser.add_argument(
        "--root",
        default="/Library/Shows",
        help="Shows root folder (requires LIBRARY_ROOT or --root)",
    )
    parser.add_argument(
        "--show",
        action="append",
        default=[],
        help="Only process a specific show folder name (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without executing",
    )
    parser.add_argument(
        "--strip-years",
        action="store_true",
        help="Remove trailing (YYYY) from episode titles in filenames",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE: Showing planned changes only")
    else:
        print("EXECUTE MODE: Applying changes")

    root = Path(args.root)
    if not root.exists():
        print(f"Error: Shows root not found: {root}")
        raise SystemExit(1)

    show_dirs = sorted([d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")])
    if args.show:
        wanted = set(args.show)
        show_dirs = [d for d in show_dirs if d.name in wanted]

    all_ops = []
    for show_dir in show_dirs:
        show_title, ops = plan_show(show_dir, strip_years=args.strip_years)
        if not ops:
            continue
        all_ops.append((show_dir, show_dir.name, show_title, ops))

    if not all_ops:
        print("No shows found with video files to process")
        return

    planned_renames = 0
    planned_metadata_updates = 0
    for show_dir, folder_name, show_title, ops in all_ops:
        print(f"\n=== {folder_name} ===")
        dest_counts = {}
        for src, dst, _show_title, season, episode, ep_year in ops:
            dest_counts[str(dst)] = dest_counts.get(str(dst), 0) + 1
            try:
                src_disp = str(src.relative_to(show_dir))
            except Exception:
                src_disp = src.name
            try:
                dst_disp = str(dst.relative_to(show_dir))
            except Exception:
                dst_disp = str(dst)

            if src == dst:
                need = needs_episode_metadata_update(src, season, episode, show_title, year=ep_year)
                if need is True:
                    print(f"{src_disp}  →  [already named] (will update ordering metadata)")
                    planned_metadata_updates += 1
                elif need is False:
                    print(f"{src_disp}  →  [already named] (metadata already OK)")
                else:
                    print(f"{src_disp}  →  [already named] (metadata check unavailable)")
            else:
                print(f"{src_disp}  →  {dst_disp}")
                planned_renames += 1
                planned_metadata_updates += 1

        collisions = [p for (p, n) in dest_counts.items() if n > 1]
        if collisions:
            print("WARNING: destination collisions detected:")
            for p in collisions:
                print(p)

    if args.dry_run:
        print("\nDRY RUN: Use without --dry-run to actually apply changes")
        if planned_renames == 0 and planned_metadata_updates == 0:
            print("Dry run completed: no changes needed.")
        else:
            print(
                f"Dry run completed: {planned_renames} rename(s), "
                f"{planned_metadata_updates} metadata update(s) planned."
            )
        return

    if planned_renames == 0 and planned_metadata_updates == 0:
        print("\nNo changes needed.")
        print("All updates completed.")
        return

    print("\nApplying changes...")
    performed_renames = 0
    performed_metadata_writes = 0
    errors = 0
    for _show_dir, _folder_name, show_title, ops in all_ops:
        for src, dst, show_name, season, episode, ep_year in ops:
            try:
                if src != dst:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        print(f"Error: destination already exists, skipping: {dst}")
                        errors += 1
                        continue
                    src.rename(dst)
                    print(f"Renamed: {src} -> {dst}")
                    performed_renames += 1

                # Always set ordering metadata (idempotent inside)
                if set_episode_metadata(dst, season, episode, show_name, year=ep_year):
                    performed_metadata_writes += 1
            except Exception as e:
                print(f"Error processing {src}: {e}")
                errors += 1

    print(
        f"All updates completed. Renamed: {performed_renames}. "
        f"Metadata writes: {performed_metadata_writes}. Errors: {errors}."
    )


if __name__ == "__main__":
    sys.exit(main())
