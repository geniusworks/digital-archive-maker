#!/usr/bin/env python3

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp4 import MP4FreeForm
import base64
from datetime import datetime

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(_REPO_ROOT / ".env")
    except ImportError:
        pass

def find_imdb_id_from_file(file_path):
    """Try to extract IMDb ID from filename or existing tags."""
    # Check filename for IMDb ID pattern
    filename = os.path.basename(file_path)
    import re
    imdb_match = re.search(r'tt(\d+)', filename)
    if imdb_match:
        return f"tt{imdb_match.group(1)}"
    
    # Check existing tags for IMDb ID
    try:
        mp4 = MP4(file_path)
        # Check common IMDb ID tags
        for key in ['----:com.apple.iTunes:imdb', '----:com.apple.iTunes:IMDb', '----:com.apple.iTunes:imdb_id']:
            if key in mp4:
                return mp4[key][0].decode('utf-8')
    except:
        pass
    
    return None

def find_tmdb_id_from_file(file_path):
    """Try to extract TMDb ID from filename or existing tags."""
    filename = os.path.basename(file_path)
    import re
    tmdb_match = re.search(r'tmdb(\d+)', filename)
    if tmdb_match:
        return tmdb_match.group(1)
    
    # Check existing tags for TMDb ID
    try:
        mp4 = MP4(file_path)
        for key in ['----:com.apple.iTunes:tmdb', '----:com.apple.iTunes:TMDb', '----:com.apple.iTunes:tmdb_id']:
            if key in mp4:
                return mp4[key][0].decode('utf-8')
    except:
        pass
    
    return None

def get_tmdb_metadata(imdb_id=None, tmdb_id=None, title=None, year=None):
    """Fetch comprehensive metadata from TMDb."""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("Warning: TMDB_API_KEY not set, skipping TMDb lookup")
        return None
 
    headers = {"Accept": "application/json"}
    
    # Try to find movie by IMDb ID first
    if imdb_id:
        try:
            url = f"https://api.themoviedb.org/3/find/{imdb_id}"
            params = {"api_key": api_key, "external_source": "imdb_id"}
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if data.get('movie_results'):
                tmdb_id = data['movie_results'][0]['id']
            else:
                print(f"No TMDb results found for IMDb ID: {imdb_id}")
                return None
        except Exception as e:
            print(f"TMDb IMDb lookup failed: {e}")
            return None
    
    # Search by title/year if no IDs
    if not tmdb_id and title and year:
        try:
            url = "https://api.themoviedb.org/3/search/movie"
            params = {
                "api_key": api_key,
                'query': title,
                'year': year,
                'page': 1
            }
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                tmdb_id = data['results'][0]['id']
            else:
                print(f"No TMDb search results for: {title} ({year})")
                return None
        except Exception as e:
            print(f"TMDb search failed: {e}")
            return None
    
    if not tmdb_id:
        return None
    
    # Get full movie details
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        params = {
            "api_key": api_key,
            'append_to_response': 'credits,videos,images,releases,keywords'
        }
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"TMDb details lookup failed: {e}")
        return None

def get_omdb_metadata(imdb_id):
    """Fetch metadata from OMDb as backup/supplement."""
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        print("Warning: OMDB_API_KEY not set, skipping OMDb lookup")
        return None
    
    try:
        url = "http://www.omdbapi.com/"
        params = {
            'apikey': api_key,
            'i': imdb_id,
            'plot': 'full',
            'r': 'json'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        else:
            print(f"OMDb error: {data.get('Error', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"OMDb lookup failed: {e}")
        return None

def download_image(url, timeout=30):
    """Download image from URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Failed to download image from {url}: {e}")
        return None

def write_metadata_to_file(file_path, metadata, dry_run=False):
    """Write comprehensive metadata to MP4 file."""
    if dry_run:
        print(f"DRY RUN: Would write metadata to {file_path}")
        return True
    
    try:
        mp4 = MP4(file_path)
        
        # Basic metadata
        if metadata.get('title'):
            mp4['\xa9nam'] = metadata['title']  # Title
        
        if metadata.get('year'):
            mp4['\xa9day'] = str(metadata['year'])  # Year
        
        if metadata.get('release_date'):
            mp4['\xa9day'] = metadata['release_date'][:4]  # Year from release date
        
        # Description/Synopsis
        if metadata.get('overview'):
            mp4['\xa9des'] = metadata['overview']  # Description
        
        # Genre
        if metadata.get('genres'):
            genres = [g['name'] for g in metadata['genres']]
            mp4['\xa9gen'] = ', '.join(genres)  # Genre
        
        # Director and Writers
        if metadata.get('credits', {}).get('crew'):
            crew = metadata['credits']['crew']
            directors = [c['name'] for c in crew if c['job'] == 'Director']
            writers = [c['name'] for c in crew if c['job'] in ['Writer', 'Screenplay']]
            
            if directors:
                mp4['\xa9ART'] = ', '.join(directors)  # Artist (used for director)
            if writers:
                mp4['\xa9wrt'] = ', '.join(writers)  # Writer
        
        # Actors
        if metadata.get('credits', {}).get('cast'):
            cast = metadata['credits']['cast'][:10]  # Top 10 actors
            actors = [f"{c['name']} as {c['character']}" for c in cast if c.get('character')]
            if actors:
                mp4['\xa9act'] = '\n'.join(actors)  # Actors
        
        # Rating (MPAA)
        if metadata.get('releases', {}).get('countries'):
            us_release = None
            for country in metadata['releases']['countries']:
                if country['iso_3166_1'] == 'US':
                    us_release = country
                    break
            
            if us_release and us_release.get('certification'):
                mp4['\xa9rat'] = us_release['certification']  # Rating
        
        # Studio
        if metadata.get('production_companies'):
            studios = [c['name'] for c in metadata['production_companies']]
            if studios:
                mp4['\xa9cpy'] = studios[0]  # Copyright (used for studio)
        
        # Custom freeform atoms for additional data
        freeform_data = {}
        
        # IMDb ID
        if metadata.get('imdb_id'):
            freeform_data['imdb_id'] = metadata['imdb_id']
        
        # TMDb ID
        if metadata.get('id'):
            freeform_data['tmdb_id'] = str(metadata['id'])
        
        # Runtime
        if metadata.get('runtime'):
            freeform_data['runtime'] = str(metadata['runtime'])
        
        # Budget/Revenue
        if metadata.get('budget'):
            freeform_data['budget'] = str(metadata['budget'])
        if metadata.get('revenue'):
            freeform_data['revenue'] = str(metadata['revenue'])
        
        # Keywords
        if metadata.get('keywords', {}).get('keywords'):
            keywords = [k['name'] for k in metadata['keywords']['keywords']]
            freeform_data['keywords'] = ', '.join(keywords)
        
        # Write freeform atoms
        for key, value in freeform_data.items():
            if value:
                freeform_key = f"----:com.apple.iTunes:{key}"
                encoded_value = value.encode('utf-8')
                mp4[freeform_key] = [MP4FreeForm(encoded_value)]
        
        # Poster/Artwork
        if metadata.get('poster_path'):
            poster_url = f"https://image.tmdb.org/t/p/original{metadata['poster_path']}"
            poster_data = download_image(poster_url)
            if poster_data:
                mp4['covr'] = [MP4Cover(poster_data, MP4Cover.FORMAT_JPEG)]
                print(f"Added poster from TMDb")
        
        # Save changes
        mp4.save()
        return True
        
    except Exception as e:
        print(f"Error writing metadata to {file_path}: {e}")
        return False

def parse_title_year_from_filename(file_path):
    """Extract title and year from filename."""
    filename = os.path.basename(file_path)
    import re
    
    # Look for (YYYY) pattern
    match = re.search(r'(.+?)\s*\((\d{4})\)', filename)
    if match:
        title = match.group(1).replace('.', ' ').strip()
        year = int(match.group(2))
        return title, year
    
    return None, None

def main():
    _load_env()
    parser = argparse.ArgumentParser(description='Tag movie files with comprehensive metadata')
    parser.add_argument('paths', nargs='+', help='Movie file(s) or directory')
    parser.add_argument('--imdb-id', help='IMDb ID (tt#######)')
    parser.add_argument('--tmdb-id', help='TMDb ID')
    parser.add_argument('--title', help='Movie title (for search)')
    parser.add_argument('--year', type=int, help='Release year (for search)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without writing')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--recursive', action='store_true', help='Process directories recursively')
    
    args = parser.parse_args()
    
    if not any([args.imdb_id, args.tmdb_id, args.title]):
        print("Error: Must provide either --imdb-id, --tmdb-id, or --title")
        sys.exit(1)
    
    # Find movie files
    movie_files = []
    for path in args.paths:
        if os.path.isfile(path):
            movie_files.append(path)
        elif os.path.isdir(path):
            if args.recursive:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.m4v')):
                            movie_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(path):
                    if file.lower().endswith(('.mp4', '.m4v')):
                        movie_files.append(os.path.join(path, file))
    
    if not movie_files:
        print("No movie files found")
        return
    
    print(f"Found {len(movie_files)} movie file(s)")
    
    for file_path in movie_files:
        print(f"\nProcessing: {file_path}")
        
        # Try to find IDs from file if not provided
        imdb_id = args.imdb_id or find_imdb_id_from_file(file_path)
        tmdb_id = args.tmdb_id or find_tmdb_id_from_file(file_path)
        title = args.title
        year = args.year
        
        if not title and not imdb_id and not tmdb_id:
            title, year = parse_title_year_from_filename(file_path)
        
        if args.verbose:
            print(f"  IMDb ID: {imdb_id}")
            print(f"  TMDb ID: {tmdb_id}")
            print(f"  Title: {title}")
            print(f"  Year: {year}")
        
        # Fetch metadata
        metadata = get_tmdb_metadata(imdb_id, tmdb_id, title, year)
        
        if not metadata and imdb_id:
            # Try OMDb as backup
            metadata = get_omdb_metadata(imdb_id)
        
        if not metadata:
            print(f"  No metadata found for {file_path}")
            continue
        
        if args.verbose:
            print(f"  Found: {metadata.get('title', 'Unknown')} ({metadata.get('release_date', 'Unknown')[:4]})")
            print(f"  Genres: {', '.join([g['name'] for g in metadata.get('genres', [])])}")
            print(f"  Overview: {metadata.get('overview', 'No overview')[:100]}...")
        
        # Write metadata
        success = write_metadata_to_file(file_path, metadata, args.dry_run)
        if success:
            print(f"  {'[DRY RUN] Would write' if args.dry_run else 'Wrote'} metadata to {file_path}")
        else:
            print(f"  Failed to write metadata to {file_path}")

if __name__ == '__main__':
    main()
