"""
Test Redis Memory Manager
Run this to verify Redis integration is working
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

from src.memory.redis_memory import RedisMemoryManager
import time

def test_redis_memory():
    """Test all Redis memory manager functions"""

    print("\n" + "="*70)
    print("🧪 TESTING REDIS MEMORY MANAGER")
    print("="*70)

    try:
        memory = RedisMemoryManager()
    except Exception as e:
        print(f"\n❌ Failed to connect to Redis: {e}")
        print("\n💡 Make sure Redis is running:")
        print("   docker run -d -p 6379:6379 --name redis-fraud redis:7-alpine")
        return

    print("\n🧪 Test 1: Flag user and check")
    memory.flag_user("TEST-USER", "Test flagging", severity="high")
    status = memory.is_user_flagged("TEST-USER")
    assert status['is_flagged'] == True
    assert status['severity'] == 'high'
    print("✅ User flagging works!")
    print(f"   User status: {status}")

    print("\n🧪 Test 2: Record transactions")
    for i in range(5):
        memory.record_transaction("TEST-USER", {
            'order_id': f'ORD-{i}',
            'amount': 50.0 * (i + 1)
        })
        time.sleep(0.1)

    history = memory.get_user_transaction_history("TEST-USER")
    assert len(history) == 5
    print(f"✅ Transaction history works! ({len(history)} transactions)")
    print(f"   Latest transaction: {history[0]}")

    print("\n🧪 Test 3: Transaction count")
    count = memory.get_user_transaction_count("TEST-USER", minutes=60)
    assert count == 5
    print(f"✅ Transaction counting works! ({count} in last hour)")

    print("\n🧪 Test 4: IP flagging")
    memory.flag_ip("192.168.1.100", "Test IP")
    ip_status = memory.is_ip_flagged("192.168.1.100")
    assert ip_status['is_flagged'] == True
    print("✅ IP flagging works!")
    print(f"   IP status: {ip_status}")

    print("\n🧪 Test 5: Agent context storage")
    context_data = {
        'order_id': 'ORD-TEST-123',
        'risk_factors': ['velocity_fraud', 'new_account'],
        'ml_score': 0.85
    }
    memory.store_agent_context('ORD-TEST-123', context_data)
    retrieved_context = memory.get_agent_context('ORD-TEST-123')
    assert retrieved_context is not None
    assert retrieved_context['ml_score'] == 0.85
    print("✅ Agent context storage works!")
    print(f"   Stored context: {retrieved_context}")

    print("\n🧪 Test 6: Stats")
    stats = memory.get_stats()
    print(f"✅ Stats: {stats}")
    assert stats['total_keys'] > 0
    assert stats['flagged_users'] > 0
    assert stats['flagged_ips'] > 0

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print(f"\n📊 Final Stats:")
    print(f"   Total Keys: {stats['total_keys']}")
    print(f"   Flagged Users: {stats['flagged_users']}")
    print(f"   Flagged IPs: {stats['flagged_ips']}")
    print(f"   Transaction Histories: {stats['transaction_histories']}")
    print(f"   Agent Contexts: {stats['agent_contexts']}")

    print("\n🧹 Cleaning up test data...")
    memory.clear_all()
    print("✅ Test data cleared!")

if __name__ == "__main__":
    test_redis_memory()
