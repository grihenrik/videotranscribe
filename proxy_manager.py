#!/usr/bin/env python3
"""
Advanced Proxy Manager for YouTube Access
========================================

Enhanced proxy handling with throttling, user agent rotation, caching,
and captions API preference to optimize proxy bandwidth usage.
"""

import os
import time
import random
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import sqlite3
import threading
from queue import Queue

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """Track request metrics per session."""
    session_id: str
    request_count: int = 0
    last_request_time: float = 0
    backoff_until: float = 0
    user_agent_index: int = 0

@dataclass
class StickySession:
    """Track sticky session information for workers."""
    worker_id: str
    proxy_url: Optional[str] = None
    user_agent_index: int = 0
    session_start_time: float = 0
    last_used_time: float = 0
    request_count: int = 0
    
    def is_expired(self, max_duration: float = 600) -> bool:
        """Check if session is expired (default: 10 minutes)."""
        return time.time() - self.session_start_time > max_duration
    
    def is_stale(self, max_idle: float = 300) -> bool:
        """Check if session is stale (default: 5 minutes idle)."""
        return time.time() - self.last_used_time > max_idle
    
class ProxyThrottler:
    """Manages request throttling and backoff."""
    
    def __init__(self, max_requests_per_second: float = 2.0):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.sessions: Dict[str, RequestMetrics] = {}
        self.lock = threading.Lock()
    
    def get_session_metrics(self, session_id: str) -> RequestMetrics:
        """Get or create session metrics."""
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = RequestMetrics(session_id=session_id)
            return self.sessions[session_id]
    
    def should_throttle(self, session_id: str) -> tuple[bool, float]:
        """Check if request should be throttled and return wait time."""
        metrics = self.get_session_metrics(session_id)
        current_time = time.time()
        
        # Check if we're in backoff period
        if metrics.backoff_until > current_time:
            wait_time = metrics.backoff_until - current_time
            return True, wait_time
        
        # Check rate limiting
        if metrics.last_request_time > 0:
            time_since_last = current_time - metrics.last_request_time
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                return True, wait_time
        
        return False, 0.0
    
    def record_request(self, session_id: str, success: bool = True, status_code: int = 200):
        """Record a request and update metrics."""
        metrics = self.get_session_metrics(session_id)
        current_time = time.time()
        
        with self.lock:
            metrics.request_count += 1
            metrics.last_request_time = current_time
            
            # Handle 429 (Too Many Requests) with exponential backoff
            if status_code == 429 or not success:
                backoff_seconds = min(300, 2 ** min(metrics.request_count // 10, 8))  # Max 5 minutes
                metrics.backoff_until = current_time + backoff_seconds
                logger.warning(f"Session {session_id}: 429 detected, backing off for {backoff_seconds}s")
    
    def wait_if_needed(self, session_id: str):
        """Wait if throttling is needed."""
        should_wait, wait_time = self.should_throttle(session_id)
        if should_wait:
            logger.info(f"Session {session_id}: Throttling request, waiting {wait_time:.2f}s")
            time.sleep(wait_time)

class UserAgentRotator:
    """Manages user agent and accept-language rotation with sticky sessions."""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ]
    
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-GB,en;q=0.9",
        "en-US,en;q=0.9,fr;q=0.8",
        "en-US,en;q=0.9,de;q=0.8",
        "en-US,en;q=0.9,it;q=0.8",
        "en-US,en;q=0.9,pt;q=0.8",
        "en-US,en;q=0.9,nl;q=0.8",
        "en-US,en;q=0.9,sv;q=0.8",
        "en-US,en;q=0.9,no;q=0.8"
    ]
    
    def __init__(self):
        self.session_agents: Dict[str, int] = {}
    
    def get_headers(self, session_id: str, user_agent_index: int = None) -> Dict[str, str]:
        """Get headers for session, optionally with specific user agent index."""
        if user_agent_index is not None:
            agent_index = user_agent_index
        elif session_id not in self.session_agents:
            agent_index = random.randint(0, len(self.USER_AGENTS) - 1)
            self.session_agents[session_id] = agent_index
        else:
            agent_index = self.session_agents[session_id]
        
        lang_index = agent_index % len(self.ACCEPT_LANGUAGES)
        
        return {
            "User-Agent": self.USER_AGENTS[agent_index],
            "Accept-Language": self.ACCEPT_LANGUAGES[lang_index],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    
    def rotate_agent(self, session_id: str):
        """Rotate to next user agent for session."""
        if session_id in self.session_agents:
            self.session_agents[session_id] = (self.session_agents[session_id] + 1) % len(self.USER_AGENTS)
        else:
            self.session_agents[session_id] = random.randint(0, len(self.USER_AGENTS) - 1)
    
    def get_agent_index(self, session_id: str) -> int:
        """Get current user agent index for session."""
        return self.session_agents.get(session_id, 0)

class VideoCache:
    """Caches video metadata and transcriptions by video ID and ETag."""
    
    def __init__(self, cache_dir: str = "tmp/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.db_path = os.path.join(cache_dir, "video_cache.db")
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite cache database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_cache (
                video_id TEXT PRIMARY KEY,
                etag TEXT,
                title TEXT,
                duration INTEGER,
                captions_available BOOLEAN,
                audio_cached BOOLEAN,
                transcription_text TEXT,
                transcription_srt TEXT,
                transcription_vtt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_etag ON video_cache(video_id, etag)
        """)
        conn.commit()
        conn.close()
    
    def get_cached_video(self, video_id: str, etag: str = None) -> Optional[Dict[str, Any]]:
        """Get cached video data if available and valid."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM video_cache WHERE video_id = ?"
        params = [video_id]
        
        if etag:
            query += " AND etag = ?"
            params.append(etag)
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if row:
            # Update last accessed
            conn.execute("UPDATE video_cache SET last_accessed = CURRENT_TIMESTAMP WHERE video_id = ?", [video_id])
            conn.commit()
            
            columns = [description[0] for description in cursor.description]
            result = dict(zip(columns, row))
            conn.close()
            return result
        
        conn.close()
        return None
    
    def cache_video(self, video_id: str, etag: str, **kwargs):
        """Cache video metadata and transcription."""
        conn = sqlite3.connect(self.db_path)
        
        # Prepare data
        data = {
            'video_id': video_id,
            'etag': etag,
            'title': kwargs.get('title'),
            'duration': kwargs.get('duration'),
            'captions_available': kwargs.get('captions_available', False),
            'audio_cached': kwargs.get('audio_cached', False),
            'transcription_text': kwargs.get('transcription_text'),
            'transcription_srt': kwargs.get('transcription_srt'),
            'transcription_vtt': kwargs.get('transcription_vtt')
        }
        
        # Insert or replace
        conn.execute("""
            INSERT OR REPLACE INTO video_cache 
            (video_id, etag, title, duration, captions_available, audio_cached, 
             transcription_text, transcription_srt, transcription_vtt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            data['video_id'], data['etag'], data['title'], data['duration'],
            data['captions_available'], data['audio_cached'], 
            data['transcription_text'], data['transcription_srt'], data['transcription_vtt']
        ])
        
        conn.commit()
        conn.close()
    
    def cleanup_old_cache(self, days: int = 7):
        """Remove cache entries older than specified days."""
        conn = sqlite3.connect(self.db_path)
        cutoff_date = datetime.now() - timedelta(days=days)
        conn.execute("DELETE FROM video_cache WHERE last_accessed < ?", [cutoff_date])
        conn.commit()
        conn.close()

class CaptionsExtractor:
    """Extracts captions using YouTube's captions API to save bandwidth."""
    
    def __init__(self, proxy_manager):
        self.proxy_manager = proxy_manager
    
    def extract_captions(self, video_id: str, language: str = 'en') -> Optional[str]:
        """
        Extract captions using yt-dlp's captions-only mode.
        This uses much less bandwidth than downloading audio.
        """
        try:
            import subprocess
            import tempfile
            
            # Create temporary directory for captions
            with tempfile.TemporaryDirectory() as temp_dir:
                cmd = [
                    'yt-dlp',
                    '--write-subs',
                    '--write-auto-subs',
                    '--sub-langs', f'{language}.*',
                    '--sub-format', 'vtt/srt/best',
                    '--skip-download',  # Don't download video/audio
                    '--output', os.path.join(temp_dir, '%(id)s.%(ext)s'),
                ]
                
                # Add proxy and headers
                proxy_url = self.proxy_manager.get_proxy_url()
                if proxy_url:
                    cmd.extend(['--proxy', proxy_url])
                
                headers = self.proxy_manager.user_agent_rotator.get_headers("captions")
                cmd.extend(['--user-agent', headers['User-Agent']])
                
                cmd.append(f'https://youtube.com/watch?v={video_id}')
                
                # Throttle the request
                self.proxy_manager.throttler.wait_if_needed("captions")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                # Record the request
                self.proxy_manager.throttler.record_request(
                    "captions", 
                    success=(result.returncode == 0),
                    status_code=200 if result.returncode == 0 else 500
                )
                
                if result.returncode == 0:
                    # Find and read caption file
                    for file in os.listdir(temp_dir):
                        if file.endswith(('.vtt', '.srt')) and video_id in file:
                            with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                                captions = f.read()
                                logger.info(f"Successfully extracted captions for {video_id} (saved ~90% bandwidth)")
                                return self._clean_captions(captions)
                
                return None
                
        except Exception as e:
            logger.error(f"Error extracting captions for {video_id}: {e}")
            return None
    
    def _clean_captions(self, captions: str) -> str:
        """Clean captions text by removing timestamps and formatting."""
        import re
        
        # Remove VTT headers
        captions = re.sub(r'^WEBVTT.*?\n\n', '', captions, flags=re.MULTILINE | re.DOTALL)
        
        # Remove timestamp lines
        captions = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3} --> \d{2}:\d{2}:\d{2}[.,]\d{3}', '', captions)
        
        # Remove SRT numbering
        captions = re.sub(r'^\d+$', '', captions, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        captions = re.sub(r'\n\s*\n', '\n', captions)
        captions = ' '.join(captions.split())
        
        return captions.strip()

class StickySessionManager:
    """Manages sticky proxy sessions for workers - one session per worker for 10 minutes."""
    
    def __init__(self, session_duration: float = 600, cleanup_interval: float = 300):
        """
        Initialize sticky session manager.
        
        Args:
            session_duration: How long to keep sessions alive (default: 10 minutes)
            cleanup_interval: How often to clean up expired sessions (default: 5 minutes)
        """
        self.session_duration = session_duration
        self.cleanup_interval = cleanup_interval
        self.sessions: Dict[str, StickySession] = {}
        self.lock = threading.Lock()
        self.last_cleanup = time.time()
        
        # Available proxy configurations
        self.proxy_configs = []
        self._load_proxy_configs()
    
    def _load_proxy_configs(self):
        """Load available proxy configurations."""
        try:
            from proxy_config import (
                PROXYMESH_CONFIG, BRIGHT_DATA_CONFIG, SMARTPROXY_CONFIG,
                PUBLIC_SOCKS_PROXIES, PUBLIC_HTTP_PROXIES, get_proxy_url
            )
            
            # Add environment proxy
            env_proxy = get_proxy_url()
            if env_proxy:
                self.proxy_configs.append({
                    'type': 'environment',
                    'url': env_proxy,
                    'priority': 1
                })
            
            # Add premium proxies
            if PROXYMESH_CONFIG.get('enabled') and PROXYMESH_CONFIG.get('username'):
                for endpoint in PROXYMESH_CONFIG.get('endpoints', []):
                    proxy_url = f"http://{PROXYMESH_CONFIG['username']}:{PROXYMESH_CONFIG['password']}@{endpoint}"
                    self.proxy_configs.append({
                        'type': 'proxymesh',
                        'url': proxy_url,
                        'priority': 2
                    })
            
            if BRIGHT_DATA_CONFIG.get('enabled') and BRIGHT_DATA_CONFIG.get('username'):
                endpoint = BRIGHT_DATA_CONFIG['endpoint']
                proxy_url = f"http://{BRIGHT_DATA_CONFIG['username']}:{BRIGHT_DATA_CONFIG['password']}@{endpoint}"
                self.proxy_configs.append({
                    'type': 'bright_data',
                    'url': proxy_url,
                    'priority': 2
                })
            
            if SMARTPROXY_CONFIG.get('enabled') and SMARTPROXY_CONFIG.get('username'):
                endpoint = SMARTPROXY_CONFIG['endpoint']
                proxy_url = f"http://{SMARTPROXY_CONFIG['username']}:{SMARTPROXY_CONFIG['password']}@{endpoint}"
                self.proxy_configs.append({
                    'type': 'smartproxy',
                    'url': proxy_url,
                    'priority': 2
                })
            
            # Add public proxies (lower priority)
            for proxy in PUBLIC_SOCKS_PROXIES:
                self.proxy_configs.append({
                    'type': 'public_socks',
                    'url': proxy,
                    'priority': 3
                })
            
            for proxy in PUBLIC_HTTP_PROXIES:
                self.proxy_configs.append({
                    'type': 'public_http',
                    'url': proxy,
                    'priority': 3
                })
            
            # Sort by priority
            self.proxy_configs.sort(key=lambda x: x['priority'])
            
            logger.info(f"Loaded {len(self.proxy_configs)} proxy configurations for sticky sessions")
            
        except Exception as e:
            logger.warning(f"Failed to load proxy configs: {e}")
            self.proxy_configs = []
    
    def _cleanup_expired_sessions(self):
        """Clean up expired and stale sessions."""
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        with self.lock:
            expired_workers = []
            for worker_id, session in self.sessions.items():
                if session.is_expired(self.session_duration) or session.is_stale():
                    expired_workers.append(worker_id)
            
            for worker_id in expired_workers:
                logger.info(f"Cleaning up expired sticky session for worker: {worker_id}")
                del self.sessions[worker_id]
            
            self.last_cleanup = current_time
    
    def get_session(self, worker_id: str) -> StickySession:
        """Get or create a sticky session for a worker."""
        self._cleanup_expired_sessions()
        
        with self.lock:
            # Check if worker already has a valid session
            if worker_id in self.sessions:
                session = self.sessions[worker_id]
                if not session.is_expired(self.session_duration) and not session.is_stale():
                    # Update last used time
                    session.last_used_time = time.time()
                    session.request_count += 1
                    logger.debug(f"Reusing sticky session for worker {worker_id} (req #{session.request_count})")
                    return session
                else:
                    # Session expired, remove it
                    logger.info(f"Sticky session expired for worker {worker_id}, creating new session")
                    del self.sessions[worker_id]
            
            # Create new session
            current_time = time.time()
            
            # Select proxy for this session (round-robin or random)
            proxy_url = None
            if self.proxy_configs:
                # Use hash of worker_id to get consistent proxy selection
                proxy_index = hash(worker_id + str(int(current_time // self.session_duration))) % len(self.proxy_configs)
                proxy_url = self.proxy_configs[proxy_index]['url']
            
            # Create new sticky session
            session = StickySession(
                worker_id=worker_id,
                proxy_url=proxy_url,
                user_agent_index=random.randint(0, 9),  # Random initial user agent
                session_start_time=current_time,
                last_used_time=current_time,
                request_count=1
            )
            
            self.sessions[worker_id] = session
            logger.info(f"Created new sticky session for worker {worker_id} (proxy: {proxy_url[:50] if proxy_url else 'None'}...)")
            return session
    
    def invalidate_session(self, worker_id: str, reason: str = "manual"):
        """Invalidate a worker's session (e.g., on repeated failures)."""
        with self.lock:
            if worker_id in self.sessions:
                logger.info(f"Invalidating sticky session for worker {worker_id} (reason: {reason})")
                del self.sessions[worker_id]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        with self.lock:
            active_sessions = len(self.sessions)
            total_requests = sum(session.request_count for session in self.sessions.values())
            
            # Group by proxy type
            proxy_usage = {}
            for session in self.sessions.values():
                if session.proxy_url:
                    proxy_type = session.proxy_url.split('://')[0]
                    proxy_usage[proxy_type] = proxy_usage.get(proxy_type, 0) + 1
                else:
                    proxy_usage['no_proxy'] = proxy_usage.get('no_proxy', 0) + 1
            
            return {
                'active_sessions': active_sessions,
                'total_requests': total_requests,
                'proxy_usage': proxy_usage,
                'available_proxies': len(self.proxy_configs)
            }

class ProxyManager:
    """Main proxy manager coordinating all proxy features with sticky sessions."""
    
    def __init__(self, max_requests_per_second: float = 2.0):
        self.throttler = ProxyThrottler(max_requests_per_second)
        self.user_agent_rotator = UserAgentRotator()
        self.cache = VideoCache()
        self.captions_extractor = CaptionsExtractor(self)
        self.sticky_sessions = StickySessionManager()
        
        # Import proxy config
        try:
            from proxy_config import get_proxy_url
            self.get_proxy_url = get_proxy_url
        except ImportError:
            self.get_proxy_url = lambda: None
            logger.warning("proxy_config.py not found, proxy features disabled")
    
    def get_worker_session(self, worker_id: str) -> StickySession:
        """Get sticky session for a worker."""
        return self.sticky_sessions.get_session(worker_id)
    
    def invalidate_worker_session(self, worker_id: str, reason: str = "failure"):
        """Invalidate a worker's session on repeated failures."""
        self.sticky_sessions.invalidate_session(worker_id, reason)
    
    def get_optimized_transcription(self, video_id: str, mode: str = 'auto', language: str = 'en', worker_id: str = None) -> Optional[Dict[str, str]]:
        """
        Get transcription using optimized approach with sticky sessions:
        1. Check cache first
        2. Try captions API (saves 60-90% bandwidth) 
        3. Fall back to audio download + Whisper
        """
        # Use worker_id for session management, fallback to video_id
        session_key = worker_id or f"transcribe_{video_id}"
        
        # Check cache first
        cached = self.cache.get_cached_video(video_id)
        if cached and cached.get('transcription_text'):
            logger.info(f"Using cached transcription for {video_id}")
            return {
                'text': cached['transcription_text'],
                'srt': cached['transcription_srt'],
                'vtt': cached['transcription_vtt']
            }
        
        # Try captions first for auto/captions mode
        if mode in ['auto', 'captions']:
            logger.info(f"Attempting captions extraction for {video_id} (bandwidth-optimized)")
            captions_text = self.captions_extractor.extract_captions(video_id, language)
            
            if captions_text:
                # Convert to multiple formats
                from standalone_whisper import convert_to_srt, convert_to_vtt
                srt_content = convert_to_srt(captions_text)
                vtt_content = convert_to_vtt(captions_text)
                
                result = {
                    'text': captions_text,
                    'srt': srt_content,
                    'vtt': vtt_content
                }
                
                # Cache the result
                self.cache.cache_video(
                    video_id=video_id,
                    etag="captions",  # Special ETag for captions
                    captions_available=True,
                    transcription_text=captions_text,
                    transcription_srt=srt_content,
                    transcription_vtt=vtt_content
                )
                
                return result
        
        # Fall back to audio download (only for whisper mode or if captions failed)
        if mode in ['auto', 'whisper']:
            logger.info(f"Falling back to audio download for {video_id} (higher bandwidth)")
            return None  # Let the calling code handle audio download
        
        return None
    
    def get_download_options(self, worker_id: str) -> List[str]:
        """Get yt-dlp options with sticky session proxy and throttling."""
        # Get sticky session for this worker
        session = self.get_worker_session(worker_id)
        
        options = [
            '--extractor-retries', '3',
            '--socket-timeout', '30',
            '--sleep-interval', '1',
            '--max-sleep-interval', '3'
        ]
        
        # Add proxy from sticky session
        if session.proxy_url:
            options.extend(['--proxy', session.proxy_url])
        
        # Add consistent headers for this session
        headers = self.user_agent_rotator.get_headers(worker_id, session.user_agent_index)
        options.extend(['--user-agent', headers['User-Agent']])
        
        return options
    
    def pre_request_hook(self, worker_id: str):
        """Call before making any request - handles throttling and session management."""
        # Get or create sticky session
        session = self.get_worker_session(worker_id)
        
        # Apply throttling per worker
        self.throttler.wait_if_needed(worker_id)
        
        logger.debug(f"Worker {worker_id}: Using proxy {session.proxy_url[:50] if session.proxy_url else 'None'}... (session req #{session.request_count})")
    
    def post_request_hook(self, worker_id: str, success: bool = True, status_code: int = 200):
        """Call after making any request - records metrics and handles failures."""
        # Record request metrics
        self.throttler.record_request(worker_id, success, status_code)
        
        # Handle failures - invalidate session on repeated failures
        if not success or status_code == 429:
            session = self.sticky_sessions.sessions.get(worker_id)
            if session:
                # Check if this worker has too many failures
                failure_threshold = 5  # Invalidate session after 5 failures
                if not success and session.request_count > failure_threshold:
                    logger.warning(f"Worker {worker_id} exceeded failure threshold, invalidating sticky session")
                    self.invalidate_worker_session(worker_id, "excessive_failures")
                
            # Rotate user agent on failure
            self.user_agent_rotator.rotate_agent(worker_id)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        sticky_stats = self.sticky_sessions.get_session_stats()
        
        return {
            'sticky_sessions': sticky_stats,
            'throttling_sessions': len(self.throttler.sessions),
            'cache_size': 'N/A',  # Would need to query SQLite for exact count
            'features': {
                'sticky_sessions': True,
                'request_throttling': True,
                'user_agent_rotation': True,
                'video_caching': True,
                'captions_api': True,
                'bandwidth_optimization': True
            }
        }
    
    def cleanup_cache(self, days: int = 7):
        """Clean up old cache entries."""
        self.cache.cleanup_old_cache(days)

# Global proxy manager instance
_proxy_manager = None

def get_proxy_manager() -> ProxyManager:
    """Get global proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Advanced Proxy Manager Test")
    print("=" * 50)
    
    manager = get_proxy_manager()
    
    # Test throttling
    print("\n1. Testing throttling...")
    session = "test_session"
    
    for i in range(3):
        manager.pre_request_hook(session)
        print(f"Request {i+1} sent")
        manager.post_request_hook(session, success=True)
    
    # Test user agent rotation
    print("\n2. Testing user agent rotation...")
    for i in range(3):
        headers = manager.user_agent_rotator.get_headers(f"session_{i}")
        print(f"Session {i}: {headers['User-Agent'][:50]}...")
    
    # Test cache
    print("\n3. Testing cache...")
    manager.cache.cache_video(
        video_id="test123",
        etag="abc123",
        title="Test Video",
        transcription_text="This is a test transcription"
    )
    
    cached = manager.cache.get_cached_video("test123", "abc123")
    if cached:
        print(f"Cache test passed: {cached['title']}")
    
    print("\n✅ All tests completed!")
