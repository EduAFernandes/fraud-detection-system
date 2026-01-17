"""
CrewAI Manager for Fraud Detection
Manages multi-agent AI system for fraud investigation
"""

import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path
from crewai import Agent, Task, Crew, Process
from src.fraud_detection.rate_limiter import rate_limited

logger = logging.getLogger(__name__)


class PromptLoader:
    """Load agent prompts from markdown files"""

    def __init__(self, prompts_dir: str = "src/agents/prompts"):
        """
        Initialize prompt loader

        Args:
            prompts_dir: Directory containing prompt markdown files
        """
        self.prompts_dir = Path(prompts_dir)

        if not self.prompts_dir.exists():
            logger.warning(f"⚠️  Prompts directory not found: {prompts_dir}")

    def load_prompt(self, agent_name: str) -> Dict[str, str]:
        """
        Load agent prompt from markdown file

        Args:
            agent_name: Agent name (e.g., "pattern_detector")

        Returns:
            Dict with 'role', 'goal', 'backstory'
        """
        filepath = self.prompts_dir / f"{agent_name}.md"

        if not filepath.exists():
            logger.warning(f"⚠️  Prompt file not found: {filepath}, using defaults")
            return self._get_default_prompt(agent_name)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse markdown sections
            sections = {}
            current_section = None
            current_content = []

            for line in content.split('\n'):
                if line.startswith('## '):
                    # Save previous section
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()

                    # Start new section
                    current_section = line[3:].strip().lower()
                    current_content = []
                elif current_section:
                    current_content.append(line)

            # Save last section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            return {
                'role': sections.get('role', ''),
                'goal': sections.get('goal', ''),
                'backstory': sections.get('backstory', '')
            }

        except Exception as e:
            logger.error(f"❌ Failed to load prompt {agent_name}: {e}")
            return self._get_default_prompt(agent_name)

    def _get_default_prompt(self, agent_name: str) -> Dict[str, str]:
        """Get hardcoded default prompts as fallback"""
        defaults = {
            'pattern_detector': {
                'role': 'Senior Fraud Pattern Detection Specialist',
                'goal': 'Analyze transaction data to identify known fraud patterns, velocity attacks, card testing, and behavioral anomalies',
                'backstory': 'Expert in recognizing fraud patterns with 15+ years of experience in velocity fraud, card testing, account takeover, and geographic anomalies.'
            },
            'risk_quantifier': {
                'role': 'Fraud Risk Quantification Expert',
                'goal': 'Calculate precise fraud probability scores based on ML predictions, pattern matches, and contextual factors',
                'backstory': 'Data scientist specializing in fraud risk scoring with 10+ years experience combining multiple fraud signals into unified risk scores.'
            },
            'decision_authority': {
                'role': 'Senior Fraud Decision Authority',
                'goal': 'Make final fraud determination based on all available evidence. Recommend ALLOW, BLOCK, or MANUAL_REVIEW',
                'backstory': 'Final decision maker with 20+ years of fraud prevention experience, balancing false positives vs fraud losses.'
            }
        }

        return defaults.get(agent_name, {
            'role': f'{agent_name} Agent',
            'goal': 'Analyze fraud data',
            'backstory': 'Fraud detection specialist'
        })


class FraudAgentCrew:
    """Multi-agent AI system for fraud investigation using CrewAI"""

    def __init__(self,
                 max_requests_per_minute: int = 20,
                 request_delay_seconds: float = 3.0,
                 prompts_dir: Optional[str] = None):
        """
        Initialize AI agent crew with rate limiting

        Args:
            max_requests_per_minute: Max OpenAI API calls per minute
            request_delay_seconds: Minimum seconds between API calls
            prompts_dir: Directory containing prompt files
        """
        logger.info("🔧 Initializing AI Agent Crew...")

        self.max_requests_per_minute = max_requests_per_minute
        self.request_delay_seconds = request_delay_seconds

        # Load prompts
        self.prompt_loader = PromptLoader(prompts_dir or "src/agents/prompts")

        # Setup agents
        self.setup_agents()

        logger.info("✅ AI Agents ready:")
        logger.info("   🤖 Pattern Detection Specialist")
        logger.info("   🤖 Risk Quantification Expert")
        logger.info("   🤖 Decision Authority")
        logger.info(f"   ⏱️  Rate limit: {max_requests_per_minute} req/min, {request_delay_seconds}s delay")

    def setup_agents(self):
        """Initialize specialized fraud investigation agents"""

        # Load prompts from files
        pattern_prompt = self.prompt_loader.load_prompt("pattern_detector")
        risk_prompt = self.prompt_loader.load_prompt("risk_quantifier")
        decision_prompt = self.prompt_loader.load_prompt("decision_authority")

        # Agent 1: Pattern Detection Specialist
        self.pattern_agent = Agent(
            role=pattern_prompt['role'],
            goal=pattern_prompt['goal'],
            backstory=pattern_prompt['backstory'],
            verbose=False,
            allow_delegation=False
        )

        # Agent 2: Risk Quantification Expert
        self.risk_agent = Agent(
            role=risk_prompt['role'],
            goal=risk_prompt['goal'],
            backstory=risk_prompt['backstory'],
            verbose=False,
            allow_delegation=False
        )

        # Agent 3: Decision Authority
        self.decision_agent = Agent(
            role=decision_prompt['role'],
            goal=decision_prompt['goal'],
            backstory=decision_prompt['backstory'],
            verbose=False,
            allow_delegation=False
        )

    @rate_limited(calls_per_minute=20, delay_seconds=3.0)
    def investigate(self,
                   transaction: Dict[str, Any],
                   ml_score: float,
                   velocity_check: Optional[Dict[str, Any]] = None,
                   redis_context: Optional[list] = None,
                   qdrant_context: Optional[list] = None) -> Dict[str, Any]:
        """
        Run multi-agent investigation on high-risk transaction

        RATE LIMITED: Max 20 calls/minute with 3s delay between calls

        Args:
            transaction: Transaction data
            ml_score: ML fraud score
            velocity_check: Velocity fraud check results
            redis_context: Redis memory context
            qdrant_context: Qdrant similar cases

        Returns:
            Investigation result with recommendation
        """

        # Build context string
        context_parts = []

        # Velocity fraud context
        if velocity_check and velocity_check.get('is_fraud'):
            context_parts.append(f"\n⚠️  VELOCITY FRAUD DETECTED: {velocity_check['reason']}")

        # Redis memory context
        if redis_context:
            context_parts.append("\n📊 REDIS MEMORY:")
            for ctx in redis_context:
                context_parts.append(f"   • {ctx}")

        # Qdrant RAG context
        if qdrant_context:
            context_parts.append("\n🔍 SIMILAR FRAUD CASES:")
            for case in qdrant_context[:3]:  # Top 3 similar cases
                context_parts.append(
                    f"   • {case['fraud_type']} ({case['similarity_score']:.0%} similar): "
                    f"{case['description']}"
                )

        context_str = "".join(context_parts)

        # Task 1: Pattern Analysis
        pattern_task = Task(
            description=f"""Analyze this transaction for fraud patterns:

TRANSACTION DATA:
• Order ID: {transaction['order_id']}
• User ID: {transaction.get('user_id', 'unknown')}
• Amount: ${transaction.get('total_amount', transaction.get('amount', 0)):.2f}
• Payment Method: {transaction.get('payment_method', 'unknown')}
• Account Age: {transaction.get('account_age_days', 'unknown')} days
• Total Orders: {transaction.get('total_orders', 'unknown')}
• ML Fraud Score: {ml_score:.3f}{context_str}

Identify ALL red flags and suspicious patterns. Be specific and concise.""",
            agent=self.pattern_agent,
            expected_output="Detailed list of fraud indicators and patterns detected"
        )

        # Task 2: Risk Assessment
        risk_task = Task(
            description="""Based on the patterns identified, provide:

1. Risk Rating: LOW / MEDIUM / HIGH / CRITICAL
2. Fraud Probability: X% (0-100%)
3. Confidence Level: X% (how confident are you?)
4. Key Risk Factors: Top 3 concerns

Be quantitative and precise.""",
            agent=self.risk_agent,
            expected_output="Structured risk assessment with ratings and percentages",
            context=[pattern_task]
        )

        # Task 3: Final Decision
        decision_task = Task(
            description="""Make final recommendation:

OPTIONS:
• APPROVE - Allow transaction (low risk)
• MANUAL_REVIEW - Flag for human review (medium risk)
• BLOCK - Reject immediately (high risk)

Provide clear justification for your decision.""",
            agent=self.decision_agent,
            expected_output="Final decision with justification",
            context=[pattern_task, risk_task]
        )

        # Execute crew
        crew = Crew(
            agents=[self.pattern_agent, self.risk_agent, self.decision_agent],
            tasks=[pattern_task, risk_task, decision_task],
            process=Process.sequential,
            verbose=False
        )

        try:
            result = crew.kickoff()

            # Parse result
            return {
                'recommendation': self._extract_recommendation(str(result)),
                'analysis': str(result),
                'pattern_analysis': pattern_task.output.raw_output if hasattr(pattern_task, 'output') else '',
                'risk_assessment': risk_task.output.raw_output if hasattr(risk_task, 'output') else '',
                'decision': decision_task.output.raw_output if hasattr(decision_task, 'output') else ''
            }

        except Exception as e:
            logger.error(f"❌ Agent investigation failed: {e}")
            return {
                'recommendation': 'MANUAL_REVIEW',
                'analysis': f'Investigation failed: {str(e)}',
                'error': str(e)
            }

    def _extract_recommendation(self, result: str) -> str:
        """Extract recommendation from agent output"""
        result_upper = result.upper()

        if 'BLOCK' in result_upper or 'REJECT' in result_upper:
            return 'BLOCK'
        elif 'MANUAL_REVIEW' in result_upper or 'REVIEW' in result_upper:
            return 'MANUAL_REVIEW'
        elif 'APPROVE' in result_upper or 'ALLOW' in result_upper:
            return 'APPROVE'
        else:
            # Default to manual review if unclear
            return 'MANUAL_REVIEW'
