"""
Spotify Authorization Script

Run this ONCE before starting Docker containers to create .spotify_cache file.

Usage:
    1. Make sure .env file has your Spotify credentials
    2. Make sure SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
    3. Run: python3 authorize_spotify.py
    4. Browser opens, click "Agree"
    5. Script creates .spotify_cache file
    6. Start Docker: docker-compose up -d

Note: .spotify_cache is valid for 60 days. If it expires, run this script again.
"""

import os
import sys
from pathlib import Path

# Check if .env file exists
if not Path('.env').exists():
    print("❌ Error: .env file not found!")
    print("\nPlease create .env file with your Spotify credentials:")
    print("  cp .env.example .env")
    print("  nano .env  # Edit with your credentials")
    sys.exit(1)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("❌ Error: python-dotenv not installed")
    print("\nInstall dependencies:")
    print("  pip3 install spotipy python-dotenv")
    sys.exit(1)

# Check credentials are set
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

if not client_id or client_id == 'your_client_id_here':
    print("❌ Error: SPOTIFY_CLIENT_ID not set in .env file")
    sys.exit(1)

if not client_secret or client_secret == 'your_client_secret_here':
    print("❌ Error: SPOTIFY_CLIENT_SECRET not set in .env file")
    sys.exit(1)

if not redirect_uri:
    print("❌ Error: SPOTIFY_REDIRECT_URI not set in .env file")
    print("\nShould be: http://127.0.0.1:8888/callback")
    sys.exit(1)

# Warn if using localhost instead of 127.0.0.1
if 'localhost' in redirect_uri.lower():
    print("⚠️  WARNING: You're using 'localhost' in redirect URI")
    print("   Spotify now requires '127.0.0.1' instead")
    print("\nUpdate your .env file:")
    print("  SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback")
    print("\nAnd update Spotify Developer Dashboard to match")
    response = input("\nContinue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(0)

print("=" * 60)
print("Spotify Authorization")
print("=" * 60)
print(f"\nClient ID: {client_id[:20]}...")
print(f"Redirect URI: {redirect_uri}")
print("\nAttempting authorization...")

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("\n❌ Error: spotipy not installed")
    print("\nInstall dependencies:")
    print("  pip3 install spotipy python-dotenv")
    sys.exit(1)

# Create auth manager
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=' '.join([
        'user-read-recently-played',
        'user-library-read',
        'playlist-read-private',
        'playlist-read-collaborative',
        'user-top-read',
        'user-read-playback-state',
        'user-read-currently-playing',
    ]),
    cache_path='.spotify_cache',
    open_browser=True  # Automatically opens browser
)

print("\n🌐 Opening browser for authorization...")
print("   (If browser doesn't open, copy the URL from terminal)")

# Get Spotify client (this triggers the auth flow)
sp = spotipy.Spotify(auth_manager=sp_oauth)

# Test it works
try:
    user = sp.current_user()
    
    print("\n" + "=" * 60)
    print("✅ AUTHORIZATION SUCCESSFUL!")
    print("=" * 60)
    print(f"\n👤 Logged in as: {user['display_name']}")
    print(f"📧 Email: {user.get('email', 'N/A')}")
    print(f"🎵 Country: {user.get('country', 'N/A')}")
    print(f"💾 Cache file: .spotify_cache (created)")
    
    # Verify cache file exists
    if Path('.spotify_cache').exists():
        print("\n✓ Cache file verified")
    else:
        print("\n⚠️  Warning: Cache file not found")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("\n1. Start Docker containers:")
    print("   docker-compose up -d")
    print("\n2. Wait 90 seconds for initialization")
    print("\n3. Open Airflow UI:")
    print("   http://localhost:8080")
    print("   Username: admin")
    print("   Password: admin")
    print("\n4. Enable and trigger 'spotify_ingestion_pipeline'")
    print("\n" + "=" * 60)
    
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ AUTHORIZATION FAILED")
    print("=" * 60)
    print(f"\nError: {e}")
    print("\nCommon fixes:")
    print("  1. Check credentials in .env are correct")
    print("  2. Verify redirect URI matches Spotify Developer Dashboard:")
    print(f"     {redirect_uri}")
    print("  3. Make sure you're using http://127.0.0.1:8888/callback")
    print("     (not localhost)")
    sys.exit(1)