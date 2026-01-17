"""
Rate Limiter for API calls
Prevents cost explosion from OpenAI API calls
"""

import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def rate_limited(calls_per_minute: int = 20, delay_seconds: float = 3.0) -> Callable:
    """
    Decorator to rate limit function calls

    Prevents API cost explosion by enforcing:
    1. Maximum calls per minute
    2. Minimum delay between calls

    Args:
        calls_per_minute: Maximum calls allowed per minute
        delay_seconds: Minimum seconds between calls

    Returns:
        Decorated function with rate limiting

    Example:
        @rate_limited(calls_per_minute=20, delay_seconds=3.0)
        def call_openai_api(prompt):
            # API call here
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Shared state across calls
        last_call = [0.0]
        call_count = [0]
        window_start = [time.time()]

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal last_call, call_count, window_start

            now = time.time()

            # Reset window if 60 seconds passed
            if now - window_start[0] >= 60:
                logger.debug(f"Rate limit window reset for {func.__name__}")
                window_start[0] = now
                call_count[0] = 0

            # Check rate limit
            if call_count[0] >= calls_per_minute:
                wait_time = 60 - (now - window_start[0])
                if wait_time > 0:
                    logger.warning(
                        f"⏳ Rate limit reached for {func.__name__} "
                        f"({calls_per_minute}/min). Waiting {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    window_start[0] = time.time()
                    call_count[0] = 0

            # Enforce minimum delay between calls
            time_since_last = now - last_call[0]
            if time_since_last < delay_seconds:
                sleep_time = delay_seconds - time_since_last
                logger.debug(f"Enforcing {sleep_time:.2f}s delay for {func.__name__}")
                time.sleep(sleep_time)

            # Execute function
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in rate-limited function {func.__name__}: {e}")
                raise

            # Update tracking
            last_call[0] = time.time()
            call_count[0] += 1

            logger.debug(
                f"Rate limiter stats for {func.__name__}: "
                f"{call_count[0]}/{calls_per_minute} calls in current window"
            )

            return result

        # Add method to check current rate limit status
        def get_rate_limit_status() -> dict:
            """Get current rate limit status"""
            now = time.time()
            window_elapsed = now - window_start[0]
            return {
                'calls_in_window': call_count[0],
                'max_calls': calls_per_minute,
                'window_elapsed_seconds': window_elapsed,
                'calls_remaining': max(0, calls_per_minute - call_count[0]),
                'time_until_reset': max(0, 60 - window_elapsed)
            }

        wrapper.get_rate_limit_status = get_rate_limit_status

        return wrapper

    return decorator


class RateLimiter:
    """
    Class-based rate limiter for more control

    Usage:
        limiter = RateLimiter(calls_per_minute=20)

        with limiter:
            # Make API call
            result = api.call()
    """

    def __init__(self, calls_per_minute: int = 20, delay_seconds: float = 3.0):
        """
        Initialize rate limiter

        Args:
            calls_per_minute: Maximum calls per minute
            delay_seconds: Minimum delay between calls
        """
        self.calls_per_minute = calls_per_minute
        self.delay_seconds = delay_seconds
        self.last_call = 0.0
        self.call_count = 0
        self.window_start = time.time()

        logger.info(
            f"✅ Rate limiter initialized: {calls_per_minute} calls/min, "
            f"{delay_seconds}s delay"
        )

    def __enter__(self):
        """Context manager entry - enforce rate limit before operation"""
        self._enforce_rate_limit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - update tracking"""
        self._update_tracking()
        return False

    def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()

        # Reset window if needed
        if now - self.window_start >= 60:
            self.window_start = now
            self.call_count = 0

        # Check rate limit
        if self.call_count >= self.calls_per_minute:
            wait_time = 60 - (now - self.window_start)
            if wait_time > 0:
                logger.warning(
                    f"⏳ Rate limit reached ({self.calls_per_minute}/min). "
                    f"Waiting {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
                self.window_start = time.time()
                self.call_count = 0

        # Enforce minimum delay
        time_since_last = now - self.last_call
        if time_since_last < self.delay_seconds:
            time.sleep(self.delay_seconds - time_since_last)

    def _update_tracking(self):
        """Update rate limit tracking"""
        self.last_call = time.time()
        self.call_count += 1

    def get_status(self) -> dict:
        """Get current rate limit status"""
        now = time.time()
        window_elapsed = now - self.window_start
        return {
            'calls_in_window': self.call_count,
            'max_calls': self.calls_per_minute,
            'window_elapsed_seconds': window_elapsed,
            'calls_remaining': max(0, self.calls_per_minute - self.call_count),
            'time_until_reset': max(0, 60 - window_elapsed)
        }
