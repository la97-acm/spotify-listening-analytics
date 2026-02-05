import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Spotify Dashboard",
    page_icon="🎵",
    layout="wide"
)

st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        color: #1DB954 !important;
        font-weight: 600;
    }
    [data-testid="stMetricLabel"] {
        font-weight: 500;
        font-size: 0.95rem;
    }
    [data-testid="column"]:first-child {
        border-right: 1px solid rgba(128, 128, 128, 0.3);
        padding-right: 2rem !important;
        margin-right: 1rem !important;
    }
    .stApp h3 {
        color: #1DB954 !important;
        font-weight: 600;
        letter-spacing: -0.5px;
        margin-bottom: 0rem !important;
    }
    .stImage img {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border-radius: 4px;
    }
    .stImage:hover img {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(29, 185, 84, 0.3);
    }
    hr {
        margin: 2.5rem 0 !important;
        border-color: rgba(128, 128, 128, 0.2) !important;
    }
    .stCaption {
        color: #FFFFFF !important;
        font-size: 0.9rem;
        letter-spacing: 2px;
        margin-top: 0rem !important;
        margin-bottom: 1.5rem !important;
    }
    .stMarkdown strong {
        font-weight: 600;
        color: #FFFFFF;
    }
    small {
        font-size: 0.875rem;
        line-height: 1.4;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and preprocess Spotify listening history data.

    Combines data from Spotify API and historical export files,
    converts timestamps to local timezone, and creates additional
    time-based columns for analysis.
    """
    df = pd.read_csv('data/combined_listening_history.csv', low_memory=False)

    # Convert UTC timestamps to local timezone (US/Eastern)
    df['played_at'] = pd.to_datetime(df['played_at'], format='mixed', utc=True)
    df['played_at_local'] = df['played_at'].dt.tz_convert('US/Eastern')

    # Filter to data from 2017 onwards for consistency
    df = df[df['played_at_local'].dt.year >= 2017]

    # Extract time components for temporal analysis
    df['year'] = df['played_at_local'].dt.year
    df['month'] = df['played_at_local'].dt.month
    df['hour'] = df['played_at_local'].dt.hour
    df['day_of_week'] = df['played_at_local'].dt.dayofweek
    df['day_name'] = df['played_at_local'].dt.day_name()
    df['minutes'] = df['duration_ms'] / 60000
    df['date'] = df['played_at_local'].dt.date

    return df

df = load_data()

@st.cache_resource
def init_spotify_client():
    """Initialize Spotify API client for fetching album/artist images.

    Uses OAuth authentication with credentials from environment variables.
    Returns None if initialization fails to allow graceful degradation.
    """
    try:
        sp_oauth = SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope='user-read-recently-played user-library-read user-top-read',
            cache_path='.spotify_cache'
        )
        return spotipy.Spotify(auth_manager=sp_oauth)
    except:
        return None

sp = init_spotify_client()

@st.cache_data
def get_track_image(track_name, artist_name):
    """Fetch album cover image URL for a track via Spotify Web API."""
    if not sp:
        return None
    try:
        results = sp.search(q=f"track:{track_name} artist:{artist_name}", type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            if track['album']['images']:
                # Return largest image (first in array)
                return track['album']['images'][0]['url']
    except:
        pass
    return None

@st.cache_data
def get_artist_image(artist_name):
    """Fetch artist profile image URL via Spotify Web API."""
    if not sp:
        return None
    try:
        results = sp.search(q=f"artist:{artist_name}", type='artist', limit=1)
        if results['artists']['items']:
            artist = results['artists']['items'][0]
            if artist['images']:
                # Return largest image (first in array)
                return artist['images'][0]['url']
    except:
        pass
    return None

def display_image_with_placeholder(image_url, fallback_emoji, width=50):
    """Display image if available, otherwise show emoji placeholder.

    Provides graceful degradation when Spotify API is unavailable
    or images can't be fetched.
    """
    if image_url:
        st.image(image_url, width=width)
    else:
        # Styled placeholder box with emoji
        st.markdown(f"""
            <div style="width: {width}px;
                        height: {width}px;
                        background-color: rgba(128, 128, 128, 0.2);
                        border-radius: 4px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 24px;">
                {fallback_emoji}
            </div>
        """, unsafe_allow_html=True)

# === Header and Year Range Filter ===
col_title, col_spacer, col_year = st.columns([3, 1, 2])

with col_title:
    st.title("🎵 Spotify Listening Dashboard")

with col_year:
    st.caption("Date Range Filter")
    available_years = sorted(df['year'].unique())
    min_year = min(available_years)
    max_year = max(available_years)

    year_col1, year_col2, year_col3 = st.columns([2, 0.3, 2])

    with year_col1:
        start_year = st.selectbox("Start Year", available_years, index=0, key="start_year")

    with year_col2:
        st.write("")
        st.write("")
        st.markdown("**—**")  # Visual separator between year selectors

    with year_col3:
        # Only show end years >= start year to prevent invalid ranges
        valid_end_years = [y for y in available_years if y >= start_year]
        default_end_index = len(valid_end_years) - 1
        end_year = st.selectbox("End Year", valid_end_years, index=default_end_index, key="end_year")

# Filter dataset based on selected year range
filtered_df = df[(df['year'] >= start_year) & (df['year'] <= end_year)]

st.markdown("---")

# === Summary Metrics ===
col1, col2, col3, col4 = st.columns(4)

# Calculate core metrics from filtered data
total_plays = len(filtered_df)
hours = filtered_df['minutes'].sum() / 60
days = hours / 24
artists = filtered_df['artist_name'].nunique()
filtered_df['track_key'] = filtered_df['track_name'] + ' - ' + filtered_df['artist_name']
tracks = filtered_df['track_key'].nunique()

# Show year-over-year comparisons when viewing a single year
if start_year == end_year and start_year > min(df['year'].unique()):
    prev_year = start_year - 1
    prev_year_df = df[df['year'] == prev_year]

    prev_plays = len(prev_year_df)
    prev_hours = prev_year_df['minutes'].sum() / 60
    prev_artists = prev_year_df['artist_name'].nunique()
    prev_year_df['track_key'] = prev_year_df['track_name'] + ' - ' + prev_year_df['artist_name']
    prev_tracks = prev_year_df['track_key'].nunique()

    plays_delta = total_plays - prev_plays
    plays_pct = (plays_delta / prev_plays * 100) if prev_plays > 0 else 0

    hours_delta = hours - prev_hours
    hours_pct = (hours_delta / prev_hours * 100) if prev_hours > 0 else 0

    artists_delta = artists - prev_artists
    artists_pct = (artists_delta / prev_artists * 100) if prev_artists > 0 else 0

    tracks_delta = tracks - prev_tracks
    tracks_pct = (tracks_delta / prev_tracks * 100) if prev_tracks > 0 else 0

    with col1:
        st.metric("Total Plays", f"{total_plays:,}",
                 f"{plays_delta:+,} ({plays_pct:+.1f}%) vs {prev_year}")

    with col2:
        st.metric("Hours Listened", f"{hours:,.0f}",
                 f"{hours_delta:+,.0f} hrs ({hours_pct:+.1f}%) vs {prev_year}")

    with col3:
        first_listen_year = df.groupby('artist_name')['year'].min()
        new_artists_this_year = (first_listen_year == start_year).sum()

        st.metric("Unique Artists", f"{artists:,}",
                 f"{artists_delta:+,} ({artists_pct:+.1f}%) vs {prev_year}")
        st.caption(f"🎤 {new_artists_this_year:,} new artists discovered")

    with col4:
        df['track_key'] = df['track_name'] + ' - ' + df['artist_name']
        first_listen_year = df.groupby('track_key')['year'].min()
        new_tracks_this_year = (first_listen_year == start_year).sum()

        st.metric("Unique Tracks", f"{tracks:,}",
                 f"{tracks_delta:+,} ({tracks_pct:+.1f}%) vs {prev_year}")
        st.caption(f"🎵 {new_tracks_this_year:,} new tracks discovered")

else:
    num_years = end_year - start_year + 1

    with col1:
        avg_per_year = total_plays / num_years
        st.metric("Total Plays", f"{total_plays:,}")
        st.markdown(f"""
            <div style="background-color: rgba(128, 128, 128, 0.25);
                        border-radius: 8px;
                        padding: 4px 8px;
                        display: inline-block;
                        font-size: 0.875rem;
                        color: #BBBBBB;">
                ▶ {avg_per_year:,.0f} avg per year
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Hours Listened", f"{hours:,.0f}")
        st.markdown(f"""
            <div style="background-color: rgba(128, 128, 128, 0.25);
                        border-radius: 8px;
                        padding: 4px 8px;
                        display: inline-block;
                        font-size: 0.875rem;
                        color: #BBBBBB;">
                🕐 {days:.0f} days total
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.metric("Unique Artists", f"{artists:,}")

        first_listen_year = df.groupby('artist_name')['year'].min()
        new_artists_in_range = ((first_listen_year >= start_year) & (first_listen_year <= end_year)).sum()

        # Only show "new discovered" if it's different from total (i.e., not the full dataset range)
        if new_artists_in_range != artists:
            st.markdown(f"""
                <div style="background-color: rgba(128, 128, 128, 0.25);
                            border-radius: 8px;
                            padding: 4px 8px;
                            display: inline-block;
                            font-size: 0.875rem;
                            color: #BBBBBB;">
                    🎤 {new_artists_in_range:,} new artists discovered
                </div>
            """, unsafe_allow_html=True)

    with col4:
        st.metric("Unique Tracks", f"{tracks:,}")

        df['track_key'] = df['track_name'] + ' - ' + df['artist_name']
        first_listen_year = df.groupby('track_key')['year'].min()
        new_tracks_in_range = ((first_listen_year >= start_year) & (first_listen_year <= end_year)).sum()

        # Only show "new discovered" if it's different from total (i.e., not the full dataset range)
        if new_tracks_in_range != tracks:
            st.markdown(f"""
                <div style="background-color: rgba(128, 128, 128, 0.25);
                            border-radius: 8px;
                            padding: 4px 8px;
                            display: inline-block;
                            font-size: 0.875rem;
                            color: #BBBBBB;">
                    🎵 {new_tracks_in_range:,} new tracks discovered
                </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# === Top Artists Section ===
st.subheader("Top Artists")
if start_year == end_year:
    st.caption(f"{start_year}")
else:
    st.caption(f"{start_year} - {end_year}")

top_artists = filtered_df['artist_name'].value_counts().head(10)

col1, col2 = st.columns([1, 1])

# Left column: Horizontal bar chart
with col1:
    fig = px.bar(
        x=top_artists.values,
        y=top_artists.index,
        orientation='h',
        labels={'x': 'Plays', 'y': ''},
        title=''
    )
    fig.update_traces(
        marker_color='#1DB954',
        hovertemplate='<b>%{y}</b><br>%{x:,} plays<extra></extra>'
    )
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

# Right column: Artist list with images in two columns
with col2:
    # Add top padding to align with chart title area
    st.markdown('<div style="margin-top: 55px;"></div>', unsafe_allow_html=True)

    subcol1, subcol2 = st.columns(2)

    # Artists 1-5
    with subcol1:
        for i in range(5):
            if i < len(top_artists):
                artist = top_artists.index[i]
                plays = top_artists.values[i]

                img_col, text_col = st.columns([1, 4])
                with img_col:
                    artist_img = get_artist_image(artist)
                    display_image_with_placeholder(artist_img, "🎤", width=50)
                with text_col:
                    st.markdown(f"<small><b>{i+1}.</b> {artist}<br>{plays:,} plays</small>", unsafe_allow_html=True)

    # Artists 6-10
    with subcol2:
        for i in range(5, 10):
            if i < len(top_artists):
                artist = top_artists.index[i]
                plays = top_artists.values[i]

                img_col, text_col = st.columns([1, 4])
                with img_col:
                    artist_img = get_artist_image(artist)
                    display_image_with_placeholder(artist_img, "🎤", width=50)
                with text_col:
                    st.markdown(f"<small><b>{i+1}.</b> {artist}<br>{plays:,} plays</small>", unsafe_allow_html=True)

st.markdown("---")

# === Top Songs Section ===
st.subheader("Top Songs")
if start_year == end_year:
    st.caption(f"{start_year}")
else:
    st.caption(f"{start_year} - {end_year}")

top_songs = filtered_df['track_name'].value_counts().head(10)

col1, col2 = st.columns([1, 1])

# Left column: Horizontal bar chart with song + artist labels
with col1:
    # Build custom labels showing both song name and artist
    song_labels = []
    song_names = []
    artists = []
    for song in top_songs.index:
        artist = filtered_df[filtered_df['track_name'] == song]['artist_name'].iloc[0]
        song_labels.append(f"<b>{song}</b><br>{artist}")
        song_names.append(song)
        artists.append(artist)

    fig = px.bar(
        x=top_songs.values,
        y=song_labels,
        orientation='h',
        labels={'x': 'Plays', 'y': ''},
        title=''
    )
    fig.update_traces(
        marker_color='#1DB954',
        customdata=list(zip(song_names, artists, top_songs.values)),
        hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]:,} plays<extra></extra>'
    )
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown('<div style="margin-top: 55px;"></div>', unsafe_allow_html=True)

    subcol1, subcol2 = st.columns(2)

    with subcol1:
        for i in range(5):
            if i < len(top_songs):
                song = top_songs.index[i]
                artist = filtered_df[filtered_df['track_name'] == song]['artist_name'].iloc[0]
                plays = top_songs.values[i]

                img_col, text_col = st.columns([1, 4])
                with img_col:
                    album_img = get_track_image(song, artist)
                    display_image_with_placeholder(album_img, "🎵", width=50)
                with text_col:
                    st.markdown(f"<small><b>{i+1}.</b> {song}<br>{artist} - {plays:,} plays</small>", unsafe_allow_html=True)

    with subcol2:
        for i in range(5, 10):
            if i < len(top_songs):
                song = top_songs.index[i]
                artist = filtered_df[filtered_df['track_name'] == song]['artist_name'].iloc[0]
                plays = top_songs.values[i]

                img_col, text_col = st.columns([1, 4])
                with img_col:
                    album_img = get_track_image(song, artist)
                    display_image_with_placeholder(album_img, "🎵", width=50)
                with text_col:
                    st.markdown(f"<small><b>{i+1}.</b> {song}<br>{artist} - {plays:,} plays</small>", unsafe_allow_html=True)

st.markdown("---")

# === Listening Activity Over Time Section ===
st.subheader("Listening Activity Over Time")
if start_year == end_year:
    st.caption(f"{start_year}")
else:
    st.caption(f"{start_year} - {end_year}")

# Allow user to toggle between different time granularities
view = st.radio("View by:", ["Month", "Week", "Day"], horizontal=True)

# Aggregate plays based on selected time period
if view == "Month":
    # Group by month and convert period index to timestamps for plotting
    time_data = filtered_df.groupby(filtered_df['played_at_local'].dt.to_period('M')).size()
    time_data.index = time_data.index.to_timestamp()
    hover_template = '<b>%{x|%B %Y}</b><br>%{y:,} plays<extra></extra>'
elif view == "Week":
    # Group by week (Sunday to Saturday)
    time_data = filtered_df.groupby(filtered_df['played_at_local'].dt.to_period('W')).size()
    time_data.index = time_data.index.to_timestamp()
    hover_template = '<b>Week of %{x|%b %d, %Y}</b><br>%{y:,} plays<extra></extra>'
else:
    # Daily granularity for detailed analysis
    time_data = filtered_df.groupby(filtered_df['date']).size()
    hover_template = '<b>%{x|%B %d, %Y}</b><br>%{y:,} plays<extra></extra>'

fig = px.line(
    x=time_data.index,
    y=time_data.values,
    labels={'x': '', 'y': 'Plays'},
    title=f'Plays per {view}'
)
fig.update_traces(
    line_color='#1DB954',
    hovertemplate=hover_template
)

if len(time_data) > 0:
    first_date = time_data.index[0]
    last_date = time_data.index[-1]
    first_year = first_date.year
    last_year = last_date.year

    if hasattr(time_data.index, 'year'):
        years_in_data = sorted(set(time_data.index.year))
    else:
        years_in_data = sorted(set([pd.Timestamp(d).year for d in time_data.index]))

    y_max = max(time_data.values)

    for year in years_in_data:
        if year > first_year:
            jan_first = pd.Timestamp(f'{year}-01-01')
            fig.add_shape(
                type="line",
                x0=jan_first, x1=jan_first,
                y0=y_max * 0.05, y1=y_max,
                line=dict(color="lightgray", width=1.5, dash="dot"),
                opacity=0.5
            )
            fig.add_annotation(
                x=jan_first,
                y=0,
                text=str(year),
                showarrow=False,
                yshift=-30,
                xshift=0,
                font=dict(size=10, color="gray")
            )

    fig.add_annotation(
        x=first_date,
        y=0,
        text=str(first_year),
        showarrow=False,
        yshift=-30,
        xshift=20,
        font=dict(size=10, color="gray")
    )

    if last_year == datetime.now().year:
        fig.add_annotation(
            x=last_date,
            y=0,
            text="current day",
            showarrow=False,
            yshift=-30,
            xshift=-20,
            font=dict(size=10, color="gray")
        )

fig.update_xaxes(showticklabels=False, title_text='')
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("When Do I Listen?")
if start_year == end_year:
    st.caption(f"{start_year}")
else:
    st.caption(f"{start_year} - {end_year}")

col1, col2 = st.columns(2)

with col1:
    hour_counts = filtered_df.groupby('hour').size().reindex(range(24), fill_value=0)

    hour_labels = []
    for h in range(24):
        if h == 0:
            hour_labels.append('12am')
        elif h < 12:
            hour_labels.append(f'{h}am')
        elif h == 12:
            hour_labels.append('12pm')
        else:
            hour_labels.append(f'{h-12}pm')

    fig = px.bar_polar(
        r=hour_counts.values,
        theta=hour_labels,
        title='Plays by Hour'
    )
    fig.update_traces(
        marker_color='#1DB954',
        marker_line_color='rgba(29, 185, 84, 0.3)',
        marker_line_width=1.5,
        opacity=0.85,
        hovertemplate='<b>%{theta}</b><br>%{r:,} plays<extra></extra>'
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                showticklabels=True,
                gridcolor='rgba(128, 128, 128, 0.3)',
                tickfont=dict(size=11)
            ),
            angularaxis=dict(
                direction='clockwise',
                rotation=90,
                tickfont=dict(size=12, color='#FFFFFF')
            ),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=False,
        height=500,
        font=dict(color='#FFFFFF')
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    day_counts = filtered_df.groupby('day_of_week').size()

    all_dates = pd.date_range(
        start=filtered_df['played_at_local'].min().date(),
        end=filtered_df['played_at_local'].max().date(),
        freq='D'
    )
    day_occurrences = all_dates.dayofweek.value_counts().sort_index()
    avg_plays_per_day = day_counts / day_occurrences

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_labels = [day_order[i] for i in sorted(avg_plays_per_day.index)]

    fig = px.line(
        x=day_labels,
        y=avg_plays_per_day.sort_index().values,
        labels={'x': 'Day of Week', 'y': 'Avg Plays per Day'},
        title='Average Plays per Day of Week',
        markers=True
    )
    fig.update_traces(
        line_color='#1DB954',
        marker=dict(size=8),
        hovertemplate='<b>%{x}</b><br>Average: %{y:.1f} plays/day<extra></extra>'
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Artist discovery (all-time only)
st.subheader("Artist Discovery (All-Time)")

col1, col2 = st.columns(2)

with col1:
    # New artists per year (using full dataset) - only count artists with 1+ plays
    artist_year_plays = df.groupby(['artist_name', 'year']).size().reset_index(name='plays')
    # Filter to artists with 1+ plays in their discovery year
    artist_year_plays = artist_year_plays[artist_year_plays['plays'] >= 1]

    # Find first year each artist was listened to (with 1+ plays)
    first_plays = df.groupby('artist_name')['played_at_local'].min()
    discoveries = first_plays.dt.year.value_counts().sort_index()

    fig = px.bar(
        x=discoveries.index,
        y=discoveries.values,
        labels={'x': 'Year', 'y': 'New Artists Discovered'},
        title='New Artists Discovered by Year'
    )
    fig.update_traces(
        marker_color='#1DB954',
        hovertemplate='<b>%{x}</b><br>%{y:,} new artists<extra></extra>'
    )

    # Show year on every bar
    fig.update_xaxes(
        tickmode='linear',
        dtick=1,
        tickangle=0
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Cumulative (using full dataset)
    cumulative = range(1, len(first_plays) + 1)
    sorted_dates = sorted(first_plays.values)

    fig = px.line(
        x=sorted_dates,
        y=cumulative,
        labels={'x': 'Date', 'y': 'Total Artists'},
        title='Cumulative Artist Discovery'
    )
    fig.update_traces(
        line_color='#1DB954',
        hovertemplate='<b>%{x|%B %d, %Y}</b><br>%{y:,} total artists<extra></extra>'
    )

    # Add Jan 1 vertical lines
    if len(sorted_dates) > 0:
        first_date = sorted_dates[0]
        last_date = sorted_dates[-1]
        first_year = pd.Timestamp(first_date).year
        last_year = pd.Timestamp(last_date).year

        y_max = len(first_plays)

        for year in range(first_year + 1, last_year + 1):
            jan_first = pd.Timestamp(f'{year}-01-01')
            fig.add_shape(
                type="line",
                x0=jan_first, x1=jan_first,
                y0=y_max * 0.05, y1=y_max,
                line=dict(color="lightgray", width=1.5, dash="dot"),
                opacity=0.5
            )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# === Seasonality Section ===
st.subheader("Seasonal Listening Patterns")
if start_year == end_year:
    st.caption(f"{start_year}")
else:
    st.caption(f"{start_year} - {end_year}")

st.markdown("""
    <div style='font-size: 0.85rem; color: #B3B3B3; margin-bottom: 1.5rem;'>
        ❄️ Winter (Dec-Feb) • 🌸 Spring (Mar-May) • ☀️ Summer (Jun-Aug) • 🍂 Fall (Sep-Nov)
    </div>
""", unsafe_allow_html=True)

# Define seasons based on meteorological seasons
def get_season(month):
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    else:  # 9, 10, 11
        return 'Fall'

filtered_df['season'] = filtered_df['month'].apply(get_season)

season_order = ['Winter', 'Spring', 'Summer', 'Fall']
season_emoji = {'Winter': '❄️', 'Spring': '🌸', 'Summer': '☀️', 'Fall': '🍂'}
season_colors = {'Winter': '#4A90E2', 'Spring': '#81C784', 'Summer': '#FFB74D', 'Fall': '#E57373'}

# Overall seasonal distribution
st.markdown("#### Your Overall Seasonal Listening")

all_season_totals = filtered_df.groupby('season').size().reindex(season_order)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        x=season_order,
        y=all_season_totals.values,
        labels={'x': 'Season', 'y': 'Total Plays'},
        title='Total Plays by Season'
    )
    fig.update_traces(
        marker_color=[season_colors[s] for s in season_order],
        hovertemplate='<b>%{x}</b><br>%{y:,} plays<extra></extra>'
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Pie chart showing percentage distribution
    fig = px.pie(
        values=all_season_totals.values,
        names=season_order,
        title='Seasonal Distribution (%)',
        color=season_order,
        color_discrete_map=season_colors
    )
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>%{value:,} plays<br>%{percent}<extra></extra>'
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Artist/Song toggle and season filter
toggle_col, season_col, sort_col = st.columns([1, 2.5, 1.5])

with toggle_col:
    view_type = st.radio("View:", ["Artists", "Songs"], horizontal=True)

with season_col:
    selected_season = st.radio(
        "Filter by season:",
        ["All Seasons"] + season_order,
        horizontal=True
    )

# Show sort options only when a specific season is selected
with sort_col:
    if selected_season != "All Seasons":
        sort_by = st.radio(
            "Sort by:",
            ["Total Plays", "Season Plays", "Season %"],
            horizontal=True,
            key="season_sort"
        )
    else:
        sort_by = "Total Plays"

st.markdown(f"#### Top {view_type} by Season")

if view_type == "Artists":
    # Get top 30 artists overall from filtered range
    top_30_items = filtered_df['artist_name'].value_counts().head(30).index.tolist()
    seasonal_df = filtered_df[filtered_df['artist_name'].isin(top_30_items)]

    # Calculate plays per season for each artist
    season_item_plays = seasonal_df.groupby(['artist_name', 'season']).size().reset_index(name='plays')

    # Create a pivot table
    heatmap_data = season_item_plays.pivot(index='artist_name', columns='season', values='plays').fillna(0)
    heatmap_data = heatmap_data.reindex(columns=season_order, fill_value=0)

    # Calculate percentage distribution
    heatmap_data_pct = heatmap_data.div(heatmap_data.sum(axis=1), axis=0) * 100

    # Calculate total plays per item for sorting
    total_plays_per_item = heatmap_data.sum(axis=1)

    # Sort based on selected season and sort option
    if selected_season == "All Seasons":
        item_order = total_plays_per_item.sort_values(ascending=False).index.tolist()
    else:
        if sort_by == "Total Plays":
            item_order = total_plays_per_item.sort_values(ascending=False).index.tolist()
        elif sort_by == "Season Plays":
            item_order = heatmap_data[selected_season].sort_values(ascending=False).index.tolist()
        else:  # Season %
            item_order = heatmap_data_pct[selected_season].sort_values(ascending=False).index.tolist()

    # Split into two columns of 15 items each
    left_col, right_col = st.columns(2)

    # Left column: Items 1-15
    with left_col:
        for idx in range(15):
            if idx < len(item_order):
                item = item_order[idx]
                global_rank = idx + 1
                total_item_plays = int(total_plays_per_item[item])

                # Compact row layout
                rank_col, img_col, info_col = st.columns([0.3, 0.5, 4])

                with rank_col:
                    st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; color: #1DB954; padding-top: 8px;'>#{global_rank}</div>", unsafe_allow_html=True)

                with img_col:
                    item_img = get_artist_image(item)
                    display_image_with_placeholder(item_img, "🎤", width=700)

                with info_col:
                    # Season boxes with hover (outline style)
                    season_boxes = " ".join([
                        f"<span title='{int(heatmap_data.loc[item, season]):,} plays' style='display: inline-block; border: 1.5px solid {season_colors[season]}; color: {season_colors[season]}; opacity: {1.0 if (selected_season == 'All Seasons' or selected_season == season) else 0.35}; padding: 2px 6px; border-radius: 4px; margin-right: 4px; font-size: 0.7rem; cursor: help;'>{season_emoji[season]} {heatmap_data_pct.loc[item, season]:.0f}%</span>"
                        for season in season_order
                    ])
                    st.markdown(f"""
                        <div style='padding-top: 4px; font-size: 0.85rem;'>
                            <div><b>{item}</b> <span style='color: #B3B3B3; font-size: 0.75rem;'>({total_item_plays:,})</span></div>
                            <div style='margin-top: 4px;'>{season_boxes}</div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 4px 0; border-color: rgba(128, 128, 128, 0.1);'>", unsafe_allow_html=True)

    # Right column: Items 16-30
    with right_col:
        for idx in range(15, 30):
            if idx < len(item_order):
                item = item_order[idx]
                global_rank = idx + 1
                total_item_plays = int(total_plays_per_item[item])

                # Compact row layout
                rank_col, img_col, info_col = st.columns([0.3, 0.5, 4])

                with rank_col:
                    st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; color: #1DB954; padding-top: 8px;'>#{global_rank}</div>", unsafe_allow_html=True)

                with img_col:
                    item_img = get_artist_image(item)
                    display_image_with_placeholder(item_img, "🎤", width=700)

                with info_col:
                    # Season boxes with hover (outline style)
                    season_boxes = " ".join([
                        f"<span title='{int(heatmap_data.loc[item, season]):,} plays' style='display: inline-block; border: 1.5px solid {season_colors[season]}; color: {season_colors[season]}; opacity: {1.0 if (selected_season == 'All Seasons' or selected_season == season) else 0.35}; padding: 2px 6px; border-radius: 4px; margin-right: 4px; font-size: 0.7rem; cursor: help;'>{season_emoji[season]} {heatmap_data_pct.loc[item, season]:.0f}%</span>"
                        for season in season_order
                    ])
                    st.markdown(f"""
                        <div style='padding-top: 4px; font-size: 0.85rem;'>
                            <div><b>{item}</b> <span style='color: #B3B3B3; font-size: 0.75rem;'>({total_item_plays:,})</span></div>
                            <div style='margin-top: 4px;'>{season_boxes}</div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 4px 0; border-color: rgba(128, 128, 128, 0.1);'>", unsafe_allow_html=True)

else:  # Songs
    # Get top 30 songs overall from filtered range
    top_30_items = filtered_df['track_name'].value_counts().head(30).index.tolist()
    seasonal_df = filtered_df[filtered_df['track_name'].isin(top_30_items)]

    # Calculate plays per season for each song
    season_item_plays = seasonal_df.groupby(['track_name', 'season']).size().reset_index(name='plays')

    # Create a pivot table
    heatmap_data = season_item_plays.pivot(index='track_name', columns='season', values='plays').fillna(0)
    heatmap_data = heatmap_data.reindex(columns=season_order, fill_value=0)

    # Calculate percentage distribution
    heatmap_data_pct = heatmap_data.div(heatmap_data.sum(axis=1), axis=0) * 100

    # Calculate total plays per item for sorting
    total_plays_per_item = heatmap_data.sum(axis=1)

    # Sort based on selected season and sort option
    if selected_season == "All Seasons":
        item_order = total_plays_per_item.sort_values(ascending=False).index.tolist()
    else:
        if sort_by == "Total Plays":
            item_order = total_plays_per_item.sort_values(ascending=False).index.tolist()
        elif sort_by == "Season Plays":
            item_order = heatmap_data[selected_season].sort_values(ascending=False).index.tolist()
        else:  # Season %
            item_order = heatmap_data_pct[selected_season].sort_values(ascending=False).index.tolist()

    # Split into two columns of 15 items each
    left_col, right_col = st.columns(2)

    # Left column: Items 1-15
    with left_col:
        for idx in range(15):
            if idx < len(item_order):
                item = item_order[idx]
                global_rank = idx + 1
                total_item_plays = int(total_plays_per_item[item])

                # Get artist for this track
                artist = filtered_df[filtered_df['track_name'] == item]['artist_name'].iloc[0]

                # Compact row layout
                rank_col, img_col, info_col = st.columns([0.3, 0.5, 4])

                with rank_col:
                    st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; color: #1DB954; padding-top: 8px;'>#{global_rank}</div>", unsafe_allow_html=True)

                with img_col:
                    item_img = get_track_image(item, artist)
                    display_image_with_placeholder(item_img, "🎵", width=50)

                with info_col:
                    # Season boxes with hover (outline style)
                    season_boxes = " ".join([
                        f"<span title='{int(heatmap_data.loc[item, season]):,} plays' style='display: inline-block; border: 1.5px solid {season_colors[season]}; color: {season_colors[season]}; opacity: {1.0 if (selected_season == 'All Seasons' or selected_season == season) else 0.35}; padding: 2px 6px; border-radius: 4px; margin-right: 4px; font-size: 0.7rem; cursor: help;'>{season_emoji[season]} {heatmap_data_pct.loc[item, season]:.0f}%</span>"
                        for season in season_order
                    ])
                    st.markdown(f"""
                        <div style='padding-top: 4px; font-size: 0.85rem;'>
                            <div><b>{item}</b> <span style='color: #B3B3B3; font-size: 0.75rem;'>({total_item_plays:,})</span></div>
                            <div style='color: #B3B3B3; font-size: 0.75rem;'>{artist}</div>
                            <div style='margin-top: 4px;'>{season_boxes}</div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 4px 0; border-color: rgba(128, 128, 128, 0.1);'>", unsafe_allow_html=True)

    # Right column: Items 16-30
    with right_col:
        for idx in range(15, 30):
            if idx < len(item_order):
                item = item_order[idx]
                global_rank = idx + 1
                total_item_plays = int(total_plays_per_item[item])

                # Get artist for this track
                artist = filtered_df[filtered_df['track_name'] == item]['artist_name'].iloc[0]

                # Compact row layout
                rank_col, img_col, info_col = st.columns([0.3, 0.5, 4])

                with rank_col:
                    st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; color: #1DB954; padding-top: 8px;'>#{global_rank}</div>", unsafe_allow_html=True)

                with img_col:
                    item_img = get_track_image(item, artist)
                    display_image_with_placeholder(item_img, "🎵", width=50)

                with info_col:
                    # Season boxes with hover (outline style)
                    season_boxes = " ".join([
                        f"<span title='{int(heatmap_data.loc[item, season]):,} plays' style='display: inline-block; border: 1.5px solid {season_colors[season]}; color: {season_colors[season]}; opacity: {1.0 if (selected_season == 'All Seasons' or selected_season == season) else 0.35}; padding: 2px 6px; border-radius: 4px; margin-right: 4px; font-size: 0.7rem; cursor: help;'>{season_emoji[season]} {heatmap_data_pct.loc[item, season]:.0f}%</span>"
                        for season in season_order
                    ])
                    st.markdown(f"""
                        <div style='padding-top: 4px; font-size: 0.85rem;'>
                            <div><b>{item}</b> <span style='color: #B3B3B3; font-size: 0.75rem;'>({total_item_plays:,})</span></div>
                            <div style='color: #B3B3B3; font-size: 0.75rem;'>{artist}</div>
                            <div style='margin-top: 4px;'>{season_boxes}</div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 4px 0; border-color: rgba(128, 128, 128, 0.1);'>", unsafe_allow_html=True)

# Show total count
st.caption(f"Showing top {len(item_order)} {view_type.lower()}")

# Footer
st.markdown("---")
st.caption("Data from Spotify API + Historical Export | Updated daily via Airflow")
