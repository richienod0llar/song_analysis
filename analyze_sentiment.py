import sqlite3
import pandas as pd
import numpy as np
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
from sklearn.preprocessing import MinMaxScaler
import plotly.express as px
import plotly.graph_objects as go

# Download required NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def load_sad_words():
    """Load sad words from local file."""
    try:
        with open('sad_words.txt', 'r') as f:
            return set(word.strip().lower() for word in f.readlines())
    except FileNotFoundError:
        print("Error: sad_words.txt not found!")
        return set()

def load_data():
    """Load data from SQLite database into pandas DataFrame."""
    conn = sqlite3.connect('music_database.db')
    
    # List of specific albums to analyze
    target_albums = [
        'The New Abnormal',
        'Comedown Machine',
        'Angles',
        'First Impressions of Earth',
        'Room on Fire',
        'Is This It'
    ]
    
    # Create a SQL-friendly string of album names for the query
    album_names_sql = ', '.join(f"'{album}'" for album in target_albums)
    
    # First, let's check the raw data in our tables
    print("\nChecking database tables:")
    
    # Check songs table
    songs_check = pd.read_sql_query('''
        SELECT COUNT(*) as count, 
               COUNT(album_id) as songs_with_album_id,
               COUNT(DISTINCT album_id) as unique_album_ids
        FROM songs
    ''', conn)
    print("\nSongs table stats:")
    print(f"Total songs: {songs_check['count'].iloc[0]}")
    print(f"Songs with album_id: {songs_check['songs_with_album_id'].iloc[0]}")
    print(f"Unique album IDs: {songs_check['unique_album_ids'].iloc[0]}")
    
    # Check albums table
    albums_check = pd.read_sql_query(f'''
        SELECT COUNT(*) as count
        FROM albums
        WHERE name IN ({album_names_sql})
    ''', conn)
    print("\nTarget albums in database:")
    print(f"Found {albums_check['count'].iloc[0]} of the 6 requested albums")
    
    # Get all songs from the target albums
    query = f'''
    SELECT 
        songs.title,
        songs.lyrics,
        albums.name as album_name,
        albums.release_year,
        artists.name as artist_name
    FROM songs
    JOIN artists ON songs.artist_id = artists.id
    JOIN albums ON songs.album_id = albums.id
    WHERE 
        albums.name IN ({album_names_sql})
        AND songs.lyrics IS NOT NULL
    ORDER BY 
        albums.release_year,
        songs.title
    '''
    
    df = pd.read_sql_query(query, conn)
    
    # Print detailed information about the data loaded
    print(f"\nLoaded {len(df)} songs with lyrics from the requested albums")
    print("\nSongs per album:")
    album_counts = df['album_name'].value_counts()
    for album, count in album_counts.items():
        print(f"  {album}: {count} songs")
    
    # If we didn't find all the albums, try a case-insensitive search
    if len(album_counts) < len(target_albums):
        print("\nSome albums not found. Trying case-insensitive search...")
        
        # Get all album names for reference
        all_albums = pd.read_sql_query("SELECT name FROM albums", conn)
        print("\nAll albums in database:")
        for album in all_albums['name'].sort_values():
            print(f"  {album}")
        
        # Try to find songs with album_id but missing album name
        missing_songs = pd.read_sql_query('''
            SELECT 
                songs.title,
                songs.album_id,
                albums.name as album_name
            FROM songs
            LEFT JOIN albums ON songs.album_id = albums.id
            WHERE songs.album_id IS NOT NULL AND albums.name IS NULL
        ''', conn)
        
        if not missing_songs.empty:
            print("\nFound songs with album_id but no matching album in albums table:")
            for _, row in missing_songs.head(10).iterrows():
                print(f"  Song: {row['title']}, Album ID: {row['album_id']}")
            if len(missing_songs) > 10:
                print(f"  ... and {len(missing_songs) - 10} more")
    
    conn.close()
    return df

def calculate_sentiment(lyrics, sad_words):
    """Calculate sentiment scores for lyrics."""
    if pd.isna(lyrics):
        return 0, 0
        
    # Tokenize and remove stop words
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(str(lyrics).lower())
    words = [word for word in words if word.isalnum() and word not in stop_words]
    
    # Calculate metrics
    word_count = len(words)
    if word_count == 0:
        return 0, 0
        
    sad_count = sum(1 for word in words if word in sad_words)
    return sad_count / word_count, word_count

def analyze_lyrics():
    # Load data
    print("Loading data from database...")
    df = load_data()
    
    if df.empty:
        print("No songs found from the requested albums.")
        return
    
    # Load sad words
    print("\nLoading sentiment lexicon...")
    sad_words = load_sad_words()
    print(f"Loaded {len(sad_words)} sad words")
    
    # Calculate sentiment for each song
    print("\nCalculating sentiment scores...")
    sentiments = []
    for idx, row in df.iterrows():
        pct_sad, word_count = calculate_sentiment(row['lyrics'], sad_words)
        sentiments.append({
            'title': row['title'],
            'pct_sad': pct_sad,
            'word_count': word_count
        })
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1} songs...")
    
    sent_df = pd.DataFrame(sentiments)
    
    # Merge sentiment data with main dataframe
    df = df.merge(sent_df, on='title', how='left')
    
    # Calculate gloom index
    print("\nCalculating gloom index...")
    df['lyrical_density'] = df['word_count'] / df['word_count'].mean()
    df['gloom_index'] = df['pct_sad'] * (1 + df['lyrical_density'])
    
    # Rescale gloom index to 1-100
    scaler = MinMaxScaler((1, 100))
    df['gloom_index'] = scaler.fit_transform(df[['gloom_index']])
    
    # Create the plot
    print("\nGenerating visualization...")
    
    # Sort albums chronologically
    album_order = [
        'Is This It',
        'Room on Fire',
        'First Impressions of Earth',
        'Angles',
        'Comedown Machine',
        'The New Abnormal'
    ]
    
    # Filter to only include albums we actually found
    unique_albums = [album for album in album_order if album in df['album_name'].unique()]
    
    # Create the interactive scatter plot using go.Figure for more control
    fig = go.Figure()
    
    # Add scatter traces for each album
    for i, album in enumerate(unique_albums):
        album_data = df[df['album_name'] == album]
        n_songs = len(album_data)
        
        # Skip if no songs for this album
        if n_songs == 0:
            continue
            
        # Create jittered x positions
        if n_songs > 1:
            x_positions = [i + np.random.uniform(-0.3, 0.3) for _ in range(n_songs)]
        else:
            x_positions = [i]
        
        # Add scatter points for this album
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=album_data['gloom_index'],
            mode='markers',
            name=album,
            text=[f"Song: {title}<br>Gloom Index: {gloom:.2f}<br>Sad Words: {sad:.1%}<br>Word Count: {words}" 
                  for title, gloom, sad, words in zip(album_data['title'], 
                                                    album_data['gloom_index'],
                                                    album_data['pct_sad'],
                                                    album_data['word_count'])],
            hoverinfo='text',
            marker=dict(
                size=10,
                opacity=0.7
            )
        ))
        
        # Calculate and add album mean line
        album_mean = album_data['gloom_index'].mean()
        fig.add_shape(
            type='line',
            x0=i-0.4,
            x1=i+0.4,
            y0=album_mean,
            y1=album_mean,
            line=dict(color='rgba(0,0,0,0.3)', width=2, dash='dash')
        )

    # Update layout
    fig.update_layout(
        title=f'Data Driven Depression: The Strokes',
        height=800,
        showlegend=True,
        legend_title_text='Albums',
        xaxis_title='Album',
        yaxis_title='Sadness Index',
        hovermode='closest',
        template='plotly_white',
        xaxis=dict(
            ticktext=unique_albums,
            tickvals=list(range(len(unique_albums))),
            tickangle=45
        ),
        yaxis=dict(
            range=[-5, 105]  # Give some padding to y-axis
        ),
        # Adjust margins to prevent label cutoff
        margin=dict(b=150)
    )

    # Save the interactive plot
    fig.write_html('album_gloom_analysis.html')
    print("\nInteractive plot saved as 'album_gloom_analysis.html'")
    
    # Save detailed results to CSV
    results_df = df[['title', 'album_name', 'release_year', 'pct_sad', 'word_count', 'gloom_index']]
    
    # Sort by album (in chronological order) and then by gloom index
    album_order_dict = {album: i for i, album in enumerate(album_order)}
    results_df['album_order'] = results_df['album_name'].map(album_order_dict)
    results_df = results_df.sort_values(['album_order', 'gloom_index'], ascending=[True, False])
    results_df = results_df.drop('album_order', axis=1)
    
    results_df.to_csv('song_analysis_results.csv', index=False)
    print("Detailed results saved to 'song_analysis_results.csv'")
    
    # Print summary statistics
    print("\nMost 'Gloomy' Songs per Album:")
    for album in unique_albums:
        album_songs = results_df[results_df['album_name'] == album]
        if not album_songs.empty:
            gloomiest_song = album_songs.nlargest(1, 'gloom_index').iloc[0]
            print(f"\n{album}:")
            print(f"  {gloomiest_song['title']}")
            print(f"  Gloom Index: {gloomiest_song['gloom_index']:.2f}")
            print(f"  Word Count: {gloomiest_song['word_count']}")
            print(f"  Sad Word %: {gloomiest_song['pct_sad']*100:.1f}%")
    
    # Print overall statistics
    print("\nOverall Statistics:")
    print(f"Total songs analyzed: {len(df)}")
    print(f"Number of albums: {len(unique_albums)}")
    print(f"Average gloom index across all songs: {df['gloom_index'].mean():.2f}")
    print(f"Most common sad words: {get_most_common_sad_words(df, sad_words)}")
    
    return df

def get_most_common_sad_words(df, sad_words):
    """Get the most commonly used sad words across all lyrics."""
    all_words = []
    for lyrics in df['lyrics']:
        words = word_tokenize(str(lyrics).lower())
        all_words.extend([w for w in words if w in sad_words])
    
    word_freq = pd.Series(all_words).value_counts()
    return word_freq.head(10).to_dict()

if __name__ == "__main__":
    analyze_lyrics() 