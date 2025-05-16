from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
import os
import requests
from bs4 import BeautifulSoup
import json
import re
import subprocess
import zipfile
import shutil
from urllib.parse import urlparse, parse_qs
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')

# Ensure downloads directory exists
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

@app.route('/')
def index():
    return send_file('index.html')

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
        
        # Get playlist metadata using Spotify's oembed endpoint
        playlist_info = get_playlist_info(playlist_id)
        
        # Scrape playlist tracks
        tracks = scrape_playlist_tracks(playlist_url)
        
        # Find YouTube matches for each track
        for track in tracks:
            track['youtube'] = find_youtube_match(f"{track['name']} {track['artist']} audio")
        
        return jsonify({
            'playlist': playlist_info,
            'tracks': tracks
        })
    
    except Exception as e:
        logger.error(f"Error fetching playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_track():
    data = request.json
    youtube_url = data.get('youtube_url')
    track_name = data.get('track_name')
    artist_name = data.get('artist_name')
    
    if not youtube_url or not track_name or not artist_name:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        filename = f"{track_name} - {artist_name}.mp3"
        # Sanitize filename
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        output_path = os.path.join(DOWNLOADS_DIR, filename)
        
        # Download audio using yt-dlp
        result = download_from_youtube(youtube_url, output_path)
        
        if result['success']:
            return jsonify({
                'success': True,
                'filename': filename,
                'path': output_path
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
    
    except Exception as e:
        logger.error(f"Error downloading track: {str(e)}")
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
            youtube_url = track.get('youtube_url')
            track_name = track.get('name')
            artist_name = track.get('artist')
            
            filename = f"{track_name} - {artist_name}.mp3"
            # Sanitize filename
            filename = re.sub(r'[\\/*?:"<>|]', '', filename)
            output_path = os.path.join(DOWNLOADS_DIR, filename)
            
            # Download audio using yt-dlp
            result = download_from_youtube(youtube_url, output_path)
            
            results.append({
                'track': f"{track_name} - {artist_name}",
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

@app.route('/api/download-zip', methods=['GET'])
def download_zip():
    try:
        # Create a ZIP file of all downloaded MP3s
        zip_path = os.path.join(os.path.dirname(DOWNLOADS_DIR), 'playlist_download.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in os.listdir(DOWNLOADS_DIR):
                if file.endswith('.mp3'):
                    zipf.write(
                        os.path.join(DOWNLOADS_DIR, file),
                        arcname=file
                    )
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='playlist_download.zip'
        )
    
    except Exception as e:
        logger.error(f"Error creating ZIP file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)

def extract_playlist_id(url):
    """Extract the Spotify playlist ID from a URL."""
    try:
        parsed_url = urlparse(url)
        
        # Handle different URL formats
        if 'open.spotify.com' in parsed_url.netloc:
            path_parts = parsed_url.path.split('/')
            if 'playlist' in path_parts:
                playlist_index = path_parts.index('playlist')
                if playlist_index + 1 < len(path_parts):
                    # Handle query parameters if present
                    playlist_id = path_parts[playlist_index + 1].split('?')[0]
                    return playlist_id
        
        return None
    except Exception as e:
        logger.error(f"Error extracting playlist ID: {str(e)}")
        return None

def get_playlist_info(playlist_id):
    """Get playlist metadata using Spotify's oembed endpoint."""
    try:
        url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/playlist/{playlist_id}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract playlist name from title (remove " - playlist by...")
        playlist_name = data.get('title', '').split(' - playlist by')[0]
        
        return {
            'id': playlist_id,
            'name': playlist_name,
            'description': data.get('description', ''),
            'image': data.get('thumbnail_url', ''),
            'trackCount': 0  # Will be updated after scraping
        }
    except Exception as e:
        logger.error(f"Error getting playlist info: {str(e)}")
        return {
            'id': playlist_id,
            'name': 'Unknown Playlist',
            'description': '',
            'image': '',
            'trackCount': 0
        }

def scrape_playlist_tracks(playlist_url):
    """Scrape track information from a Spotify playlist page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(playlist_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the JSON data in the page
        # Spotify usually includes a script tag with JSON data
        tracks = []
        
        # Look for script tags with JSON data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'Spotify.Entity' in script.string:
                # Extract JSON data
                json_match = re.search(r'Spotify\.Entity = ({.*?});', script.string, re.DOTALL)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1))
                        # Extract tracks from JSON data
                        if 'tracks' in json_data:
                            for track in json_data['tracks']['items']:
                                track_info = {
                                    'id': track['id'],
                                    'name': track['name'],
                                    'artist': track['artists'][0]['name'],
                                    'duration': track['duration_ms']
                                }
                                tracks.append(track_info)
                    except json.JSONDecodeError:
                        continue
        
        # If we couldn't extract tracks from JSON, try parsing HTML directly
        if not tracks:
            # This is a fallback method and may break if Spotify changes their HTML structure
            track_elements = soup.select('.tracklist-row')
            
            for element in track_elements:
                name_element = element.select_one('.tracklist-name')
                artist_element = element.select_one('.tracklist-artist')
                
                if name_element and artist_element:
                    track_info = {
                        'id': element.get('data-track-id', ''),
                        'name': name_element.text.strip(),
                        'artist': artist_element.text.strip(),
                        'duration': 0
                    }
                    tracks.append(track_info)
        
        return tracks
    
    except Exception as e:
        logger.error(f"Error scraping playlist tracks: {str(e)}")
        # If scraping fails, return an empty list
        return []

def find_youtube_match(query):
    """Find a matching YouTube video for a track."""
    try:
        # In a real implementation, you would use YouTube Data API or scrape search results
        # For this example, we'll return a mock result
        
        # Sanitize the query
        query = query.replace('"', '').replace("'", "")
        
        # Use yt-dlp to search for videos
        cmd = [
            'yt-dlp', 
            'ytsearch1:' + query,
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
        
        # Fallback mock data if yt-dlp fails
        return {
            'title': f'YouTube result for: {query}',
            'url': f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}',
            'id': ''
        }
    
    except Exception as e:
        logger.error(f"Error finding YouTube match: {str(e)}")
        return {
            'title': f'Search on YouTube: {query}',
            'url': f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}',
            'id': ''
        }

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)