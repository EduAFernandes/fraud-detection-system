"""
Qdrant Knowledge Base for Fraud Detection
Provides RAG (Retrieval-Augmented Generation) capabilities using vector similarity
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


# Initial fraud patterns for knowledge base
INITIAL_FRAUD_PATTERNS = [
    {
        'description': "Small transaction $5-$20 from new account less than 7 days old using credit card",
        'fraud_type': 'card_testing',
        'metadata': {
            'amount_range': '5-20',
            'account_age_max': 7,
            'payment_method': 'credit_card',
            'risk_level': 'high'
        }
    },
    {
        'description': "3 or more transactions within 5 minutes from same user",
        'fraud_type': 'velocity_fraud',
        'metadata': {
            'transaction_count': 3,
            'time_window_minutes': 5,
            'risk_level': 'high'
        }
    },
    {
        'description': "Transaction over $500 from account less than 30 days old",
        'fraud_type': 'new_account_high_value',
        'metadata': {
            'amount_min': 500,
            'account_age_max': 30,
            'risk_level': 'medium'
        }
    },
    {
        'description': "Multiple failed payment attempts followed by successful charge",
        'fraud_type': 'payment_testing',
        'metadata': {
            'failed_attempts_min': 2,
            'risk_level': 'high'
        }
    },
    {
        'description': "IP address from known fraud region with VPN indicators",
        'fraud_type': 'geographic_anomaly',
        'metadata': {
            'vpn_detected': True,
            'risk_level': 'medium'
        }
    },
    {
        'description': "Transaction from IP address different from user's typical location",
        'fraud_type': 'location_mismatch',
        'metadata': {
            'risk_level': 'low'
        }
    },
    {
        'description': "Bulk orders of high-value items to new address",
        'fraud_type': 'bulk_order_fraud',
        'metadata': {
            'new_address': True,
            'high_value': True,
            'risk_level': 'high'
        }
    },
    {
        'description': "Account created and transaction made within 1 hour",
        'fraud_type': 'instant_purchase',
        'metadata': {
            'account_age_max': 1,
            'risk_level': 'medium'
        }
    },
    {
        'description': "Unusual spike in order frequency compared to user history",
        'fraud_type': 'behavioral_anomaly',
        'metadata': {
            'frequency_spike': True,
            'risk_level': 'medium'
        }
    },
    {
        'description': "Transaction using recently added payment method not verified",
        'fraud_type': 'unverified_payment',
        'metadata': {
            'payment_verified': False,
            'risk_level': 'medium'
        }
    }
]


class QdrantFraudKnowledge:
    """Vector database for historical fraud pattern matching using Qdrant"""

    def __init__(self,
                 url: str = "http://localhost:6333",
                 api_key: Optional[str] = None,
                 collection_name: str = "fraud_patterns",
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize Qdrant knowledge base

        Args:
            url: Qdrant server URL
            api_key: Qdrant API key (for cloud)
            collection_name: Collection name for fraud patterns
            embedding_model: Sentence transformer model name
        """
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model

        logger.info(f"🔧 Initializing Qdrant knowledge base...")
        logger.info(f"   URL: {url}")
        logger.info(f"   Collection: {collection_name}")

        # Initialize Qdrant client
        try:
            self.client = QdrantClient(url=url, api_key=api_key)
            logger.info("✅ Qdrant client connected")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise

        # Initialize embedding model
        logger.info(f"📦 Loading embedding model: {embedding_model}...")
        try:
            self.encoder = SentenceTransformer(embedding_model)
            logger.info("✅ Embedding model loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise

        # Create collection if not exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info(f"📝 Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info("✅ Collection created")

                # Populate with initial patterns
                logger.info("📝 Populating with initial fraud patterns...")
                self.add_fraud_patterns_bulk(INITIAL_FRAUD_PATTERNS)
            else:
                logger.info(f"✅ Collection exists: {self.collection_name}")

        except Exception as e:
            logger.error(f"❌ Failed to ensure collection: {e}")
            raise

    def add_fraud_pattern(self,
                         description: str,
                         metadata: Dict[str, Any],
                         fraud_type: str = "unknown"):
        """
        Add a single fraud pattern to knowledge base

        Args:
            description: Natural language description of fraud pattern
            metadata: Metadata (order_id, user_id, amount, etc.)
            fraud_type: Type of fraud (velocity, card_testing, etc.)
        """
        try:
            # Generate embedding
            embedding = self.encoder.encode(description).tolist()

            # Generate unique ID from description
            pattern_id = hashlib.md5(description.encode()).hexdigest()

            # Store in Qdrant
            point = PointStruct(
                id=pattern_id,
                vector=embedding,
                payload={
                    'description': description,
                    'fraud_type': fraud_type,
                    **metadata
                }
            )

            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            logger.debug(f"✅ Added fraud pattern: {fraud_type}")

        except Exception as e:
            logger.error(f"❌ Failed to add fraud pattern: {e}")

    def add_fraud_patterns_bulk(self, patterns: List[Dict[str, Any]]):
        """
        Add multiple fraud patterns at once

        Args:
            patterns: List of dicts with 'description', 'metadata', 'fraud_type'
        """
        try:
            points = []

            for pattern in patterns:
                description = pattern['description']
                embedding = self.encoder.encode(description).tolist()
                pattern_id = hashlib.md5(description.encode()).hexdigest()

                points.append(PointStruct(
                    id=pattern_id,
                    vector=embedding,
                    payload={
                        'description': description,
                        'fraud_type': pattern.get('fraud_type', 'unknown'),
                        **pattern.get('metadata', {})
                    }
                ))

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            logger.info(f"✅ Added {len(patterns)} fraud patterns")

        except Exception as e:
            logger.error(f"❌ Failed to add bulk patterns: {e}")

    def find_similar_fraud_cases(self,
                                 transaction: Dict[str, Any],
                                 limit: int = 5,
                                 score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find similar fraud cases from knowledge base

        Args:
            transaction: Current transaction to analyze
            limit: Max number of similar cases to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar fraud cases with scores
        """
        try:
            # Build query from transaction
            query_text = self._build_query_from_transaction(transaction)

            # Generate embedding
            query_embedding = self.encoder.encode(query_text).tolist()

            # Search in Qdrant (using new API)
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            ).points

            # Format results
            similar_cases = []
            for result in results:
                similar_cases.append({
                    'description': result.payload['description'],
                    'fraud_type': result.payload.get('fraud_type'),
                    'similarity_score': result.score,
                    'metadata': {
                        k: v for k, v in result.payload.items()
                        if k not in ['description', 'fraud_type']
                    }
                })

            if similar_cases:
                logger.info(f"🔍 Found {len(similar_cases)} similar fraud cases")

            return similar_cases

        except Exception as e:
            logger.error(f"❌ Failed to find similar cases: {e}")
            return []

    def _build_query_from_transaction(self, transaction: Dict[str, Any]) -> str:
        """Build natural language query from transaction"""
        query_parts = []

        # Amount
        if 'total_amount' in transaction or 'amount' in transaction:
            amount = transaction.get('total_amount') or transaction.get('amount')
            query_parts.append(f"transaction amount ${amount:.2f}")

        # Payment method
        if 'payment_method' in transaction:
            query_parts.append(f"payment method {transaction['payment_method']}")

        # Account age
        if 'account_age_days' in transaction:
            query_parts.append(f"account age {transaction['account_age_days']} days")

        # IP address
        if 'ip_address' in transaction:
            query_parts.append(f"IP address {transaction['ip_address']}")

        # Location
        if 'location' in transaction:
            query_parts.append(f"location {transaction['location']}")

        return " ".join(query_parts) if query_parts else "fraud transaction"

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            return {
                'total_patterns': collection_info.points_count,
                'vector_size': collection_info.config.params.vectors.size,
                'distance_metric': collection_info.config.params.vectors.distance.value
            }
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {
                'total_patterns': 0,
                'error': str(e)
            }
