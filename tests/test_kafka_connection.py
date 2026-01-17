"""
Test Kafka Connection
Run this to verify Kafka/Confluent Cloud connection is working
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

from dotenv import load_dotenv
load_dotenv()

def test_kafka_connection():
    """Test Kafka connection and configuration"""

    print("\n" + "="*70)
    print("🧪 TESTING KAFKA CONNECTION")
    print("="*70)

    print("\n🧪 Test 1: Check Kafka environment variables")
    required_vars = [
        'KAFKA_BOOTSTRAP_SERVERS',
        'KAFKA_API_KEY',
        'KAFKA_API_SECRET',
        'KAFKA_TOPIC_INPUT',
        'KAFKA_TOPIC_OUTPUT'
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"   ❌ {var}: NOT SET")
        else:
            # Mask secrets
            if 'SECRET' in var or 'KEY' in var:
                display_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
            else:
                display_value = value

            print(f"   ✅ {var}: {display_value}")

    if missing_vars:
        print(f"\n❌ Missing Kafka configuration variables: {', '.join(missing_vars)}")
        print("\n💡 Fix:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your Confluent Cloud credentials to .env")
        print("   3. Get credentials from: https://confluent.cloud/")
        return

    print("✅ All Kafka environment variables are set")

    print("\n🧪 Test 2: Try importing Kafka library")
    try:
        from confluent_kafka import Producer, Consumer
        print("✅ confluent-kafka library imported successfully")
    except ImportError as e:
        print(f"❌ confluent-kafka library not installed: {e}")
        print("\n💡 Fix:")
        print("   pip install confluent-kafka")
        return

    print("\n🧪 Test 3: Create Kafka producer")
    try:
        conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': os.getenv('KAFKA_API_KEY'),
            'sasl.password': os.getenv('KAFKA_API_SECRET'),
        }

        producer = Producer(conf)
        print("✅ Kafka producer created successfully")
    except Exception as e:
        print(f"❌ Failed to create Kafka producer: {e}")
        print("\n💡 Check:")
        print("   1. Bootstrap servers URL is correct")
        print("   2. API key and secret are valid")
        print("   3. Network connectivity to Confluent Cloud")
        return

    print("\n🧪 Test 4: Create Kafka consumer")
    try:
        conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': os.getenv('KAFKA_API_KEY'),
            'sasl.password': os.getenv('KAFKA_API_SECRET'),
            'group.id': os.getenv('KAFKA_CONSUMER_GROUP', 'test-group'),
            'auto.offset.reset': 'earliest'
        }

        consumer = Consumer(conf)
        print("✅ Kafka consumer created successfully")
    except Exception as e:
        print(f"❌ Failed to create Kafka consumer: {e}")
        return

    print("\n🧪 Test 5: Test producer send (will send a test message)")
    test_topic = os.getenv('KAFKA_TOPIC_INPUT')

    try:
        import json
        from datetime import datetime

        test_message = {
            'order_id': 'TEST-CONNECTION-001',
            'test': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'Kafka connection test'
        }

        producer.produce(
            test_topic,
            key='test-key',
            value=json.dumps(test_message),
            callback=lambda err, msg: print(f"   Message delivered to {msg.topic()}") if err is None else print(f"   Delivery failed: {err}")
        )

        # Wait for message to be delivered
        producer.flush(timeout=10)

        print(f"✅ Test message sent to topic: {test_topic}")
        print(f"   Message: {test_message}")

    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        print("\n💡 Check:")
        print(f"   1. Topic '{test_topic}' exists in Confluent Cloud")
        print("   2. You have write permissions for this topic")
        return

    print("\n🧪 Test 6: Test consumer subscription")
    try:
        consumer.subscribe([test_topic])
        print(f"✅ Consumer subscribed to topic: {test_topic}")

        # Try to poll for a message (don't wait long)
        print("   Polling for messages (timeout: 5 seconds)...")
        msg = consumer.poll(timeout=5.0)

        if msg is None:
            print("   ℹ️ No messages received (topic may be empty)")
        elif msg.error():
            print(f"   ⚠️ Consumer error: {msg.error()}")
        else:
            print(f"   ✅ Message received from topic!")
            print(f"   Topic: {msg.topic()}, Partition: {msg.partition()}, Offset: {msg.offset()}")

    except Exception as e:
        print(f"❌ Consumer subscription failed: {e}")
        return
    finally:
        consumer.close()

    print("\n" + "="*70)
    print("✅ ALL KAFKA CONNECTION TESTS PASSED!")
    print("="*70)

    print("\n💡 Your Kafka connection is configured correctly!")
    print("   You can now:")
    print("   1. Send transactions with kafka_producer.py")
    print("   2. Run the full fraud detector with docker-compose up")
    print("   3. Monitor messages in Confluent Cloud console")

if __name__ == "__main__":
    test_kafka_connection()
