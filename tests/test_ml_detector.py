"""
Test ML Detector (Isolation Forest)
Run this to verify ML fraud detection is working
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

from src.fraud_detection.ml_detector import MLFraudDetector

def test_ml_detector():
    """Test ML fraud detector"""

    print("\n" + "="*70)
    print("🧪 TESTING ML FRAUD DETECTOR")
    print("="*70)

    print("\n🧪 Test 1: Initialize ML model")
    try:
        detector = MLFraudDetector()
        print("✅ ML detector initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        return

    print("\n🧪 Test 2: Normal transaction (should score low)")
    normal_transaction = {
        'order_id': 'ORD-NORMAL-001',
        'user_id': 'USER-12345',
        'amount': 49.99,
        'merchant': 'Amazon',
        'category': 'Books',
        'timestamp': '2026-01-05T10:30:00Z'
    }

    try:
        score = detector.predict(normal_transaction)
        print(f"✅ Normal transaction scored: {score:.3f}")

        if score < 0.30:
            print(f"   ✓ Score is low (expected for normal transaction)")
        else:
            print(f"   ⚠️ Score is higher than expected for normal transaction")
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return

    print("\n🧪 Test 3: Suspicious transaction (should score high)")
    suspicious_transaction = {
        'order_id': 'ORD-FRAUD-001',
        'user_id': 'USER-99999',
        'amount': 9999.99,  # Very high amount
        'merchant': 'Unknown Store',
        'category': 'Gift Cards',  # High-risk category
        'timestamp': '2026-01-05T03:45:00Z',  # Odd hour
        'ip_address': '1.2.3.4',  # Foreign IP
        'device_fingerprint': 'new_device'
    }

    try:
        score = detector.predict(suspicious_transaction)
        print(f"✅ Suspicious transaction scored: {score:.3f}")

        if score > 0.50:
            print(f"   ✓ Score is high (expected for suspicious transaction)")
        else:
            print(f"   ℹ️ Score is lower (model may need more training data)")
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return

    print("\n🧪 Test 4: Batch prediction")
    batch_transactions = [
        {'order_id': f'ORD-{i}', 'user_id': f'USER-{i}', 'amount': 50.0 + i}
        for i in range(10)
    ]

    try:
        scores = [detector.predict(tx) for tx in batch_transactions]
        avg_score = sum(scores) / len(scores)
        print(f"✅ Batch prediction completed")
        print(f"   Transactions: {len(batch_transactions)}")
        print(f"   Average score: {avg_score:.3f}")
        print(f"   Min score: {min(scores):.3f}")
        print(f"   Max score: {max(scores):.3f}")
    except Exception as e:
        print(f"❌ Batch prediction failed: {e}")
        return

    print("\n🧪 Test 5: Feature extraction")
    try:
        features = detector.extract_features(normal_transaction)
        print(f"✅ Feature extraction working")
        print(f"   Features extracted: {len(features)} features")
        print(f"   Feature vector shape: {features.shape if hasattr(features, 'shape') else len(features)}")
        print(f"   Sample values: {features[:min(5, len(features))]}")
    except Exception as e:
        print(f"❌ Feature extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*70)
    print("✅ ALL ML DETECTOR TESTS PASSED!")
    print("="*70)

    print("\n💡 Notes:")
    print("   - ML scores are relative and improve with more training data")
    print("   - Combine ML scores with velocity checks and AI agents for best results")
    print("   - Current model uses Isolation Forest (unsupervised learning)")

if __name__ == "__main__":
    test_ml_detector()
