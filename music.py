import os
from typing import Optional
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
import re
import yt_dlp

_sp: Optional[spotipy.Spotify] = None

def _get_client() -> Optional[spotipy.Spotify]:
    global _sp
    if _sp is not None:
        return _sp
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    auth = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
    _sp = spotipy.Spotify(auth_manager=auth)
    return _sp

def _is_spotify_url(query: str) -> bool:
    return query.startswith("https://open.spotify.com/") or query.startswith("spotify:")

def get_preview_url(query: str) -> Optional[str]:
    """Resolve a Spotify track URL or search query to a preview MP3 URL (30s).

    Returns None if not available or credentials missing.
    """
    sp = _get_client()
    if sp is None:
        print("Spotify client not available - check SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        return None

    try:
        track = None
        if _is_spotify_url(query):
            track = sp.track(query)
        else:
            results = sp.search(q=query, type="track", limit=1)
            items = results.get("tracks", {}).get("items", [])
            track = items[0] if items else None
            
        if not track:
            print(f"No track found for query: {query}")
            return None
            
        preview_url = track.get("preview_url")
        if not preview_url:
            print(f"Track '{track.get('name', 'Unknown')}' by {track.get('artists', [{}])[0].get('name', 'Unknown')} has no preview URL available")
        return preview_url
    except Exception as e:
        print(f"Spotify API error: {e}")
        return None

def get_youtube_url(query: str) -> Optional[str]:
    """Get a YouTube URL for the query as a fallback using yt-dlp."""
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search for the query on YouTube
            search_query = f"ytsearch1:{query}"
            result = ydl.extract_info(search_query, download=False)
            
            if result and 'entries' in result and result['entries']:
                video = result['entries'][0]
                if video:
                    # Get the direct audio URL
                    video_id = video.get('id')
                    if video_id:
                        # Extract the direct audio stream URL
                        full_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                        if full_info and 'url' in full_info:
                            return full_info['url']
                        elif full_info and 'formats' in full_info:
                            # Find the best audio format
                            for fmt in full_info['formats']:
                                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                                    return fmt.get('url')
                    # Return the YouTube watch URL as fallback
                    return f"https://www.youtube.com/watch?v={video_id}"
        
        return None
    except Exception as e:
        print(f"YouTube search error: {e}")
        return None

def get_any_audio_url(query: str) -> Optional[str]:
    """Try to get any available audio URL (Spotify preview or YouTube fallback)."""
    # First try Spotify
    spotify_url = get_preview_url(query)
    if spotify_url:
        return spotify_url
    
    # If no Spotify preview, try YouTube (placeholder)
    youtube_url = get_youtube_url(query)
    if youtube_url:
        return youtube_url
    
    return None

# Global music state
current_volume = 0.5  # Default volume (0.0 to 1.0)
is_looping = False
current_track_info = None

def set_volume(volume: float) -> float:
    """Set the volume level (0.0 to 1.0)."""
    global current_volume
    current_volume = max(0.0, min(1.0, volume))
    return current_volume

def get_volume() -> float:
    """Get the current volume level."""
    return current_volume

def toggle_loop() -> bool:
    """Toggle loop mode on/off."""
    global is_looping
    is_looping = not is_looping
    return is_looping

def get_loop_status() -> bool:
    """Get the current loop status."""
    return is_looping

def set_current_track(track_name: str, artist: str = None):
    """Set the current track information."""
    global current_track_info
    current_track_info = {
        'name': track_name,
        'artist': artist or 'Unknown'
    }

def get_current_track():
    """Get the current track information."""
    return current_track_info
