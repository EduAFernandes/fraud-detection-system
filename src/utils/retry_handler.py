"""Retry Handler with Exponential Backoff for Fraud Detection System.

Provides automatic retry logic for transient failures with exponential backoff
and jitter to prevent thundering herd problems.
"""

import time
import random
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_exception: Exception):
        super().__init__(message)
        self.last_exception = last_exception


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """Decorator for automatic retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (0 = no retries)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def unreliable_api_call():
            # ... code that might fail transiently
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    # If this was the last attempt, raise
                    if attempt == max_retries:
                        raise RetryError(
                            f"Failed after {max_retries + 1} attempts: {str(e)}",
                            last_exception=e
                        )

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter if enabled (random 0-100% of delay)
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Call optional retry callback
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error(f"Retry callback failed: {callback_error}")

                    # Wait before retry
                    time.sleep(delay)

            # Should never reach here, but just in case
            raise RetryError(
                f"Unexpected retry exhaustion for {func.__name__}",
                last_exception=last_exception or Exception("Unknown error")
            )

        return wrapper
    return decorator


class RetryHandler:
    """Retry handler class for manual retry control.

    Provides more control over retry logic compared to the decorator.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

        logger.info(
            f"🔧 Initialized RetryHandler (max_retries={max_retries}, "
            f"base_delay={base_delay}s, max_delay={max_delay}s)"
        )

    def execute(
        self,
        func: Callable,
        *args,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            exceptions: Exception types to catch and retry
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RetryError: When all retry attempts are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except exceptions as e:
                last_exception = e

                # If this was the last attempt, raise
                if attempt == self.max_retries:
                    raise RetryError(
                        f"Failed after {self.max_retries + 1} attempts: {str(e)}",
                        last_exception=e
                    )

                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

        raise RetryError(
            f"Unexpected retry exhaustion",
            last_exception=last_exception or Exception("Unknown error")
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


# Predefined retry handlers for common scenarios
default_retry_handler = RetryHandler(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0
)

aggressive_retry_handler = RetryHandler(
    max_retries=5,
    base_delay=0.5,
    max_delay=60.0
)

conservative_retry_handler = RetryHandler(
    max_retries=2,
    base_delay=2.0,
    max_delay=10.0
)
