"""
Combined Spotify Analytics
Loads historical CSV data and merges it with recent API listening data
"""

import os
import json
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === Data Filtering Constants ===
# Only count plays longer than 30 seconds (Spotify's "counted as played" threshold)
MIN_PLAY_TIME_MS = 30000

# Filter for music only, excluding podcasts and video content
CONTENT_TYPE_FILTER = 'audio'

# Timezone for local timestamp conversion
TIMEZONE = 'US/Eastern'

class CombinedSpotifyAnalytics:
    """
    Combines historical CSV data with recent API data
    """

    def __init__(self, csv_path="data/Spotify Streaming History.csv"):
        self.csv_path = Path(csv_path)
        self.historical_data = None
        self.api_data = None
        self.combined_data = None

        # Initialize Spotify API client
        self.sp = self._init_spotify_client()

    def _init_spotify_client(self):
        """Initialize Spotify API client with authentication"""
        try:
            sp_oauth = SpotifyOAuth(
                client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
                scope=' '.join([
                    'user-read-recently-played',
                    'user-library-read',
                    'user-top-read',
                ]),
                cache_path='.spotify_cache'
            )

            sp = spotipy.Spotify(auth_manager=sp_oauth)
            print("✅ Successfully connected to Spotify API")
            return sp
        except Exception as e:
            print(f"⚠️  Warning: Could not connect to Spotify API: {e}")
            print("   Will only use historical CSV data")
            return None

    def load_historical_csv(self):
        """Load and process the historical CSV data"""
        print(f"\n📂 Loading historical data from {self.csv_path}...")

        if not self.csv_path.exists():
            print(f"❌ Error: CSV file not found at {self.csv_path}")
            return False

        # Load CSV
        df = pd.read_csv(self.csv_path)

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['ts'])

        # Filter out very short plays
        # Why 30 seconds? Spotify only counts plays > 30s in official statistics
        df = df[df['ms_played'] >= MIN_PLAY_TIME_MS]

        # Filter for audio content only (music, not podcasts/videos)
        # Why audio only? This dashboard focuses on music listening patterns
        df = df[df['content_type'] == CONTENT_TYPE_FILTER]

        # Create standardized columns
        df['played_at'] = df['timestamp']
        df['track_name'] = df['master_metadata_track_name']
        df['artist_name'] = df['master_metadata_album_artist_name']
        df['album_name'] = df['master_metadata_album_album_name']
        df['duration_ms'] = df['ms_played']

        # Remove rows with null track names (couldn't be identified)
        df = df[df['track_name'].notna()]

        self.historical_data = df[['played_at', 'track_name', 'artist_name',
                                     'album_name', 'duration_ms', 'spotify_track_uri',
                                     'platform', 'conn_country', 'shuffle', 'skipped']]

        print(f"✅ Loaded {len(self.historical_data):,} historical streams")
        print(f"   Date range: {self.historical_data['played_at'].min()} to {self.historical_data['played_at'].max()}")

        return True

    def fetch_recent_api_data(self, limit=50):
        """
        Fetch recent listening history from Spotify API

        Args:
            limit: Number of recently played tracks to fetch (max 50 per request)
        """
        if not self.sp:
            print("\n⚠️  Skipping API fetch - not connected")
            return False

        print(f"\n🔄 Fetching recent listening data from Spotify API...")

        try:
            all_tracks = []

            # Fetch recently played tracks
            # Note: Spotify API only provides last 50 tracks
            results = self.sp.current_user_recently_played(limit=limit)

            for item in results['items']:
                track = item['track']

                all_tracks.append({
                    'played_at': item['played_at'],
                    'track_name': track['name'],
                    'artist_name': track['artists'][0]['name'] if track['artists'] else None,
                    'album_name': track['album']['name'] if track['album'] else None,
                    'duration_ms': track['duration_ms'],
                    'spotify_track_uri': track['uri'],
                    'platform': 'API',
                    'conn_country': None,
                    'shuffle': None,
                    'skipped': None,
                })

            self.api_data = pd.DataFrame(all_tracks)
            self.api_data['played_at'] = pd.to_datetime(self.api_data['played_at'])

            print(f"✅ Fetched {len(self.api_data)} recent tracks from API")
            if len(self.api_data) > 0:
                print(f"   Date range: {self.api_data['played_at'].min()} to {self.api_data['played_at'].max()}")

            return True

        except Exception as e:
            print(f"❌ Error fetching API data: {e}")
            return False

    def combine_data(self):
        """Merge historical CSV data with recent API data"""
        print(f"\n🔗 Combining historical and API data...")

        if self.historical_data is None:
            print("❌ No historical data loaded")
            return False

        # Start with historical data
        combined = self.historical_data.copy()

        # Add API data if available
        if self.api_data is not None and len(self.api_data) > 0:
            # Find the cutoff date (last date in historical data)
            last_historical_date = combined['played_at'].max()

            # Only add API data that's newer than historical data
            new_api_data = self.api_data[self.api_data['played_at'] > last_historical_date]

            if len(new_api_data) > 0:
                combined = pd.concat([combined, new_api_data], ignore_index=True)
                print(f"✅ Added {len(new_api_data)} new tracks from API")
            else:
                print(f"ℹ️  No new tracks from API (historical data is up to date)")

        # Sort by timestamp
        combined = combined.sort_values('played_at').reset_index(drop=True)

        # Remove duplicates (same track played at same time)
        combined = combined.drop_duplicates(subset=['played_at', 'track_name', 'artist_name'], keep='first')

        self.combined_data = combined

        print(f"\n📊 Combined Data Summary:")
        print(f"   Total streams: {len(self.combined_data):,}")
        print(f"   Date range: {self.combined_data['played_at'].min()} to {self.combined_data['played_at'].max()}")
        print(f"   Unique tracks: {self.combined_data['track_name'].nunique():,}")
        print(f"   Unique artists: {self.combined_data['artist_name'].nunique():,}")

        return True

    def get_statistics(self):
        """Get comprehensive statistics from combined data"""
        if self.combined_data is None:
            print("❌ No combined data available")
            return None

        df = self.combined_data

        stats = {
            'total_streams': len(df),
            'unique_tracks': df['track_name'].nunique(),
            'unique_artists': df['artist_name'].nunique(),
            'total_hours': round(df['duration_ms'].sum() / (1000 * 60 * 60), 1),
            'date_range': {
                'first': df['played_at'].min().strftime('%Y-%m-%d'),
                'last': df['played_at'].max().strftime('%Y-%m-%d'),
            },
            'years_of_data': df['played_at'].dt.year.nunique(),
        }

        # Top artists
        top_artists = df['artist_name'].value_counts().head(10)
        stats['top_10_artists'] = top_artists.to_dict()

        # Top tracks
        top_tracks = df.groupby(['track_name', 'artist_name']).size().nlargest(10)
        stats['top_10_tracks'] = [
            {'track': track, 'artist': artist, 'plays': count}
            for (track, artist), count in top_tracks.items()
        ]

        return stats

    def save_combined_data(self, output_path="data/combined_listening_history.csv"):
        """Save the combined data to a CSV file"""
        if self.combined_data is None:
            print("❌ No combined data to save")
            return False

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.combined_data.to_csv(output_path, index=False)
        print(f"\n💾 Saved combined data to {output_path}")

        return True

    def print_statistics(self):
        """Print comprehensive statistics"""
        stats = self.get_statistics()

        if not stats:
            return

        print("\n" + "="*60)
        print("🎵 YOUR COMPLETE SPOTIFY STATISTICS 🎵")
        print("="*60)
        print(f"Total Streams: {stats['total_streams']:,}")
        print(f"Unique Tracks: {stats['unique_tracks']:,}")
        print(f"Unique Artists: {stats['unique_artists']:,}")
        print(f"Total Listening Time: {stats['total_hours']:,} hours")
        print(f"Date Range: {stats['date_range']['first']} to {stats['date_range']['last']}")
        print(f"Years of Data: {stats['years_of_data']}")

        print(f"\n🏆 Top 10 Artists:")
        for i, (artist, plays) in enumerate(list(stats['top_10_artists'].items()), 1):
            print(f"   {i:2}. {artist:<40} ({plays:,} plays)")

        print(f"\n🎵 Top 10 Tracks:")
        for i, track_info in enumerate(stats['top_10_tracks'], 1):
            print(f"   {i:2}. {track_info['track']:<35} - {track_info['artist']:<30} ({track_info['plays']} plays)")

        print("="*60)


def main():
    """Main execution"""
    print("🎵 Combined Spotify Analytics")
    print("   Historical CSV + Recent API Data\n")

    # Initialize analytics
    analytics = CombinedSpotifyAnalytics()

    # Load historical CSV
    if not analytics.load_historical_csv():
        print("\n❌ Failed to load historical data")
        return

    # Fetch recent API data
    analytics.fetch_recent_api_data(limit=50)

    # Combine the data
    if not analytics.combine_data():
        print("\n❌ Failed to combine data")
        return

    # Print statistics
    analytics.print_statistics()

    # Save combined data
    analytics.save_combined_data()

    print("\n✨ Analysis complete!")
    print("\n💡 Next steps:")
    print("   - Use the combined data for visualizations")
    print("   - Run this script periodically to update with latest API data")
    print("   - The combined data is saved to data/combined_listening_history.csv")


if __name__ == "__main__":
    main()
