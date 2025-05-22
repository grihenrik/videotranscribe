"""
Cache service implementation.

This module provides caching functionality for the application,
with support for in-memory and Redis backends.
"""
import time
import json
import asyncio
from typing import Any, Dict, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Base class for caching services."""

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        raise NotImplementedError("Subclasses must implement get()")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement set()")

    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement delete()")


class MemoryCacheService(CacheService):
    """In-memory cache service."""

    def __init__(self, ttl: int = 86400):
        """
        Initialize the memory cache service.
        
        Args:
            ttl: Default time to live in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = ttl
        
        # Start expiration loop
        self._expire_task = asyncio.create_task(self._expire_loop())

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if key not in self.cache:
            return None
        
        # Check if expired
        if self.cache[key]["expires_at"] < time.time():
            await self.delete(key)
            return None
        
        return self.cache[key]["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        expires_at = time.time() + (ttl or self.default_ttl)
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        return True

    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
        
    async def _expire_loop(self) -> None:
        """
        Loop to expire cache entries.
        """
        try:
            while True:
                now = time.time()
                # Find expired keys
                expired_keys = [
                    key for key, data in self.cache.items() 
                    if data["expires_at"] < now
                ]
                
                # Delete expired keys
                for key in expired_keys:
                    await self.delete(key)
                
                # Sleep for a while
                await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            # Task was cancelled
            pass
        except Exception as e:
            logger.error(f"Error in expire loop: {e}")


class RedisCacheService(CacheService):
    """Redis cache service."""

    def __init__(self, url: str, ttl: int = 86400):
        """
        Initialize the Redis cache service.
        
        Args:
            url: Redis URL
            ttl: Default time to live in seconds
        """
        self.url = url
        self.default_ttl = ttl
        self._redis = None

    async def _get_redis(self):
        """
        Get Redis connection.
        
        Returns:
            Redis connection
        """
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.url)
            except ImportError:
                logger.error("Redis package not installed - please install with 'pip install redis'")
                raise
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            redis = await self._get_redis()
            value = await redis.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f"Error getting value from Redis: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis()
            serialized = json.dumps(value)
            await redis.set(key, serialized, ex=(ttl or self.default_ttl))
            return True
        except Exception as e:
            logger.error(f"Error setting value in Redis: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis()
            await redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting value from Redis: {e}")
            return False


def get_cache_service() -> CacheService:
    """
    Get the cache service based on configuration.
    
    Returns:
        Cache service instance
    """
    cache_type = settings.CACHE_TYPE.lower()
    
    if cache_type == "redis":
        return RedisCacheService(settings.REDIS_URL, settings.CACHE_TTL)
    else:
        return MemoryCacheService(settings.CACHE_TTL)