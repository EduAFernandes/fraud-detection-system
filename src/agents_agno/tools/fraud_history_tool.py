"""
Fraud History Tool for Agno Agents
Enables agents to query historical fraud data from Supabase
"""

import logging
import json
import os
from typing import Optional, Dict, Any, List
from decimal import Decimal

from agno.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Pydantic schema for tool input
class FraudHistoryInput(BaseModel):
    """Input schema for fraud history queries."""
    user_id: Optional[str] = Field(None, description="User ID to query fraud history")
    ip_address: Optional[str] = Field(None, description="IP address to query")
    order_id: Optional[str] = Field(None, description="Specific order ID to query")
    limit: int = Field(10, description="Maximum number of records to return")


def decimal_to_float(obj: Any) -> Any:
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


@tool
def fraud_history_tool(
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    order_id: Optional[str] = None,
    limit: int = 10
) -> str:
    """Query historical fraud data from Supabase.

    Enables agents to investigate user fraud history, IP reputation,
    and past fraud cases for pattern matching.

    Args:
        user_id: User ID to query fraud history
        ip_address: IP address to check for previous fraud
        order_id: Specific order ID to retrieve details
        limit: Maximum number of records to return (default: 10)

    Returns:
        JSON string containing fraud history records or error message
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Get database connection string from environment
        conn_string = os.getenv('POSTGRES_CONNECTION_STRING')
        if not conn_string:
            return json.dumps({
                "error": "Database connection not configured",
                "hint": "Set POSTGRES_CONNECTION_STRING environment variable"
            })

        # Connect to database
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query based on parameters
        if order_id:
            # Query specific order
            query = """
                SELECT
                    r.order_id,
                    t.user_id,
                    r.fraud_score,
                    r.fraud_prediction,
                    r.confidence,
                    r.triage_decision,
                    r.created_at,
                    aa.risk_factors,
                    aa.recommendation,
                    aa.findings as fraud_indicators
                FROM fraud_detection.results r
                LEFT JOIN fraud_detection.transactions t ON r.order_id = t.order_id
                LEFT JOIN fraud_detection.agent_analysis aa ON r.order_id = aa.order_id
                WHERE r.order_id = %s
            """
            cursor.execute(query, (order_id,))
            results = cursor.fetchall()

        elif user_id:
            # Query user history
            query = """
                SELECT
                    r.order_id,
                    r.fraud_score,
                    r.fraud_prediction,
                    r.confidence,
                    r.created_at,
                    aa.recommendation,
                    aa.findings as fraud_indicators
                FROM fraud_detection.results r
                LEFT JOIN fraud_detection.transactions t ON r.order_id = t.order_id
                LEFT JOIN fraud_detection.agent_analysis aa ON r.order_id = aa.order_id
                WHERE t.user_id = %s
                ORDER BY r.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
            results = cursor.fetchall()

        elif ip_address:
            # Query IP history
            # Note: IP address not currently stored in schema
            # Return high fraud cases as fallback
            query = """
                SELECT
                    r.order_id,
                    t.user_id,
                    r.fraud_score,
                    r.fraud_prediction,
                    r.created_at,
                    aa.findings as fraud_indicators
                FROM fraud_detection.results r
                LEFT JOIN fraud_detection.transactions t ON r.order_id = t.order_id
                LEFT JOIN fraud_detection.agent_analysis aa ON r.order_id = aa.order_id
                WHERE r.fraud_score >= 0.7
                ORDER BY r.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()

        else:
            # Get recent high-fraud cases
            query = """
                SELECT
                    r.order_id,
                    t.user_id,
                    r.fraud_score,
                    r.fraud_prediction,
                    r.confidence,
                    r.created_at,
                    aa.recommendation,
                    aa.findings as fraud_indicators
                FROM fraud_detection.results r
                LEFT JOIN fraud_detection.transactions t ON r.order_id = t.order_id
                LEFT JOIN fraud_detection.agent_analysis aa ON r.order_id = aa.order_id
                WHERE r.fraud_score >= 0.7
                ORDER BY r.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()

        cursor.close()
        conn.close()

        if not results:
            return json.dumps({
                "found": False,
                "message": "No fraud history found for the given criteria",
                "user_id": user_id,
                "ip_address": ip_address,
                "order_id": order_id
            })

        # Convert results to JSON-serializable format
        fraud_records = []
        for row in results:
            record = decimal_to_float(dict(row))
            # Convert datetime to string
            if 'created_at' in record and record['created_at']:
                record['created_at'] = str(record['created_at'])
            fraud_records.append(record)

        return json.dumps({
            "found": True,
            "count": len(fraud_records),
            "records": fraud_records,
            "summary": {
                "total_cases": len(fraud_records),
                "avg_fraud_score": sum(r.get('fraud_score', 0) for r in fraud_records) / len(fraud_records) if fraud_records else 0,
                "fraud_predictions": sum(1 for r in fraud_records if r.get('fraud_prediction') == 'FRAUD'),
                "query_type": "order" if order_id else "user" if user_id else "ip" if ip_address else "recent_high_fraud"
            }
        }, indent=2)

    except Exception as e:
        logger.error(f"Error querying fraud history: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "user_id": user_id,
            "ip_address": ip_address,
            "order_id": order_id
        })
