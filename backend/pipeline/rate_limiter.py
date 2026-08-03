"""
Rate limiting and exponential backoff utilities for API collectors.

Provides decorators and callable wrappers for both async and sync functions.
All collectors should use these when making external API/network calls.
"""

import asyncio
import time
import random
from functools import wraps


def async_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Decorator for async functions: retry on exception with exponential backoff + jitter.

    Delay formula: min(base_delay * 2^attempt, max_delay) + random_jitter
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.5)
                        total = delay + jitter
                        print(f"[RateLimiter] Retry {attempt + 1}/{max_retries} after {total:.1f}s: {e}")
                        await asyncio.sleep(total)
            raise last_exception
        return wrapper
    return decorator


def sync_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Decorator for sync functions: retry on exception with exponential backoff + jitter.

    Use this for functions that run in ThreadPoolExecutor (yfinance, edgartools, etc.).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.5)
                        total = delay + jitter
                        print(f"[RateLimiter] Retry {attempt + 1}/{max_retries} after {total:.1f}s: {e}")
                        time.sleep(total)
            raise last_exception
        return wrapper
    return decorator


async def async_call_with_retry(coro_factory, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Call an async operation (provided as a zero-arg coroutine factory) with retry + backoff.

    Useful when you can't use the decorator (e.g., one-off httpx calls).

    Example:
        result = await async_call_with_retry(lambda: client.get(url))
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.5)
                total = delay + jitter
                print(f"[RateLimiter] Retry {attempt + 1}/{max_retries} after {total:.1f}s: {e}")
                await asyncio.sleep(total)
    raise last_exception


def sync_call_with_retry(func, *args, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0, **kwargs):
    """
    Call a sync function with retry + backoff.

    Useful for one-off calls that run in executor threads.

    Example:
        result = sync_call_with_retry(yf.Ticker, "AAPL")
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.5)
                total = delay + jitter
                print(f"[RateLimiter] Retry {attempt + 1}/{max_retries} after {total:.1f}s: {e}")
                time.sleep(total)
    raise last_exception
