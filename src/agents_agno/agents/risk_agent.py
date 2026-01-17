"""
Risk Assessment Agent for Fraud Detection
Quantitative risk scoring and analysis
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from src.agents_agno.base_agent import FraudDetectionBaseAgent

logger = logging.getLogger(__name__)


class RiskAssessmentAgent(FraudDetectionBaseAgent):
    """Fraud Risk Quantification Expert.

    Analyzes investigation findings and calculates precise fraud probability
    scores with statistical rigor. Provides quantitative risk assessment
    and confidence scores.
    """

    def __init__(self, model_name: Optional[str] = None):
        """Initialize Risk Assessment Agent.

        Args:
            model_name: Model to use (default: gpt-4o-mini)
        """
        # Load prompt from markdown file
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "risk_assessment.md"
        instructions = self._load_prompt(prompt_path)

        # No specialized tools needed - analyzes investigation results
        super().__init__(
            agent_id="fraud_risk_assessment_agent",
            instructions=instructions,
            model_name=model_name,
            enable_reasoning=True,  # Enable chain-of-thought reasoning
            enable_memory=True,  # Enable Redis memory
            specialized_tools=None  # Risk agent analyzes, doesn't need tools
        )

        logger.info("✅ RiskAssessmentAgent initialized")

    def _load_prompt(self, prompt_path: Path) -> str:
        """Load agent instructions from markdown file."""
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_path}, using default")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Fallback prompt if markdown file not found."""
        return """You are a Senior Fraud Risk Quantification Expert.

Your mission: Convert investigation findings into precise, quantifiable risk scores.

Risk Scoring Framework:
- ML Fraud Score: Weight 0.25
- Velocity Fraud: Weight 0.20
- Historical Fraud: Weight 0.30
- Similar Cases: Weight 0.15
- Transaction Anomalies: Weight 0.10

Calculate:
1. Precise fraud probability (0.00 - 1.00)
2. Risk level (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
3. Confidence score (0-100%)
4. Top 3 risk factors with impact scores

Be precise, quantitative, and evidence-based."""

    async def assess_risk(
        self,
        investigation_results: Dict[str, Any],
        ml_score: float,
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess fraud risk based on investigation findings.

        Args:
            investigation_results: Results from Investigation Agent
            ml_score: ML fraud score (0-1)
            transaction: Original transaction data

        Returns:
            Risk assessment with fraud probability and confidence
        """
        try:
            # Build risk assessment request
            request = {
                "investigation_findings": investigation_results,
                "ml_fraud_score": ml_score,
                "transaction_data": transaction,
                "task": """Analyze the investigation findings and calculate:
                1. Precise fraud probability (0.00 - 1.00)
                2. Risk level classification
                3. Confidence score (0-100%)
                4. Top 3 risk factors with impact
                5. Score breakdown showing calculation

                Use the risk scoring framework from your instructions."""
            }

            # Process with metrics tracking
            result = await self.process_request_with_metrics(request)

            return result

        except Exception as e:
            logger.error(f"Risk assessment failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "agent_id": self.agent_id,
                "success": False
            }
