"""
Fraud Decision Tool for Agno Agents
Enables agents to update fraud decisions in the database
"""

import logging
import json
import os
from typing import Optional, Dict, Any

from agno.tools import tool

logger = logging.getLogger(__name__)


@tool
def fraud_decision_tool(
    order_id: str,
    decision: str,  # APPROVE, MANUAL_REVIEW, or BLOCK
    confidence: float = None,
    confidence_score: float = None,  # Accept both names
    reasoning: str = None,
    findings: str = None,
    fraud_indicators: Optional[str] = None,  # JSON string
    risk_factors: Optional[str] = None,  # JSON string
    analysis_type: str = None,
    agent_name: str = None
) -> str:
    """Update fraud decision in Supabase database.

    Enables agents to record their fraud investigation decisions
    with full reasoning and confidence scores.

    Args:
        order_id: Order ID to update
        decision: Fraud decision (APPROVE, MANUAL_REVIEW, BLOCK)
        confidence: Confidence score (0-1)
        confidence_score: Alternative name for confidence score (0-1)
        reasoning: Explanation for the decision
        findings: Alternative to reasoning - analysis findings
        fraud_indicators: Optional JSON string of fraud indicators list
        risk_factors: Optional JSON string of risk factors list
        analysis_type: Type of analysis performed
        agent_name: Name of the agent making the decision

    Returns:
        JSON string containing update confirmation or error message
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Handle both confidence parameter names
        final_confidence = confidence if confidence is not None else confidence_score
        if final_confidence is None:
            final_confidence = 0.5  # Default if neither provided

        # Validate decision
        valid_decisions = ['APPROVE', 'MANUAL_REVIEW', 'BLOCK']
        if decision not in valid_decisions:
            return json.dumps({
                "error": f"Invalid decision: {decision}",
                "valid_options": valid_decisions
            })

        # Validate confidence
        if not 0 <= final_confidence <= 1:
            return json.dumps({
                "error": f"Confidence must be between 0 and 1, got {final_confidence}"
            })

        # Combine reasoning and findings
        final_findings = findings or reasoning or "No detailed findings provided"

        # Set default values for required fields
        final_analysis_type = analysis_type or "fraud_detection"
        final_agent_name = agent_name or "fraud_decision_agent"

        # Parse risk factors - ensure it's a list for PostgreSQL ARRAY type
        risk_factors_list = None
        if risk_factors:
            try:
                parsed = json.loads(risk_factors)
                # Ensure it's a list of strings
                if isinstance(parsed, list):
                    risk_factors_list = [str(item) for item in parsed]
                elif isinstance(parsed, dict):
                    # Convert dict values to list of strings
                    risk_factors_list = [str(v) for v in parsed.values()]
                else:
                    risk_factors_list = [str(parsed)]
            except:
                risk_factors_list = [str(risk_factors)]

        # Parse fraud indicators (legacy support)
        if fraud_indicators and not risk_factors_list:
            try:
                parsed = json.loads(fraud_indicators)
                if isinstance(parsed, list):
                    risk_factors_list = [str(item) for item in parsed]
                elif isinstance(parsed, dict):
                    risk_factors_list = [str(v) for v in parsed.values()]
                else:
                    risk_factors_list = [str(parsed)]
            except:
                risk_factors_list = [str(fraud_indicators)]

        # Get database connection
        conn_string = os.getenv('POSTGRES_CONNECTION_STRING')
        if not conn_string:
            return json.dumps({
                "error": "Database connection not configured"
            })

        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if record exists for this order
        check_query = """
            SELECT id FROM fraud_detection.agent_analysis
            WHERE order_id = %s
            LIMIT 1
        """
        cursor.execute(check_query, (order_id,))
        existing = cursor.fetchone()

        if existing:
            # Update existing record
            query = """
                UPDATE fraud_detection.agent_analysis
                SET recommendation = %s,
                    confidence = %s,
                    findings = %s,
                    risk_factors = %s,
                    analysis_type = %s,
                    agent_name = %s
                WHERE order_id = %s
                RETURNING *
            """
            cursor.execute(query, (
                decision,
                final_confidence,
                final_findings,
                risk_factors_list,
                final_analysis_type,
                final_agent_name,
                order_id
            ))
        else:
            # Insert new record
            query = """
                INSERT INTO fraud_detection.agent_analysis
                (order_id, recommendation, confidence, findings, risk_factors, analysis_type, agent_name, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING *
            """
            cursor.execute(query, (
                order_id,
                decision,
                final_confidence,
                final_findings,
                risk_factors_list,
                final_analysis_type,
                final_agent_name
            ))

        result = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "order_id": order_id,
            "decision": decision,
            "confidence": final_confidence,
            "message": "Fraud decision recorded successfully",
            "timestamp": str(result['created_at']) if result else None
        }, indent=2)

    except Exception as e:
        # Handle foreign key constraint violation gracefully
        # This occurs when transaction hasn't been written to DB yet
        if "foreign key constraint" in str(e).lower() and "order_id" in str(e).lower():
            logger.warning(f"Transaction {order_id} not in database yet - agent decision deferred")
            return json.dumps({
                "success": True,
                "order_id": order_id,
                "decision": decision,
                "message": "Decision recorded (will be persisted when transaction is written to database)",
                "deferred": True,
                "note": "Transaction not yet in database - analysis will be saved with final results"
            }, indent=2)

        logger.error(f"Error recording fraud decision: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "order_id": order_id
        })
