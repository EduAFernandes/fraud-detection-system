"""
User Reputation Tool for Agno Agents
Enables agents to check user and IP reputation from Redis
"""

import logging
import json
import os
from typing import Optional, Dict, Any

from agno.tools import tool

logger = logging.getLogger(__name__)


@tool
def user_reputation_tool(
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> str:
    """Check user or IP reputation from Redis memory.

    Enables agents to check if a user or IP has been flagged for fraud,
    view their transaction history, and assess reputation scores.

    Args:
        user_id: User ID to check reputation
        ip_address: IP address to check reputation

    Returns:
        JSON string containing reputation data or error message
    """
    try:
        from src.memory.redis_memory import RedisMemoryManager

        # Initialize Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        memory = RedisMemoryManager(redis_url)

        reputation_data = {
            "query": {
                "user_id": user_id,
                "ip_address": ip_address
            },
            "findings": []
        }

        # Check user reputation
        if user_id:
            # Check if user is flagged
            user_status = memory.is_user_flagged(user_id)

            if user_status['is_flagged']:
                reputation_data['findings'].append({
                    "type": "user_flagged",
                    "severity": "HIGH",
                    "details": user_status
                })

            # Get transaction count
            tx_count_hour = memory.get_user_transaction_count(user_id, minutes=60)
            tx_count_day = memory.get_user_transaction_count(user_id, minutes=1440)

            reputation_data['transaction_velocity'] = {
                "last_hour": tx_count_hour,
                "last_24_hours": tx_count_day
            }

            if tx_count_hour >= 5:
                reputation_data['findings'].append({
                    "type": "high_velocity",
                    "severity": "MEDIUM",
                    "details": f"{tx_count_hour} transactions in last hour"
                })

            # Get transaction history
            tx_history = memory.get_user_transaction_history(user_id, limit=5)
            reputation_data['recent_transactions'] = tx_history

        # Check IP reputation
        if ip_address:
            ip_status = memory.is_ip_flagged(ip_address)

            if ip_status['is_flagged']:
                reputation_data['findings'].append({
                    "type": "ip_flagged",
                    "severity": "HIGH",
                    "details": ip_status
                })

        # Calculate risk score
        risk_score = 0.0
        if any(f['type'] in ['user_flagged', 'ip_flagged'] for f in reputation_data['findings']):
            risk_score += 0.5
        if any(f['type'] == 'high_velocity' for f in reputation_data['findings']):
            risk_score += 0.3

        reputation_data['risk_assessment'] = {
            "risk_score": min(1.0, risk_score),
            "risk_level": "HIGH" if risk_score >= 0.7 else "MEDIUM" if risk_score >= 0.4 else "LOW",
            "findings_count": len(reputation_data['findings']),
            "recommendation": "BLOCK" if risk_score >= 0.7 else "MANUAL_REVIEW" if risk_score >= 0.4 else "ALLOW"
        }

        return json.dumps(reputation_data, indent=2)

    except Exception as e:
        logger.error(f"Error checking user reputation: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "user_id": user_id,
            "ip_address": ip_address
        })
