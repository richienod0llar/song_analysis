# Import necessary libraries
import os
import requests
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Set environment variables for Spotify API
os.environ['SPOTIPY_CLIENT_ID'] = '838a32980bea47a7a385977cdbc3c74f'
os.environ['SPOTIPY_CLIENT_SECRET'] = 'dfa21e3dee1b49ce9e239d569bdf6cd8'

# Authenticate with Spotify
spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials())

# Get Radiohead's audio features
artist = 'radiohead'
results = spotify.search(q=f'artist:{artist}', type='artist')
artist_id = results['artists']['items'][0]['id']

spotify_df = []
albums = spotify.artist_albums(artist_id, album_type='album')['items']
for album in albums:
    tracks = spotify.album_tracks(album['id'])['items']
    for track in tracks:
        audio_features = spotify.audio_features(track['id'])[0]
        audio_features['track_name'] = track['name']
        audio_features['album_name'] = album['name']
        audio_features['album_release_year'] = album['release_date'][:4]
        audio_features['album_img'] = album['images'][0]['url']
        spotify_df.append(audio_features)

spotify_df = pd.DataFrame(spotify_df)

# Filter out non-studio album
non_studio_albums = ['TKOL RMX 1234567', 'In Rainbows Disk 2', 'Com Lag: 2+2=5', 'I Might Be Wrong', 'OK Computer OKNOTOK 1997 2017']
spotify_df = spotify_df[~spotify_df['album_name'].isin(non_studio_albums)]

# Set Genius API token
token = 'VoiHulUkbE0d-9lk05LFg2IqwNrhRSAuMtkdYVlu8JMrYZ4-siaH-PB6ddX7878K'

# Function to get artists from Genius
def genius_get_artists(artist_name, n_results=10):
    baseURL = 'https://api.genius.com/search'
    headers = {'Authorization': f'Bearer {token}'}
    params = {'q': artist_name, 'per_page': n_results}
    
    response = requests.get(baseURL, headers=headers, params=params).json()
    hits = response['response']['hits']
    
    artists = [{'artist_id': hit['result']['primary_artist']['id'], 'artist_name': hit['result']['primary_artist']['name']} for hit in hits]
    return pd.DataFrame(artists).drop_duplicates()

genius_artists = genius_get_artists('radiohead')

# Get track lyric URLs from Genius
baseURL = f'https://api.genius.com/artists/{genius_artists.iloc[0]["artist_id"]}/songs'
track_lyric_urls = []
page = 1

while True:
    params = {'access_token': token, 'per_page': 50, 'page': page}
    response = requests.get(baseURL, params=params).json()['response']
    track_lyric_urls.extend(response['songs'])
    
    if response['next_page'] is not None:
        page = response['next_page']
    else:
        break

# Function to scrape lyrics from Genius
def lyric_scraper(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    lyrics = soup.find('div', class_='lyrics')
    return lyrics.get_text() if lyrics else ''

# Get lyrics for each track
genius_df = []

for track in track_lyric_urls:
    try:
        lyrics = lyric_scraper(track['url'])
        # Clean lyrics
        lyrics = lyrics.lower()
        lyrics = ''.join([c if c.isalnum() else ' ' for c in lyrics])
        lyrics = ' '.join(lyrics.split())
        
        genius_df.append({
            'track_name': track['title'],
            'lyrics': lyrics
        })
    except Exception as e:
        genius_df.append({
            'track_name': track['title'],
            'lyrics': None
        })

genius_df = pd.DataFrame(genius_df)

# Correct track names
track_name_corrections = {
    'Packt Like Sardines in a Crushd Tin Box': 'Packt Like Sardines in a Crushed Tin Box',
    'Weird Fishes / Arpeggi': 'Weird Fishes/ Arpeggi',
    'A Punchup at a Wedding': 'A Punch Up at a Wedding',
    'Dollars and Cents': 'Dollars & Cents',
    'Bullet Proof...I Wish I Was': 'Bullet Proof ... I Wish I Was'
}

genius_df['track_name'] = genius_df['track_name'].replace(track_name_corrections)
genius_df['track_name_join'] = genius_df['track_name'].str.replace('[^a-zA-Z0-9]', '', regex=True).str.lower()

genius_df = genius_df.drop_duplicates(subset=['track_name_join'])

# Merge Spotify and Genius dataframes
spotify_df['track_name_join'] = spotify_df['track_name'].str.replace('[^a-zA-Z0-9]', '', regex=True).str.lower()
track_df = spotify_df.merge(genius_df, on='track_name_join', how='left')

# Calculate valence and arrange tracks by valence
valence_df = track_df[['valence', 'track_name']].sort_values(by='valence').head(10)

# Sentiment analysis
stop_words = set(stopwords.words('english'))
sad_words = pd.read_csv('https://raw.githubusercontent.com/datasciencedojo/datasets/master/NRC-Emotion-Lexicon-Wordlevel-v0.92/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt', 
                        names=['word', 'emotion', 'association'], 
                        sep='\t')
sad_words = sad_words[(sad_words['emotion'] == 'sadness') & (sad_words['association'] == 1)]['word'].tolist()

def calculate_sentiment(lyrics):
    words = word_tokenize(lyrics)
    words = [word for word in words if word not in stop_words]
    sad_count = sum(1 for word in words if word in sad_words)
    return sad_count / len(words), len(words)

sentiments = []
for index, row in track_df.iterrows():
    if pd.notnull(row['lyrics']):
        pct_sad, word_count = calculate_sentiment(row['lyrics'])
    else:
        pct_sad, word_count = 0, 0
    sentiments.append({
        'track_name': row['track_name'],
        'pct_sad': pct_sad,
        'word_count': word_count
    })

sent_df = pd.DataFrame(sentiments)

# Merge sentiment data with track dataframe
track_df = track_df.merge(sent_df, on='track_name', how='left')
track_df['lyrical_density'] = track_df['word_count'] / track_df['duration_ms'] * 1000
track_df['gloom_index'] = 1 - ((1 - track_df['valence']) + (track_df['pct_sad'] * (1 + track_df['lyrical_density']))) / 2

# Rescale gloom index
scaler = MinMaxScaler((1, 100))
track_df['gloom_index'] = scaler.fit_transform(track_df[['gloom_index']])

# Plotting
plt.figure(figsize=(14, 8))
sns.scatterplot(data=track_df, x='album_release_year', y='gloom_index', hue='album_name', palette='Paired')
plt.title('Data Driven Depression: Radiohead song sadness by album')
plt.xlabel('Album')
plt.ylabel('Gloom Index')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.show()
