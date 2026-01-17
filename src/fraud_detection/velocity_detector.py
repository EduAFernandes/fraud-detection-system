"""
Velocity Fraud Detection
Detects rapid-fire orders and card testing patterns
"""

import logging
import time
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VelocityFraudDetector:
    """Detects velocity fraud patterns like rapid orders and card testing"""

    def __init__(self,
                 velocity_threshold_ms: int = 500,
                 card_testing_order_threshold: int = 3,
                 card_testing_window_minutes: int = 5):
        """
        Initialize velocity fraud detector

        Args:
            velocity_threshold_ms: Time threshold for rapid orders (milliseconds)
            card_testing_order_threshold: Number of orders to flag card testing
            card_testing_window_minutes: Time window for card testing detection
        """
        self.velocity_threshold_ms = velocity_threshold_ms
        self.card_testing_order_threshold = card_testing_order_threshold
        self.card_testing_window_minutes = card_testing_window_minutes

        # Track user orders: user_id -> list of order data
        self.user_orders: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        logger.info(f"✅ Velocity detector initialized:")
        logger.info(f"   Velocity threshold: {velocity_threshold_ms}ms")
        logger.info(f"   Card testing: {card_testing_order_threshold} orders in {card_testing_window_minutes} min")

    def check_velocity_fraud(self, user_id: str, amount: float) -> Dict[str, Any]:
        """
        Check for velocity fraud patterns

        Args:
            user_id: User identifier
            amount: Transaction amount

        Returns:
            Dictionary with fraud check results:
            {
                'is_fraud': bool,
                'reason': str,
                'score_boost': float,
                'fraud_type': str  # 'velocity' or 'card_testing'
            }
        """
        current_time = time.time() * 1000  # Convert to milliseconds
        current_datetime = datetime.now()

        # Record current order
        order_data = {
            'timestamp_ms': current_time,
            'timestamp': current_datetime,
            'amount': amount
        }
        self.user_orders[user_id].append(order_data)

        # Check 1: Velocity fraud (rapid successive orders)
        velocity_result = self._check_velocity(user_id, current_time)
        if velocity_result['is_fraud']:
            return velocity_result

        # Check 2: Card testing (multiple small orders)
        card_testing_result = self._check_card_testing(user_id, current_datetime)
        if card_testing_result['is_fraud']:
            return card_testing_result

        # Clean up old orders to prevent memory bloat
        self._cleanup_old_orders()

        return {
            'is_fraud': False,
            'reason': 'No velocity fraud detected',
            'score_boost': 0.0,
            'fraud_type': None
        }

    def _check_velocity(self, user_id: str, current_time_ms: float) -> Dict[str, Any]:
        """Check for rapid successive orders"""
        user_order_history = self.user_orders.get(user_id, [])

        if len(user_order_history) < 2:
            return {'is_fraud': False}

        # Get last two orders
        last_order = user_order_history[-2]
        time_diff_ms = current_time_ms - last_order['timestamp_ms']

        if time_diff_ms < self.velocity_threshold_ms:
            logger.warning(f"🚨 VELOCITY FRAUD: User {user_id} placed order {time_diff_ms:.0f}ms after previous order")
            return {
                'is_fraud': True,
                'reason': f'VELOCITY_FRAUD: {time_diff_ms:.0f}ms since last order (threshold: {self.velocity_threshold_ms}ms)',
                'score_boost': 0.4,
                'fraud_type': 'velocity',
                'time_diff_ms': time_diff_ms
            }

        return {'is_fraud': False}

    def _check_card_testing(self, user_id: str, current_time: datetime) -> Dict[str, Any]:
        """Check for card testing patterns (multiple small orders)"""
        user_order_history = self.user_orders.get(user_id, [])

        # Need at least threshold number of orders
        if len(user_order_history) < self.card_testing_order_threshold:
            return {'is_fraud': False}

        # Check orders within time window
        cutoff_time = current_time - timedelta(minutes=self.card_testing_window_minutes)
        recent_orders = [
            order for order in user_order_history
            if order['timestamp'] >= cutoff_time
        ]

        if len(recent_orders) >= self.card_testing_order_threshold:
            # Check if orders are small amounts (typical card testing)
            small_orders = [order for order in recent_orders if order['amount'] < 50]

            if len(small_orders) >= self.card_testing_order_threshold:
                logger.warning(
                    f"🚨 CARD TESTING: User {user_id} made {len(small_orders)} "
                    f"small orders (<$50) in {self.card_testing_window_minutes} minutes"
                )
                return {
                    'is_fraud': True,
                    'reason': f'CARD_TESTING: {len(small_orders)} small orders in {self.card_testing_window_minutes} minutes',
                    'score_boost': 0.5,
                    'fraud_type': 'card_testing',
                    'order_count': len(small_orders)
                }

        return {'is_fraud': False}

    def _cleanup_old_orders(self):
        """Remove orders older than cleanup threshold to prevent memory bloat"""
        cleanup_threshold = datetime.now() - timedelta(hours=1)

        for user_id in list(self.user_orders.keys()):
            # Keep only recent orders
            self.user_orders[user_id] = [
                order for order in self.user_orders[user_id]
                if order['timestamp'] > cleanup_threshold
            ]

            # Remove user if no orders left
            if not self.user_orders[user_id]:
                del self.user_orders[user_id]

    def get_user_order_count(self, user_id: str, minutes: int = 60) -> int:
        """
        Get count of orders for user in time window

        Args:
            user_id: User identifier
            minutes: Time window in minutes

        Returns:
            Number of orders
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        user_order_history = self.user_orders.get(user_id, [])

        return len([
            order for order in user_order_history
            if order['timestamp'] > cutoff_time
        ])

    def get_stats(self) -> Dict[str, Any]:
        """Get velocity detector statistics"""
        total_users = len(self.user_orders)
        total_orders = sum(len(orders) for orders in self.user_orders.values())

        return {
            'tracked_users': total_users,
            'total_orders_tracked': total_orders,
            'velocity_threshold_ms': self.velocity_threshold_ms,
            'card_testing_threshold': self.card_testing_order_threshold,
            'card_testing_window_min': self.card_testing_window_minutes
        }
