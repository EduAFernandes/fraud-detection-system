"""
Supabase PostgreSQL Writer for Fraud Detection
Writes to the fraud_detection schema in Supabase with connection pooling
"""

import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values
from typing import List
from pyspark.sql import DataFrame
from datetime import datetime

from src.utils.circuit_breaker import circuit_breaker_manager
from src.utils.retry_handler import retry_with_backoff

logger = logging.getLogger(__name__)

class SupabaseWriter:
    """Writer for Supabase PostgreSQL with connection pooling"""

    def __init__(self, connection_string: str = None, minconn: int = 2, maxconn: int = 10):
        """Initialize Supabase writer with connection pooling

        Args:
            connection_string: PostgreSQL connection string
            minconn: Minimum connections in pool (default 2)
            maxconn: Maximum connections in pool (default 10)
        """
        self.connection_string = connection_string or self._get_connection_string()
        self.minconn = minconn
        self.maxconn = maxconn

        # Initialize connection pool
        try:
            logger.info(f"🔧 Initializing PostgreSQL connection pool (min={minconn}, max={maxconn})...")
            self._connection_pool = pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                dsn=self.connection_string
            )
            logger.info("✅ PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL connection pool: {e}")
            raise

        # Initialize circuit breaker
        self._circuit_breaker = circuit_breaker_manager.get_circuit_breaker(
            name="postgresql",
            failure_threshold=5,
            recovery_timeout=30.0,
            success_threshold=2
        )

        self.test_connection()

    def _get_connection_string(self) -> str:
        """Get PostgreSQL connection string from environment variables"""
        import os
        connection_string = os.getenv('POSTGRES_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("POSTGRES_CONNECTION_STRING environment variable is required")
        return connection_string

    def test_connection(self) -> bool:
        """Test PostgreSQL connection from pool"""
        conn = None
        try:
            conn = self._connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()

            logger.info("✅ Supabase PostgreSQL connection pool test successful")
            return result[0] == 1

        except Exception as e:
            logger.error(f"❌ Supabase PostgreSQL connection pool test failed: {e}")
            return False
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def write_fraud_detection_batch(self, batch_df: DataFrame, batch_id: int):
        """Write fraud detection results batch to Supabase using connection pool"""
        conn = None
        try:
            batch_data = batch_df.collect()

            if not batch_data:
                logger.info(f"Batch {batch_id}: No data to write")
                return

            # Get connection from pool
            conn = self._connection_pool.getconn()
            cursor = conn.cursor()

            transaction_records = []
            result_records = []

            for row in batch_data:
                row_dict = row.asDict()

                # Safe conversion functions
                def safe_float(val, default=0.0):
                    return float(val) if val is not None else default

                def safe_int(val, default=0):
                    return int(val) if val is not None else default

                def safe_str(val, default="unknown"):
                    return str(val) if val is not None else default

                def safe_bool(val, default=False):
                    return bool(val) if val is not None else default

                # Get timestamp
                processing_timestamp = row_dict.get('processing_timestamp') or datetime.now()

                # Prepare transaction record
                transaction_record = (
                    row_dict.get('order_id'),
                    safe_str(row_dict.get('user_id')),
                    safe_float(row_dict.get('total_amount')),
                    safe_str(row_dict.get('payment_method')),
                    safe_int(row_dict.get('account_age_days')),
                    safe_int(row_dict.get('total_orders')),
                    safe_float(row_dict.get('avg_order_value')),
                    processing_timestamp
                )
                transaction_records.append(transaction_record)

                # Prepare fraud result record
                result_record = (
                    row_dict.get('order_id'),
                    safe_float(row_dict.get('fraud_score')),
                    safe_str(row_dict.get('fraud_prediction'), 'UNKNOWN'),
                    safe_float(row_dict.get('confidence')),
                    safe_str(row_dict.get('triage_decision'), 'AUTO_ALLOW'),
                    safe_str(row_dict.get('priority_level'), 'LOW'),
                    safe_bool(row_dict.get('requires_agent_analysis'), False)
                )
                result_records.append(result_record)

            # Insert transactions
            transaction_sql = """
            INSERT INTO fraud_detection.transactions (
                order_id, user_id, total_amount, payment_method,
                account_age_days, total_orders, avg_order_value, processing_timestamp
            ) VALUES %s
            ON CONFLICT (order_id) DO NOTHING
            """
            execute_values(cursor, transaction_sql, transaction_records)

            # Insert fraud results
            result_sql = """
            INSERT INTO fraud_detection.results (
                order_id, fraud_score, fraud_prediction, confidence,
                triage_decision, priority_level, requires_agent_analysis
            ) VALUES %s
            ON CONFLICT (order_id) DO UPDATE SET
                fraud_score = EXCLUDED.fraud_score,
                fraud_prediction = EXCLUDED.fraud_prediction,
                confidence = EXCLUDED.confidence,
                triage_decision = EXCLUDED.triage_decision,
                priority_level = EXCLUDED.priority_level,
                requires_agent_analysis = EXCLUDED.requires_agent_analysis
            """
            execute_values(cursor, result_sql, result_records)

            conn.commit()
            cursor.close()

            logger.info(f"✅ Supabase Batch {batch_id}: Inserted {len(transaction_records)} transactions and {len(result_records)} results")

        except Exception as e:
            logger.error(f"❌ Error writing Supabase batch {batch_id}: {e}")
            if conn:
                conn.rollback()
        finally:
            # Return connection to pool
            if conn:
                self._connection_pool.putconn(conn)

    def write_agent_analysis(self, order_id: str, analysis_type: str, agent_name: str,
                            findings: str, risk_factors: List[str], recommendation: str,
                            confidence: float = None, processing_time_seconds: float = None):
        """Write agent analysis result to Supabase using connection pool"""
        conn = None
        try:
            # Get connection from pool
            conn = self._connection_pool.getconn()
            cursor = conn.cursor()

            insert_sql = """
            INSERT INTO fraud_detection.agent_analysis (
                order_id, analysis_type, agent_name, findings, risk_factors,
                recommendation, confidence, processing_time_seconds
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_sql, (
                order_id,
                analysis_type,
                agent_name,
                findings,
                risk_factors,
                recommendation,
                confidence,
                processing_time_seconds
            ))

            conn.commit()
            cursor.close()

            logger.info(f"✅ Agent analysis saved for order {order_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error writing agent analysis for order {order_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            # Return connection to pool
            if conn:
                self._connection_pool.putconn(conn)

    def close(self):
        """Close all connections in the pool gracefully"""
        try:
            if hasattr(self, '_connection_pool') and self._connection_pool:
                self._connection_pool.closeall()
                logger.info("✅ PostgreSQL connection pool closed")
        except Exception as e:
            logger.error(f"❌ Error closing PostgreSQL connection pool: {e}")

# Global instance
supabase_writer = SupabaseWriter()
