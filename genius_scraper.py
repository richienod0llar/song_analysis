import os
import sqlite3
from dotenv import load_dotenv
import lyricsgenius
import sys
import requests
import json
import time
from bs4 import BeautifulSoup
import re

# Load environment variables
load_dotenv()

# Get the API token
GENIUS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

if not GENIUS_TOKEN:
    print("Error: No Genius API token found in .env file")
    sys.exit(1)

# Define the target albums
TARGET_ALBUMS = [
    'OK Computer',
    'Kid A',
    'Amnesiac',
    'Hail to the Thief',
    'In Rainbows',
    'A Moon Shaped Pool'
]

# Define album URLs for direct scraping
ALBUM_URLS = {
    'OK Computer': 'https://genius.com/albums/Radiohead/Ok-computer',
    'Kid A': 'https://genius.com/albums/Radiohead/Kid-a',
    'Amnesiac': 'https://genius.com/albums/Radiohead/Amnesiac',
    'Hail to the Thief': 'https://genius.com/albums/Radiohead/Hail-to-the-thief',
    'In Rainbows': 'https://genius.com/albums/Radiohead/In-rainbows',
    'A Moon Shaped Pool': 'https://genius.com/albums/Radiohead/A-moon-shaped-pool'
}

class CustomGenius:
    def __init__(self, access_token):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def get_lyrics(self, url):
        """Fetch lyrics from Genius URL."""
        try:
            print(f"Fetching lyrics from: {url}")
            response = self.session.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try different possible selectors for lyrics
                lyrics = None
                
                # Method 1: New Genius format
                lyrics_containers = soup.select('[class*="Lyrics__Container-"]')
                if lyrics_containers:
                    lyrics = '\n'.join([container.get_text(separator='\n') for container in lyrics_containers])
                
                # Method 2: Classic format
                if not lyrics:
                    lyrics_div = soup.find('div', class_='lyrics')
                    if lyrics_div:
                        lyrics = lyrics_div.get_text()
                
                # Method 3: Alternative new format
                if not lyrics:
                    lyrics_spans = soup.select('[class*="lyrics"], [class*="Lyrics"]')
                    if lyrics_spans:
                        lyrics = '\n'.join([span.get_text(separator='\n') for span in lyrics_spans])
                
                if lyrics:
                    # Clean up the lyrics
                    lyrics = re.sub(r'\[.*?\]', '', lyrics)  # Remove [Verse], [Chorus], etc.
                    lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)  # Remove excessive newlines
                    lyrics = lyrics.strip()
                    print(f"Successfully fetched lyrics ({len(lyrics)} characters)")
                    return lyrics
                else:
                    print("No lyrics found in the page")
                    return None
            else:
                print(f"Failed to fetch lyrics: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching lyrics: {e}")
            return None

    def get_album_songs(self, album_url, album_name):
        """Get all songs from a specific album URL."""
        print(f"\nFetching songs from album: {album_name}")
        try:
            response = self.session.get(album_url)
            if response.status_code != 200:
                print(f"Failed to fetch album page: HTTP {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all song links in the album page
            song_links = []
            
            # Method 1: Look for song links in the tracklist
            tracklist_items = soup.select('div.chart_row-content')
            for item in tracklist_items:
                link = item.find('a', href=True)
                if link and 'genius.com' in link['href']:
                    song_links.append({
                        'title': link.text.strip(),
                        'url': link['href']
                    })
            
            # Method 2: Alternative selector for newer layout
            if not song_links:
                song_items = soup.select('a[class*="TracksListDesktop__Track-"]')
                for item in song_items:
                    if item.get('href') and 'genius.com' in item['href']:
                        title = item.text.strip()
                        # Remove track numbers if present
                        title = re.sub(r'^\d+\.\s*', '', title)
                        song_links.append({
                            'title': title,
                            'url': item['href']
                        })
            
            # Method 3: Another alternative selector
            if not song_links:
                song_items = soup.select('a.u-display_block')
                for item in song_items:
                    if item.get('href') and '/lyrics/' in item['href']:
                        title = item.text.strip()
                        song_links.append({
                            'title': title,
                            'url': item['href']
                        })
            
            print(f"Found {len(song_links)} songs in album {album_name}")
            
            # Get song details and lyrics
            songs = []
            for i, song_link in enumerate(song_links, 1):
                print(f"\nProcessing song {i}/{len(song_links)}: {song_link['title']}")
                
                # Get song ID from URL
                song_id = None
                match = re.search(r'/songs/(\d+)', song_link['url'])
                if match:
                    song_id = int(match.group(1))
                
                # Get lyrics
                lyrics = self.get_lyrics(song_link['url'])
                
                # Create song object
                song = type('Song', (), {
                    'title': song_link['title'],
                    'id': song_id,
                    'url': song_link['url'],
                    'lyrics': lyrics,
                    'album': {
                        'name': album_name,
                        'id': None,  # We don't have album ID from direct scraping
                        'release_date': self.get_album_year(album_name)
                    }
                })
                songs.append(song)
                
                # Add delay to avoid rate limiting
                time.sleep(2)
            
            return songs
            
        except Exception as e:
            print(f"Error fetching album songs: {e}")
            return []
    
    def get_album_year(self, album_name):
        """Return the release year for the album."""
        album_years = {
            'OK Computer': 1997,
            'Kid A': 2000,
            'Amnesiac': 2001,
            'Hail to the Thief': 2003,
            'In Rainbows': 2007,
            'A Moon Shaped Pool': 2016
        }
        return album_years.get(album_name)
    
    def search_artist(self, artist_name):
        """Get artist info and then fetch songs from specific albums."""
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        print(f"\nSearching for artist: {artist_name}")
        # First search for the artist
        search_url = f'https://api.genius.com/search?q={artist_name}'
        response = requests.get(search_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error searching for artist: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        data = response.json()
        
        # Find the first result that's an artist
        artist_hit = None
        for hit in data['response']['hits']:
            if hit['result']['primary_artist']['name'].lower() == artist_name.lower():
                artist_hit = hit['result']['primary_artist']
                break
        
        if not artist_hit:
            print(f"Could not find artist: {artist_name}")
            return None
            
        print(f"Found artist: {artist_hit['name']} (ID: {artist_hit['id']})")
        
        # Create artist object
        artist = type('Artist', (), {
            'name': artist_hit['name'],
            'id': artist_hit['id'],
            'songs': []
        })
        
        # Fetch songs from each target album
        for album_name, album_url in ALBUM_URLS.items():
            album_songs = self.get_album_songs(album_url, album_name)
            artist.songs.extend(album_songs)
            print(f"Added {len(album_songs)} songs from album: {album_name}")
            time.sleep(2)  # Delay between albums
            
        print(f"\nCompleted processing {len(artist.songs)} songs for {artist.name}")
        return artist

# Initialize custom Genius API client
genius = CustomGenius(GENIUS_TOKEN)

def verify_token():
    """Verify if the API token is valid by making a test request."""
    try:
        headers = {'Authorization': f'Bearer {GENIUS_TOKEN}'}
        response = requests.get(
            'https://api.genius.com/search?q=test',
            headers=headers
        )
        
        if response.status_code == 200:
            print("API Token verified successfully!")
            return True
        else:
            print(f"\nError: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\nError: Failed to verify Genius API token.")
        print(f"Make sure your token is valid and properly configured in .env file")
        print(f"Error details: {str(e)}")
        return False

def create_database():
    """Create the SQLite database and necessary tables."""
    conn = sqlite3.connect('music_database.db')
    c = conn.cursor()
    
    # Create artists table
    c.execute('''
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            genius_id INTEGER UNIQUE
        )
    ''')
    
    # Create albums table
    c.execute('''
        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            release_date TEXT,
            release_year INTEGER,
            genius_id INTEGER UNIQUE,
            artist_id INTEGER,
            FOREIGN KEY (artist_id) REFERENCES artists (id)
        )
    ''')
    
    # Create songs table with lyrics column
    c.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            genius_id INTEGER UNIQUE,
            genius_url TEXT,
            lyrics TEXT,
            album_id INTEGER,
            artist_id INTEGER,
            FOREIGN KEY (album_id) REFERENCES albums (id),
            FOREIGN KEY (artist_id) REFERENCES artists (id)
        )
    ''')
    
    conn.commit()
    return conn

def store_artist_data(conn, artist):
    """Store artist, album, and song data in the database."""
    c = conn.cursor()
    
    # First, clear existing data for these albums
    print("\nClearing existing data for target albums...")
    album_names = ', '.join(f"'{album}'" for album in TARGET_ALBUMS)
    
    # Get album IDs to delete
    c.execute(f"SELECT id FROM albums WHERE name IN ({album_names})")
    album_ids = [row[0] for row in c.fetchall()]
    
    if album_ids:
        album_ids_str = ', '.join(str(id) for id in album_ids)
        # Delete songs associated with these albums
        c.execute(f"DELETE FROM songs WHERE album_id IN ({album_ids_str})")
        # Delete the albums
        c.execute(f"DELETE FROM albums WHERE id IN ({album_ids_str})")
        print(f"Cleared data for {len(album_ids)} albums and their songs")
    
    # Store artist
    c.execute('''
        INSERT OR IGNORE INTO artists (name, genius_id)
        VALUES (?, ?)
    ''', (artist.name, artist.id))
    artist_id = c.lastrowid or c.execute('SELECT id FROM artists WHERE genius_id = ?', (artist.id,)).fetchone()[0]
    
    # Track albums we've already processed
    processed_albums = {}
    
    # Process each song
    for song in artist.songs:
        # Get album info if available
        album_id = None
        if hasattr(song, 'album') and song.album:
            album_name = song.album['name']
            
            # Check if we've already processed this album
            if album_name in processed_albums:
                album_id = processed_albums[album_name]
            else:
                # Store the album
                c.execute('''
                    INSERT OR IGNORE INTO albums (name, release_date, release_year, genius_id, artist_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    album_name,
                    None,  # release_date
                    song.album.get('release_date'),
                    song.album.get('id'),
                    artist_id
                ))
                
                # Get the album ID
                c.execute('SELECT id FROM albums WHERE name = ? AND artist_id = ?', (album_name, artist_id))
                album_row = c.fetchone()
                if album_row:
                    album_id = album_row[0]
                    processed_albums[album_name] = album_id
                    print(f"Stored album: {album_name} (ID: {album_id})")
        
        # Store song with lyrics
        c.execute('''
            INSERT OR IGNORE INTO songs (title, genius_id, genius_url, lyrics, album_id, artist_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (song.title, song.id, song.url, song.lyrics, album_id, artist_id))
        print(f"Stored song: {song.title}")
    
    conn.commit()

def main():
    # First verify the token
    if not verify_token():
        return

    # Create database and get connection
    conn = create_database()
    
    # Set artist name to Radiohead
    artist_name = "Radiohead"
    
    # Fetch artist data
    print(f"Fetching data for {artist_name}...")
    artist = genius.search_artist(artist_name)
    
    if artist:
        print(f"\nFound artist: {artist.name}")
        print(f"Number of songs found: {len(artist.songs)}")
        print(f"\nStoring data for {artist.name}...")
        store_artist_data(conn, artist)
        print("Data storage complete!")
    else:
        print("Failed to fetch artist data.")
    
    conn.close()

if __name__ == "__main__":
    main() 