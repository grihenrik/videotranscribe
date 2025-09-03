# YouTube Transcription Tool

A modern, full-stack web application that transcribes YouTube videos using either YouTube's available captions or OpenAI's Whisper speech-to-text model. Built with FastAPI and featuring real-time progress updates.

## ✨ Features

- **🎥 Single Video Transcription** - Process individual YouTube videos
- **📚 Batch Processing** - Transcribe multiple videos at once  
- **🎵 Playlist Support** - Process entire YouTube playlists
- **📝 Multiple Output Formats** - Download transcriptions as TXT, SRT, or VTT files
- **⚡ Real-time Progress** - Live updates via WebSocket connections
- **🔄 Smart Mode Selection** - Auto-detect best transcription method
- **🌐 Modern Web Interface** - Clean, responsive design with Bootstrap

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg (for audio processing)
- OpenAI API key (optional, for Whisper transcription)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd youtube-transcription-tool
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional)
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

4. **Start the application**
   ```bash
   python main.py
   ```

5. **Access the web interface**
   Open your browser to `http://localhost:5000`

## 🛠️ Usage

### Single Video Transcription
1. Navigate to the **Single Video** tab
2. Enter a YouTube URL
3. Select transcription mode:
   - **Auto** - Try captions first, fallback to Whisper
   - **Captions** - YouTube captions only
   - **Whisper** - AI speech recognition only
4. Choose target language
5. Click **Transcribe Video**

### Batch Processing
1. Go to the **Batch Processing** tab
2. Enter multiple YouTube URLs (one per line)
3. Configure processing settings
4. Click **Process Batch**

### Playlist Processing
1. Switch to the **Playlist** tab
2. Enter a YouTube playlist URL
3. Set your preferences
4. Click **Process Playlist**

## 📁 Project Structure

```
├── app/                    # FastAPI application
│   ├── api/               # API routes and endpoints
│   │   ├── transcribe.py  # Transcription endpoints
│   │   ├── download.py    # File download endpoints
│   │   └── progress_ws.py # WebSocket progress updates
│   ├── core/              # Core configuration
│   │   ├── config.py      # Application settings
│   │   └── logging.py     # Logging configuration
│   ├── models/            # Pydantic data models
│   │   ├── request.py     # Request models
│   │   └── response.py    # Response models
│   ├── services/          # Business logic services
│   │   ├── youtube_service.py    # YouTube API interactions
│   │   ├── whisper_service.py    # Whisper transcription
│   │   └── cache_service.py      # Caching layer
│   └── utils/             # Utility functions
│       ├── file_manager.py       # File operations
│       ├── xml_parser.py         # Caption parsing
│       └── youtube.py            # YouTube helpers
├── static/                # Frontend assets
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   └── index.html        # Main web interface
├── tests/                 # Test files
├── main.py               # Application entry point
└── README.md             # This file
```

## ⚙️ Configuration

The application can be configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for Whisper | None |
| `WHISPER_MODEL` | Whisper model size (tiny, base, small, medium, large) | base |
| `CACHE_TTL` | Cache time-to-live in seconds | 3600 |
| `LOG_LEVEL` | Logging level | INFO |

## 🔧 API Reference

### Core Endpoints

- `POST /api/transcribe` - Submit transcription job
- `GET /api/job/{job_id}/status` - Check job status
- `GET /api/download/{job_id}` - Download transcription files
- `WebSocket /api/ws/progress/{job_id}` - Real-time progress updates

### Example API Usage

```python
import requests

# Submit transcription job
response = requests.post('/api/transcribe', json={
    'url': 'https://www.youtube.com/watch?v=VIDEO_ID',
    'mode': 'auto',
    'lang': 'en'
})

job_data = response.json()
job_id = job_data['job_id']

# Check status
status = requests.get(f'/api/job/{job_id}/status').json()

# Download when complete
if status['status'] == 'complete':
    transcript = requests.get(f'/api/download/{job_id}?format=txt')
```

## 🚀 Deployment

### Development
```bash
# Start with auto-reload
python main.py
```

### Production
```bash
# Start with uvicorn (recommended)
uvicorn main:app --host 0.0.0.0 --port 5000 --workers 4

# Or with gunicorn + uvicorn workers
gunicorn main:app --bind 0.0.0.0:5000 --worker-class uvicorn.workers.UvicornWorker --workers 4
```

### Docker
```bash
# Build image
docker build -t youtube-transcription .

# Run container
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key youtube-transcription
```

## 🔍 Troubleshooting

### Common Issues

**FFmpeg Not Found**
```bash
# Install FFmpeg
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg       # macOS
```

**YouTube Access Blocked**
- Try using "captions" mode only
- Some videos may have restricted access
- Consider using different videos for testing

**Whisper Transcription Fails**
- Ensure OPENAI_API_KEY is set
- Check API quota and billing
- Verify internet connection

## 📈 Performance Tips

- Use "captions" mode when available (faster, no API costs)
- Enable caching for repeated requests
- Consider running with multiple workers in production
- Monitor memory usage with large batch operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://openai.com/research/whisper) - Speech recognition AI
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video processing
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Bootstrap](https://getbootstrap.com/) - UI components

## 📞 Support

- 📧 Email: [support@example.com](mailto:support@example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-repo/discussions)