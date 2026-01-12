#!/usr/bin/env python3
"""
Fix music videos in the secondary collection at /Volumes/Macintosh HD 2/Library/Videos/Music
Creates artist folders and moves/renames files with proper metadata tagging.
Based on fix_music_videos_mapped.py but with separate mappings to avoid collisions.
"""

import os
import sys
import re
import unicodedata
import shutil
from pathlib import Path
from dotenv import load_dotenv
from mutagen.mp4 import MP4

# Load environment variables
load_dotenv()

# Configuration
SOURCE_ROOT = Path("/Volumes/Macintosh HD 2/Library/Videos/Music")
TARGET_ROOT = Path("/Volumes/Macintosh HD 2/Library/Videos/Music")  # Same directory, will organize into subfolders
VERBOSE = True
DRY_RUN = False

# Hardcoded mapping for this specific collection
MUSIC_VIDEO_MAPPING = {
    # Pop/Rock
    "Billy Joel - Turn the Lights Back On (Official Lyric Video).mp4": ("Billy Joel", "Turn the Lights Back On"),
    "Boston - More Than a Feeling.mp3": ("Boston", "More Than a Feeling"),
    "Chicago - If You Leave Me Now (Official Audio).mp4": ("Chicago", "If You Leave Me Now"),
    "Daryl Hall & John Oates - You Make My Dreams.mp4": ("Daryl Hall & John Oates", "You Make My Dreams"),
    "Daryl Hall & John Oates - You Make My Dreams.mp3": ("Daryl Hall & John Oates", "You Make My Dreams"),
    "Foreigner - Waiting For A Girl Like You (Official Vinyl Video).mp4": ("Foreigner", "Waiting For A Girl Like You"),
    "Steve Perry - Oh Sherrie.mp3": ("Steve Perry", "Oh Sherrie"),
    "The Beatles - Something.mp4": ("The Beatles", "Something"),
    "The Cars - Drive.mp3": ("The Cars", "Drive"),
    "The Cars - Magic.mp3": ("The Cars", "Magic"),
    "The Cars - Shake It Up.mp3": ("The Cars", "Shake It Up"),
    "Toto - Africa.mp3": ("Toto", "Africa"),
    
    # 80s Rock/New Wave
    "Asia - Heat Of The Moment.mp3": ("Asia", "Heat of the Moment"),
    "David Lee Roth - Forgiveness.mp4": ("David Lee Roth", "Forgiveness"),
    "David Lee Roth - Somewhere Over The Rainbow Bar and Grill.mp4": ("David Lee Roth", "Somewhere Over the Rainbow Bar and Grill"),
    "Generation X - One Hundred Punks.mp4": ("Generation X", "One Hundred Punks"),
    "Huey Lewis & The News - Do You Believe In Love.mp3": ("Huey Lewis & The News", "Do You Believe in Love"),
    "Huey Lewis & The News - Walking On A Thin Line.mp3": ("Huey Lewis & The News", "Walking on a Thin Line"),
    "Mr. Mister - Broken Wings.mp3": ("Mr. Mister", "Broken Wings"),
    "Survivor - High On You.mp3": ("Survivor", "High on You"),
    "The Time - Girl - The Time.mp4": ("The Time", "Girl"),
    
    # Funk/Soul/Disco
    "Earth, Wind & Fire - December (Official Video).mp4": ("Earth, Wind & Fire", "December"),
    "George Benson - Give Me The Night.mp4": ("George Benson", "Give Me the Night"),
    "Midnight Star - No Parking On The Dance Floor.mp3": ("Midnight Star", "No Parking on the Dance Floor"),
    "Mike & The Mechanics - All I Need Is a Miracle.mp3": ("Mike & The Mechanics", "All I Need Is a Miracle"),
    "Missing Persons - Walking In L.A..mp4": ("Missing Persons", "Walking in L.A."),
    
    # Classic Rock
    "Bob Dylan - Don't Think Twice, It's All Right (Official Audio).mp4": ("Bob Dylan", "Don't Think Twice, It's All Right"),
    "Bob Seger - Against the Wind.mp3": ("Bob Seger", "Against the Wind"),
    "Bruce - Rick Springfield.mp4": ("Rick Springfield", "Bruce"),
    "Don't Do Me Like That.mp4": ("Tom Petty and the Heartbreakers", "Don't Do Me Like That"),
    "Sammy Hagar - I'll Fall In Love Again.mp4": ("Sammy Hagar", "I'll Fall in Love Again"),
    
    # 60s/70s
    "Bing Crosby - San Fernando Valley 1944 Vic Schoen's Orchestra.mp4": ("Bing Crosby", "San Fernando Valley"),
    "Doris Day Greatest Hits - The Best Songs Of Doris Day - Full Album.mp4": ("Doris Day", "Greatest Hits"),
    "Ella Fitzgerald - The Ella Fitzgerald Live Selection (Full Album).mp4": ("Ella Fitzgerald", "Live Selection"),
    "The Five Stairsteps - O-o-h Child (Audio).mp4": ("The Five Stairsteps", "O-o-h Child"),
    "The Ronettes - Be My Baby (Official Audio).mp4": ("The Ronettes", "Be My Baby"),
    
    # Classical/Instrumental
    "101 Strings - The Soul Of Spain.mp4": ("101 Strings", "The Soul of Spain"),
    "101 Strings - The soul of Mexico (1963) Full vinyl LP.mp4": ("101 Strings", "The Soul of Mexico"),
    "L. V. Beethoven - Violin Concerto in D major Op, 61 (David Oistrakh) (2).mp4": ("Ludwig van Beethoven", "Violin Concerto in D major, Op. 61"),
    "Violin Concerto in D Major, Op. 61_ I. Allegro ma non troppo.mp4": ("Ludwig van Beethoven", "Violin Concerto in D major, Op. 61 - I. Allegro ma non troppo"),
    "Violin Concerto in D Major, Op. 61_ II. Larghetto.mp4": ("Ludwig van Beethoven", "Violin Concerto in D major, Op. 61 - II. Larghetto"),
    "Violin Concerto in D Major, Op. 61_ III. Rondo. Allegro.mp4": ("Ludwig van Beethoven", "Violin Concerto in D major, Op. 61 - III. Rondo. Allegro"),
    
    # Soundtracks/Themes
    "Alan Silvestri - Cast Away Theme (Cast Away Soundtrack) [HQ].mp4": ("Alan Silvestri", "Cast Away Theme"),
    "20th century fox theme song.mp4": ("20th Century Fox", "Theme Song"),
    "Cheers intro song.mp4": ("Various", "Cheers Theme Song"),
    
    # Electronic/Synth
    "Daft Punk - Around The World.mp4": ("Daft Punk", "Around the World"),
    "Giorgio Moroder - Chase (Casablanca Records 1978).mp4": ("Giorgio Moroder", "Chase"),
    "Thomas Dolby - One of our Submarines.mp3": ("Thomas Dolby", "One of Our Submarines"),
    
    # Hip Hop/Rap
    "Ice Cube - Hood Robbin' (Official Lyric Video).mp4": ("Ice Cube", "Hood Robbin'"),
    "Rappin 4 Tay - Players Club.mp4": ("Rappin' 4 Tay", "Players Club"),
    
    # Modern/Indie
    "Janelle Monáe - Dirty Computer (feat. Brian Wilson).mp4": ("Janelle Monáe", "Dirty Computer"),
    "Mr.Kitty - After Dark.mp4": ("Mr. Kitty", "After Dark"),
    "LukHash - Better Than Reality [FULL ALBUM].mp4": ("LukHash", "Better Than Reality"),
    "LukHash - Patch It!.mp4": ("LukHash", "Patch It!"),
    "Aldo Nova-Busted Up-Army of Ghosts-ft. Emil.mp4": ("Aldo Nova", "Busted Up"),
    
    # Country
    "Go Rest High On That Mountain - Vince Gill (lyrics).mp4": ("Vince Gill", "Go Rest High on That Mountain"),
    
    # International
    "劉美君 - 亞熱帶少年 Subtropical Boy.mp4": ("劉美君", "亞熱帶少年 (Subtropical Boy)"),
    
    # Various Artists (compilations that should be preserved as-is)
    "80's R&B Soul Groove Mix.mp4": ("Various", "80's R&B Soul Groove Mix"),
    "FUNKY SOUL - Chic, KC & the Sunshine Band, Kool & The Gang, Sister Sledge and more.mp4": ("Various", "Funky Soul Mix"),
    "Funk Soul Classics.mp4": ("Various", "Funk Soul Classics"),
    "Greatest Funk Songs - The Best Funk Hits of All Time.mp4": ("Various", "Greatest Funk Songs"),
    "LEGENDARY OLD SCHOOL HIP HOP MIX 🔥🔥🔥 Snoop Dogg, Dr. Dre, 50 Cent, 2Pac, Ice Cube, Eminem & More.mp4": ("Various", "Legendary Old School Hip Hop Mix"),
    "The 100 Greatest Soul Songs of the 70s   Unforgettable Soul Music Full Playlist.mp4": ("Various", "100 Greatest Soul Songs of the 70s"),
    "Ultimate Old School Funk Mix Complete 3 Hours.mp4": ("Various", "Ultimate Old School Funk Mix"),
    "MeatLoaf's Greatest Hits | Best Songs of MeatLoaf - Full Album MeatLoaf NEW Playlist 2021.mp4": ("Meat Loaf", "Greatest Hits"),
    "Bedroom Pop Playlist | Vol. 1.mp4": ("Various", "Bedroom Pop Playlist Vol. 1"),
    "Best Songs Of Frank Sinatra New Playlist 2022 - Frank Sinatra Greatest Hits Full ALbum Ever.mp4": ("Frank Sinatra", "Greatest Hits"),
    "Chess Original Concept Album (complete).mp4": ("Various", "Chess Original Concept Album"),
    "Doris Day Greatest Hits - The Best Songs Of Doris Day - Full Album.mp4": ("Doris Day", "Greatest Hits"),
    "Ella Fitzgerald - The Ella Fitzgerald Live Selection (Full Album).mp4": ("Ella Fitzgerald", "Live Selection"),
    "Funkadelic-Funkadelic (1970) (Full Album).mp4": ("Funkadelic", "Funkadelic"),
    "Michael Jackson - Off The Wall Full Album.mp4": ("Michael Jackson", "Off the Wall"),
    "Michael Jackson Unreleased 1990 Vault (Full Album).mp4": ("Michael Jackson", "Unreleased 1990 Vault"),
    "Morning Star.mp4": ("Morning Star", "Morning Star"),
    "NAT KING COLE Greatest Hits Full Album - Best Of NAT KING COLE 2021 - NAT KING COLE Jazz Songs.mp4": ("Nat King Cole", "Greatest Hits"),
    "Phoenix Orion and Team Eloheem - Secret Wars (2001 Full Album).mp4": ("Phoenix Orion and Team Eloheem", "Secret Wars"),
    "R A M M S T E I N Greatest Hits Full Album - Best Songs Of R A M M S T E I N Playlist 2021.mp4": ("Rammstein", "Greatest Hits"),
    "Rammstein - (Lincoln Financial Field) Philadelphia,Pa 8.31.22 (Vollständig Senden).mp4": ("Rammstein", "Live at Lincoln Financial Field"),
    "THE BEST FREESTYLE MIXMASTER MEGAMIX 2 {DJ PINOCHIO} (1).mp4": ("Various", "Best Freestyle Mixmaster Megamix"),
    "Top 100 Best Old Country Songs Of All Time - Don Williams, Kenny Rogers, Willie Nelson, John Denver.mp4": ("Various", "Top 100 Best Old Country Songs"),
    
    # Additional individual songs
    "In My Life (Remastered 2009).mp4": ("The Beatles", "In My Life"),
    "Nothing Could Have Stopped Us Back Then Anyway.mp4": ("Donald Fagen", "Nothing Could Have Stopped Us Back Then Anyway"),
    "I.G.Y..mp4": ("Donald Fagen", "I.G.Y."),
    "Let's Go.mp4": ("The Cars", "Let's Go"),
    "Can't Take My Eyes off You.mp4": ("Frankie Valli", "Can't Take My Eyes Off You"),
    "Deja Vu (I've Been Here Before).mp4": (" Crosby, Stills, Nash & Young", "Deja Vu"),
    "Distractions (Remastered 2017).mp4": ("Crosby, Stills, Nash & Young", "Distractions"),
    "Drive.mp4": ("The Cars", "Drive"),
    "Magic (2016 Remaster).mp4": ("The Cars", "Magic"),
    "Broken Wings.mp4": ("Mr. Mister", "Broken Wings"),
    "Temptation.mp4": ("Temptation", "Temptation"),
    "This Is Not America (2002 Remaster).mp4": ("David Bowie & Pat Metheny Group", "This Is Not America"),
    "Whatever Happened To True Love.mp4": ("David Bowie", "Whatever Happened To True Love"),
    "Nitro.mp4": ("Nitro", "Nitro"),
    "Only A Lad.mp4": ("Oingo Boingo", "Only a Lad"),
    "As.mp4": ("Steely Dan", "As"),
    "Ballad of Dwight Fry.mp4": ("Alice Cooper", "Ballad of Dwight Fry"),
    "Joni Mitchell-A Case of You.mp4": ("Joni Mitchell", "A Case of You"),
    "The Alan Parsons Project - Time (Official Audio).mp4": ("The Alan Parsons Project", "Time"),
    "KOOL & THE GANG VS EARTH, WIND & FIRE.mp4": ("Various", "Kool & The Gang vs Earth, Wind & Fire"),
    "16 With a Little Luck [DJ Edit].mp3": ("Paul McCartney", "With a Little Luck"),
    "04 Peanut Butter.mp3": ("Peanut Butter", "Peanut Butter"),
    "07 Silly Love Songs {Wings at the Speed of Sound + Single}.mp3": ("Paul McCartney & Wings", "Silly Love Songs"),
    "08 Pipes of Peace.mp3": ("Paul McCartney", "Pipes of Peace"),
    "38 Special - If I'd Been The One.mp3": ("38 Special", "If I'd Been The One"),
    "Dolly Parton, Kenny Rogers - Islands In The Stream (Official Audio).mp4": ("Dolly Parton & Kenny Rogers", "Islands In The Stream"),
    "Eva Cassidy - Who Knows Where The Time Goes.mp4": ("Eva Cassidy", "Who Knows Where The Time Goes"),
    "Here I Go Again (1987 Version) (2017 Remaster).mp4": ("Whitesnake", "Here I Go Again"),
    "How Long Blues (78rpm Version).mp4": ("Count Basie", "How Long Blues"),
    "HOW LONG BLUES _ COUNT BASIE and his ALL AMERICAN RHYTHM SECTION [COLUMBIA 36710].mp4": ("Count Basie", "How Long Blues"),
    "Jackson Browne - Somebody's Baby.mp3": ("Jackson Browne", "Somebody's Baby"),
    "Sammy Hagar - I'll Fall In Love Again.mp3": ("Sammy Hagar", "I'll Fall in Love Again"),
    "Survivor - High On You.mp3": ("Survivor", "High on You"),
    "Survivor - High On You.mp4": ("Survivor", "High on You"),
    "Mr. Mister - Broken Wings.mp3": ("Mr. Mister", "Broken Wings"),
    "Mr. Mister - Broken Wings.mp4": ("Mr. Mister", "Broken Wings"),
    "George Benson - Give Me The Night.mp3": ("George Benson", "Give Me the Night"),
    "Earth, Wind & Fire - December.mp3": ("Earth, Wind & Fire", "December"),
    
    # Final remaining files
    "Ice Cube - Hood Robbin' (Official Lyric Video).mp4": ("Ice Cube", "Hood Robbin'"),
    "Ice Cube - Hood Robbin' (Official Lyric Video).mp4": ("Ice Cube", "Hood Robbin'"),
    "1O1$trings 0rchestra! Romantic H.D. 3-Hr. Beautiful Music Mega-Album! #ProfHowdy.mp4": ("101 Strings Orchestra", "Romantic HD Beautiful Music Mega-Album"),
    "Greatest Oldies But Goodies 50s 60s 70s - Engelbert , Andy Williams, Paul Anka,  Elvis Presley.mp4": ("Various", "Greatest Oldies But Goodies 50s 60s 70s"),
    "101 Strings Orchestra Major 5-Hour H.D. Easy Listening 1950's Music Album!.mp4": ("101 Strings Orchestra", "5-Hour HD Easy Listening 1950's Music Album"),
    "Madonna Material Girl (Chinese Version).mp4": ("Madonna", "Material Girl (Chinese Version)"),
    "Foreigner   I Want To Know What Love Is Longer Ultrasound Version.mp4": ("Foreigner", "I Want To Know What Love Is (Longer Ultrasound Version)"),
    "David Lee Roth - MANDA BALA...mp4": ("David Lee Roth", "Manda Bala"),
    "#DJThrowback #FunkMix #OldSchoolMix Best Old School Funk Mix on YouTube-D.J. Throwback.mp4": ("Various", "Best Old School Funk Mix"),
}

def canonicalize_key(raw: str) -> str:
    """Normalize filename for matching."""
    s = unicodedata.normalize("NFKC", raw).lower()
    s = s.replace("'", "'").replace("'", "'").replace("'", "'").replace("'", "'")  # Handle various apostrophe types
    s = s.replace(""", '"').replace(""", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("_", " ")
    s = re.sub(r"[^\w\s\u00A1-\uFFFF]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    
    # Remove trailing bracketed/parenthetical groups
    suffix_pattern = re.compile(r"\b(full album|official video|official audio|lyric video|hq|hd|remastered|remaster|edit|version|mix)\b")
    while True:
        prev = s
        s = re.sub(r"\s*\[[^\]]*\]\s*$", "", s)
        s = re.sub(r"\s*\([^\)]*\)\s*$", "", s)
        s = suffix_pattern.sub("", s)
        s = re.sub(r"\s+\d{4}\s*$", "", s)
        s = re.sub(r"\s+['']?\d{2}\s*$", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        if s == prev:
            break
    return s

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Strip leading/trailing spaces and dots
    filename = filename.strip(' .')
    return filename

def create_artist_folder(artist: str, base_path: Path) -> Path:
    """Create artist folder if it doesn't exist."""
    safe_artist = sanitize_filename(artist)
    artist_folder = base_path / safe_artist
    if not DRY_RUN:
        artist_folder.mkdir(exist_ok=True)
    return artist_folder

def update_metadata(file_path: Path, artist: str, title: str) -> bool:
    """Update MP4 metadata with artist and title."""
    try:
        mp4 = MP4(file_path)
        changed = False
        
        # Set title
        if '\xa9nam' not in mp4 or mp4['\xa9nam'][0] != title:
            mp4['\xa9nam'] = [title]
            changed = True
        
        # Set artist
        if '\xa9ART' not in mp4 or mp4['\xa9ART'][0] != artist:
            mp4['\xa9ART'] = [artist]
            changed = True
        
        # Also set standard tags for compatibility
        mp4['TITLE'] = [title]
        mp4['ARTIST'] = [artist]
        
        # Set media type to music video
        mp4['stik'] = [6]  # 6 = Music Video (iTunes/Apple standard)
        
        if changed and not DRY_RUN:
            mp4.save()
            if VERBOSE:
                print(f"  Updated metadata: Artist='{artist}', Title='{title}'")
        elif VERBOSE:
            print(f"  Metadata already correct")
        
        return True
    except Exception as e:
        print(f"  Error updating metadata: {e}")
        return False

def process_file(file_path: Path, mapping: dict) -> tuple[str, str]:
    """Process a single music video file."""
    print(f"\nProcessing: {file_path.name}")
    
    try:
        # Find mapping via canonical key
        canonical_name = canonicalize_key(file_path.name)
        
        artist, title = None, None
        
        # Try exact filename match first
        if file_path.name in mapping:
            artist, title = mapping[file_path.name]
        else:
            # Try canonical match
            for filename in mapping:
                if canonicalize_key(filename) == canonical_name:
                    artist, title = mapping[filename]
                    break
        
        if not artist or not title:
            print(f"  No mapping found - skipping")
            return "skipped", file_path
        
        # Create artist folder
        artist_folder = create_artist_folder(artist, TARGET_ROOT)
        
        # Generate new filename
        safe_title = sanitize_filename(title)
        extension = file_path.suffix
        new_filename = f"{safe_title}{extension}"
        new_path = artist_folder / new_filename
        
        # Handle duplicates
        counter = 1
        while new_path.exists():
            new_filename = f"{safe_title} ({counter}){extension}"
            new_path = artist_folder / new_filename
            counter += 1
        
        print(f"  Artist: {artist}")
        print(f"  Title: {title}")
        print(f"  Target: {new_path.relative_to(TARGET_ROOT.parent)}")
        
        if DRY_RUN:
            print(f"  [DRY RUN] Would move and tag file")
            return "changed", new_path
        
        # Move file
        try:
            shutil.move(str(file_path), str(new_path))
            print(f"  Moved file to artist folder")
        except Exception as e:
            print(f"  Error moving file: {e}")
            return "error", file_path
        
        # Update metadata
        if update_metadata(new_path, artist, title):
            return "changed", new_path
        else:
            return "error", new_path
            
    except Exception as e:
        print(f"  Unexpected error processing file: {e}")
        return "error", file_path

def main():
    """Main processing function."""
    global DRY_RUN
    
    # Check for dry-run flag
    if "--dry-run" in sys.argv:
        DRY_RUN = True
        print("DRY RUN MODE - No files will be moved or modified")
    
    if not SOURCE_ROOT.exists():
        print(f"Error: Source directory not found: {SOURCE_ROOT}")
        sys.exit(1)
    
    print(f"Processing music videos in: {SOURCE_ROOT}")
    print(f"Target directory: {TARGET_ROOT}")
    
    # Counters
    processed = 0
    changed = 0
    skipped = 0
    errors = 0
    
    # Process all files
    for file_path in SOURCE_ROOT.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mp3']:
            status, result_path = process_file(file_path, MUSIC_VIDEO_MAPPING)
            processed += 1
            
            if status == "changed":
                changed += 1
            elif status == "skipped":
                skipped += 1
            elif status == "error":
                errors += 1
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {processed}")
    print(f"Files moved/renamed: {changed}")
    print(f"Files skipped (no mapping): {skipped}")
    print(f"Errors: {errors}")
    
    if DRY_RUN:
        print(f"\nDRY RUN - No actual changes made")
    else:
        print(f"\nFiles organized into artist folders in: {TARGET_ROOT}")

if __name__ == "__main__":
    main()
