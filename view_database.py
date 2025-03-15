import sqlite3
from tabulate import tabulate

def view_database():
    conn = sqlite3.connect('music_database.db')
    c = conn.cursor()
    
    # View artists
    print("\n=== ARTISTS ===")
    c.execute('SELECT * FROM artists')
    artists = c.fetchall()
    if artists:
        print(tabulate(artists, headers=['ID', 'Name', 'Genius ID'], tablefmt='grid'))
    else:
        print("No artists found")
    
    # View albums
    print("\n=== ALBUMS ===")
    c.execute('''
        SELECT albums.*, artists.name as artist_name 
        FROM albums 
        JOIN artists ON albums.artist_id = artists.id
    ''')
    albums = c.fetchall()
    if albums:
        print(tabulate(albums, headers=['ID', 'Name', 'Release Date', 'Genius ID', 'Artist ID', 'Artist Name'], tablefmt='grid'))
    else:
        print("No albums found")
    
    # View songs
    print("\n=== SONGS ===")
    c.execute('''
        SELECT songs.*, artists.name as artist_name, albums.name as album_name 
        FROM songs 
        JOIN artists ON songs.artist_id = artists.id
        LEFT JOIN albums ON songs.album_id = albums.id
    ''')
    songs = c.fetchall()
    if songs:
        print(tabulate(songs, headers=['ID', 'Title', 'Genius ID', 'URL', 'Album ID', 'Artist ID', 'Artist Name', 'Album Name'], tablefmt='grid'))
    else:
        print("No songs found")
    
    conn.close()

if __name__ == "__main__":
    view_database() 