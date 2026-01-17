"""
Velocity Check Tool for Agno Agents
Real-time velocity fraud detection
"""

import logging
import json
import os
from typing import Optional

from agno.tools import tool

logger = logging.getLogger(__name__)


@tool
def velocity_check_tool(
    user_id: str,
    amount: float,
    payment_method: Optional[str] = None
) -> str:
    """Check for velocity fraud patterns in real-time.

    Enables agents to detect rapid-fire orders, card testing,
    and other velocity-based fraud patterns.

    Args:
        user_id: User ID to check
        amount: Transaction amount
        payment_method: Payment method used

    Returns:
        JSON string containing velocity check results
    """
    try:
        from src.fraud_detection.velocity_detector import VelocityFraudDetector

        # Initialize detector
        detector = VelocityFraudDetector()

        # Check velocity fraud
        check_result = detector.check_velocity_fraud(user_id, amount)

        # Get order count
        order_count = detector.get_user_order_count(user_id, minutes=60)

        result = {
            "user_id": user_id,
            "amount": amount,
            "velocity_check": check_result,
            "order_statistics": {
                "orders_last_hour": order_count,
                "average_amount": amount  # Simplified - could calculate actual average
            }
        }

        # Add risk assessment
        if check_result['is_fraud']:
            result['risk_assessment'] = {
                "risk_level": "HIGH",
                "recommendation": "BLOCK",
                "fraud_type": check_result['fraud_type'],
                "score_boost": check_result['score_boost']
            }
        elif order_count >= 3:
            result['risk_assessment'] = {
                "risk_level": "MEDIUM",
                "recommendation": "MANUAL_REVIEW",
                "reason": f"{order_count} orders in last hour"
            }
        else:
            result['risk_assessment'] = {
                "risk_level": "LOW",
                "recommendation": "ALLOW",
                "reason": "Normal velocity pattern"
            }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error checking velocity fraud: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "user_id": user_id
        })
