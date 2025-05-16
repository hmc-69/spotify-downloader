document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const playlistUrlInput = document.getElementById('playlist-url');
    const fetchButton = document.getElementById('fetch-btn');
    const loadingElement = document.getElementById('loading');
    const playlistInfoSection = document.getElementById('playlist-info');
    const playlistCover = document.getElementById('playlist-cover');
    const playlistTitle = document.getElementById('playlist-title');
    const playlistDescription = document.getElementById('playlist-description');
    const trackCount = document.getElementById('track-count');
    const tracksSection = document.getElementById('tracks-section');
    const tracksList = document.getElementById('tracks-list');
    const downloadAllButton = document.getElementById('download-all');
    const downloadSection = document.getElementById('download-section');
    const downloadProgress = document.getElementById('download-progress');
    const downloadZipContainer = document.getElementById('download-zip-container');
    const downloadZipButton = document.getElementById('download-zip');

    // Event Listeners
    fetchButton.addEventListener('click', fetchPlaylist);
    downloadAllButton.addEventListener('click', downloadAllTracks);
    downloadZipButton.addEventListener('click', downloadAsZip);

    // Fetch playlist data
    async function fetchPlaylist() {
        const playlistUrl = playlistUrlInput.value.trim();
        
        if (!playlistUrl || !playlistUrl.includes('open.spotify.com/playlist/')) {
            alert('Please enter a valid Spotify playlist URL');
            return;
        }

        // Show loading state
        loadingElement.classList.remove('hidden');
        fetchButton.disabled = true;
        
        try {
            const response = await fetch('/api/fetch-playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: playlistUrl })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch playlist');
            }

            const data = await response.json();
            displayPlaylistInfo(data.playlist);
            displayTracks(data.tracks);
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to fetch playlist. Please try again.');
        } finally {
            loadingElement.classList.add('hidden');
            fetchButton.disabled = false;
        }
    }

    // Display playlist information
    function displayPlaylistInfo(playlist) {
        playlistCover.src = playlist.image || 'default-cover.jpg';
        playlistTitle.textContent = playlist.name;
        playlistDescription.textContent = playlist.description || '';
        trackCount.textContent = playlist.trackCount;
        
        playlistInfoSection.classList.remove('hidden');
    }

    // Display tracks with YouTube matches
    function displayTracks(tracks) {
        tracksList.innerHTML = '';
        
        tracks.forEach((track, index) => {
            const trackItem = document.createElement('div');
            trackItem.className = 'track-item';
            trackItem.dataset.trackId = track.id;

            // Fallbacks for youtube property
            const youtubeTitle = track.youtube && track.youtube.title ? track.youtube.title : 'Not matched yet';
            const youtubeUrl = track.youtube && track.youtube.url ? track.youtube.url : '#';

            trackItem.innerHTML = `
                <div class="track-number">${index + 1}</div>
                <div class="track-info">
                    <div class="track-title">${track.name}</div>
                    <div class="track-artist">${track.artist}</div>
                </div>
                <div class="youtube-match">
                    <div class="youtube-title">${youtubeTitle}</div>
                    <a href="${youtubeUrl}" target="_blank" class="youtube-link">${youtubeUrl !== '#' ? 'View on YouTube' : ''}</a>
                </div>
                <div class="track-actions">
                    <button class="download-single" data-index="${index}">Download</button>
                </div>
            `;
            
            tracksList.appendChild(trackItem);
            
            // Add event listener for single track download
            const downloadButton = trackItem.querySelector('.download-single');
            downloadButton.addEventListener('click', () => downloadSingleTrack(index));
        });
        
        tracksSection.classList.remove('hidden');
    }

    // Download a single track
    async function downloadSingleTrack(index) {
        downloadSection.classList.remove('hidden');
        
        const progressItem = createProgressItem(`Track ${index + 1}`);
        downloadProgress.appendChild(progressItem);
        
        try {
            await simulateDownload(progressItem);
            progressItem.querySelector('.status').textContent = 'Completed';
        } catch (error) {
            progressItem.querySelector('.status').textContent = 'Failed';
            progressItem.querySelector('.status').style.color = 'red';
        }
    }

    // Download all tracks
    async function downloadAllTracks() {
        downloadSection.classList.remove('hidden');
        downloadProgress.innerHTML = '';
        downloadAllButton.disabled = true;
        
        const trackItems = document.querySelectorAll('.track-item');
        
        for (let i = 0; i < trackItems.length; i++) {
            const trackTitle = trackItems[i].querySelector('.track-title').textContent;
            const trackArtist = trackItems[i].querySelector('.track-artist').textContent;
            const progressItem = createProgressItem(`${trackTitle} - ${trackArtist}`);
            
            downloadProgress.appendChild(progressItem);
            
            try {
                await simulateDownload(progressItem);
                progressItem.querySelector('.status').textContent = 'Completed';
            } catch (error) {
                progressItem.querySelector('.status').textContent = 'Failed';
                progressItem.querySelector('.status').style.color = 'red';
            }
        }
        
        downloadAllButton.disabled = false;
        downloadZipContainer.classList.remove('hidden');
    }

    // Create a progress item element
    function createProgressItem(name) {
        const progressItem = document.createElement('div');
        progressItem.className = 'download-progress-item';
        
        progressItem.innerHTML = `
            <div class="progress-info">
                <span class="progress-name">${name}</span>
                <span class="status">Downloading...</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar"></div>
            </div>
            <div class="progress-percentage">0%</</div>
        `;
        
        return progressItem;
    }

    // Simulate download progress
    function simulateDownload(progressItem) {
        return new Promise((resolve) => {
            const progressBar = progressItem.querySelector('.progress-bar');
            const progressPercentage = progressItem.querySelector('.progress-percentage');
            let progress = 0;
            
            const interval = setInterval(() => {
                progress += Math.random() * 10;
                
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(interval);
                    resolve();
                }
                
                progressBar.style.width = `${progress}%`;
                progressPercentage.textContent = `${Math.round(progress)}%`;
            }, 300);
        });
    }

    // Download as ZIP
    function downloadAsZip() {
        alert('ZIP download functionality would be implemented on the server side.');
        // In a real implementation, this would make a request to the server to generate and download a ZIP file
    }
});