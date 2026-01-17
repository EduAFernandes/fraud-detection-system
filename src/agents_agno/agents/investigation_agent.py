"""
Investigation Agent for Fraud Detection
Comprehensive fraud investigation using all available tools
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from src.agents_agno.base_agent import FraudDetectionBaseAgent
from src.agents_agno.tools.fraud_history_tool import fraud_history_tool
from src.agents_agno.tools.user_reputation_tool import user_reputation_tool
from src.agents_agno.tools.similar_cases_tool import similar_cases_tool
from src.agents_agno.tools.velocity_check_tool import velocity_check_tool
from src.agents_agno.tools.transaction_analysis_tool import transaction_analysis_tool

logger = logging.getLogger(__name__)


class InvestigationAgent(FraudDetectionBaseAgent):
    """Fraud Investigation Specialist Agent.

    Equipped with all 6 fraud detection tools to conduct comprehensive
    investigations. This agent gathers evidence, checks historical data,
    and identifies suspicious patterns.

    Tools:
        - fraud_history_tool: Query historical fraud data
        - user_reputation_tool: Check Redis reputation
        - similar_cases_tool: Find similar fraud cases (RAG)
        - velocity_check_tool: Real-time velocity detection
        - transaction_analysis_tool: Deep transaction analysis
    """

    def __init__(self, model_name: Optional[str] = None):
        """Initialize Investigation Agent with all tools.

        Args:
            model_name: Model to use (default: gpt-4o-mini)
        """
        # Load prompt from markdown file
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "investigation.md"
        instructions = self._load_prompt(prompt_path)

        # Initialize with all investigation tools
        tools = [
            fraud_history_tool,
            user_reputation_tool,
            similar_cases_tool,
            velocity_check_tool,
            transaction_analysis_tool
        ]

        super().__init__(
            agent_id="fraud_investigation_agent",
            instructions=instructions,
            model_name=model_name,
            enable_reasoning=True,  # Enable chain-of-thought reasoning
            enable_memory=True,  # Enable Redis memory
            specialized_tools=tools
        )

        logger.info("✅ InvestigationAgent initialized with 5 tools")

    def _load_prompt(self, prompt_path: Path) -> str:
        """Load agent instructions from markdown file.

        Args:
            prompt_path: Path to prompt markdown file

        Returns:
            Prompt instructions as string
        """
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_path}, using default")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Fallback prompt if markdown file not found."""
        return """You are a Senior Fraud Investigation Specialist.

Your mission: Conduct comprehensive fraud investigations using all available tools.

ALWAYS use these tools to gather evidence:
1. fraud_history_tool - Check user's fraud history
2. user_reputation_tool - Check Redis reputation flags
3. similar_cases_tool - Find similar fraud cases
4. velocity_check_tool - Detect velocity fraud
5. transaction_analysis_tool - Analyze transaction patterns

Provide detailed investigation reports with all findings."""

    async def investigate(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive fraud investigation on transaction.

        This method processes the transaction through the agent's investigation
        pipeline, using all available tools to gather evidence.

        Args:
            transaction: Transaction data dictionary

        Returns:
            Investigation results with findings and evidence
        """
        try:
            # Build investigation request
            request = {
                "transaction": transaction,
                "task": "Investigate this transaction for fraud using ALL available tools",
                "required_tools": [
                    "fraud_history_tool (check user history)",
                    "user_reputation_tool (check Redis flags)",
                    "similar_cases_tool (find similar fraud)",
                    "velocity_check_tool (check velocity fraud)",
                    "transaction_analysis_tool (deep analysis)"
                ]
            }

            # Process with metrics tracking
            result = await self.process_request_with_metrics(request)

            return result

        except Exception as e:
            logger.error(f"Investigation failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "agent_id": self.agent_id,
                "success": False
            }
