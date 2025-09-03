# Deployment Guide

This document provides detailed deployment instructions for the YouTube Transcription Tool.

## 🏗️ System Architecture

The application is built with:
- **Backend**: FastAPI (ASGI-compatible)
- **Frontend**: Static HTML/CSS/JavaScript with Bootstrap
- **Real-time Updates**: WebSocket connections
- **Storage**: In-memory caching (expandable to Redis)

## 🚀 Deployment Options

### Option 1: Uvicorn (Recommended)

The simplest and most reliable way to deploy the FastAPI application:

```bash
# Development
uvicorn main:app --host 0.0.0.0 --port 5000 --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 5000 --workers 4
```

### Option 2: Gunicorn with Uvicorn Workers

For production deployments requiring process management:

```bash
gunicorn main:app \
  --bind 0.0.0.0:5000 \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --timeout 300 \
  --keepalive 2
```

### Option 3: Docker Deployment

1. **Create Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-update && apt-get install -y ffmpeg

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
```

2. **Build and run**:
```bash
docker build -t youtube-transcription .
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key youtube-transcription
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | No | None | OpenAI API key for Whisper |
| `WHISPER_MODEL` | No | base | Whisper model size |
| `CACHE_TTL` | No | 3600 | Cache TTL in seconds |
| `LOG_LEVEL` | No | INFO | Logging level |
| `HOST` | No | 0.0.0.0 | Server bind host |
| `PORT` | No | 5000 | Server port |

### Production Configuration

For production deployments, consider:

1. **Resource Limits**:
   - Memory: 2GB+ (depending on batch size)
   - CPU: 2+ cores recommended
   - Storage: 10GB+ for temporary files

2. **Security**:
   - Use HTTPS in production
   - Set up proper CORS policies
   - Implement rate limiting
   - Use environment variables for secrets

3. **Monitoring**:
   - Enable structured logging
   - Set up health checks
   - Monitor memory usage
   - Track API response times

## ⚠️ Important Notes

### ASGI vs WSGI
- **FastAPI requires ASGI servers** (uvicorn, hypercorn, daphne)
- **Do NOT use pure WSGI servers** (gunicorn with sync workers)
- **Mixed deployments**: Use uvicorn workers with gunicorn

### Common Deployment Issues

1. **"TypeError: FastAPI.__call__() missing 1 required positional argument: 'send'"**
   - **Cause**: Using WSGI server instead of ASGI
   - **Solution**: Use uvicorn or gunicorn with uvicorn workers

2. **"ffmpeg not found"**
   - **Cause**: FFmpeg not installed
   - **Solution**: Install ffmpeg package

3. **"Module not found" errors**
   - **Cause**: Missing Python dependencies
   - **Solution**: Install from requirements.txt

## 🌐 Platform-Specific Deployment

### Replit
```bash
# Use this command in the workflow:
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

### Heroku
Add `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Railway
Create `railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

### DigitalOcean App Platform
Create `.do/app.yaml`:
```yaml
name: youtube-transcription
services:
- name: web
  source_dir: /
  github:
    repo: your-repo
    branch: main
  run_command: uvicorn main:app --host 0.0.0.0 --port 8080
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
```

## 🔍 Health Checks

Add health check endpoint (already implemented):
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

Test deployment:
```bash
curl http://localhost:5000/health
```

## 🚨 Troubleshooting

### Check Application Logs
```bash
# Development
python main.py

# Production with uvicorn
uvicorn main:app --log-level debug

# Check Docker logs
docker logs container-id
```

### Common Solutions

1. **Port already in use**:
   ```bash
   # Kill process on port 5000
   sudo kill -9 $(sudo lsof -t -i:5000)
   ```

2. **Permission denied**:
   ```bash
   # Use non-privileged port
   uvicorn main:app --port 8000
   ```

3. **Memory issues**:
   - Reduce batch size
   - Enable streaming for large files
   - Monitor memory usage

## 🔄 Continuous Deployment

### GitHub Actions Example
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to production
      run: |
        # Your deployment script here
```

## 📊 Performance Optimization

1. **Use multiple workers** in production
2. **Enable caching** for repeated requests
3. **Optimize batch sizes** based on available memory
4. **Use CDN** for static files
5. **Implement connection pooling** if using external APIs

## 🔐 Security Considerations

1. **API Rate Limiting**: Implement request throttling
2. **Input Validation**: Validate all YouTube URLs
3. **File Cleanup**: Regularly clean temporary files
4. **HTTPS Only**: Use SSL/TLS in production
5. **Environment Variables**: Never commit secrets to code