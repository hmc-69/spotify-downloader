from flask import Flask, request, jsonify, send_file, render_template
import os
import re
import logging
import subprocess
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Initialize Spotify client
spotify = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# Ensure downloads directory exists
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/fetch-playlist', methods=['POST'])
def fetch_playlist():
    data = request.json
    playlist_url = data.get('url')
    
    if not playlist_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Extract playlist ID from URL
        playlist_id = extract_playlist_id(playlist_url)
        if not playlist_id:
            return jsonify({'error': 'Invalid Spotify playlist URL'}), 400
        
        # Fetch all tracks from Spotify API
        playlist_data = spotify.playlist(playlist_id)
        all_items = get_all_playlist_tracks(playlist_id)
        tracks = []

        for item in all_items:
            track = item['track']
            tracks.append({
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'duration': track['duration_ms']
            })
        
        playlist_info = {
            'id': playlist_data['id'],
            'name': playlist_data['name'],
            'description': playlist_data['description'],
            'image': playlist_data['images'][0]['url'] if playlist_data['images'] else '',
            'trackCount': len(tracks)
        }
        
        return jsonify({
            'playlist': playlist_info,
            'tracks': tracks
        })
    
    except Exception as e:
        logger.error(f"Error fetching playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-all', methods=['POST'])
def download_all_tracks():
    data = request.json
    tracks = data.get('tracks')
    
    if not tracks:
        return jsonify({'error': 'No tracks provided'}), 400
    
    try:
        results = []
        
        for track in tracks:
            query = f"{track['name']} {track['artist']} audio"
            youtube_match = find_youtube_match(query)
            
            if youtube_match:
                filename = f"{track['name']} - {track['artist']}.mp3"
                filename = re.sub(r'[\\/*?:"<>|]', '', filename)  # Sanitize filename
                output_path = os.path.join(DOWNLOADS_DIR, filename)
                
                result = download_from_youtube(youtube_match['url'], output_path)
                results.append({
                    'track': f"{track['name']} - {track['artist']}",
                    'success': result['success'],
                    'error': result.get('error')
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Error downloading all tracks: {str(e)}")
        return jsonify({'error': str(e)}), 500

def extract_playlist_id(url):
    """Extract the Spotify playlist ID from a URL."""
    try:
        if 'playlist/' in url:
            return url.split('playlist/')[1].split('?')[0]
        return None
    except Exception as e:
        logger.error(f"Error extracting playlist ID: {str(e)}")
        return None

def find_youtube_match(query):
    """Find a matching YouTube video for a track."""
    try:
        cmd = [
            'yt-dlp', 
            f'ytsearch1:{query}',
            '--get-title',
            '--get-id',
            '--no-playlist'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                video_title = lines[0]
                video_id = lines[1]
                return {
                    'title': video_title,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'id': video_id
                }
        return None
    except Exception as e:
        logger.error(f"Error finding YouTube match: {str(e)}")
        return None

def download_from_youtube(youtube_url, output_path):
    """Download audio from YouTube using yt-dlp."""
    try:
        cmd = [
            'yt-dlp',
            '-x',  # Extract audio
            '--audio-format', 'mp3',
            '--audio-quality', '0',  # Best quality
            '-o', output_path,
            youtube_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {'success': True}
        else:
            return {'success': False, 'error': result.stderr}
    
    except Exception as e:
        logger.error(f"Error downloading from YouTube: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_all_playlist_tracks(playlist_id):
    tracks = []
    results = spotify.playlist_tracks(playlist_id, limit=100, offset=0)
    tracks.extend(results['items'])
    while results['next']:
        results = spotify.next(results)
        tracks.extend(results['items'])
    return tracks

if __name__ == '__main__':
    app.run(debug=True, port=5000)