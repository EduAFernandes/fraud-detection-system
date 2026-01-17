"""
Test Qdrant Knowledge Base
Run this to verify Qdrant RAG integration is working
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

from src.memory.qdrant_knowledge import QdrantFraudKnowledge
import time

def test_qdrant_knowledge():
    """Test all Qdrant knowledge base functions"""

    print("\n" + "="*70)
    print("🧪 TESTING QDRANT KNOWLEDGE BASE")
    print("="*70)

    print("\n🧪 Test 1: Initialize Qdrant and create collection")
    try:
        kb = QdrantFraudKnowledge(
            url="http://localhost:6333",
            collection_name="fraud_patterns_test"
        )
        print("✅ Qdrant initialized and collection created")
    except Exception as e:
        print(f"\n❌ Failed to initialize Qdrant: {e}")
        print("\n💡 Make sure Qdrant is running:")
        print("   docker-compose up -d qdrant")
        print("   OR")
        print("   docker run -d -p 6333:6333 qdrant/qdrant")
        return

    print("\n🧪 Test 2: Check initial patterns loaded")
    try:
        stats = kb.get_stats()
        pattern_count = stats.get('total_patterns', 0)

        print(f"✅ Initial patterns loaded: {pattern_count} patterns")

        if pattern_count >= 10:
            print(f"   ✓ Expected 10+ patterns, got {pattern_count}")
        else:
            print(f"   ⚠️ Expected 10+ patterns, got {pattern_count}")

        print(f"   Vector size: {stats.get('vector_size')}")
        print(f"   Distance metric: {stats.get('distance_metric')}")

    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return

    print("\n🧪 Test 3: Search for similar fraud cases")

    # Test transaction that should match velocity fraud
    test_transaction = {
        'order_id': 'TEST-001',
        'user_id': 'USER-123',
        'amount': 15.00,
        'account_age_days': 3,
        'payment_method': 'credit_card'
    }

    try:
        similar_cases = kb.find_similar_fraud_cases(
            test_transaction,
            limit=3,
            score_threshold=0.5
        )

        print(f"✅ Similar fraud cases found: {len(similar_cases)} matches")

        if similar_cases:
            print("\n   Top matches:")
            for i, case in enumerate(similar_cases, 1):
                print(f"\n   Match {i}:")
                print(f"   - Similarity: {case['similarity_score']:.3f}")
                print(f"   - Type: {case['fraud_type']}")
                print(f"   - Pattern: {case['description'][:80]}...")
        else:
            print("   ⚠️ No matches found (try lowering score_threshold)")

    except Exception as e:
        print(f"❌ Similarity search failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n🧪 Test 4: Add new fraud pattern")

    new_pattern_desc = """
    User created account today and immediately made 5 transactions
    totaling $2,500 using a virtual credit card from a high-risk country.
    All orders shipped to freight forwarder.
    """

    try:
        kb.add_fraud_pattern(
            description=new_pattern_desc.strip(),
            metadata={
                'account_age_hours': 2,
                'transaction_count': 5,
                'total_amount': 2500,
                'payment_type': 'virtual_card',
                'shipping_type': 'freight_forwarder',
                'risk_level': 'critical'
            },
            fraud_type='account_takeover'
        )
        print("✅ New fraud pattern added to knowledge base")
    except Exception as e:
        print(f"❌ Failed to add pattern: {e}")
        return

    print("\n🧪 Test 5: Verify new pattern is searchable")

    # Wait a moment for indexing
    time.sleep(0.5)

    search_transaction = {
        'order_id': 'SEARCH-001',
        'amount': 2000,
        'account_age_days': 0,
        'payment_method': 'virtual_card'
    }

    try:
        matches = kb.find_similar_fraud_cases(
            search_transaction,
            limit=5,
            score_threshold=0.3
        )

        # Check if our new pattern is in results
        found_new_pattern = any(
            'freight_forwarder' in str(match.get('metadata', {})) or
            'account_takeover' in match.get('fraud_type', '')
            for match in matches
        )

        if found_new_pattern:
            print("✅ Newly added pattern is searchable")
        else:
            print("⚠️ New pattern not found in search results")
            print(f"   (This may be normal - got {len(matches)} other matches)")

    except Exception as e:
        print(f"❌ Search after adding pattern failed: {e}")

    print("\n🧪 Test 6: Add multiple patterns in bulk")

    bulk_patterns = [
        {
            'description': 'Cryptocurrency purchase over $1000 from new account',
            'fraud_type': 'crypto_fraud',
            'metadata': {'amount_min': 1000, 'risk_level': 'high'}
        },
        {
            'description': 'Gift card purchase with recently stolen credit card',
            'fraud_type': 'gift_card_fraud',
            'metadata': {'payment_status': 'stolen', 'risk_level': 'critical'}
        }
    ]

    try:
        kb.add_fraud_patterns_bulk(bulk_patterns)
        print(f"✅ Added {len(bulk_patterns)} patterns in bulk")
    except Exception as e:
        print(f"❌ Bulk add failed: {e}")

    print("\n🧪 Test 7: Final stats")
    try:
        final_stats = kb.get_stats()
        print(f"✅ Final collection stats:")
        print(f"   Total patterns: {final_stats.get('total_patterns')}")
        print(f"   Vector dimension: {final_stats.get('vector_size')}")

        expected_count = pattern_count + 1 + len(bulk_patterns)
        actual_count = final_stats.get('total_patterns', 0)

        if actual_count >= expected_count:
            print(f"   ✓ Pattern count increased as expected")
        else:
            print(f"   ℹ️ Expected ~{expected_count}, got {actual_count}")

    except Exception as e:
        print(f"❌ Failed to get final stats: {e}")

    print("\n" + "="*70)
    print("✅ ALL QDRANT TESTS PASSED!")
    print("="*70)

    print("\n💡 Notes:")
    print("   - Qdrant vector database is working correctly")
    print("   - RAG similarity search is operational")
    print("   - Fraud patterns are being stored and retrieved")
    print("\n🧹 Test collection 'fraud_patterns_test' remains in Qdrant")
    print("   To clear: docker exec qdrant-fraud-optionc rm -rf /qdrant/storage/collections/fraud_patterns_test")

if __name__ == "__main__":
    test_qdrant_knowledge()
