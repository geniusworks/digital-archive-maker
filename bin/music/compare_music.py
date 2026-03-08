#!/usr/bin/env python3
"""
compare_music_fast.py - Fast comparison of two music library folders for differences.
- Uses os.scandir for fast recursive file listing.
- Filters ignored extensions before all processing.
- RapidFuzz bulk matching for speed.
Usage and options as original.
"""

import argparse
import os
import re
import unicodedata

from rapidfuzz import process

IGNORE_EXTS = {
    "db",
    "doc",
    "ds_store",
    "esc",
    "gif",
    "jpg",
    "json",
    "m3u",
    "pdf",
    "plist",
    "png",
    "strings",
    "txt",
    "webloc",
}


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse spaces, remove diacritics."""
    name = name.lower()
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"[^a-z0-9 ]", "", name)  # remove punctuation
    name = re.sub(r"\s+", " ", name).strip()  # collapse spaces
    return name


def is_album_match(path_album: str, lib_album: str, min_prefix_chars: int = 5) -> bool:
    path_norm = normalize_name(path_album)
    lib_norm = normalize_name(lib_album)
    return path_norm[:min_prefix_chars] == lib_norm[:min_prefix_chars]


def list_files_fast(folder):
    """Recursively list files using os.scandir. Excludes ignored extensions, returns set of relpaths."""
    out = set()

    def _scan(path, rel=""):
        with os.scandir(path) as it:
            for entry in it:
                entry_rel = os.path.join(rel, entry.name)
                if entry.is_dir(follow_symlinks=False):
                    _scan(entry.path, entry_rel)
                elif entry.is_file(follow_symlinks=False):
                    ext = entry.name.rsplit(".", 1)[-1].lower()
                    if ext not in IGNORE_EXTS:
                        out.add(entry_rel.lower())

    _scan(folder)
    return out


def make_key(f):
    parts = f.split(os.sep)
    artist = parts[-3] if len(parts) >= 3 else ""
    album = parts[-2] if len(parts) >= 2 else ""
    filename = parts[-1]
    base = re.sub(r"^\d+[-. ]*", "", os.path.splitext(filename)[0])
    key = f"{normalize_name(artist)} {normalize_name(base)}"
    return key, album


def compare_sets_fast(old_files, new_files, cutoff=0.9, min_album_prefix=5):
    # Precompute normalized keys
    old_info = [(f, *make_key(f)) for f in old_files]
    new_info = [(f, *make_key(f)) for f in new_files]

    # Group new files by album prefix for quick lookup
    new_by_album = {}
    for nf, nkey, nalbum in new_info:
        prefix = normalize_name(nalbum)[:min_album_prefix]
        new_by_album.setdefault(prefix, []).append((nf, nkey))

    only_in_old = set()
    matched_new = set()
    for o_file, o_key, o_album in old_info:
        prefix = normalize_name(o_album)[:min_album_prefix]
        candidates = new_by_album.get(prefix, [])
        best_match = process.extractOne(
            o_key, [nkey for _, nkey in candidates], score_cutoff=cutoff * 100
        )
        if best_match:
            idx = [nkey for _, nkey in candidates].index(best_match[0])
            matched_new.add(candidates[idx][0])
        else:
            only_in_old.add(o_file)
    only_in_new = set(f for f, _, _ in new_info) - matched_new
    return only_in_old, only_in_new


def group_by_album(file_set):
    albums = {}
    for f in file_set:
        parts = f.split(os.sep)
        if len(parts) >= 2:
            album = parts[-2]
            albums.setdefault(album, []).append(f)
    return albums


def group_by_artist(file_set):
    artists = {}
    for f in file_set:
        parts = f.split(os.sep)
        if len(parts) >= 3:
            artist = parts[-3]
            artists.setdefault(artist, []).append(f)
    return artists


def main():
    parser = argparse.ArgumentParser(description="Compare two music library folders FAST")
    parser.add_argument("old_dir", help="Old music folder")
    parser.add_argument("new_dir", help="New music folder")
    parser.add_argument(
        "--threshold",
        type=int,
        default=90,
        help="Similarity threshold (0–100)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--albums", action="store_true", help="Group output by album")
    group.add_argument("--artists", action="store_true", help="Group output by artist")
    args = parser.parse_args()
    old_items = list_files_fast(args.old_dir)
    new_items = list_files_fast(args.new_dir)
    only_in_old, only_in_new = compare_sets_fast(old_items, new_items, cutoff=args.threshold / 100)
    if args.albums:
        print("Albums only in old:")
        for album, files in group_by_album(only_in_old).items():
            print(f"  {album}: {len(files)} tracks")
        print("\nAlbums only in new:")
        for album, files in group_by_album(only_in_new).items():
            print(f"  {album}: {len(files)} tracks")
    elif args.artists:
        print("Artists only in old:")
        for artist, files in group_by_artist(only_in_old).items():
            print(f"  {artist}: {len(files)} tracks")
        print("\nArtists only in new:")
        for artist, files in group_by_artist(only_in_new).items():
            print(f"  {artist}: {len(files)} tracks")
    else:
        with open("only_in_old.txt", "w") as f:
            f.writelines(f"{item}\n" for item in sorted(only_in_old))
        with open("only_in_new.txt", "w") as f:
            f.writelines(f"{item}\n" for item in sorted(only_in_new))
        print("Differences written to only_in_old.txt and only_in_new.txt")


if __name__ == "__main__":
    main()
