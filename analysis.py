import pandas as pd
import plotly.graph_objects as go
import numpy as np

def create_viral_radiohead_plot():
    """
    Recreate the viral 'Data-Driven Depression: Radiohead' visualization.
    Jittered scatter plot with album means.
    """
    
    # Load data
    df = pd.read_csv('radiohead_gloom_analysis.csv')
    
    # Define album order (chronological)
    album_order = [
        'OK Computer',
        'Kid A', 
        'Amnesiac',
        'In Rainbows',
        'A Moon Shaped Pool'
    ]
    
    # Filter to main albums only and ensure we have data
    df_filtered = df[df['album'].isin(album_order)].copy()
    
    print(f"Creating visualization with {len(df_filtered)} songs from {df_filtered['album'].nunique()} albums")
    
    # Create figure
    fig = go.Figure()
    
    # Color palette - subdued colors
    colors = {
        'OK Computer': '#e41a1c',
        'Kid A': '#377eb8',
        'Amnesiac': '#4daf4a',
        'In Rainbows': '#984ea3',
        'A Moon Shaped Pool': '#ff7f00'
    }
    
    # Track data for legend
    added_to_legend = set()
    
    # Process each album
    for i, album in enumerate(album_order):
        album_data = df_filtered[df_filtered['album'] == album]
        
        if len(album_data) == 0:
            continue
        
        n_songs = len(album_data)
        
        # Create jittered x positions (add random noise for visual separation)
        np.random.seed(42 + i)  # Consistent jitter
        if n_songs > 1:
            jitter_amount = 0.25
            x_positions = [i + np.random.uniform(-jitter_amount, jitter_amount) for _ in range(n_songs)]
        else:
            x_positions = [i]
        
        # Add individual song points
        for idx, (x_pos, (_, row)) in enumerate(zip(x_positions, album_data.iterrows())):
            show_legend = album not in added_to_legend
            
            hover_text = (
                f"<b>{row['track_name']}</b><br>" +
                f"Album: {row['album']}<br>" +
                f"<b>Gloom Index: {row['gloom_index']:.1f}</b><br>" +
                f"Valence: {row['valence']:.3f}<br>" +
                f"Sad Words: {row['pct_sad']*100:.1f}%<br>" +
                f"Word Count: {int(row['word_count'])}"
            )
            
            fig.add_trace(go.Scatter(
                x=[x_pos],
                y=[row['gloom_index']],
                mode='markers',
                name=album,
                legendgroup=album,
                showlegend=show_legend,
                marker=dict(
                    size=10,
                    color=colors[album],
                    opacity=0.7,
                    line=dict(width=0.5, color='white')
                ),
                text=hover_text,
                hoverinfo='text',
                hoverlabel=dict(
                    bgcolor=colors[album],
                    font=dict(color='white', size=12)
                )
            ))
            
            if show_legend:
                added_to_legend.add(album)
    
    # Calculate album means for trend line
    album_means = []
    album_x_positions = []
    for i, album in enumerate(album_order):
        album_data = df_filtered[df_filtered['album'] == album]
        if len(album_data) > 0:
            album_means.append(album_data['gloom_index'].mean())
            album_x_positions.append(i)
    
    # Add trend line connecting album averages
    fig.add_trace(go.Scatter(
        x=album_x_positions,
        y=album_means,
        mode='lines+markers',
        name='Album Average',
        line=dict(
            color='rgba(0, 0, 0, 0.6)',
            width=3,
            dash='solid'
        ),
        marker=dict(
            size=12,
            color='rgba(0, 0, 0, 0.8)',
            symbol='diamond',
            line=dict(width=2, color='white')
        ),
        hovertemplate='<b>%{text}</b><br>Mean Gloom: %{y:.2f}<extra></extra>',
        text=[album_order[i] for i in album_x_positions],
        showlegend=True,
        legendgroup='average'
    ))
    
    # Calculate overall statistics
    overall_mean = df_filtered['gloom_index'].mean()
    
    # Update layout with the viral plot aesthetic
    fig.update_layout(
        title={
            'text': '<b>Data-Driven Depression: Radiohead</b><br>' +
                    '<sub>Gloom Index by Album (Lower = More Gloomy)</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis=dict(
            title='',
            ticktext=album_order,
            tickvals=list(range(len(album_order))),
            tickangle=-45,
            tickfont=dict(size=12),
            showgrid=False,
            zeroline=False,
            range=[-0.6, len(album_order) - 0.4]
        ),
        yaxis=dict(
            title=dict(
                text='<b>Gloom Index</b>',
                font=dict(size=14)
            ),
            tickfont=dict(size=11),
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=False,
            range=[0, 105]
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        height=700,
        width=1200,
        showlegend=True,
        legend=dict(
            title='<b>Albums</b>',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1,
            font=dict(size=11)
        ),
        margin=dict(l=80, r=200, t=100, b=100),
        font=dict(family='Arial, sans-serif')
    )
    
    # Add overall mean reference line (optional, subtle)
    fig.add_hline(
        y=overall_mean,
        line_dash='dot',
        line_color='rgba(128, 128, 128, 0.3)',
        line_width=1,
        annotation_text=f"Overall mean: {overall_mean:.1f}",
        annotation_position='right',
        annotation=dict(font=dict(size=9, color='gray'))
    )
    
    # Save the plot
    output_file = 'data_driven_depression_radiohead.html'
    fig.write_html(output_file)
    print(f"\n✅ Viral-style plot saved as '{output_file}'")
    
    # Print summary
    print("\n" + "="*70)
    print("ALBUM SUMMARY")
    print("="*70)
    
    for album in album_order:
        album_data = df_filtered[df_filtered['album'] == album]
        if len(album_data) > 0:
            mean = album_data['gloom_index'].mean()
            median = album_data['gloom_index'].median()
            n = len(album_data)
            print(f"\n{album}:")
            print(f"  Songs: {n}")
            print(f"  Mean Gloom: {mean:.2f}")
            print(f"  Median Gloom: {median:.2f}")
            print(f"  Range: {album_data['gloom_index'].min():.2f} - {album_data['gloom_index'].max():.2f}")
    
    print("\n" + "="*70)
    print(f"Overall Mean Gloom Index: {overall_mean:.2f}")
    print("="*70)
    
    return fig

if __name__ == "__main__":
    print("Creating viral 'Data-Driven Depression: Radiohead' visualization...")
    print("="*70)
    fig = create_viral_radiohead_plot()
    print("\n🎉 Visualization complete!")
    print("\nOpen 'data_driven_depression_radiohead.html' in your browser to view.")

