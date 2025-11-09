import sqlite3
import pandas as pd
import numpy as np
import re
from sklearn.preprocessing import MinMaxScaler

# Simple stopwords list (most common English stopwords)
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'that', 'this',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them',
    'their', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all',
    'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
    'not', 'no', 'nor', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'just', 'now'
}

def tokenize(text):
    """Simple tokenization function."""
    # Convert to lowercase and extract words
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return words

def load_sad_words():
    """Load sad words from local file."""
    try:
        with open('sad_words.txt', 'r') as f:
            return set(word.strip().lower() for word in f.readlines())
    except FileNotFoundError:
        print("Error: sad_words.txt not found!")
        return set()

def get_lyrics_from_database():
    """Get lyrics for Radiohead songs from the database."""
    conn = sqlite3.connect('music_database.db')
    
    # Get Radiohead songs with lyrics
    query = '''
    SELECT 
        songs.title as track_name,
        songs.lyrics,
        albums.name as album_name,
        artists.name as artist_name
    FROM songs
    JOIN artists ON songs.artist_id = artists.id
    LEFT JOIN albums ON songs.album_id = albums.id
    WHERE songs.lyrics IS NOT NULL
    AND artists.name = 'Radiohead'
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Clean song titles - remove "\n              Lyrics" suffix
    df['track_name'] = df['track_name'].str.replace(r'\n\s+Lyrics', '', regex=True)
    
    print(f"Loaded {len(df)} Radiohead songs with lyrics from database")
    return df

def calculate_sentiment(lyrics, sad_words):
    """Calculate sentiment metrics for lyrics."""
    if pd.isna(lyrics) or not lyrics:
        return 0, 0
        
    # Tokenize and process text
    words = tokenize(str(lyrics))
    words = [word for word in words if word not in STOPWORDS]
    
    # Calculate word count
    word_count = len(words)
    
    if word_count == 0:
        return 0, 0
        
    # Calculate sad word percentage
    sad_count = sum(1 for word in words if word in sad_words)
    pct_sad = sad_count / word_count
    
    return pct_sad, word_count

def calculate_gloom_index():
    """
    Calculate gloom index for all songs combining Spotify valence 
    with lyrical sentiment analysis.
    """
    print("=" * 60)
    print("CALCULATING GLOOM INDEX FOR ALL SONGS")
    print("=" * 60)
    
    # Load track data from CSV (contains Spotify audio features)
    print("\nStep 1: Loading track data with audio features...")
    track_df = pd.read_csv('radiohead_complete_songs.csv')
    print(f"Loaded {len(track_df)} tracks")
    print(f"Columns: {', '.join(track_df.columns.tolist())}")
    
    # Load lyrics from database
    print("\nStep 2: Loading lyrics from database...")
    lyrics_df = get_lyrics_from_database()
    
    # Load sad words
    print("\nStep 3: Loading sentiment lexicon...")
    sad_words = load_sad_words()
    print(f"Loaded {len(sad_words)} sad words")
    
    # Calculate sentiment for each song
    print("\nStep 4: Analyzing lyrics sentiment...")
    sentiments = []
    for idx, row in lyrics_df.iterrows():
        pct_sad, word_count = calculate_sentiment(row['lyrics'], sad_words)
        sentiments.append({
            'track_name': row['track_name'],
            'pct_sad': pct_sad,
            'word_count': word_count
        })
        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(lyrics_df)} songs...")
    
    sent_df = pd.DataFrame(sentiments)
    print(f"Analyzed sentiment for {len(sent_df)} songs")
    
    # Join track data with sentiment data
    print("\nStep 5: Joining track features with sentiment analysis...")
    # Use the title column from track_df, rename it to track_name for joining
    if 'title' in track_df.columns:
        track_df = track_df.rename(columns={'title': 'track_name'})
    
    # Left join to keep all tracks
    result_df = track_df.merge(sent_df, on='track_name', how='left')
    
    # Replace NaN values with 0 for songs without lyrics
    result_df['pct_sad'] = result_df['pct_sad'].fillna(0)
    result_df['word_count'] = result_df['word_count'].fillna(0)
    
    print(f"Merged data: {len(result_df)} total tracks")
    print(f"  - {result_df['word_count'].gt(0).sum()} tracks with lyrics")
    print(f"  - {result_df['word_count'].eq(0).sum()} tracks without lyrics")
    
    # Calculate lyrical density and gloom index
    print("\nStep 6: Calculating gloom index...")
    
    # Lyrical density: words per second (scaled by 1000 to match R formula)
    result_df['lyrical_density'] = result_df['word_count'] / result_df['duration_ms'] * 1000
    
    # Calculate the gloom formula before rescaling
    # Formula: 1 - ((1 - valence) + (pct_sad * (1 + lyrical_density))) / 2
    result_df['gloom_raw'] = 1 - ((1 - result_df['valence']) + 
                                    (result_df['pct_sad'] * (1 + result_df['lyrical_density']))) / 2
    
    # Rescale to 1-100 range
    scaler = MinMaxScaler(feature_range=(1, 100))
    result_df['gloom_index'] = scaler.fit_transform(result_df[['gloom_raw']])
    result_df['gloom_index'] = result_df['gloom_index'].round(2)
    
    # Drop the raw gloom column
    result_df = result_df.drop('gloom_raw', axis=1)
    
    # Sort by gloom index (descending) to see gloomiest songs first
    result_df = result_df.sort_values('gloom_index', ascending=False)
    
    # Save results
    output_file = 'radiohead_gloom_analysis.csv'
    result_df.to_csv(output_file, index=False)
    print(f"\nResults saved to '{output_file}'")
    
    # Display summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    
    print(f"\nGloom Index Statistics:")
    print(f"  Mean: {result_df['gloom_index'].mean():.2f}")
    print(f"  Median: {result_df['gloom_index'].median():.2f}")
    print(f"  Min: {result_df['gloom_index'].min():.2f}")
    print(f"  Max: {result_df['gloom_index'].max():.2f}")
    print(f"  Std Dev: {result_df['gloom_index'].std():.2f}")
    
    # Show top 10 gloomiest songs
    print("\n" + "=" * 60)
    print("TOP 10 GLOOMIEST SONGS")
    print("=" * 60)
    top_10 = result_df.head(10)
    for idx, row in top_10.iterrows():
        print(f"\n{row.name + 1}. {row['track_name']}")
        print(f"   Album: {row.get('album', 'N/A')}")
        print(f"   Gloom Index: {row['gloom_index']:.2f}")
        print(f"   Valence: {row['valence']:.3f}")
        print(f"   Sad Word %: {row['pct_sad']*100:.1f}%")
        print(f"   Word Count: {int(row['word_count'])}")
        print(f"   Lyrical Density: {row['lyrical_density']:.2f}")
    
    # Show top 10 least gloomy songs
    print("\n" + "=" * 60)
    print("TOP 10 LEAST GLOOMY SONGS")
    print("=" * 60)
    bottom_10 = result_df.tail(10).sort_values('gloom_index', ascending=True)
    for idx, row in bottom_10.iterrows():
        print(f"\n{row.name + 1}. {row['track_name']}")
        print(f"   Album: {row.get('album', 'N/A')}")
        print(f"   Gloom Index: {row['gloom_index']:.2f}")
        print(f"   Valence: {row['valence']:.3f}")
        print(f"   Sad Word %: {row['pct_sad']*100:.1f}%")
        print(f"   Word Count: {int(row['word_count'])}")
        print(f"   Lyrical Density: {row['lyrical_density']:.2f}")
    
    # Album statistics
    if 'album' in result_df.columns:
        print("\n" + "=" * 60)
        print("GLOOM INDEX BY ALBUM")
        print("=" * 60)
        album_stats = result_df.groupby('album').agg({
            'gloom_index': ['mean', 'median', 'min', 'max', 'count']
        }).round(2)
        album_stats.columns = ['Mean', 'Median', 'Min', 'Max', 'Songs']
        album_stats = album_stats.sort_values('Mean', ascending=False)
        print(album_stats)
    
    return result_df

if __name__ == "__main__":
    df = calculate_gloom_index()
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE!")
    print("=" * 60)

