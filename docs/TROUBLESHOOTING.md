# Troubleshooting Guide

This document helps resolve common issues with the YouTube Transcription Tool.

## 🚨 Common Issues

### 1. FFmpeg Not Found

**Error Messages:**
- `WARNING: ffmpeg not found`
- `ERROR: Postprocessing: ffprobe and ffmpeg not found`

**Solutions:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Or use chocolatey: choco install ffmpeg
```

### 2. YouTube Access Blocked

**Error Messages:**
- `ERROR: HTTP Error 403: Forbidden`
- `ERROR: Sign in to confirm you're not a bot`
- `ERROR: Did not get any data blocks`

**Solutions:**
1. **Use "captions" mode only** - avoids downloading audio
2. **Try different videos** - some have restricted access
3. **Clear browser cache** and try again
4. **Wait and retry** - YouTube may have temporary blocks

### 3. ASGI Server Issues

**Error Messages:**
- `TypeError: FastAPI.__call__() missing 1 required positional argument: 'send'`

**Solution:**
```bash
# CORRECT: Use ASGI server
uvicorn main:app --host 0.0.0.0 --port 5000

# INCORRECT: Don't use pure WSGI
# gunicorn main:app  # This will fail
```

### 4. OpenAI API Issues

**Error Messages:**
- `Authentication failed`
- `API quota exceeded`
- `Rate limit exceeded`

**Solutions:**
1. **Check API key**: Verify `OPENAI_API_KEY` is set correctly
2. **Check billing**: Ensure you have API credits
3. **Use captions mode**: Avoid Whisper API when possible
4. **Reduce request frequency**: Wait between API calls

### 5. Memory Issues

**Error Messages:**
- `MemoryError`
- `Out of memory`
- Application becomes unresponsive

**Solutions:**
1. **Reduce batch size**: Process fewer videos at once
2. **Clear cache**: Restart application to clear memory
3. **Use smaller Whisper model**: Set `WHISPER_MODEL=tiny`
4. **Increase system memory**: Add more RAM

### 6. Port Already in Use

**Error Messages:**
- `[Errno 48] Address already in use`
- `Port 5000 is already in use`

**Solutions:**
```bash
# Find and kill process using port 5000
sudo lsof -ti:5000 | xargs kill -9

# Or use a different port
uvicorn main:app --port 8000
```

### 7. WebSocket Connection Issues

**Error Messages:**
- `WebSocket connection failed`
- `Connection closed abnormally`

**Solutions:**
1. **Check browser console** for JavaScript errors
2. **Verify server is running** on correct port
3. **Clear browser cache** and refresh page
4. **Check firewall settings** - ensure WebSocket traffic allowed

## 🔍 Debugging Steps

### 1. Enable Debug Logging

```bash
# Start with debug logging
uvicorn main:app --log-level debug

# Or set environment variable
export LOG_LEVEL=DEBUG
python main.py
```

### 2. Test API Endpoints

```bash
# Check health
curl http://localhost:5000/health

# Test transcription endpoint
curl -X POST http://localhost:5000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "mode": "captions"}'
```

### 3. Check System Requirements

```bash
# Python version (3.11+ required)
python --version

# Check installed packages
pip list

# Check ffmpeg
ffmpeg -version

# Check system resources
free -h  # Memory
df -h    # Disk space
```

### 4. Browser Developer Tools

1. Open **Developer Tools** (F12)
2. Check **Console** tab for JavaScript errors
3. Check **Network** tab for failed requests
4. Verify **WebSocket connections**

## 🛠️ Advanced Troubleshooting

### Check Application Health

```python
import requests

# Health check
response = requests.get('http://localhost:5000/health')
print(response.json())

# Check specific job status
job_status = requests.get(f'http://localhost:5000/api/job/{job_id}/status')
print(job_status.json())
```

### Monitor System Resources

```bash
# Monitor memory usage
watch -n 1 'ps aux | grep python'

# Monitor disk space
watch -n 1 'df -h'

# Monitor network connections
netstat -tulpn | grep :5000
```

### Log Analysis

```bash
# Follow application logs
tail -f app.log

# Search for errors
grep -i error app.log

# Filter by timestamp
grep "2025-09-03" app.log
```

## 📝 Error Code Reference

### HTTP Status Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid input data
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Application Error Codes

- **CAPTION_ERROR**: Failed to extract captions
- **WHISPER_ERROR**: Whisper transcription failed
- **DOWNLOAD_ERROR**: Audio download failed
- **VALIDATION_ERROR**: Invalid YouTube URL

## 🆘 Getting Help

### Before Asking for Help

1. ✅ Check this troubleshooting guide
2. ✅ Review error messages carefully
3. ✅ Test with simple examples
4. ✅ Check system requirements
5. ✅ Enable debug logging

### When Reporting Issues

Include the following information:

1. **Error message** (complete stack trace)
2. **System information** (OS, Python version)
3. **Steps to reproduce** the issue
4. **Example URLs** that fail
5. **Configuration** (environment variables)
6. **Logs** (relevant portions)

### Contact Information

- 🐛 **GitHub Issues**: [Report bugs](https://github.com/your-repo/issues)
- 💬 **Discussions**: [Ask questions](https://github.com/your-repo/discussions)
- 📧 **Email**: [support@example.com](mailto:support@example.com)

## 🔧 Quick Fixes

### Reset Application

```bash
# Stop application
pkill -f uvicorn

# Clear cache directory
rm -rf tmp/*

# Restart application
uvicorn main:app --host 0.0.0.0 --port 5000
```

### Test with Known Working Video

Try with this public domain video:
```
https://www.youtube.com/watch?v=jNQXAC9IVRw
```

### Verify Installation

```bash
# Re-install dependencies
pip install --force-reinstall -r requirements.txt

# Check application import
python -c "from app import create_app; print('✅ Import successful')"
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)