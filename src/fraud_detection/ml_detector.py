"""
ML-based fraud detection using Isolation Forest
Provides anomaly detection scores for transactions
"""

import logging
import numpy as np
from typing import Dict, Any
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class MLFraudDetector:
    """Machine learning fraud detector using Isolation Forest algorithm"""

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        """
        Initialize ML fraud detector

        Args:
            contamination: Expected proportion of outliers (default 0.1 = 10%)
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self._train_model()

    def _train_model(self):
        """Train Isolation Forest model with synthetic fraud patterns"""
        logger.info("🔧 Training ML fraud detection model...")

        # Generate synthetic training data representing normal and fraudulent patterns
        np.random.seed(self.random_state)

        # Normal transactions
        normal_transactions = np.random.multivariate_normal(
            mean=[30, 5, 150, 1],  # account_age, orders, amount, payment_method
            cov=[[100, 0, 0, 0],
                 [0, 4, 0, 0],
                 [0, 0, 5000, 0],
                 [0, 0, 0, 0.1]],
            size=1000
        )

        # Fraudulent transactions (anomalies)
        fraud_transactions = np.concatenate([
            # New accounts with high amounts
            np.random.multivariate_normal([3, 1, 500, 2], [[1, 0, 0, 0], [0, 0.1, 0, 0], [0, 0, 10000, 0], [0, 0, 0, 0.1]], 50),
            # High velocity orders
            np.random.multivariate_normal([15, 15, 100, 1], [[20, 0, 0, 0], [0, 10, 0, 0], [0, 0, 2000, 0], [0, 0, 0, 0.1]], 50),
        ])

        # Combine training data
        training_data = np.vstack([normal_transactions, fraud_transactions])

        # Train model
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        self.model.fit(training_data)

        logger.info("✅ ML model trained successfully")

    def extract_features(self, transaction: Dict[str, Any]) -> np.ndarray:
        """
        Extract numerical features from transaction

        Args:
            transaction: Transaction dictionary

        Returns:
            numpy array of features
        """
        # Map payment method to numeric
        payment_method_map = {
            'credit_card': 2,
            'debit_card': 1,
            'bank_transfer': 0,
            'paypal': 1,
            'crypto': 3
        }

        payment_numeric = payment_method_map.get(
            transaction.get('payment_method', '').lower(),
            0
        )

        features = np.array([[
            transaction.get('account_age_days', 0),
            transaction.get('total_orders', 0),
            transaction.get('total_amount', 0),
            payment_numeric
        ]])

        return features

    def predict(self, transaction: Dict[str, Any]) -> float:
        """
        Predict fraud probability for a transaction

        Args:
            transaction: Transaction dictionary

        Returns:
            Fraud probability score (0.0 to 1.0)
        """
        if not self.model:
            logger.error("Model not trained")
            return 0.5

        # Extract features
        features = self.extract_features(transaction)

        # Get anomaly score
        anomaly_score = self.model.score_samples(features)[0]

        # Convert to probability (0-1 range)
        # Lower anomaly scores indicate higher fraud likelihood
        ml_probability = 1 / (1 + np.exp(anomaly_score * 2))

        # Add rule-based components
        rule_score = self._calculate_rule_score(transaction)

        # Ensemble: 65% ML + 35% Rules
        final_score = (0.65 * ml_probability) + (0.35 * rule_score)

        return min(float(final_score), 1.0)

    def _calculate_rule_score(self, transaction: Dict[str, Any]) -> float:
        """
        Calculate rule-based fraud score

        Args:
            transaction: Transaction dictionary

        Returns:
            Rule-based score (0.0 to 1.0)
        """
        rule_score = 0.0

        # Rule 1: New account + high amount
        if transaction.get('account_age_days', 999) < 7 and transaction.get('total_amount', 0) > 200:
            rule_score += 0.35

        # Rule 2: First order + very high amount
        if transaction.get('total_orders', 0) == 1 and transaction.get('total_amount', 0) > 300:
            rule_score += 0.30

        # Rule 3: New account + credit card
        if (transaction.get('payment_method', '').lower() == 'credit_card' and
            transaction.get('account_age_days', 999) < 7):
            rule_score += 0.25

        # Rule 4: Amount >> average
        avg_order_value = transaction.get('avg_order_value', 0)
        total_amount = transaction.get('total_amount', 0)
        if avg_order_value > 0 and total_amount > avg_order_value * 3:
            rule_score += 0.15

        return min(rule_score, 1.0)

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'model_type': 'IsolationForest',
            'contamination': self.contamination,
            'n_estimators': self.model.n_estimators if self.model else 0,
            'trained': self.model is not None
        }
