"""
Decision Agent for Fraud Detection
Final fraud determination and action recommendation
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from src.agents_agno.base_agent import FraudDetectionBaseAgent
from src.agents_agno.tools.fraud_decision_tool import fraud_decision_tool

logger = logging.getLogger(__name__)


class DecisionAgent(FraudDetectionBaseAgent):
    """Senior Fraud Decision Authority.

    Makes final fraud decisions based on investigation and risk assessment.
    Has authority to APPROVE, MANUAL_REVIEW, or BLOCK transactions.
    Records all decisions in the database.

    Tools:
        - fraud_decision_tool: Record decisions in database
    """

    def __init__(self, model_name: Optional[str] = None):
        """Initialize Decision Agent.

        Args:
            model_name: Model to use (default: gpt-4o-mini)
        """
        # Load prompt from markdown file
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "decision.md"
        instructions = self._load_prompt(prompt_path)

        # Only needs fraud_decision_tool to record decisions
        tools = [fraud_decision_tool]

        super().__init__(
            agent_id="fraud_decision_agent",
            instructions=instructions,
            model_name=model_name,
            enable_reasoning=True,  # Enable chain-of-thought reasoning
            enable_memory=True,  # Enable Redis memory
            specialized_tools=tools
        )

        logger.info("✅ DecisionAgent initialized with fraud_decision_tool")

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
        return """You are the Senior Fraud Decision Authority.

Your mission: Make final fraud decisions and record them in the database.

Decision Options:
- APPROVE: Transaction appears legitimate
- MANUAL_REVIEW: Uncertain, needs human review
- BLOCK: High fraud probability, reject immediately

Decision Matrix:
- Risk 0.85-1.00: BLOCK (critical fraud risk)
- Risk 0.70-0.84 + High Confidence: BLOCK
- Risk 0.70-0.84 + Low Confidence: MANUAL_REVIEW
- Risk 0.50-0.69: MANUAL_REVIEW
- Risk 0.30-0.49: APPROVE (low risk)
- Risk 0.00-0.29: APPROVE (minimal risk)

CRITICAL: Use fraud_decision_tool to record every decision in the database!

Provide:
1. Clear decision (APPROVE/MANUAL_REVIEW/BLOCK)
2. Confidence score (0-100%)
3. Justification (2-3 sentences)
4. Top 3 factors influencing decision
5. Next actions"""

    async def make_decision(
        self,
        investigation_results: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make final fraud decision.

        Args:
            investigation_results: Investigation Agent findings
            risk_assessment: Risk Assessment Agent analysis
            transaction: Original transaction data

        Returns:
            Final decision with reasoning and next actions
        """
        try:
            # Build decision request
            request = {
                "investigation_findings": investigation_results,
                "risk_assessment": risk_assessment,
                "transaction_data": transaction,
                "task": """Review all evidence and make your final decision:

                1. Choose ONE decision: APPROVE, MANUAL_REVIEW, or BLOCK
                2. Provide confidence score (0-100%)
                3. Justify your decision (2-3 sentences)
                4. List top 3 factors that influenced this decision
                5. Specify next actions

                IMPORTANT: After making your decision, use fraud_decision_tool to record it in the database!

                Required fields for fraud_decision_tool:
                - order_id: from transaction data
                - decision: APPROVE/MANUAL_REVIEW/BLOCK
                - confidence: your confidence score (0.0-1.0)
                - reasoning: your justification
                - fraud_indicators: list of key fraud indicators found"""
            }

            # Process with metrics tracking
            result = await self.process_request_with_metrics(request)

            return result

        except Exception as e:
            logger.error(f"Decision making failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "agent_id": self.agent_id,
                "success": False
            }
