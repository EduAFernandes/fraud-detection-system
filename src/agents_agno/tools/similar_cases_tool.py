"""
Similar Cases Tool for Agno Agents
Enables agents to find similar fraud cases using Qdrant vector search
"""

import logging
import json
import os
from typing import Optional, Dict, Any

from agno.tools import tool

logger = logging.getLogger(__name__)


@tool
def similar_cases_tool(
    transaction_description: str,
    amount: Optional[float] = None,
    payment_method: Optional[str] = None,
    account_age_days: Optional[int] = None,
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> str:
    """Find similar fraud cases using Qdrant vector similarity search.

    Enables agents to leverage historical fraud patterns by finding
    cases with similar characteristics using RAG (Retrieval-Augmented Generation).

    Args:
        transaction_description: Natural language description of the transaction
        amount: Transaction amount
        payment_method: Payment method used
        account_age_days: Age of the account in days
        limit: Maximum number of similar cases to return
        similarity_threshold: Minimum similarity score (0-1)

    Returns:
        JSON string containing similar fraud cases or error message
    """
    try:
        from src.memory.qdrant_knowledge import QdrantFraudKnowledge

        # Initialize Qdrant
        qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        kb = QdrantFraudKnowledge(url=qdrant_url)

        # Build transaction dict for query
        transaction = {
            'description': transaction_description
        }

        if amount is not None:
            transaction['amount'] = amount
        if payment_method:
            transaction['payment_method'] = payment_method
        if account_age_days is not None:
            transaction['account_age_days'] = account_age_days

        # Find similar fraud cases
        similar_cases = kb.find_similar_fraud_cases(
            transaction=transaction,
            limit=limit,
            score_threshold=similarity_threshold
        )

        if not similar_cases:
            return json.dumps({
                "found": False,
                "message": "No similar fraud cases found above similarity threshold",
                "threshold": similarity_threshold
            })

        # Analyze patterns across similar cases
        fraud_types = {}
        for case in similar_cases:
            fraud_type = case.get('fraud_type', 'unknown')
            fraud_types[fraud_type] = fraud_types.get(fraud_type, 0) + 1

        most_common_fraud_type = max(fraud_types, key=fraud_types.get) if fraud_types else "unknown"

        result = {
            "found": True,
            "count": len(similar_cases),
            "similar_cases": similar_cases,
            "pattern_analysis": {
                "fraud_types": fraud_types,
                "most_common_type": most_common_fraud_type,
                "avg_similarity": sum(c['similarity_score'] for c in similar_cases) / len(similar_cases),
                "high_confidence_matches": sum(1 for c in similar_cases if c['similarity_score'] >= 0.85)
            },
            "recommendation": {
                "risk_level": "HIGH" if len([c for c in similar_cases if c['similarity_score'] >= 0.85]) >= 2 else "MEDIUM",
                "reasoning": f"Found {len(similar_cases)} similar cases, most common: {most_common_fraud_type}",
                "action": "BLOCK" if len([c for c in similar_cases if c['similarity_score'] >= 0.9]) >= 2 else "MANUAL_REVIEW"
            }
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error finding similar fraud cases: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "transaction_description": transaction_description
        })
