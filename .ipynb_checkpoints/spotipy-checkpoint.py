import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

os.environ['SPOTIPY_CLIENT_ID'] = '838a32980bea47a7a385977cdbc3c74f'
os.environ['SPOTIPY_CLIENT_SECRET'] = 'dfa21e3dee1b49ce9e239d569bdf6cd8'
#cid = '838a32980bea47a7a385977cdbc3c74f'
#secret = 'dfa21e3dee1b49ce9e239d569bdf6cd8'


sp = spotipy.Spotify(client_credentials_manager= SpotifyClientCredentials())

playlists = sp.user_playlists('spotify')
while playlists:
    for i, playlist in enumerate(playlists['items']):
        print("%4d %s %s" % (i + 1 + playlists['offset'], playlist['uri'],  playlist['name']))
    if playlists['next']:
        playlists = sp.next(playlists)
    else:
        playlists = None
