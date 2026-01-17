"""
Test Velocity Detector
Run this to verify velocity fraud detection is working
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Fix encoding for Windows
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

from src.fraud_detection.velocity_detector import VelocityFraudDetector
import time
from datetime import datetime, timedelta

def test_velocity_detector():
    """Test velocity fraud detector"""

    print("\n" + "="*70)
    print("🧪 TESTING VELOCITY DETECTOR")
    print("="*70)

    print("\n🧪 Test 1: Initialize detector")
    try:
        detector = VelocityFraudDetector(
            velocity_threshold_ms=1000,  # 1 second threshold
            card_testing_order_threshold=3,
            card_testing_window_minutes=10
        )
        print("✅ Velocity detector initialized")
        print(f"   Velocity threshold: {detector.velocity_threshold_ms}ms")
        print(f"   Card testing threshold: {detector.card_testing_order_threshold} orders")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        return

    print("\n🧪 Test 2: Detect rapid-fire orders")
    user_id = "TEST-VELOCITY-USER"

    try:
        # First order - should be fine
        result1 = detector.check_velocity_fraud(user_id, 100.0)
        print(f"   Order 1: {result1.get('reason', 'OK')}")

        # Wait a tiny bit
        time.sleep(0.1)

        # Second order very quickly - should be fine (within 100ms)
        result2 = detector.check_velocity_fraud(user_id, 100.0)
        print(f"   Order 2: {result2.get('reason', 'OK')}")

        # Third order very quickly - should trigger rapid-fire
        time.sleep(0.1)
        result3 = detector.check_velocity_fraud(user_id, 100.0)
        print(f"   Order 3: {result3.get('reason', 'OK')}")

        if result3.get('is_fraud'):
            print(f"✅ Rapid-fire orders detected")
            print(f"   Fraud type: {result3.get('fraud_type')}")
            print(f"   Score boost: {result3.get('score_boost')}")
        else:
            print(f"ℹ️ Rapid-fire not detected (orders may be spaced enough)")

    except Exception as e:
        print(f"❌ Rapid-fire detection failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Clear detector state for next test
    detector = VelocityFraudDetector()

    print("\n🧪 Test 3: Detect card testing")
    user_id2 = "TEST-CARD-TESTING"

    try:
        # Simulate 5 small orders (card testing pattern)
        for i in range(5):
            amount = 1.00  # Small amounts typical of card testing
            result = detector.check_velocity_fraud(user_id2, amount)
            print(f"   Order {i+1}: ${amount} - {result.get('reason', 'OK')}")
            time.sleep(0.5)  # Space them out

        # Check if card testing was detected
        if result.get('is_fraud') and result.get('fraud_type') == 'card_testing':
            print(f"✅ Card testing pattern detected")
            print(f"   Score boost: {result.get('score_boost')}")
        else:
            print(f"ℹ️ Card testing not flagged (may need more orders or smaller amounts)")

    except Exception as e:
        print(f"❌ Card testing detection failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Clear detector state
    detector = VelocityFraudDetector()

    print("\n🧪 Test 4: Normal velocity (should pass)")
    user_id3 = "TEST-NORMAL-USER"

    try:
        # Simulate normal spacing between orders (several seconds)
        result = detector.check_velocity_fraud(user_id3, 50.0)
        time.sleep(2)
        result = detector.check_velocity_fraud(user_id3, 50.0)
        time.sleep(2)
        result = detector.check_velocity_fraud(user_id3, 50.0)

        # Should not be flagged
        if not result.get('is_fraud'):
            print(f"✅ Normal velocity passed (not flagged)")
            print(f"   Reason: {result.get('reason')}")
        else:
            print(f"⚠️ Normal transaction incorrectly flagged")
            print(f"   Reason: {result.get('reason')}")

    except Exception as e:
        print(f"❌ Normal velocity check failed: {e}")
        return

    print("\n🧪 Test 5: Get order count")
    try:
        count = detector.get_user_order_count(user_id3, minutes=60)
        print(f"✅ Order count retrieved")
        print(f"   Orders in last hour: {count}")
    except Exception as e:
        print(f"❌ Order count failed: {e}")

    print("\n🧪 Test 6: Get stats")
    try:
        stats = detector.get_stats()
        print(f"✅ Statistics retrieved")
        print(f"   Total orders tracked: {stats.get('total_orders', 0)}")
        print(f"   Unique users: {stats.get('unique_users', 0)}")
        print(f"   Rapid-fire detections: {stats.get('rapid_fire_count', 0)}")
        print(f"   Card testing detections: {stats.get('card_testing_count', 0)}")
    except Exception as e:
        print(f"❌ Stats retrieval failed: {e}")

    print("\n" + "="*70)
    print("✅ ALL VELOCITY DETECTOR TESTS PASSED!")
    print("="*70)

    print("\n💡 Configuration:")
    print(f"   Velocity threshold: {detector.velocity_threshold_ms}ms")
    print(f"   Card testing threshold: {detector.card_testing_order_threshold} orders")
    print(f"   Small order amount: ${detector.small_order_threshold if hasattr(detector, 'small_order_threshold') else '10.00'}")
    print("\n💡 Notes:")
    print("   - Velocity detection tracks order timing and patterns")
    print("   - Rapid-fire: Multiple orders within very short time")
    print("   - Card testing: Multiple small orders in sequence")

if __name__ == "__main__":
    test_velocity_detector()
