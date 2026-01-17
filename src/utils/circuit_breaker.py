"""Circuit Breaker Pattern Implementation for Fraud Detection System.

Provides fault tolerance and graceful degradation when external services
(like AI agents, Redis, Qdrant) become unreliable or unresponsive.
"""

import time
import threading
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    state_transitions: Dict[str, int] = field(default_factory=lambda: {
        "closed_to_open": 0,
        "open_to_half_open": 0,
        "half_open_to_closed": 0,
        "half_open_to_open": 0
    })


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation with configurable thresholds and recovery logic.

    Prevents cascading failures by failing fast when a service becomes unreliable.
    Automatically attempts recovery after a timeout period.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: tuple = (Exception,),
        success_threshold: int = 2
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name for logging
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception types that count as failures
            success_threshold: Successful calls needed to close circuit from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold

        self._state = CircuitBreakerState.CLOSED
        self._stats = CircuitBreakerStats()
        self._lock = threading.RLock()
        self._consecutive_successes = 0

        logger.info(f"🔧 Initialized circuit breaker '{name}' "
                   f"(failure_threshold={failure_threshold}, "
                   f"recovery_timeout={recovery_timeout}s)")

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        with self._lock:
            return CircuitBreakerStats(
                total_requests=self._stats.total_requests,
                successful_requests=self._stats.successful_requests,
                failed_requests=self._stats.failed_requests,
                consecutive_failures=self._stats.consecutive_failures,
                last_failure_time=self._stats.last_failure_time,
                state_transitions=self._stats.state_transitions.copy()
            )

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        with self._lock:
            return self._state == CircuitBreakerState.OPEN

    def is_closed(self) -> bool:
        """Check if circuit breaker is closed."""
        with self._lock:
            return self._state == CircuitBreakerState.CLOSED

    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open."""
        with self._lock:
            return self._state == CircuitBreakerState.HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
        """
        with self._lock:
            self._stats.total_requests += 1

            # Check if we should allow the call
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._set_state(CircuitBreakerState.HALF_OPEN)
                    logger.info(f"🔄 Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Recovery in: {self._time_until_recovery():.1f}s"
                    )

        # Execute the function
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            self._on_success()
            logger.debug(f"✅ '{self.name}' call succeeded ({execution_time:.3f}s)")
            return result

        except self.expected_exception as e:
            self._on_failure()
            logger.warning(f"❌ '{self.name}' call failed: {e}")
            raise

    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self._stats.successful_requests += 1
            self._stats.consecutive_failures = 0
            self._consecutive_successes += 1

            # If in HALF_OPEN and enough successes, close the circuit
            if (self._state == CircuitBreakerState.HALF_OPEN and
                self._consecutive_successes >= self.success_threshold):
                self._set_state(CircuitBreakerState.CLOSED)
                self._consecutive_successes = 0
                logger.info(f"✅ Circuit breaker '{self.name}' CLOSED (service recovered)")

    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self._stats.failed_requests += 1
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = time.time()
            self._consecutive_successes = 0

            # If in HALF_OPEN and failure, reopen the circuit
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._set_state(CircuitBreakerState.OPEN)
                logger.warning(f"⚠️ Circuit breaker '{self.name}' reopened (service still failing)")

            # If too many consecutive failures, open the circuit
            elif (self._state == CircuitBreakerState.CLOSED and
                  self._stats.consecutive_failures >= self.failure_threshold):
                self._set_state(CircuitBreakerState.OPEN)
                logger.error(f"🚨 Circuit breaker '{self.name}' OPENED "
                           f"({self._stats.consecutive_failures} consecutive failures)")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._stats.last_failure_time is None:
            return True

        time_since_failure = time.time() - self._stats.last_failure_time
        return time_since_failure >= self.recovery_timeout

    def _time_until_recovery(self) -> float:
        """Calculate time remaining until recovery attempt."""
        if self._stats.last_failure_time is None:
            return 0.0

        time_since_failure = time.time() - self._stats.last_failure_time
        return max(0.0, self.recovery_timeout - time_since_failure)

    def _set_state(self, new_state: CircuitBreakerState):
        """Set circuit breaker state and track transition."""
        old_state = self._state

        if old_state != new_state:
            transition_key = f"{old_state.value}_to_{new_state.value}"
            self._stats.state_transitions[transition_key] = \
                self._stats.state_transitions.get(transition_key, 0) + 1

            self._state = new_state

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._stats.consecutive_failures = 0
            self._consecutive_successes = 0
            logger.info(f"🔄 Circuit breaker '{self.name}' manually reset")


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different services."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: tuple = (Exception,),
        success_threshold: int = 2
    ) -> CircuitBreaker:
        """Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception types that count as failures
            success_threshold: Successes needed to close from half-open

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception,
                    success_threshold=success_threshold
                )

            return self._breakers[name]

    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {
                name: breaker.stats
                for name, breaker in self._breakers.items()
            }

    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
