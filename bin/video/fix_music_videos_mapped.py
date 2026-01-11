#!/usr/bin/env python3
"""
Music Video Filename and Metadata Normalizer (Mapping-based)

This script uses a predefined mapping to normalize music video filenames and metadata.
It processes files based on exact filename matches to the reference table.

Usage:
    python3 bin/video/fix_music_videos_mapped.py /path/to/Music/Videos [--dry-run]
"""

import argparse
import csv
import os
import re
import sys
import unicodedata
import difflib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

VERBOSE = False

try:
    from mutagen.mp4 import MP4, MP4FreeForm
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    missing = str(e).split("required")[0].strip() if "required" in str(e) else str(e)
    print(f"Error: Missing dependencies - {missing}")
    print("Install with: pip install mutagen")
    sys.exit(1)


def load_dotenv(repo_root: Path) -> None:
    """Load .env file if present."""
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # If python-dotenv not available, try simple parsing
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def get_library_root() -> Path:
    """Get library root from environment or default."""
    # Try LIBRARY_ROOT from environment
    lib_root = os.getenv('LIBRARY_ROOT')
    if lib_root:
        return Path(lib_root)
    
    # Fallback to default
    return Path("/Volumes/Data/Media/Library")


def canonicalize_key(raw: str) -> str:
    """Normalize filenames so small variations still match mapping."""
    s = unicodedata.normalize("NFKC", raw).lower()

    # Normalize common punctuation/spacing variations
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("_", " ")

    # Treat most punctuation as separators (helps & vs , vs - variations)
    s = re.sub(r"[^\w\s\u00A1-\uFFFF]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()

    suffix_pattern = re.compile(
        r"\s*(official\s+video|official\s+music\s+video|music\s+video|official\s+lyric\s+video|lyric\s+video|video\s+remastered|remastered|hq|hd|4k|1080p|720p|mv|m\s*v)\s*$"
    )

    # Iteratively strip trailing noise until stable
    while True:
        prev = s

        # Strip trailing bracketed/parenthetical groups (repeatable)
        s = re.sub(r"\s*\[[^\]]*\]\s*$", "", s)
        s = re.sub(r"\s*\([^\)]*\)\s*$", "", s)

        # Strip known suffix tokens
        s = suffix_pattern.sub("", s)

        # Strip trailing year like 1982
        s = re.sub(r"\s+\d{4}\s*$", "", s)

        # Strip trailing short year like '71 or 71
        s = re.sub(r"\s+['’]?\d{2}\s*$", "", s)

        # Strip trailing punctuation-like leftovers
        s = re.sub(r"\s+", " ", s).strip()

        if s == prev:
            break

    return s


def load_mapping() -> Dict[str, Tuple[str, str]]:
    """Load the filename mapping from the reference table."""
    mapping: Dict[str, Tuple[str, str]] = {}
    
    # Format: original_filename -> (clean_artist, clean_title)
    mapping_data = [
        ("Warrant - Uncle Tom's Cabin (Official Video).mp4", ("Warrant", "Uncle Tom's Cabin")),
        ("El DeBarge - Who's Johnny (High Quality).mp4", ("El DeBarge", "Who's Johnny")),
        ("Martha Argerich & grandson, David Chen, play Ravel's Laideronnette, impératrice des pagodes.mp4", ("Maurice Ravel", "Laideronnette, impératrice des pagodes (Ma mère l'Oye)")),
        ("Bee Gees - Jive Talkin'.mp4", ("Bee Gees", "Jive Talkin'")),
        ("Bee Gees _ How Can You Mend a Broken Heart ('71) HQ (with lyrics).mp4", ("Bee Gees", "How Can You Mend a Broken Heart")),
        ("Bee Gees - Too Much Heaven.mp4", ("Bee Gees", "Too Much Heaven")),
        ("Bee Gees - How Deep Is Your Love (Official Video).mp4", ("Bee Gees", "How Deep Is Your Love")),
        ("Bobby Womack - American Dream (Official Lyric Video).mp4", ("Bobby Womack", "American Dream")),
        ("Shalamar - \"A Night To Remember\" (Official HD Video).mp4", ("Shalamar", "A Night to Remember")),
        ("George Harrison - This Song.mp4", ("George Harrison", "This Song")),
        ("Gnarls Barkley Crazy Theremin Jam.mp4", ("Gnarls Barkley", "Crazy")),
        ("Julian Lennon - Too Late for Goodbyes.mp4", ("Julian Lennon", "Too Late for Goodbyes")),
        ("The Time - Oh Baby - The Time.mp4", ("The Time", "Oh Baby")),
        ("The Time - Cool (Official Music Video) [HD].mp4", ("The Time", "Cool")),
        ("Modern English - I Melt With You (from Quarantine).mp4", ("Modern English", "I Melt with You")),
        ("2NE1 - 내가 제일 잘 나가(I AM THE BEST) M_V.mp4", ("2NE1", "내가 제일 잘 나가 (I Am the Best)")),
        ("Don Henley - The Boys Of Summer (Official Music Video).mp4", ("Don Henley", "The Boys of Summer")),
        ("HIRSCH - Love Is Real (Official Video).mp4", ("Hirsch", "Love Is Real")),
        ("The Alan Parsons Project - Time - 1981.mp4", ("The Alan Parsons Project", "Time")),
        ("Spandau Ballet - True (HD Remastered).mp4", ("Spandau Ballet", "True")),
        ("The Moody Blues - Your Wildest Dreams (Official Video).mp4", ("The Moody Blues", "Your Wildest Dreams")),
        ("The Moody Blues - I Know You're Out There Somewhere.mp4", ("The Moody Blues", "I Know You're Out There Somewhere")),
        ("James Taylor - Fire And Rain (BBC In Concert, 11_16_1970).mp4", ("James Taylor", "Fire and Rain")),
        ("The Sugarcubes - Birthday-(English) HD.mp4", ("The Sugarcubes", "Birthday")),
        ("The Sugarcubes - Hit - TOTP - 1992.mp4", ("The Sugarcubes", "Hit")),
        ("Rema, Selena Gomez - Calm Down (Official Music Video).mp4", ("Rema & Selena Gomez", "Calm Down")),
        ("Kenny Rogers - The Gambler.mp4", ("Kenny Rogers", "The Gambler")),
        ("Jackson Browne - Running On Empty - OFFICIAL VIDEO MONTAGE.mp4", ("Jackson Browne", "Running on Empty")),
        ("Jackson Browne- Somebody's Baby.mp4", ("Jackson Browne", "Somebody's Baby")),
        ("The Cars - Shake It Up (Official Music Video).mp4", ("The Cars", "Shake It Up")),
        ("The Cars - Drive (Official Music Video).mp4", ("The Cars", "Drive")),
        ("The Jacksons - Blame It On the Boogie (Official Video).mp4", ("The Jacksons", "Blame It on the Boogie")),
        ("The Jacksons - Can You Feel It.mp4", ("The Jacksons", "Can You Feel It")),
        ("Kool Keith - Livin' Astro (1999).mp4", ("Kool Keith", "Livin' Astro")),
        ("Earth, Wind & Fire - Let's Groove (Official HD Video).mp4", ("Earth, Wind & Fire", "Let's Groove")),
        ("Earth, Wind & Fire - September (Official HD Video).mp4", ("Earth, Wind & Fire", "September")),
        ("Frank Zappa, Moon Zappa - Valley Girl.mp4", ("Frank Zappa", "Valley Girl")),
        ("Styx - The Best Of Times (Official Video).mp4", ("Styx", "The Best of Times")),
        ("Black Eyed Peas, Shakira - GIRL LIKE ME (Official Music Video).mp4", ("Black Eyed Peas & Shakira", "Girl Like Me")),
        ("Daði Freyr – Think About Things (Official Video).mp4", ("Daði Freyr", "Think About Things")),
        ("Joe Jackson - Steppin' Out (Official Video).mp4", ("Joe Jackson", "Steppin' Out")),
        ("Joni Mitchell - River (Official Music Video).mp4", ("Joni Mitchell", "River")),
        ("Chicago - If you leave me now - 1977 (HQ).mp4", ("Chicago", "If You Leave Me Now")),
        ("David Bowie - Space Oddity.mp4", ("David Bowie", "Space Oddity")),
        ("Ozzy Osbourne - \"Mama, I'm Coming Home\".mp4", ("Ozzy Osbourne", "Mama, I'm Coming Home")),
        ("Supertramp - The Logical Song (Official Video).mp4", ("Supertramp", "The Logical Song")),
        ("Depeche Mode - Enjoy The Silence (Official Video).mp4", ("Depeche Mode", "Enjoy the Silence")),
        ("Billie Eilish - What Was I Made For?.mp4", ("Billie Eilish", "What Was I Made For?")),
        ("Fatboy Slim - Right Here, Right Now.mp4", ("Fatboy Slim", "Right Here, Right Now")),
        ("Leonard Nimoy - The Ballad of Bilbo Baggins.mp4", ("Leonard Nimoy", "The Ballad of Bilbo Baggins")),
        ("Prince - Controversy (Official Music Video).mp4", ("Prince", "Controversy")),
        ("Toto - Africa (Official HD Video).mp4", ("Toto", "Africa")),
        ("Bob Seger- Against the Wind.mp4", ("Bob Seger", "Against the Wind")),
        ("CeCe Peniston - Finally (Official Music Video).mp4", ("CeCe Peniston", "Finally")),
        ("Journey - Don't Stop Believin'.mp4", ("Journey", "Don't Stop Believin'")),
        ("Queen - Another One Bites the Dust (Official Video).mp4", ("Queen", "Another One Bites the Dust")),
        # Additional mappings to catch filename variations
        ("'Til Tuesday - Voices Carry.mp4", ("'Til Tuesday", "Voices Carry")),
        ("2NE1 - 내가 제일 잘 나가(I AM THE BEST) M_V.mp4", ("2NE1", "내가 제일 잘 나가 (I Am the Best)")),
        ("2NE1 - 내가 제일 잘 나가(I AM THE BEST) M_V.mp4", ("2NE1", "내가 제일 잘 나가 (I Am the Best)")),
        ("38 Special - If I'd Been The One (OFFICIAL VIDEO).mp4", ("38 Special", "If I'd Been the One")),
        ("A Flock Of Seagulls - Space Age Love Song 1982.mp4", ("A Flock of Seagulls", "Space Age Love Song")),
        ("Ace -  How Long HD.mp4", ("Ace", "How Long")),
        ("ALDO NOVA - Bright Lights.mp4", ("Aldo Nova", "Bright Lights")),
        ("Alice Cooper - \"Our Love Will Change The World\" - Official Lyric Video.mp4", ("Alice Cooper", "Our Love Will Change the World")),
        ("Aqua - Barbie Girl (Official Music Video).mp4", ("Aqua", "Barbie Girl")),
        ("Aqua - Cartoon Heroes.mp4", ("Aqua", "Cartoon Heroes")),
        ("Aqua - Turn Back Time.mp4", ("Aqua", "Turn Back Time")),
        ("Heat Of The Moment.mp4", ("Asia", "Heat of the Moment")),
        ("\"2020\" Lyric Video.mp4", ("Ben Folds", "2020")),
        ("Berlin - No More Words (Official Video).mp4", ("Berlin", "No More Words")),
        ("BIGBANG - FANTASTIC BABY M_V.mp4", ("BigBang", "Fantastic Baby")),
        ("Billie Eilish - What Was I Made For? [From The Motion Picture \"Barbie\"] (Official Video).mp4", ("Billie Eilish", "What Was I Made For?")),
        ("Billie Eilish - my future.mp4", ("Billie Eilish", "my future")),
        ("Billy Idol - Dancing With Myself (Official Music Video).mp4", ("Billy Idol", "Dancing With Myself")),
        ("Billy Idol - Eyes Without A Face (Official Music Video).mp4", ("Billy Idol", "Eyes Without a Face")),
        ("Billy Idol - Rebel Yell (Official Music Video).mp4", ("Billy Idol", "Rebel Yell")),
        ("Billy Idol - Save Me Now.mp4", ("Billy Idol", "Save Me Now")),
        ("Bone Thugs-N-Harmony - I Tried (Official Music Video) ft. Akon.mp4", ("Bone Thugs-N-Harmony", "I Tried")),
        ("Boston - More Than A Feeling - Remastered.mp4", ("Boston", "More Than a Feeling")),
        ("Gonna Make You Sweat (Everybody Dance Now) (Official HD Video).mp4", ("C+C Music Factory", "Gonna Make You Sweat (Everybody Dance Now)")),
        ("Calvin Harris - Acceptable in the 80's (Official Video).mp4", ("Calvin Harris", "Acceptable in the 80s")),
        ("Calvin Harris - Ready for the Weekend (Official Video).mp4", ("Calvin Harris", "Ready for the Weekend")),
        ("Is It Peace Or Is It Prozac?.mp4", ("Cheryl Wheeler", "Is It Peace or Is It Prozac?")),
        ("Chris de Burgh - Don't Pay The Ferryman.mp4", ("Chris de Burgh", "Don't Pay the Ferryman")),
        ("Chrispy&Gido Weihnacht im Julei 1080.mp4", ("Chrispy & Gido", "Weihnacht im Julei")),
        ("Culture Club (Boy George) - The war Song 1984.mp4", ("Culture Club", "The War Song")),
        ("Dan Hartman - I Can Dream About You.mp4", ("Dan Hartman", "I Can Dream About You")),
        ("Gratitude.mp4", ("Danny Elfman", "Gratitude")),
        ("Daryl Hall & John Oates - Maneater.mp4", ("Daryl Hall & John Oates", "Maneater")),
        ("David Lee Roth - Just Like Paradise.mp4", ("David Lee Roth", "Just Like Paradise")),
        ("David Lee Roth - Stand Up (Skyscraper '88).mp4", ("David Lee Roth", "Stand Up")),
        ("17 STRINGS Double Neck Bass Guitar Solo.mp4", ("Davide Biale", "17 STRINGS Double Neck Bass Guitar Solo")),
        ("Dax - \"Depression\" (Official Music Video).mp4", ("Dax", "Depression")),
        ("Dax - Dr. Dre ft. Snoop Dogg \"Still D.R.E.\" Remix [One Take Video].mp4", ("Dax", "Still D.R.E. Remix")),
        ("Daði Freyr (Daði & Gagnamagnið) – Think About Things (Official Video).mp4", ("Daði Freyr", "Think About Things")),
        ("DeBarge - I Like It.mp4", ("DeBarge", "I Like It")),
        ("Def Leppard - Bringin' On The Heartbreak (Version 1).mp4", ("Def Leppard", "Bringin' on the Heartbreak")),
        ("Dennis DeYoung (Formerly of Styx) - \"Isle of Misanthrope\" Official Music Video.mp4", ("Dennis DeYoung", "Isle of Misanthrope")),
        ("Dennis DeYoung - \"The Last Guitar Hero\" featuring Tom Morello - Lyric Video.mp4", ("Dennis DeYoung", "The Last Guitar Hero")),
        ("Depeche Mode - Halo (Official Video).mp4", ("Depeche Mode", "Halo")),
        ("Depeche Mode - Policy Of Truth (Official Video).mp4", ("Depeche Mode", "Policy of Truth")),
        ("Dr. Dre - Still D.R.E. (Official Music Video) ft. Snoop Dogg.mp4", ("Dr. Dre", "Still D.R.E.")),
        ("Eazy-E - Real Muthaphuckkin G's (Music Video).mp4", ("Eazy-E", "Real Muthaphuckkin G's")),
        ("ELO (Electric Light Orchestra) - Last Train To London.mp4", ("Electric Light Orchestra", "Last Train to London")),
        ("ELO (Electric Light Orchestra) - Telephone Line.mp4", ("Electric Light Orchestra", "Telephone Line")),
        ("ELO - CONFUSION.mp4", ("Electric Light Orchestra", "Confusion")),
        ("ELO - One Summer Dream.mp4", ("Electric Light Orchestra", "One Summer Dream")),
        ("Electric Light Orchestra - Ticket To The Moon (Official Video).mp4", ("Electric Light Orchestra", "Ticket to the Moon")),
        ("Eurythmics, Annie Lennox, Dave Stewart - Here Comes The Rain Again (Remastered).mp4", ("Eurythmics", "Here Comes the Rain Again")),
        ("Eurythmics, Annie Lennox, Dave Stewart - Miracle of Love (Video Remastered).mp4", ("Eurythmics", "Miracle of Love")),
        ("Eurythmics, Annie Lennox, Dave Stewart - Sweet Dreams (Are Made Of This) (Official Video).mp4", ("Eurythmics", "Sweet Dreams (Are Made of This)")),
        ("Dance - Fly By Midnight (Official Video).mp4", ("Fly By Midnight", "Dance")),
        ("Frankie Smith - Double Dutch Bus (Official Music Video).mp4", ("Frankie Smith", "Double Dutch Bus")),
        ("George Michael - Older (Official Video).mp4", ("George Michael", "Older")),
        ("George Michael - You Have Been Loved (Live).mp4", ("George Michael", "You Have Been Loved")),
        ("Gotye - Somebody That I Used To Know (feat. Kimbra) [Official Music Video].mp4", ("Gotye", "Somebody That I Used to Know")),
        ("Huey Lewis And The News - Do You Believe In Love (Official Music Video).mp4", ("Huey Lewis and the News", "Do You Believe in Love")),
        ("Huey Lewis And The News - Heart And Soul (Official Music Video).mp4", ("Huey Lewis and the News", "Heart and Soul")),
        ("Walking On A Thin Line.mp4", ("Huey Lewis and the News", "Walking on a Thin Line")),
        ("Ice Cube - Can You Dig It?.mp4", ("Ice Cube", "Can You Dig It?")),
        ("Ice Cube - That New Funkadelic (Official Music Video).mp4", ("Ice Cube", "That New Funkadelic")),
        ("Janet Jackson - Escapade.mp4", ("Janet Jackson", "Escapade")),
        ("Janet Jackson - Runaway (Official Video).mp4", ("Janet Jackson", "Runaway")),
        ("Jeff Goldblum & The Mildred Snitzer Orchestra feat. Haley Reinhart - My Baby Just Cares....mp4", ("Jeff Goldblum", "My Baby Just Cares for You")),
        ("Nobody Told Me - John Lennon (official music video HD).mp4", ("John Lennon", "Nobody Told Me")),
        ("JONGHYUN 종현 'Lonely (Feat. 태연)' MV.mp4", ("Jonghyun", "Lonely")),
        ("Journey - Any Way You Want It (Official HD Video - 1980).mp4", ("Journey", "Any Way You Want It")),
        ("Kanye West - Come to Life (Official Video).mp4", ("Kanye West", "Come to Life")),
        ("In Your Arms - Kina Grannis (Official Music Video) Stop Motion Animation.mp4", ("Kina Grannis", "In Your Arms")),
        ("Kylie Minogue - Real Groove (INFINITE DISCO).mp4", ("Kylie Minogue", "Real Groove")),
        ("LFO - 'Freak' | Future Shorts.mp4", ("LFO", "Freak")),
        ("Leonard Nimoy_ The Ballad of Bilbo Baggins - Full Album Version.mp4", ("Leonard Nimoy", "The Ballad of Bilbo Baggins")),
        ("Lindsey Buckingham - Go Insane (Official Music Video).mp4", ("Lindsey Buckingham", "Go Insane")),
        ("Lindsey Buckingham - Trouble (Official Music Video).mp4", ("Lindsey Buckingham", "Trouble")),
        ("Little River Band - Reminiscing (1978).mp4", ("Little River Band", "Reminiscing")),
        ("Lou Gramm - \"Midnight Blue\" - ORIGINAL VIDEO - stereo HQ (1).mp4", ("Lou Gramm", "Midnight Blue")),
        ("Ludwig van Beethoven Violin Concerto in D Major, Op. 61 - the best-known Violin Concertos.mp4", ("Ludwig van Beethoven", "Violin Concerto in D Major, Op. 61")),
        ("Mac Miller - Circles.mp4", ("Mac Miller", "Circles")),
        ("Mac Miller - Good News [Official Music Video].mp4", ("Mac Miller", "Good News")),
        ("Michael Jackson - Childhood (Official Video).mp4", ("Michael Jackson", "Childhood")),
        ("Michael Jackson - Earth Song (Official Video).mp4", ("Michael Jackson", "Earth Song")),
        ("Michael Jackson - Stranger In Moscow (Official Video).mp4", ("Michael Jackson", "Stranger in Moscow")),
        ("Midnight Star - No Parking On The Dance Floor (Official Music Video).mp4", ("Midnight Star", "No Parking on the Dance Floor")),
        ("Mike + The Mechanics - All I Need Is a Miracle (1985 LP Version) HQ.mp4", ("Mike + The Mechanics", "All I Need Is a Miracle")),
        ("Missing Persons - Walking In L.A..mp4", ("Missing Persons", "Walking in L.A.")),
        ("Missing Persons - Words.mp4", ("Missing Persons", "Words")),
        ("Mötley Crüe - Kickstart My Heart (Official Music Video).mp4", ("Mötley Crüe", "Kickstart My Heart")),
        ("NEWCLEUS - JAM ON IT.mp4", ("Newcleus", "Jam on It")),
        ("Nicolette Larson - Lotta Love (Official Music Video).mp4", ("Nicolette Larson", "Lotta Love")),
        ("OZZY OSBOURNE - \"Dreamer\" (Official Video).mp4", ("Ozzy Osbourne", "Dreamer")),
        ("PM Dawn - Set A Drift On Memory Bliss 1991.mp4", ("PM Dawn", "Set Adrift on Memory Bliss")),
        ("Paul McCartney & Wings - My Love (Official Music Video).mp4", ("Paul McCartney & Wings", "My Love")),
        ("Pentatonix - Last Christmas (Official Video) ft. HIKAKIN & SEIKIN.mp4", ("Pentatonix", "Last Christmas")),
        ("Peter Gabriel - Sledgehammer (HD version).mp4", ("Peter Gabriel", "Sledgehammer")),
        ("Puff the Magic Dragon by Peter Paul and Mary play along with scrolling guitar chords and lyrics.mp4", ("Peter, Paul and Mary", "Puff the Magic Dragon")),
        ("Pilot - Magic (1975 - HD).mp4", ("Pilot", "Magic")),
        ("Pink Floyd - High Hopes (Official Music Video HD).mp4", ("Pink Floyd", "High Hopes")),
        ("pink floyd - us and them.mp4", ("Pink Floyd", "Us and Them")),
        ("Powerman 5000 - Nobody's Real (Official Video).mp4", ("Powerman 5000", "Nobody's Real")),
        ("Prince - Silver Tongue (Official Audio).mp4", ("Prince", "Silver Tongue")),
        ("PSY - 'I LUV IT' M_V.mp4", ("Psy", "I LUV IT")),
        ("Brain Damage _ Eclipse (Pink Floyd Cover).mp4", ("Puddles Pity Party", "Brain Damage/Eclipse")),
        ("Queen - Don't Stop Me Now (Official Video).mp4", ("Queen", "Don't Stop Me Now")),
        ("REO Speedwagon - One Lonely Night.mp4", ("REO Speedwagon", "One Lonely Night")),
        ("Real Life - Send Me An Angel '89.mp4", ("Real Life", "Send Me an Angel")),
        ("Red Hot Chili Peppers - Can't Stop [Official Music Video].mp4", ("Red Hot Chili Peppers", "Can't Stop")),
        ("Red Hot Chili Peppers - Under The Bridge [Official Music Video].mp4", ("Red Hot Chili Peppers", "Under the Bridge")),
        ("Rod Stewart - Sailing (Official Video).mp4", ("Rod Stewart", "Sailing")),
        ("Roger - I Want To Be Your Man (Official Music Video).mp4", ("Roger", "I Want to Be Your Man")),
        ("Rupert's Kitchen Orchestra - Die Kopie (2019).mp4", ("Ruperts Kitchen Orchestra", "Die Kopie")),
        ("Rupert's Kitchen Orchestra - Horizont.mp4", ("Ruperts Kitchen Orchestra", "Horizont")),
        ("Rupert's Kitchen Orchestra - Weihnachten bei der AFD (Lyrics).mp4", ("Ruperts Kitchen Orchestra", "Weihnachten bei der AFD")),
        ("Rupert's Kitchen Orchestra - Youtube Universität (Lyrics).mp4", ("Ruperts Kitchen Orchestra", "Youtube Universität")),
        ("Rupert's Kitchen Orchestra ... derweil in Berlin.mp4", ("Ruperts Kitchen Orchestra", "...derweil in Berlin")),
        ("Ruperts Kitchen Orchestra - \"Social\"- Media- Schnippsel.mp4", ("Ruperts Kitchen Orchestra", "\"Social\"- Media- Schnippsel")),
        ("Ruperts Kitchen Orchestra - Der Jahresrückblick 2020.mp4", ("Ruperts Kitchen Orchestra", "Der Jahresrückblick 2020")),
        ("Ruperts Kitchen Orchestra - Die Erde.mp4", ("Ruperts Kitchen Orchestra", "Die Erde")),
        ("Ruperts Kitchen Orchestra - Jasagerwüste.mp4", ("Ruperts Kitchen Orchestra", "Jasagerwüste")),
        ("Ruperts Kitchen Orchestra - Jetzt und Hier - Live bei Mein4tel - TV am Alexanderplatz.mp4", ("Ruperts Kitchen Orchestra", "Jetzt und Hier - Live bei Mein4tel - TV")),
        ("Ruperts Kitchen Orchestra - Soul Kitchen - Live bei Mein4tel - TV.mp4", ("Ruperts Kitchen Orchestra", "Soul Kitchen - Live bei Mein4tel - TV")),
        ("Ruperts Kitchen Orchestra - Wie ein Blitz - Live bei Mein4tel - TV am Alexanderplatz.mp4", ("Ruperts Kitchen Orchestra", "Wie ein Blitz - Live bei Mein4tel - TV")),
        ("Unser letzter Jam 2020!.mp4", ("Ruperts Kitchen Orchestra", "Unser letzter Jam 2020")),
        ("Scorpions - Wind Of Change (Official Music Video).mp4", ("Scorpions", "Wind of Change")),
        ("Rema & Selena Gomez - Calm Down.mp4", ("Selena Gomez", "Calm Down")),
        ("Sheila E - The Glamorous Life (Live 1985).mp4", ("Sheila E.", "The Glamorous Life")),
        ("Snoop Dogg - Sensual Seduction.mp4", ("Snoop Dogg", "Sensual Seduction")),
        ("Soft Cell - Tainted Love (Official Music Video).mp4", ("Soft Cell", "Tainted Love")),
        ("Starland Vocal Band - Afternoon Delight (1976) Uncut Video.mp4", ("Starland Vocal Band", "Afternoon Delight")),
        ("Steve Perry - Oh Sherry (lyrics).mp4", ("Steve Perry", "Oh Sherry")),
        ("Supertramp - Dreamer.mp4", ("Supertramp", "Dreamer")),
        ("Supertramp - It's Raining Again.mp4", ("Supertramp", "It's Raining Again")),
        ("Teenage Priest - Cool to You [Official Video].mp4", ("Teenage Priest", "Cool to You")),
        ("The Alan Parsons Project - Time.mp4", ("The Alan Parsons Project", "Time")),
        ("The Alan Parsons Symphonic Project \"Time\" (Live in Colombia).mp4", ("The Alan Parsons Symphonic Project", "Time")),
        ("The B-52's - Roam (Official Music Video).mp4", ("The B-52s", "Roam")),
        ("The Beatles - Revolver (Full Album) [1966].mp4", ("The Beatles", "Revolver (Full Album)")),
        ("The Beatles - Something (1).mp4", ("The Beatles", "Something")),
        ("The Beatles - Something.mp4", ("The Beatles", "Something")),
        ("The Sugarcubes - Birthday.mp4", ("The Sugarcubes", "Birthday")),
        ("The Sugarcubes - Hit.mp4", ("The Sugarcubes", "Hit")),
        ("The Time - Oh Baby.mp4", ("The Time", "Oh Baby")),
        ("I Know What Boys Like  -  The Waitresses (HQ Audio).mp4", ("The Waitresses", "I Know What Boys Like")),
        ("The Waitresses - Christmas Wrapping (Music Video).mp4", ("The Waitresses", "Christmas Wrapping")),
        ("Dolby Kids - Corona and the Pirate Twins.mp4", ("Thomas Dolby", "Corona and the Pirate Twins")),
        ("Matthew Seligman_ 'The Brightest Star'.mp4", ("Thomas Dolby", "The Brightest Star")),
        ("Screen Kiss - For Matthew Seligman.mp4", ("Thomas Dolby", "Screen Kiss")),
        ("Thomas Dolby - She Blinded Me With Science (Official Video - HD Remaster).mp4", ("Thomas Dolby", "She Blinded Me With Science")),
        ("Toto - 99 (Official Video).mp4", ("Toto", "99")),
        ("Van Halen Hollywood Bowl Dance The Night Away Live 2015.mp4", ("Van Halen", "Dance the Night Away (Live)")),
        ("Wendy & Lisa - Are You My Baby.mp4", ("Wendy and Lisa", "Are You My Baby")),
        ("Wendy & Lisa - Honeymoon Express.mp4", ("Wendy and Lisa", "Honeymoon Express")),
        ("Wendy & Lisa - Waterfall (Video).mp4", ("Wendy and Lisa", "Waterfall")),
        ("Wham! - Club Tropicana (Official Video).mp4", ("Wham!", "Club Tropicana")),
        ("Witch Doctor - Ooh Eeh Ooh Ah Aah Ting Tang Walla Walla Bing.mp4", ("Witch Doctor", "Ooh Eeh Ooh Ah Aah Ting Tang Walla Walla Bing")),
        ("Wreckx N Effect - Rump Shaker.mp4", ("Wreckx-N-Effect", "Rump Shaker")),
        ("XG - MASCARA (Official Music Video).mp4", ("XG", "MASCARA")),
        ("a-ha - Summer Moved On (Official Video).mp4", ("a-ha", "Summer Moved On")),
        ("a-ha - Take On Me (Official 4K Music Video).mp4", ("a-ha", "Take On Me")),
        # Additional mappings for remaining unmapped songs (31 entries)
        ("Asia - Heat of the Moment.mp4", ("Asia", "Heat of the Moment")),
        ("Bee Gees - How Can You Mend a Broken Heart.mp4", ("Bee Gees", "How Can You Mend a Broken Heart")),
        ("Bone Thugs-N-Harmony - I Tried.mp4", ("Bone Thugs-N-Harmony", "I Tried")),
        ("C+C Music Factory - Gonna Make You Sweat (Everybody Dance Now).mp4", ("C+C Music Factory", "Gonna Make You Sweat (Everybody Dance Now)")),
        ("Calvin Harris - Acceptable in the 80s.mp4", ("Calvin Harris", "Acceptable in the 80s")),
        ("Culture Club - The War Song.mp4", ("Culture Club", "The War Song")),
        ("Dax - Still D.R.E. Remix.mp4", ("Dax", "Still D.R.E. Remix")),
        ("Def Leppard - Bringin' on the Heartbreak.mp4", ("Def Leppard", "Bringin' on the Heartbreak")),
        ("Dennis DeYoung - Isle of Misanthrope.mp4", ("Dennis DeYoung", "Isle of Misanthrope")),
        ("Dr. Dre - Still D.R.E..mp4", ("Dr. Dre", "Still D.R.E.")),
        ("Earth, Wind & Fire - Let's Groove.mp4", ("Earth, Wind & Fire", "Let's Groove")),
        ("Earth, Wind & Fire - September.mp4", ("Earth, Wind & Fire", "September")),
        ("El DeBarge - Who's Johnny.mp4", ("El DeBarge", "Who's Johnny")),
        ("Fly By Midnight - Dance.mp4", ("Fly By Midnight", "Dance")),
        ("Frank Zappa - Valley Girl.mp4", ("Frank Zappa", "Valley Girl")),
        ("George Michael - You Have Been Loved.mp4", ("George Michael", "You Have Been Loved")),
        ("Gnarls Barkley - Crazy.mp4", ("Gnarls Barkley", "Crazy")),
        ("Gotye - Somebody That I Used to Know.mp4", ("Gotye", "Somebody That I Used to Know")),
        ("Jackson Browne - Running on Empty.mp4", ("Jackson Browne", "Running on Empty")),
        ("James Taylor - Fire and Rain.mp4", ("James Taylor", "Fire and Rain")),
        ("Jan Delay - Alles Gut (Official Video).mp4", ("Jan Delay", "Alles Gut")),
        ("Maurice Ravel - Laideronnette, impératrice des pagodes (Ma mère l'Oye).mp4", ("Maurice Ravel", "Laideronnette, impératrice des pagodes (Ma mère l'Oye)")),
        ("Modern English - I Melt with You.mp4", ("Modern English", "I Melt with You")),
        ("Ruperts Kitchen Orchestra - Youtube Universität.mp4", ("Ruperts Kitchen Orchestra", "Youtube Universität")),
        ("Selena Gomez - Calm Down.mp4", ("Selena Gomez", "Calm Down")),
        ("Shalamar - A Night to Remember.mp4", ("Shalamar", "A Night to Remember")),
        ("The Alan Parsons Symphonic Project - Time.mp4", ("The Alan Parsons Symphonic Project", "Time")),
        ("Thomas Dolby - The Brightest Star.mp4", ("Thomas Dolby", "The Brightest Star")),
        ("Toto - Africa.mp4", ("Toto", "Africa")),
        ("【ハク。Cover企画】MONO NO AWARE \"かむかもしかもにどもかも！\".mp4", ("Mono no aware", "かむかもしかもにどもかも！")),
        ("Mono no aware - かむかもしかもにどもかも！.mp4", ("Mono no aware", "かむかもしかもにどもかも！")),
    ]
    
    for original, (artist, title) in mapping_data:
        key = canonicalize_key(Path(original).stem)
        if key in mapping and mapping[key] != (artist, title) and VERBOSE:
            print(f"Warning: mapping collision for '{key}'")
        mapping[key] = (artist, title)
    
    return mapping


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in a filename."""
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Remove leading/trailing spaces
    return sanitized.strip()


def update_video_metadata(file_path: Path, artist: str, title: str, dry_run: bool = False) -> Tuple[bool, bool]:
    """Update MP4/M4V metadata with artist and title."""
    if file_path.suffix.lower() not in {".mp4", ".m4v"}:
        if VERBOSE:
            print(f"  Skipping metadata update for unsupported container: {file_path.suffix}")
        return True, False

    try:
        mp4 = MP4(str(file_path))
        
        # Update title
        if '©nam' in mp4:
            current_title = mp4['©nam'][0]
        else:
            current_title = ""
        
        # Update artist
        if '©ART' in mp4:
            current_artist = mp4['©ART'][0]
        else:
            current_artist = ""
        
        needs_update = (current_title != title) or (current_artist != artist)
        if not needs_update:
            if VERBOSE:
                print(f"  Metadata already correct")
            return True, False
        
        if dry_run:
            print(f"  Would update metadata: '{current_artist}' → '{artist}', '{current_title}' → '{title}'")
            return True, True
        
        # Set metadata
        mp4['©nam'] = [title]  # Title
        mp4['©ART'] = [artist]  # Artist
        
        # Also set standard tags for compatibility
        mp4['TITLE'] = [title]
        mp4['ARTIST'] = [artist]
        
        # Set media type to music video
        mp4['stik'] = [6]  # 6 = Music Video (iTunes/Apple standard)
        
        mp4.save()
        if VERBOSE:
            print(f"  Updated metadata: Artist='{artist}', Title='{title}'")
        
        return True, True
        
    except Exception as e:
        print(f"  Error updating metadata: {e}")
        return False, False


def process_video_file(file_path: Path, mapping: Dict[str, Tuple[str, str]], dry_run: bool = False, force: bool = False) -> str:
    """Process a single music video file using the mapping."""
    print(f"\n Processing: {file_path.name}")
    
    # Skip obvious non-song compilations/content
    non_song_keywords = {
        "full album", "commercials", "halftime", "every number one", "most popular",
        "play along", "scrolling", "weihnacht", "julei",
        "17 strings", "double neck", "violin concerto", "hometown song",
        "is it peace or is it prozac",
        "social media", "schnippsel", "jahresrückblick", "derweil", "horizont", "die kopie",
        "weihnachten",
        "for matthew seligman", "99", "hollywood bowl",
        "the time", "oh baby",
        "die kopie", "horizont", "weihnacht im julei", "social media", "schnippsel",
        "jahresrückblick", "derweil", "die erde", "jasagerwüste", "jetzt und hier",
        "soul kitchen", "wie ein blitz", "unser letzter jam"
    }

    lower_name = file_path.name.lower()
    lower_folder = file_path.parent.name.lower()
    if any(kw in lower_name for kw in non_song_keywords) or lower_folder == "1980s":
        print(f"  Skipping non-song content")
        return "skipped"
    
    # Find mapping via canonical key(s)
    candidates = [
        canonicalize_key(file_path.stem),
        canonicalize_key(f"{file_path.parent.name} - {file_path.stem}"),
    ]

    clean_artist = None
    clean_title = None
    for cand in candidates:
        if cand in mapping:
            clean_artist, clean_title = mapping[cand]
            break

    if not clean_artist or not clean_title:
        print(f"  No mapping found for: {file_path.name}")
        if VERBOSE:
            close = difflib.get_close_matches(candidates[0], mapping.keys(), n=3, cutoff=0.85)
            for k in close:
                a, t = mapping[k]
                print(f"   Suggestion: {a} - {t}")
        log_unmapped_file(file_path)
        return "skipped"

    print(f" Artist: {clean_artist}")
    print(f" Title: {clean_title}")
    
    # Generate new filename
    new_filename = f"{sanitize_filename(clean_artist)} - {sanitize_filename(clean_title)}{file_path.suffix}"
    new_path = file_path.parent / new_filename

    rename_needed = (new_path != file_path)
    
    # Check if rename needed
    if rename_needed:
        if new_path.exists():
            print(f"  Target file exists, skipping rename: {new_filename}")
        elif dry_run:
            print(f" Would rename: {file_path.name} → {new_filename}")
        else:
            try:
                file_path.rename(new_path)
                print(f" Renamed: {file_path.name} → {new_filename}")
                file_path = new_path
            except Exception as e:
                print(f" Rename failed: {e}")
                return "skipped"
     
    # Update metadata
    ok, meta_changed = update_video_metadata(file_path, clean_artist, clean_title, dry_run)
    if not ok:
        return "skipped"

    if force:
        return "changed"

    if rename_needed or meta_changed:
        return "changed"

    return "unchanged"


def log_unmapped_file(file_path: Path) -> None:
    """Log files that don't have mappings (file is cleared at start of each run for a clean unique list)."""
    LOG_DIR.mkdir(exist_ok=True)
    
    log_path = LOG_DIR / "music_videos_unmapped.csv"
    
    # Append the new entry
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([str(file_path)])


def scan_music_videos(root_path: Path, mapping: Dict[str, Tuple[str, str]], dry_run: bool = False, force: bool = False) -> Tuple[int, int, int]:
    """Scan music video directory and process all video files."""
    if not root_path.exists():
        print(f" Directory not found: {root_path}")
        return 0, 0, 0
    
    print(f" Scanning: {root_path}")
    print(f" Mapping contains {len(mapping)} entries")
    
    # Clear unmapped log at start of run for a clean unique list
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / "music_videos_unmapped.csv"
    with open(log_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['file_path'])
    
    changed = 0
    unchanged = 0
    skipped = 0
    
    # Scan artist folders
    for artist_folder in sorted(root_path.iterdir()):
        if not artist_folder.is_dir() or artist_folder.name.startswith('.'):
            continue
        
        artist_name = artist_folder.name
        print(f"\n Artist folder: {artist_name}")
        
        # Find video files in artist folder
        video_files = []
        for ext in ['*.mp4', '*.m4v', '*.mkv', '*.avi', '*.mov']:
            video_files.extend(artist_folder.glob(ext))
        
        if not video_files:
            print(f"  No video files found")
            continue
        
        for video_file in sorted(video_files):
            status = process_video_file(video_file, mapping, dry_run, force)
            if status == "changed":
                changed += 1
            elif status == "unchanged":
                unchanged += 1
            else:
                skipped += 1
     
    return changed, unchanged, skipped


def main():
    parser = argparse.ArgumentParser(description="Normalize music video filenames and metadata using mapping")
    parser.add_argument("root", nargs="?", 
                       help="Root music videos directory (defaults to LIBRARY_ROOT/Music Videos)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true",
                       help="Force updates even if metadata appears correct")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    global VERBOSE, LOG_DIR
    VERBOSE = args.verbose
    
    # Load environment and determine root path
    repo_root = Path(__file__).parent.parent.parent
    load_dotenv(repo_root)
    
    if args.root:
        root_path = Path(args.root)
    else:
        library_root = get_library_root()
        root_path = library_root / "Music Videos"
        if VERBOSE:
            print(f"Using default path: {root_path}")
    
    # Setup logging
    LOG_DIR = repo_root / "log"
    
    if not DEPS_AVAILABLE:
        sys.exit(1)
    
    # Load the mapping
    mapping = load_mapping()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    changed, unchanged, skipped = scan_music_videos(root_path, mapping, args.dry_run, args.force)
    
    print(f"\n📊 Summary:")
    if args.dry_run:
        print(f"🔍 Would change {changed} files")
        print(f"✅ Already correct {unchanged} files")
        if skipped > 0:
            print(f"⚠️  Would skip {skipped} files")
            print(f"   📄 See current unmapped files: {LOG_DIR / 'music_videos_unmapped.csv'}")
    else:
        print(f"✅ Changed {changed} files")
        print(f"✅ Already correct {unchanged} files")
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} files")
            print(f"   📄 See current unmapped files: {LOG_DIR / 'music_videos_unmapped.csv'}")
    
    if args.dry_run:
        print("💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
