"""
Agno-CrewAI Adapter
Provides CrewAI-compatible interface for Agno agents
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from src.agents_agno.fraud_agent_manager import FraudAgentManager

logger = logging.getLogger(__name__)


class AgnoCrewAdapter:
    """Adapter to use Agno agents with CrewAI-style interface.

    This allows seamless integration with existing fraud orchestrator
    that expects CrewAI's interface.
    """

    def __init__(
        self,
        max_requests_per_minute: int = 20,
        request_delay_seconds: float = 3.0,
        prompts_dir: Optional[str] = None
    ):
        """Initialize Agno agents with CrewAI-compatible interface.

        Args:
            max_requests_per_minute: Rate limiting (preserved for compatibility)
            request_delay_seconds: Delay between calls (preserved for compatibility)
            prompts_dir: Prompt directory (preserved for compatibility)
        """
        logger.info("🔧 Initializing Agno Agent System (via CrewAI adapter)...")

        # Initialize Agno agent manager
        self.manager = FraudAgentManager()

        # Store rate limiting params (Agno handles internally)
        self.max_requests_per_minute = max_requests_per_minute
        self.request_delay_seconds = request_delay_seconds

        logger.info("✅ Agno agents ready (CrewAI-compatible interface):")
        logger.info("   🤖 Investigation Agent (5 tools)")
        logger.info("   🤖 Risk Assessment Agent")
        logger.info("   🤖 Decision Agent")
        logger.info(f"   ⏱️  Rate limit: {max_requests_per_minute} req/min")

    def investigate(
        self,
        transaction: Dict[str, Any],
        ml_score: float,
        velocity_check: Optional[Dict[str, Any]] = None,
        redis_context: Optional[list] = None,
        qdrant_context: Optional[list] = None
    ) -> Dict[str, Any]:
        """Run fraud investigation (synchronous wrapper for async agents).

        This method provides CrewAI-compatible interface while using
        Agno agents under the hood.

        Args:
            transaction: Transaction data
            ml_score: ML fraud score
            velocity_check: Velocity fraud check results
            redis_context: Redis memory context
            qdrant_context: Qdrant similar cases

        Returns:
            Investigation result with recommendation (CrewAI-compatible format)
        """
        try:
            # Run async investigation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self.manager.investigate_fraud(
                    transaction=transaction,
                    ml_score=ml_score,
                    velocity_check=velocity_check,
                    redis_context=redis_context,
                    qdrant_context=qdrant_context
                )
            )

            loop.close()

            # Convert Agno result to CrewAI-compatible format
            if not result.get('success', True):
                # Error occurred
                return {
                    'recommendation': 'MANUAL_REVIEW',
                    'analysis': f"Investigation error: {result.get('error', 'Unknown error')}",
                    'error': result.get('error')
                }

            # Extract recommendation from decision agent's response
            decision_response = result.get('decision', {}).get('response', '')

            # Parse recommendation
            recommendation = self._extract_recommendation(str(decision_response))

            # Format response to match CrewAI interface
            return {
                'recommendation': recommendation,
                'analysis': self._format_analysis(result),
                'investigation': result.get('investigation', {}).get('response', ''),
                'risk_assessment': result.get('risk_assessment', {}).get('response', ''),
                'decision': decision_response,
                'processing_time': result.get('processing_time', 0),
                'agents_used': result.get('agents_used', [])
            }

        except Exception as e:
            logger.error(f"❌ Agno investigation failed: {e}", exc_info=True)
            return {
                'recommendation': 'MANUAL_REVIEW',
                'analysis': f'Investigation failed: {str(e)}',
                'error': str(e)
            }

    def _extract_recommendation(self, result: str) -> str:
        """Extract recommendation from agent output (CrewAI-compatible)."""
        result_upper = result.upper()

        if 'BLOCK' in result_upper:
            return 'BLOCK'
        elif 'MANUAL_REVIEW' in result_upper or 'REVIEW' in result_upper:
            return 'MANUAL_REVIEW'
        elif 'APPROVE' in result_upper or 'ALLOW' in result_upper:
            return 'APPROVE'
        else:
            # Default to manual review if unclear
            return 'MANUAL_REVIEW'

    def _format_analysis(self, result: Dict[str, Any]) -> str:
        """Format multi-agent result into single analysis string."""
        parts = []

        # Investigation findings
        if result.get('investigation'):
            parts.append("=== INVESTIGATION ===")
            parts.append(str(result['investigation'].get('response', '')))

        # Risk assessment
        if result.get('risk_assessment'):
            parts.append("\n=== RISK ASSESSMENT ===")
            parts.append(str(result['risk_assessment'].get('response', '')))

        # Decision
        if result.get('decision'):
            parts.append("\n=== DECISION ===")
            parts.append(str(result['decision'].get('response', '')))

        # Processing info
        processing_time = result.get('processing_time', 0)
        parts.append(f"\n⏱️ Processing time: {processing_time:.2f}s")

        return "\n".join(parts)

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return self.manager.get_metrics()
