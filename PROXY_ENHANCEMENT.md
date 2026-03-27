# Advanced Proxy Manager Implementation

## Overview

The advanced proxy manager has been implemented with all the requested controls to optimize proxy usage, reduce bandwidth consumption, and prevent rate limiting. This replaces the basic proxy configuration with a comprehensive solution.

## Key Features Implemented

### 1. Request Throttling (1-3 req/s per session)
- **Implementation**: `ProxyThrottler` class manages request rates per session
- **Configuration**: Configurable max requests per second (default: 2.0)
- **Session-based**: Each video/playlist gets its own throttling session
- **Automatic waiting**: Requests are automatically delayed to maintain rate limits

### 2. 429 Backoff with Exponential Retry
- **Detection**: Automatically detects 429 (Too Many Requests) responses
- **Backoff**: Exponential backoff with maximum 5-minute delay
- **Per-session**: Each session maintains its own backoff state
- **Smart recovery**: Automatic recovery when backoff period expires

### 3. User Agent & Accept-Language Rotation
- **User Agents**: 10 different realistic user agents (Chrome, Firefox, Safari, Edge)
- **Accept-Language**: 10 different language preferences for diversity
- **Session-based**: Each session gets a consistent agent until rotation
- **Automatic rotation**: Rotates on failures or 429 responses

### 4. Video Caching by ID and ETag
- **SQLite database**: Persistent caching across server restarts
- **Video metadata**: Caches titles, duration, transcriptions
- **ETag support**: Validates cache freshness using ETags
- **Automatic cleanup**: 7-day retention with configurable cleanup
- **Thread-safe**: Concurrent access support

### 5. Captions API Preference (60-90% Bandwidth Savings)
- **Primary method**: Attempts captions extraction first
- **Bandwidth optimization**: Uses `--skip-download` to avoid audio download
- **Format support**: VTT and SRT caption formats
- **Fallback**: Falls back to audio download if captions unavailable
- **Savings tracking**: Logs bandwidth savings for monitoring

### 6. **NEW: Sticky Sessions (10-minute per worker)**
- **Worker consistency**: Each worker maintains the same proxy for 10 minutes
- **Automatic rotation**: Sessions rotate every 10 minutes or on expiration
- **Session persistence**: Consistent proxy, user agent, and headers per worker
- **Load balancing**: Distributes workers across available proxies
- **Failure handling**: Invalid sessions are recreated automatically
- **Statistics tracking**: Monitor active sessions and proxy usage

## File Structure

```
proxy_manager.py          # Main proxy manager implementation
proxy_config.py          # Basic proxy configuration (existing)
simple_server.py          # Updated to use proxy manager
standalone_whisper.py     # Updated with proxy_options support
test_proxy_manager.py     # Comprehensive test suite
```

## Implementation Details

### ProxyThrottler Class
```python
class ProxyThrottler:
    def __init__(self, max_requests_per_second: float = 2.0)
    def should_throttle(self, session_id: str) -> tuple[bool, float]
    def record_request(self, session_id: str, success: bool = True, status_code: int = 200)
    def wait_if_needed(self, session_id: str)
```

### UserAgentRotator Class
```python
class UserAgentRotator:
    def get_headers(self, session_id: str) -> Dict[str, str]
    def rotate_agent(self, session_id: str)
```

### VideoCache Class
```python
class VideoCache:
    def get_cached_video(self, video_id: str, etag: str = None) -> Optional[Dict[str, Any]]
    def cache_video(self, video_id: str, etag: str, **kwargs)
    def cleanup_old_cache(self, days: int = 7)
```

### CaptionsExtractor Class
```python
class CaptionsExtractor:
    def extract_captions(self, video_id: str, language: str = 'en') -> Optional[str]
```

### ProxyManager Class (Main Coordinator)
```python
class ProxyManager:
    def get_worker_session(self, worker_id: str) -> StickySession
    def invalidate_worker_session(self, worker_id: str, reason: str = "failure")
    def get_optimized_transcription(self, video_id: str, mode: str = 'auto', language: str = 'en', worker_id: str = None)
    def get_download_options(self, worker_id: str) -> List[str]
    def pre_request_hook(self, worker_id: str)
    def post_request_hook(self, worker_id: str, success: bool = True, status_code: int = 200)
    def get_session_stats(self) -> Dict[str, Any]
```

### StickySessionManager Class
```python
class StickySessionManager:
    def __init__(self, session_duration: float = 600, cleanup_interval: float = 300)
    def get_session(self, worker_id: str) -> StickySession
    def invalidate_session(self, worker_id: str, reason: str = "manual")
    def get_session_stats(self) -> Dict[str, Any]
```

### StickySession Dataclass
```python
@dataclass
class StickySession:
    worker_id: str
    proxy_url: Optional[str] = None
    user_agent_index: int = 0
    session_start_time: float = 0
    last_used_time: float = 0
    request_count: int = 0
    
    def is_expired(self, max_duration: float = 600) -> bool
    def is_stale(self, max_idle: float = 300) -> bool
```

## Bandwidth Optimization Strategy

### Captions-First Approach
1. **Check cache** for existing transcription
2. **Extract captions** using YouTube's captions API (5-10KB)
3. **Convert formats** (text, SRT, VTT)
4. **Cache result** for future requests
5. **Fallback** to audio download only if captions unavailable

### Expected Savings
- **Small video (5 min)**: Audio ~25MB → Captions ~2KB (99.9% savings)
- **Medium video (15 min)**: Audio ~75MB → Captions ~5KB (99.9% savings)
- **Long video (60 min)**: Audio ~300MB → Captions ~20KB (99.9% savings)

## Integration Points

### Server Integration
- `simple_server.py` automatically detects and uses proxy manager
- Fallback to basic proxy configuration if proxy manager unavailable
- Both single video and playlist transcription use optimized approach

### yt-dlp Integration
- `extract_playlist_videos()` and `download_audio_from_youtube()` support `proxy_options`
- Advanced proxy settings passed through to yt-dlp
- Consistent throttling across all YouTube requests

## Usage Examples

### Basic Usage with Sticky Sessions
```python
from proxy_manager import get_proxy_manager

manager = get_proxy_manager()

# Get sticky session for a worker
worker_id = "playlist_job_123"
session = manager.get_worker_session(worker_id)

# Use optimized transcription with worker ID
result = manager.get_optimized_transcription(
    video_id="abc123",
    mode="auto",
    language="en",
    worker_id=worker_id  # Ensures sticky session usage
)
```

### Manual Session Management
```python
# Get session information
session = manager.get_worker_session("worker_456")
print(f"Proxy: {session.proxy_url}")
print(f"Requests: {session.request_count}")
print(f"Age: {time.time() - session.session_start_time:.0f}s")

# Invalidate problematic session
manager.invalidate_worker_session("worker_456", "too_many_failures")

# Get session statistics
stats = manager.get_session_stats()
print(f"Active sessions: {stats['sticky_sessions']['active_sessions']}")
```

### Manual Throttling with Sticky Sessions
```python
# Before making request (uses worker ID for sticky session)
worker_id = "transcribe_worker_789"
manager.pre_request_hook(worker_id)

# Make your request here
success = make_youtube_request()

# After request (maintains sticky session)
manager.post_request_hook(worker_id, success=success)
```

### Cache Management
```python
# Get cached transcription
cached = manager.cache.get_cached_video("video_id", "etag")

# Cache new transcription
manager.cache.cache_video(
    video_id="video_id",
    etag="etag",
    transcription_text="...",
    transcription_srt="...",
    transcription_vtt="..."
)
```

## Configuration

### Environment Variables
- `YOUTUBE_PROXY`: Basic proxy URL override
- `OPENAI_API_KEY`: Required for Whisper transcription

### Proxy Services (proxy_config.py)
- ProxyMesh, Bright Data, SmartProxy configurations
- Free proxy lists (not recommended for production)

### Throttling Settings
- Default: 2 requests per second
- Configurable via `ProxyThrottler(max_requests_per_second=X)`
- Per-session tracking prevents cross-contamination

## Monitoring and Logging

### Request Metrics
- Request count per session
- Throttling delays
- 429 backoff events
- Bandwidth savings reports

### Cache Statistics
- Cache hits vs misses
- Storage usage
- Cleanup events

### Proxy Performance
- User agent rotation events
- Request success rates
- Backoff recovery times

## Error Handling

### Graceful Degradation
1. Proxy manager unavailable → Basic proxy configuration
2. Captions extraction fails → Audio download fallback
3. Cache unavailable → Direct processing
4. Throttling fails → Continue with warnings

### Recovery Mechanisms
- Automatic retry with exponential backoff
- User agent rotation on failures
- Cache cleanup on corruption
- Proxy rotation (if multiple configured)

## Testing

Run the comprehensive test suite:
```bash
python test_proxy_manager.py
```

Tests cover:
- Request throttling accuracy
- User agent rotation
- Cache operations
- 429 backoff behavior
- Integration with server
- Performance metrics

## Benefits Summary

1. **Bandwidth Savings**: 60-90% reduction using captions API
2. **Rate Limit Prevention**: Smart throttling prevents 429 errors
3. **Proxy Longevity**: User agent rotation reduces detection
4. **Session Consistency**: Sticky sessions provide stable connections
5. **Performance**: Caching eliminates duplicate requests
6. **Reliability**: Smart fallbacks ensure high availability
7. **Monitoring**: Comprehensive logging for optimization
8. **Load Distribution**: Workers distributed across proxy pool

## Backward Compatibility

- Fully backward compatible with existing proxy_config.py
- Falls back to basic proxy if advanced features unavailable
- No breaking changes to existing API
- Optional enhancement that activates automatically when available

This implementation provides enterprise-grade proxy management while maintaining simplicity and reliability.
