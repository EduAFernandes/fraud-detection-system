"""
Langfuse Observability for Fraud Detection
Tracks AI agent costs, latency, and effectiveness
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import Langfuse, but make it optional
try:
    from langfuse import Langfuse, observe
    LANGFUSE_AVAILABLE = True
    langfuse_context = None  # Context not needed for basic monitoring
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("⚠️  Langfuse not available - install: pip install langfuse")
    observe = None
    langfuse_context = None


class LangfuseMonitor:
    """Langfuse monitoring wrapper for fraud detection"""

    def __init__(self,
                 public_key: Optional[str] = None,
                 secret_key: Optional[str] = None,
                 host: str = "https://cloud.langfuse.com",
                 enabled: bool = True):
        """
        Initialize Langfuse monitoring

        Args:
            public_key: Langfuse public key
            secret_key: Langfuse secret key
            host: Langfuse host URL
            enabled: Whether monitoring is enabled
        """
        self.enabled = enabled and LANGFUSE_AVAILABLE and public_key and secret_key
        self.langfuse = None

        if not self.enabled:
            if not LANGFUSE_AVAILABLE:
                logger.info("⚠️  Langfuse monitoring disabled (not installed)")
            elif not (public_key and secret_key):
                logger.info("⚠️  Langfuse monitoring disabled (no credentials)")
            else:
                logger.info("⚠️  Langfuse monitoring disabled")
            return

        try:
            self.langfuse = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host
            )
            logger.info("✅ Langfuse monitoring initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Langfuse: {e}")
            self.enabled = False

    def track_fraud_investigation(self,
                                  order_id: str,
                                  fraud_score: float,
                                  transaction_data: Dict[str, Any],
                                  agent_result: Dict[str, Any],
                                  latency_seconds: float):
        """
        Track AI agent fraud investigation

        Args:
            order_id: Order identifier
            fraud_score: ML fraud score
            transaction_data: Transaction details
            agent_result: Agent analysis result
            latency_seconds: Investigation latency
        """
        if not self.enabled:
            return

        try:
            self.langfuse.create_event(
                name="fraud_investigation",
                metadata={
                    "order_id": order_id,
                    "fraud_score": fraud_score,
                    "amount": transaction_data.get('total_amount') or transaction_data.get('amount'),
                    "payment_method": transaction_data.get('payment_method'),
                    "latency_seconds": latency_seconds,
                    "recommendation": agent_result.get('recommendation'),
                    "tags": ["fraud_detection", "ai_agent"]
                },
                input=transaction_data,
                output=agent_result
            )
        except Exception as e:
            logger.error(f"❌ Failed to track investigation: {e}")

    def track_ml_prediction(self,
                           order_id: str,
                           features: Dict[str, Any],
                           prediction: str,
                           fraud_score: float):
        """
        Track ML model prediction

        Args:
            order_id: Order identifier
            features: Input features
            prediction: Model prediction
            fraud_score: Fraud probability score
        """
        if not self.enabled:
            return

        try:
            self.langfuse.create_event(
                name="ml_fraud_prediction",
                metadata={
                    "order_id": order_id,
                    "prediction": prediction,
                    "fraud_score": fraud_score,
                    "tags": ["ml_model", "fraud_detection"]
                },
                input=features,
                output={
                    "prediction": prediction,
                    "fraud_score": fraud_score
                }
            )
        except Exception as e:
            logger.error(f"❌ Failed to track ML prediction: {e}")

    def track_qdrant_query(self,
                          transaction: Dict[str, Any],
                          results: list,
                          query_time_seconds: float):
        """
        Track Qdrant RAG query

        Args:
            transaction: Transaction being analyzed
            results: Query results
            query_time_seconds: Query latency
        """
        if not self.enabled:
            return

        try:
            self.langfuse.create_event(
                name="qdrant_rag_query",
                metadata={
                    "order_id": transaction.get('order_id'),
                    "results_count": len(results),
                    "query_time_ms": query_time_seconds * 1000,
                    "tags": ["qdrant", "rag"]
                },
                input=transaction,
                output=results
            )
        except Exception as e:
            logger.error(f"❌ Failed to track Qdrant query: {e}")

    def track_redis_operation(self,
                             operation: str,
                             user_id: str,
                             result: Dict[str, Any],
                             latency_ms: float):
        """
        Track Redis memory operations

        Args:
            operation: Operation type (check_user, flag_user, etc.)
            user_id: User identifier
            result: Operation result
            latency_ms: Operation latency
        """
        if not self.enabled:
            return

        try:
            self.langfuse.create_event(
                name="redis_memory_operation",
                metadata={
                    "operation": operation,
                    "user_id": user_id,
                    "latency_ms": latency_ms,
                    "tags": ["redis", "memory"]
                },
                input={"operation": operation, "user_id": user_id},
                output=result
            )
        except Exception as e:
            logger.error(f"❌ Failed to track Redis operation: {e}")

    def flush(self):
        """Flush pending traces to Langfuse"""
        if not self.enabled or not self.langfuse:
            return

        try:
            self.langfuse.flush()
            logger.debug("✅ Langfuse traces flushed")
        except Exception as e:
            logger.error(f"❌ Failed to flush Langfuse: {e}")

    def __del__(self):
        """Cleanup - flush on destruction"""
        self.flush()


def track_operation(operation_name: str, tags: list = None):
    """
    Decorator to track any operation with Langfuse

    Args:
        operation_name: Name of the operation
        tags: Optional tags for categorization

    Usage:
        @track_operation("my_function", tags=["fraud", "ml"])
        def my_function(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not LANGFUSE_AVAILABLE:
                return func(*args, **kwargs)

            start_time = time.time()

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Track execution
                latency = time.time() - start_time

                # Use Langfuse observe decorator if available
                if LANGFUSE_AVAILABLE:
                    try:
                        langfuse_context.update_current_observation(
                            name=operation_name,
                            metadata={"latency_seconds": latency},
                            tags=tags or []
                        )
                    except:
                        pass  # Silently fail if context not available

                return result

            except Exception as e:
                # Track error
                latency = time.time() - start_time
                logger.error(f"Error in {operation_name}: {e}")
                raise

        return wrapper
    return decorator


# Metrics aggregator for system-wide stats
class MetricsAggregator:
    """Aggregate system metrics for monitoring"""

    def __init__(self):
        self.metrics = {
            'total_transactions': 0,
            'fraud_detected': 0,
            'ai_investigations': 0,
            'velocity_fraud': 0,
            'card_testing': 0,
            'redis_hits': 0,
            'qdrant_queries': 0,
            'total_processing_time': 0.0,
            'total_ai_time': 0.0,
        }

    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric"""
        if metric in self.metrics:
            self.metrics[metric] += value

    def add_time(self, metric: str, seconds: float):
        """Add time to a timing metric"""
        if metric in self.metrics:
            self.metrics[metric] += seconds

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        metrics = self.metrics.copy()

        # Calculate derived metrics
        if metrics['total_transactions'] > 0:
            metrics['fraud_rate'] = metrics['fraud_detected'] / metrics['total_transactions']
            metrics['avg_processing_time'] = metrics['total_processing_time'] / metrics['total_transactions']

            if metrics['ai_investigations'] > 0:
                metrics['avg_ai_time'] = metrics['total_ai_time'] / metrics['ai_investigations']

        return metrics

    def reset(self):
        """Reset all metrics"""
        for key in self.metrics:
            if isinstance(self.metrics[key], int):
                self.metrics[key] = 0
            else:
                self.metrics[key] = 0.0


# Global metrics instance
metrics = MetricsAggregator()
