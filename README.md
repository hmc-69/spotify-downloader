# Spotify Playlist Downloader

A private-use website to download songs from public Spotify playlists without requiring authentication.

## Features

- Paste a public Spotify playlist URL to extract track information
- Search and match each song on YouTube
- Download audio as MP3 files using yt-dlp
- Download all songs as a ZIP file

## Requirements

- Python 3.7+
- yt-dlp (for YouTube downloading)
- Modern web browser

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/spotify-downloader.git
   cd spotify-downloader
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install yt-dlp if not included in your system:
   ```
   pip install yt-dlp
   ```

## Usage

1. Start the Flask server:
   ```
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Paste a public Spotify playlist URL and click "Fetch Songs"

4. Review the matched YouTube videos for each track

5. Download individual songs or the entire playlist

## Legal & Ethical Guidelines

- This tool is for **private use only**
- Only works with **public** Spotify playlists
- Does not use Spotify's protected audio
- Downloads from YouTube only (as permitted under their terms)
- Please respect copyright laws in your jurisdiction

## Technical Details

- Frontend: HTML, CSS, JavaScript
- Backend: Python with Flask
- Scraping: BeautifulSoup4
- Downloader: yt-dlp

## Limitations

- Works only with public Spotify playlists
- YouTube matching accuracy depends on search results
- Download speed depends on your internet connection and YouTube's policies

## Disclaimer

This project is for educational purposes only. The developers are not responsible for any misuse of this software. Please use responsibly and respect copyright laws.