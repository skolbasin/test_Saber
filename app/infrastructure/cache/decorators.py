"""Cache decorators for automatic caching of service methods."""

import functools
import hashlib
import json
from typing import Any, Callable, Optional, Union
from datetime import timedelta

from .redis_client import get_redis_client


def cache_result(
    ttl: Union[int, timedelta] = timedelta(minutes=30),
    key_prefix: str = "",
    key_generator: Optional[Callable] = None,
) -> Callable:
    """
    Decorator for caching method results.
    
    Args:
        ttl: Cache time-to-live
        key_prefix: Prefix for cache keys
        key_generator: Custom function to generate cache keys
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            redis_client = get_redis_client()
            
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = _generate_default_key(func, args, kwargs, key_prefix)
            
            cached_result = await redis_client.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            if result is not None:
                await redis_client.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(
    key_pattern: str,
    key_generator: Optional[Callable] = None,
) -> Callable:
    """
    Decorator for invalidating cache entries after method execution.
    
    Args:
        key_pattern: Pattern for keys to invalidate
        key_generator: Custom function to generate invalidation keys
        
    Returns:
        Decorated function with cache invalidation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            
            redis_client = get_redis_client()
            
            if key_generator:
                invalidation_keys = key_generator(*args, **kwargs)
                if isinstance(invalidation_keys, str):
                    invalidation_keys = [invalidation_keys]
            else:
                invalidation_keys = [key_pattern]
            
            for key in invalidation_keys:
                if "*" in key:
                    await redis_client.clear_pattern(key)
                else:
                    await redis_client.delete(key)
            
            return result
        
        return wrapper
    return decorator


def cache_aside(
    ttl: Union[int, timedelta] = timedelta(minutes=30),
    key_prefix: str = "",
) -> Callable:
    """
    Cache-aside pattern decorator for read-through caching.
    
    Args:
        ttl: Cache time-to-live
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorated function with cache-aside pattern
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            redis_client = get_redis_client()
            cache_key = _generate_default_key(func, args, kwargs, key_prefix)
            
            cached_result = await redis_client.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            
            if result is not None:
                await redis_client.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def write_through_cache(
    ttl: Union[int, timedelta] = timedelta(minutes=30),
    key_prefix: str = "",
) -> Callable:
    """
    Write-through cache decorator for keeping cache synchronized.
    
    Args:
        ttl: Cache time-to-live
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorated function with write-through caching
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            
            if result is not None:
                redis_client = get_redis_client()
                cache_key = _generate_default_key(func, args, kwargs, key_prefix)
                await redis_client.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def rate_limit(
    max_requests: int,
    window_seconds: int,
    key_generator: Optional[Callable] = None,
) -> Callable:
    """
    Rate limiting decorator using Redis counters.
    
    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        key_generator: Custom function to generate rate limit keys
        
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            redis_client = get_redis_client()
            
            if key_generator:
                rate_key = key_generator(*args, **kwargs)
            else:
                rate_key = f"rate_limit:{func.__name__}:{_hash_args(args, kwargs)}"
            
            current_count = await redis_client.increment(rate_key)
            if current_count == 1:
                await redis_client.expire(rate_key, window_seconds)
            
            if current_count > max_requests:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    reset_timeout: int = 60,
    key_prefix: str = "circuit_breaker",
) -> Callable:
    """
    Circuit breaker decorator for fault tolerance.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        reset_timeout: Seconds before attempting to close circuit
        key_prefix: Prefix for circuit breaker keys
        
    Returns:
        Decorated function with circuit breaker pattern
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            redis_client = get_redis_client()
            failure_key = f"{key_prefix}:failures:{func.__name__}"
            last_failure_key = f"{key_prefix}:last_failure:{func.__name__}"
            
            failure_count = await redis_client.get(failure_key) or 0
            if isinstance(failure_count, str):
                failure_count = int(failure_count)
            
            if failure_count >= failure_threshold:
                last_failure = await redis_client.get(last_failure_key)
                if last_failure:
                    import time
                    if time.time() - float(last_failure) < reset_timeout:
                        from fastapi import HTTPException, status
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service temporarily unavailable"
                        )
                    else:
                        await redis_client.delete(failure_key)
                        await redis_client.delete(last_failure_key)
            
            try:
                result = await func(*args, **kwargs)
                if failure_count > 0:
                    await redis_client.delete(failure_key)
                    await redis_client.delete(last_failure_key)
                return result
            except Exception as e:
                import time
                await redis_client.increment(failure_key)
                await redis_client.set(last_failure_key, str(time.time()))
                raise e
        
        return wrapper
    return decorator


def _generate_default_key(func: Callable, args: tuple, kwargs: dict, prefix: str = "") -> str:
    """Generate default cache key from function name and arguments."""
    key_parts = [prefix] if prefix else []
    key_parts.append(func.__name__)
    key_parts.append(_hash_args(args, kwargs))
    return ":".join(filter(None, key_parts))


def _hash_args(args: tuple, kwargs: dict) -> str:
    """Generate hash from function arguments."""
    arg_str = json.dumps({
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
    }, sort_keys=True)
    
    return hashlib.md5(arg_str.encode()).hexdigest()[:16]