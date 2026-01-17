"""
Fraud Detection Orchestrator
Coordinates all fraud detection components: ML, velocity, agents, memory, and observability
Supports both CrewAI and Agno agent frameworks
"""

import logging
import os
import time
from typing import Dict, Any, Optional
from pydantic import ValidationError as PydanticValidationError
from src.fraud_detection.ml_detector import MLFraudDetector
from src.fraud_detection.velocity_detector import VelocityFraudDetector
from src.config.settings import Settings
from src.models.transaction_models import TransactionInput

logger = logging.getLogger(__name__)

# Agent framework selection
USE_AGNO_AGENTS = os.getenv('USE_AGNO_AGENTS', 'true').lower() == 'true'

# Optional imports
try:
    from src.memory.redis_memory import RedisMemoryManager
except ImportError:
    RedisMemoryManager = None
    logger.warning("⚠️  Redis not available")

try:
    from src.memory.qdrant_knowledge import QdrantFraudKnowledge
except ImportError:
    QdrantFraudKnowledge = None
    logger.warning("⚠️  Qdrant not available")

try:
    from src.observability.langfuse_monitor import LangfuseMonitor, metrics
except ImportError:
    LangfuseMonitor = None
    metrics = None
    logger.warning("⚠️  Langfuse not available")


class FraudOrchestrator:
    """
    Main orchestrator for fraud detection
    Coordinates ML, velocity detection, memory systems, and AI agents
    """

    def __init__(self, settings: Settings):
        """
        Initialize fraud orchestrator

        Args:
            settings: Application settings
        """
        self.settings = settings

        logger.info("="*70)
        logger.info("🚀 INITIALIZING FRAUD DETECTION ORCHESTRATOR")
        logger.info("="*70)

        # Initialize core components
        self.ml_detector = MLFraudDetector()
        self.velocity_detector = VelocityFraudDetector(
            velocity_threshold_ms=settings.fraud_detection.velocity_threshold_ms,
            card_testing_order_threshold=settings.fraud_detection.card_testing_order_threshold,
            card_testing_window_minutes=settings.fraud_detection.card_testing_window_minutes
        )

        # Initialize AI agents (Agno or CrewAI)
        if USE_AGNO_AGENTS:
            try:
                from src.agents_agno.agno_crew_adapter import AgnoCrewAdapter
                self.agent_crew = AgnoCrewAdapter(
                    max_requests_per_minute=settings.fraud_detection.max_ai_requests_per_minute,
                    request_delay_seconds=settings.fraud_detection.ai_request_delay_seconds
                )
                logger.info("✅ AI agents initialized: Agno 2.3+ (production-grade with 6 tools)")
            except Exception as e:
                logger.error(f"❌ Agno initialization failed, falling back to CrewAI: {e}")
                from src.agents.crew_manager import FraudAgentCrew
                self.agent_crew = FraudAgentCrew(
                    max_requests_per_minute=settings.fraud_detection.max_ai_requests_per_minute,
                    request_delay_seconds=settings.fraud_detection.ai_request_delay_seconds
                )
                logger.info("✅ AI agents initialized: CrewAI (fallback)")
        else:
            from src.agents.crew_manager import FraudAgentCrew
            self.agent_crew = FraudAgentCrew(
                max_requests_per_minute=settings.fraud_detection.max_ai_requests_per_minute,
                request_delay_seconds=settings.fraud_detection.ai_request_delay_seconds
            )
            logger.info("✅ AI agents initialized: CrewAI (legacy mode)")

        # Initialize Option C enhancements
        self.redis_memory = None
        self.qdrant_knowledge = None
        self.langfuse_monitor = None

        # Redis memory
        if settings.redis.enabled and RedisMemoryManager:
            try:
                self.redis_memory = RedisMemoryManager(settings.redis.url)
                logger.info(f"✅ Redis memory enabled: {settings.redis.url}")
            except Exception as e:
                logger.error(f"❌ Redis initialization failed: {e}")

        # Qdrant knowledge base
        if settings.qdrant.enabled and QdrantFraudKnowledge:
            try:
                self.qdrant_knowledge = QdrantFraudKnowledge(
                    url=settings.qdrant.url,
                    api_key=settings.qdrant.api_key,
                    collection_name=settings.qdrant.collection_name
                )
                logger.info(f"✅ Qdrant knowledge base enabled: {settings.qdrant.url}")
            except Exception as e:
                logger.error(f"❌ Qdrant initialization failed: {e}")

        # Langfuse observability
        if settings.langfuse.enabled and LangfuseMonitor:
            try:
                self.langfuse_monitor = LangfuseMonitor(
                    public_key=settings.langfuse.public_key,
                    secret_key=settings.langfuse.secret_key,
                    host=settings.langfuse.host,
                    enabled=True
                )
                logger.info("✅ Langfuse monitoring enabled")
            except Exception as e:
                logger.error(f"❌ Langfuse initialization failed: {e}")

        # Statistics
        self.stats = {
            'total_transactions': 0,
            'fraud_detected': 0,
            'agent_investigations': 0,
            'velocity_fraud_count': 0,
            'card_testing_count': 0,
            'redis_boosts': 0,
            'qdrant_boosts': 0
        }

        logger.info("="*70)
        logger.info("✅ FRAUD ORCHESTRATOR READY")
        logger.info("="*70)

    def process_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transaction through full fraud detection pipeline

        Args:
            transaction: Transaction data

        Returns:
            Fraud detection result with recommendation

        Raises:
            ValueError: If transaction validation fails
        """
        start_time = time.time()

        # VALIDATE: Defense-in-depth validation (secondary validation layer)
        try:
            validated_transaction = TransactionInput(**transaction)
            transaction = validated_transaction.model_dump()
        except PydanticValidationError as e:
            logger.error(f"❌ Transaction validation failed in orchestrator")
            logger.error(f"   Validation errors: {e.errors()}")
            raise ValueError(f"Invalid transaction data: {e}")

        order_id = transaction.get('order_id', 'unknown')
        user_id = transaction.get('user_id', 'unknown')

        logger.info(f"\n{'='*70}")
        logger.info(f"📨 Processing Transaction: {order_id}")
        logger.info(f"{'='*70}")
        logger.info(f"💰 Amount: ${transaction.get('total_amount', transaction.get('amount', 0)):.2f}")
        logger.info(f"👤 User: {user_id}")

        # Step 1: Check Redis Memory
        redis_context = []
        redis_boost = 0.0

        if self.redis_memory:
            redis_start = time.time()

            # Check user flagging
            user_status = self.redis_memory.is_user_flagged(user_id)
            if user_status['is_flagged']:
                redis_boost += 0.3
                redis_context.append(f"User flagged: {user_status['reason']}")
                logger.warning(f"🚨 REDIS: User {user_id} is flagged!")

            # Check IP flagging
            ip_address = transaction.get('ip_address', 'unknown')
            ip_status = self.redis_memory.is_ip_flagged(ip_address)
            if ip_status['is_flagged']:
                redis_boost += 0.4
                redis_context.append(f"IP flagged: {ip_status['reason']}")
                logger.warning(f"🚨 REDIS: IP {ip_address} is flagged!")

            # Check transaction velocity
            tx_count = self.redis_memory.get_user_transaction_count(user_id, minutes=60)
            if tx_count >= 5:
                redis_boost += 0.2
                redis_context.append(f"{tx_count} transactions in last hour")
                logger.warning(f"🚨 REDIS: {tx_count} transactions in 1 hour!")

            # Track monitoring
            if self.langfuse_monitor:
                self.langfuse_monitor.track_redis_operation(
                    operation="check_user_context",
                    user_id=user_id,
                    result={'flagged': user_status['is_flagged'], 'boost': redis_boost},
                    latency_ms=(time.time() - redis_start) * 1000
                )

        # Step 2: Velocity Fraud Detection
        velocity_check = self.velocity_detector.check_velocity_fraud(
            user_id,
            transaction.get('total_amount', transaction.get('amount', 0))
        )

        velocity_boost = 0.0
        if velocity_check['is_fraud']:
            logger.warning(f"🚨 {velocity_check['reason']}")
            velocity_boost = velocity_check['score_boost']

            if velocity_check['fraud_type'] == 'velocity':
                self.stats['velocity_fraud_count'] += 1
            elif velocity_check['fraud_type'] == 'card_testing':
                self.stats['card_testing_count'] += 1

        # Step 3: ML Fraud Detection
        ml_score = self.ml_detector.predict(transaction)
        logger.info(f"🤖 ML Fraud Score: {ml_score:.3f}")

        # Track ML prediction
        if self.langfuse_monitor:
            self.langfuse_monitor.track_ml_prediction(
                order_id=order_id,
                features=transaction,
                prediction="FRAUD" if ml_score > 0.7 else "LEGITIMATE",
                fraud_score=ml_score
            )

        # Step 4: Qdrant RAG Query
        qdrant_context = []
        qdrant_boost = 0.0

        if self.qdrant_knowledge:
            qdrant_start = time.time()

            similar_cases = self.qdrant_knowledge.find_similar_fraud_cases(
                transaction,
                limit=3,
                score_threshold=0.75
            )

            if similar_cases:
                logger.info(f"🔍 Found {len(similar_cases)} similar fraud cases")
                for case in similar_cases:
                    similarity = case['similarity_score']
                    qdrant_boost += similarity * 0.2  # Max +0.6 for 3 highly similar cases
                    qdrant_context.append(case)
                    logger.info(f"   • {case['fraud_type']} ({similarity:.0%} similar)")

                # Track Qdrant query
                if self.langfuse_monitor:
                    self.langfuse_monitor.track_qdrant_query(
                        transaction=transaction,
                        results=similar_cases,
                        query_time_seconds=time.time() - qdrant_start
                    )

        # Step 5: Calculate Final Fraud Score
        final_fraud_score = min(1.0, ml_score + velocity_boost + redis_boost + qdrant_boost)

        logger.info(f"\n📊 FRAUD SCORE BREAKDOWN:")
        logger.info(f"   ML Base Score: {ml_score:.3f}")
        if velocity_boost > 0:
            logger.info(f"   Velocity Boost: +{velocity_boost:.3f}")
        if redis_boost > 0:
            logger.info(f"   Redis Boost: +{redis_boost:.3f}")
            self.stats['redis_boosts'] += 1
        if qdrant_boost > 0:
            logger.info(f"   Qdrant Boost: +{qdrant_boost:.3f}")
            self.stats['qdrant_boosts'] += 1
        logger.info(f"   FINAL SCORE: {final_fraud_score:.3f}")

        # Step 6: Determine Triage
        if final_fraud_score >= self.settings.fraud_detection.block_threshold:
            triage = "AGENT_ANALYSIS"  # High risk - needs AI investigation
        elif final_fraud_score >= self.settings.fraud_detection.review_threshold:
            triage = "MANUAL_REVIEW"  # Medium risk
        else:
            triage = "APPROVE"  # Low risk

        # Step 7: AI Agent Investigation (if needed)
        agent_result = None
        if triage == "AGENT_ANALYSIS":
            logger.info("\n🤖 Launching AI Agent Investigation...")

            investigation_start = time.time()

            agent_result = self.agent_crew.investigate(
                transaction=transaction,
                ml_score=ml_score,
                velocity_check=velocity_check if velocity_check['is_fraud'] else None,
                redis_context=redis_context if redis_context else None,
                qdrant_context=qdrant_context if qdrant_context else None
            )

            investigation_time = time.time() - investigation_start

            logger.info(f"✅ AI Investigation complete ({investigation_time:.2f}s)")
            logger.info(f"   Recommendation: {agent_result['recommendation']}")

            self.stats['agent_investigations'] += 1

            # Track investigation
            if self.langfuse_monitor:
                self.langfuse_monitor.track_fraud_investigation(
                    order_id=order_id,
                    fraud_score=final_fraud_score,
                    transaction_data=transaction,
                    agent_result=agent_result,
                    latency_seconds=investigation_time
                )

            # Use agent recommendation
            triage = agent_result['recommendation']

        # Step 8: Update Redis Memory
        if self.redis_memory:
            # Record transaction
            self.redis_memory.record_transaction(user_id, {
                'order_id': order_id,
                'amount': transaction.get('total_amount', transaction.get('amount', 0)),
                'payment_method': transaction.get('payment_method'),
                'fraud_score': final_fraud_score
            })

            # Flag user/IP if high fraud
            if final_fraud_score >= 0.8:
                self.redis_memory.flag_user(
                    user_id,
                    f"Fraud score {final_fraud_score:.2f}",
                    severity="high" if final_fraud_score >= 0.9 else "medium"
                )

                if final_fraud_score >= 0.9:
                    ip_address = transaction.get('ip_address', 'unknown')
                    if ip_address != 'unknown':
                        self.redis_memory.flag_ip(
                            ip_address,
                            f"User {user_id} fraud score {final_fraud_score:.2f}"
                        )

        # Step 9: Add to Qdrant if confirmed fraud
        if self.qdrant_knowledge and final_fraud_score >= 0.9:
            fraud_description = self._build_fraud_description(transaction, final_fraud_score)
            self.qdrant_knowledge.add_fraud_pattern(
                description=fraud_description,
                metadata={
                    'order_id': order_id,
                    'user_id': user_id,
                    'amount': transaction.get('total_amount', transaction.get('amount', 0)),
                    'fraud_score': final_fraud_score
                },
                fraud_type=velocity_check.get('fraud_type', 'unknown') if velocity_check['is_fraud'] else 'ml_detected'
            )

        # Update statistics
        self.stats['total_transactions'] += 1
        if final_fraud_score >= 0.7:
            self.stats['fraud_detected'] += 1

        # Calculate processing time
        processing_time = time.time() - start_time

        logger.info(f"\n⏱️  Processing Time: {processing_time:.3f}s")
        logger.info(f"🎯 Final Decision: {triage}")
        logger.info("="*70)

        # Return result
        return {
            'order_id': order_id,
            'fraud_score': final_fraud_score,
            'ml_score': ml_score,
            'velocity_boost': velocity_boost,
            'redis_boost': redis_boost,
            'qdrant_boost': qdrant_boost,
            'recommendation': triage,
            'agent_analysis': agent_result,
            'processing_time_seconds': processing_time,
            'redis_context': redis_context,
            'qdrant_similar_cases': len(qdrant_context) if qdrant_context else 0
        }

    def _build_fraud_description(self, transaction: Dict[str, Any], fraud_score: float) -> str:
        """Build natural language description of fraud case"""
        parts = [
            f"Fraud score {fraud_score:.2f}",
            f"amount ${transaction.get('total_amount', transaction.get('amount', 0)):.2f}",
            f"payment {transaction.get('payment_method', 'unknown')}"
        ]

        if 'account_age_days' in transaction:
            parts.append(f"account age {transaction['account_age_days']} days")

        return " ".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        stats = self.stats.copy()

        if self.redis_memory:
            stats['redis_stats'] = self.redis_memory.get_stats()

        if self.qdrant_knowledge:
            stats['qdrant_stats'] = self.qdrant_knowledge.get_stats()

        if self.velocity_detector:
            stats['velocity_stats'] = self.velocity_detector.get_stats()

        return stats
