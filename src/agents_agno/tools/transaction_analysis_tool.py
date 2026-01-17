"""
Transaction Analysis Tool for Agno Agents
Detailed transaction pattern analysis
"""

import logging
import json
from typing import Dict, Any

from agno.tools import tool

logger = logging.getLogger(__name__)


@tool
def transaction_analysis_tool(
    transaction_data: str  # JSON string of transaction
) -> str:
    """Analyze transaction for suspicious patterns and anomalies.

    Enables agents to perform deep analysis of transaction characteristics,
    identifying red flags and risk indicators.

    Args:
        transaction_data: JSON string containing transaction details

    Returns:
        JSON string containing detailed analysis results
    """
    try:
        # Parse transaction data
        transaction = json.loads(transaction_data)

        # Extract key fields
        amount = transaction.get('amount', transaction.get('total_amount', 0))
        payment_method = transaction.get('payment_method', 'unknown')
        account_age = transaction.get('account_age_days', 0)
        total_orders = transaction.get('total_orders', 0)
        user_id = transaction.get('user_id', 'unknown')

        # Analyze patterns
        risk_factors = []
        risk_score = 0.0

        # Amount analysis
        if amount < 10:
            risk_factors.append({
                "factor": "Small transaction amount",
                "value": f"${amount:.2f}",
                "risk_level": "MEDIUM",
                "reason": "Possible card testing"
            })
            risk_score += 0.2

        if amount > 500:
            risk_factors.append({
                "factor": "Large transaction amount",
                "value": f"${amount:.2f}",
                "risk_level": "MEDIUM",
                "reason": "High-value transaction requires verification"
            })
            risk_score += 0.15

        # Account age analysis
        if account_age < 7:
            risk_factors.append({
                "factor": "New account",
                "value": f"{account_age} days old",
                "risk_level": "HIGH" if account_age < 1 else "MEDIUM",
                "reason": "New accounts have higher fraud risk"
            })
            risk_score += 0.3 if account_age < 1 else 0.2

        # Order history analysis
        if total_orders == 0:
            risk_factors.append({
                "factor": "First order",
                "value": "0 previous orders",
                "risk_level": "MEDIUM",
                "reason": "No transaction history for this user"
            })
            risk_score += 0.15

        # Payment method analysis
        if payment_method == 'credit_card':
            risk_factors.append({
                "factor": "Credit card payment",
                "value": payment_method,
                "risk_level": "LOW",
                "reason": "Credit cards have higher fraud rates than other methods"
            })
            risk_score += 0.05

        # Compile analysis
        analysis = {
            "transaction_id": transaction.get('order_id', 'unknown'),
            "user_id": user_id,
            "risk_factors": risk_factors,
            "risk_score": min(1.0, risk_score),
            "risk_level": "HIGH" if risk_score >= 0.7 else "MEDIUM" if risk_score >= 0.4 else "LOW",
            "recommendation": {
                "action": "BLOCK" if risk_score >= 0.7 else "MANUAL_REVIEW" if risk_score >= 0.4 else "ALLOW",
                "confidence": "HIGH" if len(risk_factors) >= 3 else "MEDIUM" if len(risk_factors) >= 2 else "LOW",
                "reasoning": f"Identified {len(risk_factors)} risk factors with cumulative score {risk_score:.2f}"
            },
            "key_metrics": {
                "amount": amount,
                "account_age_days": account_age,
                "total_orders": total_orders,
                "payment_method": payment_method
            }
        }

        return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Error analyzing transaction: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "error_type": type(e).__name__
        })
