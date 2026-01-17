"""
Master Test Runner
Run all tests in sequence with comprehensive reporting
"""

import sys
import os
import subprocess
import time
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

# Test suites
INFRASTRUCTURE_TESTS = [
    ('test_openai_connection.py', 'OpenAI API Connection', False),
    ('test_kafka_connection.py', 'Kafka Connection', False),
]

UNIT_TESTS = [
    ('test_redis_memory.py', 'Redis Memory Manager', True),
    ('test_qdrant_knowledge.py', 'Qdrant Knowledge Base', True),
    ('test_ml_detector.py', 'ML Fraud Detector', False),
    ('test_velocity_detector.py', 'Velocity Detector', False),
    ('test_agents.py', 'CrewAI Agents', False),
]

INTEGRATION_TESTS = [
    ('test_fraud_orchestrator.py', 'Fraud Orchestrator Integration', True),
]

E2E_TESTS = [
    ('test_e2e_mock.py', 'End-to-End with Mock Data', True),
]

def run_test(test_file, test_name, requires_services):
    """Run a single test and return results"""

    print(f"\n{'='*70}")
    print(f"🧪 Running: {test_name}")
    print(f"{'='*70}")

    if requires_services:
        print("   ℹ️ This test requires Redis/Qdrant services running")

    test_path = os.path.join(os.path.dirname(__file__), test_file)

    if not os.path.exists(test_path):
        print(f"   ⚠️ Test file not found: {test_file}")
        return {
            'name': test_name,
            'status': 'SKIPPED',
            'duration': 0,
            'error': 'File not found'
        }

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per test
        )

        duration = time.time() - start_time

        # Print output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Determine status
        if result.returncode == 0:
            status = 'PASSED'
        else:
            status = 'FAILED'

        return {
            'name': test_name,
            'status': status,
            'duration': duration,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"   ❌ Test timed out after {duration:.1f} seconds")
        return {
            'name': test_name,
            'status': 'TIMEOUT',
            'duration': duration,
            'error': 'Test exceeded 2 minute timeout'
        }

    except Exception as e:
        duration = time.time() - start_time
        print(f"   ❌ Test execution failed: {e}")
        return {
            'name': test_name,
            'status': 'ERROR',
            'duration': duration,
            'error': str(e)
        }

def run_test_suite(suite_name, tests, skip_on_failure=False):
    """Run a suite of tests"""

    print(f"\n{'#'*70}")
    print(f"# {suite_name}")
    print(f"{'#'*70}")

    results = []

    for test_file, test_name, requires_services in tests:
        result = run_test(test_file, test_name, requires_services)
        results.append(result)

        # If critical test fails, stop
        if skip_on_failure and result['status'] != 'PASSED':
            print(f"\n⚠️ Critical test failed, skipping remaining tests in this suite")
            break

    return results

def print_summary(all_results):
    """Print test summary"""

    print(f"\n{'='*70}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*70}")

    total_tests = len(all_results)
    passed = sum(1 for r in all_results if r['status'] == 'PASSED')
    failed = sum(1 for r in all_results if r['status'] == 'FAILED')
    skipped = sum(1 for r in all_results if r['status'] == 'SKIPPED')
    timeout = sum(1 for r in all_results if r['status'] == 'TIMEOUT')
    error = sum(1 for r in all_results if r['status'] == 'ERROR')

    total_duration = sum(r['duration'] for r in all_results)

    print(f"\n📈 Results:")
    print(f"   Total Tests:    {total_tests}")
    print(f"   ✅ Passed:      {passed}")
    print(f"   ❌ Failed:      {failed}")
    print(f"   ⏭️  Skipped:     {skipped}")
    print(f"   ⏱️  Timeout:     {timeout}")
    print(f"   ⚠️  Error:       {error}")
    print(f"\n⏱️  Total Duration: {total_duration:.2f} seconds")

    print(f"\n📋 Detailed Results:")
    for result in all_results:
        status_emoji = {
            'PASSED': '✅',
            'FAILED': '❌',
            'SKIPPED': '⏭️',
            'TIMEOUT': '⏱️',
            'ERROR': '⚠️'
        }.get(result['status'], '❓')

        print(f"   {status_emoji} {result['name']:<40} {result['status']:<10} ({result['duration']:.2f}s)")

    # Overall status
    print(f"\n{'='*70}")
    if failed == 0 and timeout == 0 and error == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\n💡 Check individual test output above for details")
        return 1

def main(ci_mode=False):
    """Main test runner"""

    print(f"\n{'#'*70}")
    print(f"# Option C Fraud Detection - Test Suite")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    if ci_mode:
        print("\n🤖 Running in CI mode (non-interactive)")

    all_results = []

    # Phase 1: Infrastructure Tests
    print("\n\n📡 PHASE 1: INFRASTRUCTURE TESTS")
    print("Testing external service connections...")
    infra_results = run_test_suite("Infrastructure Tests", INFRASTRUCTURE_TESTS)
    all_results.extend(infra_results)

    # Check if infrastructure is ready
    infra_failed = any(r['status'] != 'PASSED' for r in infra_results)
    if infra_failed and not ci_mode:
        print("\n⚠️ Infrastructure tests failed. Continue anyway? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("\n❌ Test run cancelled")
            return 1

    # Phase 2: Unit Tests
    print("\n\n🔧 PHASE 2: UNIT TESTS")
    print("Testing individual components...")
    unit_results = run_test_suite("Unit Tests", UNIT_TESTS)
    all_results.extend(unit_results)

    # Phase 3: Integration Tests
    print("\n\n🔗 PHASE 3: INTEGRATION TESTS")
    print("Testing components working together...")

    if not ci_mode:
        print("\n⚠️ Integration tests will use OpenAI API credits. Continue? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("\n⏭️ Skipping integration tests")
            integration_results = []
        else:
            integration_results = run_test_suite("Integration Tests", INTEGRATION_TESTS)
            all_results.extend(integration_results)
    else:
        print("⏭️ Skipping integration tests in CI mode (requires OpenAI credits)")

    # Phase 4: E2E Tests
    print("\n\n🚀 PHASE 4: END-TO-END TESTS")
    print("Testing full pipeline with mock data...")
    e2e_results = run_test_suite("End-to-End Tests", E2E_TESTS)
    all_results.extend(e2e_results)

    # Print summary
    exit_code = print_summary(all_results)

    if exit_code == 0:
        print("\n🎉 All tests passed! Your fraud detection system is ready!")
        print("\n📝 Next steps:")
        print("   1. Review test output above for any warnings")
        print("   2. Configure .env with production credentials")
        print("   3. Run: docker-compose up -d")
        print("   4. Monitor with: docker-compose logs -f fraud-detector")
    else:
        print("\n💡 Some tests failed. Review output above and fix issues.")
        print("\n🔧 Common fixes:")
        print("   - Start services: docker-compose up -d redis qdrant")
        print("   - Check .env file has all required variables")
        print("   - Verify OpenAI API key is valid")
        print("   - Ensure Kafka credentials are correct")

    return exit_code

if __name__ == "__main__":
    # Check for CI mode flag
    ci_mode = '--ci-mode' in sys.argv or '--ci' in sys.argv

    exit_code = main(ci_mode=ci_mode)
    sys.exit(exit_code)
