"""Async utility functions for running async code in sync contexts."""

import asyncio
import functools
from typing import Any, Coroutine, TypeVar

T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine in a sync context.
    
    This is useful for Celery tasks that need to call async functions.
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
        raise RuntimeError("Cannot run async code from within an event loop")
    except RuntimeError:
        return asyncio.run(coro)


def async_to_sync(func):
    """
    Decorator to convert an async function to a sync function.
    
    Useful for making async functions callable from Celery tasks.
    
    Args:
        func: Async function to convert
        
    Returns:
        Sync version of the function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return run_async(func(*args, **kwargs))
    
    return wrapper


def sync_to_async(func):
    """
    Decorator to convert a sync function to an async function.
    
    Args:
        func: Sync function to convert
        
    Returns:
        Async version of the function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    return wrapper