"""
Fraud Agent Manager - Orchestrates multi-agent fraud detection
Coordinates Investigation, Risk Assessment, and Decision agents
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.agents_agno.agents import InvestigationAgent, RiskAssessmentAgent, DecisionAgent

logger = logging.getLogger(__name__)


class FraudAgentManager:
    """Orchestrates multi-agent fraud detection workflow.

    Manages the collaboration between three specialized agents:
    1. Investigation Agent - Gathers evidence using all tools
    2. Risk Assessment Agent - Calculates fraud probability
    3. Decision Agent - Makes final determination

    Features:
        - Async processing for high throughput
        - Sequential agent workflow with context passing
        - Performance metrics tracking
        - Error handling and recovery
        - Rate limiting support
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        enable_parallel: bool = False
    ):
        """Initialize Fraud Agent Manager.

        Args:
            model_name: Model to use for all agents (default: gpt-4o-mini)
            enable_parallel: Enable parallel processing (experimental)
        """
        logger.info("🔧 Initializing Fraud Agent Manager...")

        # Initialize all three agents
        self.investigation_agent = InvestigationAgent(model_name=model_name)
        self.risk_agent = RiskAssessmentAgent(model_name=model_name)
        self.decision_agent = DecisionAgent(model_name=model_name)

        self.enable_parallel = enable_parallel

        # Performance tracking
        self.metrics = {
            "total_investigations": 0,
            "successful": 0,
            "blocked": 0,
            "approved": 0,
            "manual_reviews": 0,
            "errors": 0,
            "avg_processing_time": 0.0,
            "total_processing_time": 0.0
        }

        logger.info("✅ Fraud Agent Manager initialized:")
        logger.info("   🤖 Investigation Agent (5 tools)")
        logger.info("   🤖 Risk Assessment Agent")
        logger.info("   🤖 Decision Agent (fraud_decision_tool)")

    async def investigate_fraud(
        self,
        transaction: Dict[str, Any],
        ml_score: float,
        velocity_check: Optional[Dict[str, Any]] = None,
        redis_context: Optional[List[str]] = None,
        qdrant_context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Run complete fraud investigation with all three agents.

        This is the main entry point for fraud detection. It orchestrates
        the sequential workflow:
        1. Investigation Agent gathers evidence
        2. Risk Agent calculates fraud probability
        3. Decision Agent makes final call

        Args:
            transaction: Transaction data to investigate
            ml_score: ML fraud score (0-1)
            velocity_check: Optional velocity fraud check results
            redis_context: Optional Redis memory context
            qdrant_context: Optional similar cases from Qdrant

        Returns:
            Complete fraud analysis with final decision
        """
        start_time = datetime.now()
        order_id = transaction.get('order_id', 'unknown')

        try:
            logger.info(f"🔍 Starting fraud investigation for order {order_id}")

            # Add context to transaction
            enhanced_transaction = {
                **transaction,
                "ml_score": ml_score,
                "velocity_check": velocity_check,
                "redis_context": redis_context,
                "qdrant_context": qdrant_context
            }

            # Step 1: Investigation (gather evidence)
            logger.info(f"   📊 Step 1/3: Running investigation...")
            investigation_result = await self.investigation_agent.investigate(enhanced_transaction)

            if not investigation_result.get('success', True):
                raise Exception(f"Investigation failed: {investigation_result.get('error')}")

            # Step 2: Risk Assessment (calculate fraud probability)
            logger.info(f"   📈 Step 2/3: Assessing risk...")
            risk_result = await self.risk_agent.assess_risk(
                investigation_results=investigation_result,
                ml_score=ml_score,
                transaction=enhanced_transaction
            )

            if not risk_result.get('success', True):
                raise Exception(f"Risk assessment failed: {risk_result.get('error')}")

            # Step 3: Decision (make final call)
            logger.info(f"   ⚖️  Step 3/3: Making decision...")
            decision_result = await self.decision_agent.make_decision(
                investigation_results=investigation_result,
                risk_assessment=risk_result,
                transaction=enhanced_transaction
            )

            if not decision_result.get('success', True):
                raise Exception(f"Decision making failed: {decision_result.get('error')}")

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            # Compile final result
            final_result = {
                "order_id": order_id,
                "success": True,
                "investigation": investigation_result,
                "risk_assessment": risk_result,
                "decision": decision_result,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "agents_used": ["investigation", "risk_assessment", "decision"]
            }

            # Update metrics
            self._update_metrics(decision_result, processing_time)

            logger.info(f"✅ Investigation complete for {order_id} in {processing_time:.2f}s")

            return final_result

        except Exception as e:
            logger.error(f"❌ Investigation failed for {order_id}: {e}", exc_info=True)

            self.metrics["errors"] += 1
            self.metrics["total_investigations"] += 1

            return {
                "order_id": order_id,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }

    async def batch_investigate(
        self,
        transactions: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Process multiple transactions concurrently.

        Args:
            transactions: List of transactions to investigate
            max_concurrent: Maximum concurrent investigations

        Returns:
            List of investigation results
        """
        logger.info(f"🔄 Starting batch investigation of {len(transactions)} transactions")

        # Create investigation tasks
        tasks = []
        for tx in transactions:
            ml_score = tx.get('ml_score', 0.5)  # Default if not provided
            task = self.investigate_fraud(
                transaction=tx,
                ml_score=ml_score
            )
            tasks.append(task)

        # Process with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_investigate(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(*[bounded_investigate(task) for task in tasks])

        logger.info(f"✅ Batch investigation complete: {len(results)} results")

        return results

    def _update_metrics(self, decision_result: Dict[str, Any], processing_time: float):
        """Update performance metrics."""
        self.metrics["total_investigations"] += 1
        self.metrics["successful"] += 1
        self.metrics["total_processing_time"] += processing_time

        # Update average
        self.metrics["avg_processing_time"] = (
            self.metrics["total_processing_time"] / self.metrics["successful"]
        )

        # Track decision types
        decision_text = str(decision_result.get('response', ''))
        if 'BLOCK' in decision_text:
            self.metrics["blocked"] += 1
        elif 'APPROVE' in decision_text:
            self.metrics["approved"] += 1
        elif 'MANUAL_REVIEW' in decision_text:
            self.metrics["manual_reviews"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get manager performance metrics.

        Returns:
            Dictionary containing:
            - Total investigations
            - Success/error counts
            - Decision breakdowns
            - Processing time statistics
            - Agent health status
        """
        return {
            "manager_metrics": self.metrics,
            "agent_health": {
                "investigation_agent": self.investigation_agent.get_health_status(),
                "risk_agent": self.risk_agent.get_health_status(),
                "decision_agent": self.decision_agent.get_health_status()
            },
            "timestamp": datetime.now().isoformat()
        }

    async def reset_metrics(self):
        """Reset all metrics and agent performance data."""
        self.metrics = {
            "total_investigations": 0,
            "successful": 0,
            "blocked": 0,
            "approved": 0,
            "manual_reviews": 0,
            "errors": 0,
            "avg_processing_time": 0.0,
            "total_processing_time": 0.0
        }

        # Reset agent metrics
        await self.investigation_agent.reset_metrics()
        await self.risk_agent.reset_metrics()
        await self.decision_agent.reset_metrics()

        logger.info("📊 Metrics reset for all agents")
