"""
End-to-End Test with Mock Data
Run this to test full pipeline without consuming OpenAI credits
Uses mock AI responses instead of real API calls
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

from datetime import datetime, timedelta
import random
import json
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_mock_transactions(count=100):
    """Generate realistic mock transactions"""

    transactions = []
    base_time = datetime.now()

    # Transaction patterns
    normal_merchants = ['Amazon', 'Walmart', 'Target', 'Starbucks', 'Netflix']
    fraud_merchants = ['Unknown Electronics', 'Gift Card Store', 'Crypto Exchange']

    for i in range(count):
        # 20% fraud rate
        is_fraud = random.random() < 0.20

        if is_fraud:
            tx = {
                'order_id': f'ORD-FRAUD-{i}',
                'user_id': f'USER-{random.randint(1, 20)}',
                'amount': random.uniform(500, 10000),
                'merchant': random.choice(fraud_merchants),
                'category': random.choice(['Gift Cards', 'Electronics', 'Crypto']),
                'timestamp': (base_time - timedelta(minutes=random.randint(0, 60))).isoformat(),
                'ip_address': f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
                'device_fingerprint': 'new_device',
                'is_actually_fraud': True  # Ground truth for testing
            }
        else:
            tx = {
                'order_id': f'ORD-NORMAL-{i}',
                'user_id': f'USER-{random.randint(100, 200)}',
                'amount': random.uniform(10, 200),
                'merchant': random.choice(normal_merchants),
                'category': random.choice(['Books', 'Clothing', 'Food', 'Entertainment']),
                'timestamp': (base_time - timedelta(minutes=random.randint(0, 120))).isoformat(),
                'ip_address': f'192.168.1.{random.randint(1, 255)}',
                'is_actually_fraud': False
            }

        transactions.append(tx)

    return transactions

def test_e2e_mock():
    """End-to-end test with mock data"""

    print("\n" + "="*70)
    print("🚀 END-TO-END TEST (MOCK DATA)")
    print("="*70)
    print("\n💡 Using mock AI responses - no OpenAI credits consumed")

    print("\n🧪 Step 1: Generate mock transactions")
    try:
        transactions = generate_mock_transactions(100)
        print(f"✅ Generated {len(transactions)} mock transactions")

        fraud_count = sum(1 for tx in transactions if tx.get('is_actually_fraud'))
        normal_count = len(transactions) - fraud_count
        print(f"   Normal: {normal_count}, Fraud: {fraud_count}")
    except Exception as e:
        print(f"❌ Mock data generation failed: {e}")
        return

    print("\n🧪 Step 2: Initialize fraud detection system")
    try:
        # Mock the OpenAI calls to avoid API costs
        with patch('openai.ChatCompletion.create') as mock_openai:
            # Mock AI response
            mock_openai.return_value = Mock(
                choices=[
                    Mock(message=Mock(content=json.dumps({
                        'decision': 'BLOCK',
                        'confidence': 0.85,
                        'reasoning': 'High-risk transaction pattern detected'
                    })))
                ]
            )

            from src.fraud_detection.fraud_orchestrator import FraudOrchestrator
            from src.config.settings import Settings

            # Initialize settings from environment
            settings = Settings()

            # Initialize with mocked AI
            orchestrator = FraudOrchestrator(settings)
            print(f"✅ Fraud detection system initialized (with mocked AI)")

    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        print(f"   Make sure Redis and Qdrant are running:")
        print(f"   docker-compose up -d redis qdrant")
        return

    print("\n🧪 Step 3: Process all transactions")
    results = []
    start_time = datetime.now()

    try:
        for i, tx in enumerate(transactions):
            if i % 20 == 0:
                print(f"   Processing: {i}/{len(transactions)}...")

            # Simplified processing without AI agents for mock test
            ml_score = orchestrator.ml_detector.predict(tx)
            velocity_result = orchestrator.velocity_detector.check_velocity_fraud(
                tx.get('user_id', 'unknown'),
                tx.get('amount', 0.0)
            )

            # Simple decision logic for mock test
            fraud_score = ml_score
            if velocity_result.get('is_fraud'):
                fraud_score += velocity_result.get('score_boost', 0.3)

            decision = 'BLOCK' if fraud_score > 0.70 else 'REVIEW' if fraud_score > 0.40 else 'APPROVE'

            result = {
                'order_id': tx['order_id'],
                'decision': decision,
                'fraud_score': fraud_score,
                'ml_score': ml_score,
                'is_actually_fraud': tx.get('is_actually_fraud', False),
                'is_flagged_fraud': decision in ['BLOCK', 'REVIEW']
            }

            results.append(result)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"✅ All transactions processed")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Throughput: {len(transactions) / duration:.1f} tx/sec")

    except Exception as e:
        print(f"❌ Transaction processing failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n🧪 Step 4: Calculate detection metrics")
    try:
        # True Positives: Actual fraud that was flagged
        true_positives = sum(1 for r in results if r['is_actually_fraud'] and r['is_flagged_fraud'])

        # False Positives: Normal transactions that were flagged
        false_positives = sum(1 for r in results if not r['is_actually_fraud'] and r['is_flagged_fraud'])

        # True Negatives: Normal transactions that were approved
        true_negatives = sum(1 for r in results if not r['is_actually_fraud'] and not r['is_flagged_fraud'])

        # False Negatives: Actual fraud that was not flagged
        false_negatives = sum(1 for r in results if r['is_actually_fraud'] and not r['is_flagged_fraud'])

        # Detection rate (recall)
        detection_rate = (true_positives / (true_positives + false_negatives)) * 100 if (true_positives + false_negatives) > 0 else 0

        # False positive rate
        false_positive_rate = (false_positives / (false_positives + true_negatives)) * 100 if (false_positives + true_negatives) > 0 else 0

        # Precision
        precision = (true_positives / (true_positives + false_positives)) * 100 if (true_positives + false_positives) > 0 else 0

        print(f"✅ Metrics calculated")

    except Exception as e:
        print(f"❌ Metrics calculation failed: {e}")
        return

    print("\n🧪 Step 5: Check Redis memory state")
    if orchestrator.redis_memory:
        try:
            stats = orchestrator.redis_memory.get_stats()
            print(f"✅ Redis memory stats retrieved")
            print(f"   Flagged users: {stats.get('flagged_users', 0)}")
            print(f"   Flagged IPs: {stats.get('flagged_ips', 0)}")
            print(f"   Transaction histories: {stats.get('transaction_histories', 0)}")
        except Exception as e:
            print(f"⚠️ Redis stats failed: {e}")
    else:
        print(f"⚠️ Redis memory not enabled")

    print("\n🧪 Step 6: Check Qdrant knowledge base")
    if orchestrator.qdrant_knowledge:
        try:
            kb_stats = orchestrator.qdrant_knowledge.get_stats()
            print(f"✅ Qdrant knowledge base stats retrieved")
            print(f"   Total patterns: {kb_stats.get('total_patterns', 0)}")
        except Exception as e:
            print(f"⚠️ Qdrant stats failed: {e}")
    else:
        print(f"⚠️ Qdrant not enabled")

    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)

    print(f"\n📈 Detection Metrics:")
    print(f"   True Positives:  {true_positives:3d} (fraud correctly detected)")
    print(f"   False Positives: {false_positives:3d} (normal flagged as fraud)")
    print(f"   True Negatives:  {true_negatives:3d} (normal correctly approved)")
    print(f"   False Negatives: {false_negatives:3d} (fraud missed)")

    print(f"\n🎯 Performance:")
    print(f"   Detection Rate:        {detection_rate:.1f}% (recall)")
    print(f"   Precision:             {precision:.1f}%")
    print(f"   False Positive Rate:   {false_positive_rate:.1f}%")

    print(f"\n📊 Decisions:")
    blocked = sum(1 for r in results if r['decision'] == 'BLOCK')
    review = sum(1 for r in results if r['decision'] == 'REVIEW')
    approved = sum(1 for r in results if r['decision'] == 'APPROVE')
    print(f"   BLOCKED:  {blocked:3d}/{len(results)}")
    print(f"   REVIEW:   {review:3d}/{len(results)}")
    print(f"   APPROVED: {approved:3d}/{len(results)}")

    # Evaluate results
    print("\n" + "="*70)
    passed_all = True

    if detection_rate >= 60:
        print(f"✅ Detection rate is good: {detection_rate:.1f}%")
    else:
        print(f"⚠️ Detection rate is low: {detection_rate:.1f}% (target: >60%)")
        passed_all = False

    if false_positive_rate <= 10:
        print(f"✅ False positive rate is acceptable: {false_positive_rate:.1f}%")
    else:
        print(f"⚠️ False positive rate is high: {false_positive_rate:.1f}% (target: <10%)")
        passed_all = False

    if orchestrator.redis_memory and stats.get('total_keys', 0) > 0:
        print(f"✅ Redis memory is working")
    else:
        print(f"⚠️ Redis memory may not be persisting data")

    if orchestrator.qdrant_knowledge and kb_stats.get('total_patterns', 0) > 0:
        print(f"✅ Qdrant knowledge base is working")
    else:
        print(f"⚠️ Qdrant knowledge base may not be loaded")

    print("="*70)

    if passed_all:
        print("✅ END-TO-END TEST PASSED!")
    else:
        print("⚠️ END-TO-END TEST COMPLETED WITH WARNINGS")
        print("   Consider tuning thresholds in .env file")

    print("\n💡 Next steps:")
    print("   1. Review metrics above")
    print("   2. Adjust thresholds in .env if needed")
    print("   3. Test with real Kafka using test_fraud_orchestrator.py")
    print("   4. Monitor production with Langfuse")

    # Cleanup
    if orchestrator.redis_memory:
        print("\n🧹 Cleaning up test data...")
        try:
            orchestrator.redis_memory.clear_all()
            print("✅ Test data cleared")
        except:
            pass

if __name__ == "__main__":
    test_e2e_mock()
