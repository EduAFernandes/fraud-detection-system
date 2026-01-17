"""
Configuration settings for Fraud Detection System
Loads settings from environment variables with sensible defaults
"""

import os
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class KafkaConfig:
    """Kafka connection configuration"""
    bootstrap_servers: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    topic_input: str = "fraud-detection-input"
    topic_output: str = "fraud-detection-output"
    topic_agent_queue: str = "agent-analysis-queue"
    consumer_group: str = "fraud-detection-group"

    @property
    def security_protocol(self) -> str:
        return "SASL_SSL" if self.api_key else "PLAINTEXT"

    @property
    def sasl_mechanism(self) -> str:
        return "PLAIN" if self.api_key else None


@dataclass
class RedisConfig:
    """Redis memory configuration"""
    url: str = "redis://localhost:6379"
    enabled: bool = True

    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
            enabled=os.getenv('ENABLE_REDIS', 'true').lower() == 'true'
        )


@dataclass
class QdrantConfig:
    """Qdrant vector database configuration"""
    url: str = "http://localhost:6333"
    api_key: Optional[str] = None
    collection_name: str = "fraud_patterns"
    enabled: bool = True

    @classmethod
    def from_env(cls) -> 'QdrantConfig':
        return cls(
            url=os.getenv('QDRANT_URL', 'http://localhost:6333'),
            api_key=os.getenv('QDRANT_API_KEY'),
            collection_name=os.getenv('QDRANT_COLLECTION', 'fraud_patterns'),
            enabled=os.getenv('ENABLE_QDRANT', 'true').lower() == 'true'
        )


@dataclass
class LangfuseConfig:
    """Langfuse observability configuration"""
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: str = "https://cloud.langfuse.com"
    enabled: bool = False

    @classmethod
    def from_env(cls) -> 'LangfuseConfig':
        public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        secret_key = os.getenv('LANGFUSE_SECRET_KEY')

        return cls(
            public_key=public_key,
            secret_key=secret_key,
            host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com'),
            enabled=bool(public_key and secret_key)
        )


@dataclass
class FraudDetectionConfig:
    """Fraud detection thresholds and parameters"""
    block_threshold: float = 0.70
    review_threshold: float = 0.40
    velocity_threshold_ms: int = 500
    card_testing_order_threshold: int = 3
    card_testing_window_minutes: int = 5
    max_ai_requests_per_minute: int = 20
    ai_request_delay_seconds: float = 3.0

    @classmethod
    def from_env(cls) -> 'FraudDetectionConfig':
        return cls(
            block_threshold=float(os.getenv('FRAUD_BLOCK_THRESHOLD', '0.70')),
            review_threshold=float(os.getenv('FRAUD_REVIEW_THRESHOLD', '0.40')),
            velocity_threshold_ms=int(os.getenv('VELOCITY_THRESHOLD_MS', '500')),
            card_testing_order_threshold=int(os.getenv('CARD_TESTING_ORDERS', '3')),
            card_testing_window_minutes=int(os.getenv('CARD_TESTING_WINDOW_MIN', '5')),
            max_ai_requests_per_minute=int(os.getenv('MAX_AI_REQUESTS_PER_MIN', '20')),
            ai_request_delay_seconds=float(os.getenv('AI_REQUEST_DELAY_SEC', '3.0'))
        )


@dataclass
class DatabaseConfig:
    """Database configuration for Supabase/PostgreSQL"""
    connection_string: str

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        connection_string = os.getenv('POSTGRES_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("POSTGRES_CONNECTION_STRING environment variable is required")
        return cls(connection_string=connection_string)


class Settings:
    """Main settings class - singleton pattern"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Load all configurations
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        # Kafka configuration
        kafka_bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
        if not kafka_bootstrap:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS environment variable is required")

        self.kafka = KafkaConfig(
            bootstrap_servers=kafka_bootstrap,
            api_key=os.getenv('KAFKA_API_KEY'),
            api_secret=os.getenv('KAFKA_API_SECRET'),
            topic_input=os.getenv('KAFKA_TOPIC_INPUT', 'fraud-detection-input'),
            topic_output=os.getenv('KAFKA_TOPIC_OUTPUT', 'fraud-detection-output'),
            topic_agent_queue=os.getenv('KAFKA_TOPIC_AGENT_QUEUE', 'agent-analysis-queue'),
            consumer_group=os.getenv('KAFKA_CONSUMER_GROUP', 'fraud-detection-group')
        )

        # Option C enhancements
        self.redis = RedisConfig.from_env()
        self.qdrant = QdrantConfig.from_env()
        self.langfuse = LangfuseConfig.from_env()

        # Fraud detection parameters
        self.fraud_detection = FraudDetectionConfig.from_env()

        # Agent timeout (for complex investigations with multiple tool calls)
        self.agent_timeout = int(os.getenv('AGENT_TIMEOUT_SECONDS', '90'))

        # Database
        try:
            self.database = DatabaseConfig.from_env()
        except ValueError as e:
            logger.warning(f"Database config not available: {e}")
            self.database = None

        # Logging level
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

        self._initialized = True

        # Log configuration summary
        self._log_config()

    def _log_config(self):
        """Log configuration summary"""
        logger.info("="*70)
        logger.info("🔧 FRAUD DETECTION SYSTEM CONFIGURATION")
        logger.info("="*70)
        logger.info(f"Kafka Bootstrap: {self.kafka.bootstrap_servers}")
        logger.info(f"Kafka Input Topic: {self.kafka.topic_input}")
        logger.info(f"Redis Enabled: {self.redis.enabled} ({self.redis.url})")
        logger.info(f"Qdrant Enabled: {self.qdrant.enabled} ({self.qdrant.url})")
        logger.info(f"Langfuse Enabled: {self.langfuse.enabled}")
        logger.info(f"Block Threshold: {self.fraud_detection.block_threshold}")
        logger.info(f"Review Threshold: {self.fraud_detection.review_threshold}")
        logger.info(f"Max AI Requests: {self.fraud_detection.max_ai_requests_per_minute}/min")
        logger.info("="*70)


# Singleton instance
settings = Settings()


# Helper function for easy access
def get_settings() -> Settings:
    """Get application settings"""
    return settings
