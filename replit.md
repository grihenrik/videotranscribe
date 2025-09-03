# YouTube Transcription Tool - Development Notes

## Project Overview

This FastAPI application transcribes YouTube videos using captions or OpenAI's Whisper API. Built with modern web technologies and designed for easy deployment on Replit.

**Preferred communication style**: Simple, everyday language.

## Current Status ✅

- ✅ **FastAPI Structure**: Clean, organized codebase
- ✅ **ASGI Compatibility**: Runs properly with uvicorn
- ✅ **Frontend Interface**: Tabbed design with Single/Batch/Playlist modes
- ✅ **Real-time Updates**: WebSocket progress tracking
- ✅ **Error Handling**: Proper error messages and status tracking
- ✅ **File Downloads**: Multiple formats (TXT, SRT, VTT)

## Architecture

### Backend (FastAPI)
```
app/
├── api/           # REST endpoints + WebSocket
├── services/      # Business logic (YouTube, Whisper, Cache)
├── models/        # Pydantic request/response models
├── core/          # Configuration and logging
└── utils/         # Helper functions
```

### Frontend
- **Bootstrap 5** - Responsive UI components
- **JavaScript** - Form handling and real-time updates
- **WebSockets** - Live progress notifications

## Key Features

1. **Smart Transcription Modes**:
   - `auto` - Try captions first, fallback to Whisper
   - `captions` - YouTube captions only (fast, free)
   - `whisper` - AI transcription (requires OpenAI API)

2. **Multiple Processing Types**:
   - Single video transcription ✅
   - Batch processing (UI ready)
   - Playlist processing (UI ready)

3. **Real-time Progress**:
   - Live status updates via WebSocket
   - Progress bar with percentage
   - Detailed status messages

## Deployment Configuration

### Current Setup ✅
```bash
# Correct command for Replit workflow:
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

### Dependencies
- **ffmpeg** - Audio processing (installed)
- **yt-dlp** - YouTube integration (latest version)
- **OpenAI API** - Whisper transcription (optional)

## Recent Fixes (September 2025)

### ✅ ASGI Compatibility
- **Issue**: FastAPI requires ASGI, not WSGI
- **Solution**: Use uvicorn instead of gunicorn with sync workers
- **Status**: RESOLVED

### ✅ JavaScript Polling Fix
- **Issue**: Endless error alerts crashing browser
- **Solution**: Proper polling control with safety limits
- **Status**: RESOLVED

### ✅ Progress Bar Implementation
- **Issue**: No real-time status updates
- **Solution**: WebSocket-based progress tracking
- **Status**: WORKING

### ✅ UI Restoration
- **Issue**: Missing batch and playlist options
- **Solution**: Added tabbed interface with all processing modes
- **Status**: COMPLETE

## Configuration Options

Environment variables (all optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | None | Whisper API access |
| `WHISPER_MODEL` | base | Model size (tiny/base/small/medium/large) |
| `CACHE_TTL` | 3600 | Cache time-to-live (seconds) |
| `LOG_LEVEL` | INFO | Logging verbosity |

## Known Limitations

1. **YouTube Restrictions**: Some videos blocked by YouTube's anti-bot measures
2. **Memory Usage**: Large batch operations require sufficient RAM
3. **API Costs**: Whisper mode uses OpenAI credits

## Performance Notes

- **Captions mode**: Fastest, no API costs, works for most videos
- **Auto mode**: Good balance of speed and coverage
- **Whisper mode**: Most accurate but requires API and time
- **Batch processing**: UI complete, backend implementation needed
- **Playlist support**: UI complete, backend implementation needed

## Development Workflow

```bash
# Start development server
python main.py

# Access interface
http://localhost:5000

# API documentation
http://localhost:5000/docs
```

## Troubleshooting Quick Reference

- **FFmpeg warnings**: Normal, audio features still work
- **YouTube 403 errors**: Try captions-only mode
- **Browser crashes**: Fixed with polling limits
- **ASGI errors**: Use uvicorn, not gunicorn with sync workers

## User Preferences Remembered

- Clean, structured documentation
- Simple explanations over technical jargon  
- Focus on practical solutions
- Minimal emoji usage unless requested
- Professional but friendly tone