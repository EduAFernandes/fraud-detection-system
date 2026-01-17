"""
Agno-based Fraud Detection Agents
Production-grade fraud detection with async processing, Redis memory, and specialized tools
"""

from src.agents_agno.base_agent import FraudDetectionBaseAgent
from src.agents_agno.fraud_agent_manager import FraudAgentManager
from src.agents_agno.agents import (
    InvestigationAgent,
    RiskAssessmentAgent,
    DecisionAgent
)

__version__ = "2.0.0"
__all__ = [
    "FraudDetectionBaseAgent",
    "FraudAgentManager",
    "InvestigationAgent",
    "RiskAssessmentAgent",
    "DecisionAgent"
]
