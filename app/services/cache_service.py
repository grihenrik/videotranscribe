import json
import logging
import asyncio
from typing import Dict, Any, Optional, Union
from functools import lru_cache

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
        raise NotImplementedError
    
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
        raise NotImplementedError
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError


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
        
        # Start expiration task
        self.task = asyncio.create_task(self._expire_loop())
        logger.info("Started memory cache expiration loop")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        entry = self.cache.get(key)
        if entry is None:
            return None
        
        # Check if entry is expired
        if entry.get("expires_at") and entry["expires_at"] <= asyncio.get_event_loop().time():
            await self.delete(key)
            return None
        
        return entry["value"]
    
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
        ttl = ttl or self.default_ttl
        
        # Calculate expiration time
        expires_at = asyncio.get_event_loop().time() + ttl if ttl > 0 else None
        
        # Store in cache
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
        while True:
            try:
                # Find expired keys
                now = asyncio.get_event_loop().time()
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if entry.get("expires_at") and entry["expires_at"] <= now
                ]
                
                # Delete expired keys
                for key in expired_keys:
                    await self.delete(key)
                
                # Sleep for a while
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in expiration loop: {str(e)}")
                await asyncio.sleep(60)  # Sleep on error and retry


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
        self.redis = None
    
    async def _get_redis(self):
        """
        Get Redis connection.
        
        Returns:
            Redis connection
        """
        if self.redis is None:
            try:
                import redis.asyncio as redis
                self.redis = redis.from_url(self.url)
            except ImportError:
                logger.error("Redis package is not installed. Please install it with: pip install redis")
                raise
        return self.redis
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        redis = await self._get_redis()
        value = await redis.get(key)
        
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.decode("utf-8")
    
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
        redis = await self._get_redis()
        ttl = ttl or self.default_ttl
        
        # Serialize value
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)
        
        # Set in Redis
        await redis.set(key, value, ex=ttl if ttl > 0 else None)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        redis = await self._get_redis()
        result = await redis.delete(key)
        return result > 0


@lru_cache()
def get_cache_service() -> CacheService:
    """
    Get the cache service based on configuration.
    
    Returns:
        Cache service instance
    """
    if settings.CACHE_TYPE.lower() == "redis" and settings.REDIS_URL:
        logger.info("Using Redis cache service")
        return RedisCacheService(settings.REDIS_URL, settings.CACHE_TTL)
    else:
        logger.info("Using in-memory cache service")
        return MemoryCacheService(settings.CACHE_TTL)
