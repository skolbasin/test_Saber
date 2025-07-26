"""Redis client implementation for caching."""

import json
from typing import Any, Optional, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from app.settings import get_settings


class RedisClient:
    """
    High-performance Redis client for caching build system data.
    
    Provides async Redis operations with automatic serialization,
    connection pooling, and error handling for enterprise applications.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis client.
        
        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self._redis: Optional[Redis] = None
        self._redis_url = redis_url or get_settings().redis_url

    async def connect(self) -> None:
        """
        Establish Redis connection.
        
        Creates connection pool with optimized settings for high performance.
        """
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        await self.connect()
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except (json.JSONDecodeError, Exception):
            return value if 'value' in locals() else None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        Set value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (seconds or timedelta)
            
        Returns:
            True if successful, False otherwise
        """
        await self.connect()
        try:
            serialized_value = json.dumps(value, default=str)
            
            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                return await self._redis.setex(key, ttl, serialized_value)
            else:
                return await self._redis.set(key, serialized_value)
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        await self.connect()
        try:
            result = await self._redis.delete(key)
            return result > 0
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        await self.connect()
        try:
            return await self._redis.exists(key) > 0
        except Exception:
            return False

    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """
        Set expiration time for existing key.
        
        Args:
            key: Cache key
            ttl: Time to live (seconds or timedelta)
            
        Returns:
            True if expiration was set, False otherwise
        """
        await self.connect()
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            return await self._redis.expire(key, ttl)
        except Exception:
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment numeric value in Redis.
        
        Args:
            key: Cache key
            amount: Amount to increment (default: 1)
            
        Returns:
            New value after increment, None on error
        """
        await self.connect()
        try:
            return await self._redis.incrby(key, amount)
        except Exception:
            return None

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get time-to-live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, None if key doesn't exist or has no expiration
        """
        await self.connect()
        try:
            ttl = await self._redis.ttl(key)
            return ttl if ttl > 0 else None
        except Exception:
            return None

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "build:*")
            
        Returns:
            Number of keys deleted
        """
        await self.connect()
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception:
            return 0

    async def ping(self) -> bool:
        """
        Ping Redis server to check connectivity.
        
        Returns:
            True if Redis is responsive, False otherwise
        """
        await self.connect()
        try:
            response = await self._redis.ping()
            return response is True
        except Exception:
            return False

    async def get_info(self) -> dict:
        """
        Get Redis server information.
        
        Returns:
            Redis server info dictionary
        """
        await self.connect()
        try:
            return await self._redis.info()
        except Exception:
            return {}


_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get global Redis client instance.
    
    Returns:
        RedisClient: Global Redis client
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def close_redis_connection():
    """Close global Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None