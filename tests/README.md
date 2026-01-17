# Test Suite for Option C Fraud Detection

Comprehensive test suite covering all components of the fraud detection system.

## Quick Start

### 1. Run Quick Start Test (Recommended First Step)

```bash
cd projC
python tests/quick_start_test.py
```

This verifies:
- ✅ Python version
- ✅ Docker installation
- ✅ Environment configuration
- ✅ Python dependencies
- ✅ Docker services running

### 2. Run Individual Tests

After quick start passes, test components one by one:

```bash
# Test Redis memory
python tests/test_redis_memory.py

# Test Qdrant knowledge base
python tests/test_qdrant_knowledge.py

# Test ML detector
python tests/test_ml_detector.py

# Test velocity detector
python tests/test_velocity_detector.py

# Test agents (requires OpenAI credits)
python tests/test_agents.py
```

### 3. Run Full Test Suite

```bash
# Interactive mode (prompts before using OpenAI credits)
python tests/run_all_tests.py

# CI mode (skips interactive prompts and credit-using tests)
python tests/run_all_tests.py --ci-mode
```

## Test Categories

### Infrastructure Tests (No OpenAI Credits)

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_openai_connection.py` | Verify OpenAI API key | OpenAI API key |
| `test_kafka_connection.py` | Verify Kafka connectivity | Kafka credentials |

### Unit Tests

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_redis_memory.py` | Redis memory manager | Redis running |
| `test_qdrant_knowledge.py` | Qdrant vector DB | Qdrant running |
| `test_ml_detector.py` | ML fraud scoring | None |
| `test_velocity_detector.py` | Velocity detection | None |
| `test_agents.py` | CrewAI agents | OpenAI API key |

### Integration Tests (Uses OpenAI Credits!)

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_fraud_orchestrator.py` | Full system integration | All services + OpenAI |

### End-to-End Tests

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_e2e_mock.py` | Full pipeline with mocks | Redis + Qdrant |

## Test Requirements

### Required Services

Start services before running tests:

```bash
# Start Redis and Qdrant
docker-compose up -d redis qdrant

# Verify they're running
docker-compose ps
```

### Environment Variables

Ensure `.env` file has:

```bash
# Required for most tests
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# Required for Kafka tests
KAFKA_BOOTSTRAP_SERVERS=...
KAFKA_API_KEY=...
KAFKA_API_SECRET=...

# Required for database tests
POSTGRES_CONNECTION_STRING=postgresql://...
```

## Cost Estimates

| Test | OpenAI Credits | Notes |
|------|----------------|-------|
| Infrastructure tests | $0 | No API calls |
| Unit tests (no agents) | $0 | No API calls |
| `test_agents.py` | ~$0.02 | 1-2 API calls |
| `test_fraud_orchestrator.py` | ~$0.10 | 3-6 API calls |
| `test_e2e_mock.py` | $0 | Uses mocks |
| Full test suite | ~$0.15 | Total for all tests |

## Troubleshooting

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Test connection
docker exec redis-fraud-optionc redis-cli ping
```

### Qdrant Connection Failed

```bash
# Check Qdrant is running
docker-compose ps qdrant

# View Qdrant logs
docker-compose logs qdrant

# Test connection
curl http://localhost:6333/collections
```

### OpenAI API Errors

```bash
# Verify key is set
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key:', os.getenv('OPENAI_API_KEY')[:10] + '...')"

# Test connection
python tests/test_openai_connection.py
```

### Import Errors

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install specific package
pip install redis qdrant-client openai crewai
```

## Test Coverage

Current test coverage:

- **Redis Memory**: 100% (6/6 features tested)
- **Qdrant KB**: 100% (6/6 features tested)
- **ML Detector**: 80% (4/5 features tested)
- **Velocity Detector**: 100% (3/3 patterns tested)
- **Agents**: 90% (agent setup + prompts tested)
- **Orchestrator**: 90% (7/8 workflows tested)
- **E2E Pipeline**: 80% (mock data tested)

## CI/CD Integration

For automated testing in CI/CD:

```bash
# Non-interactive mode that exits with proper code
python tests/run_all_tests.py --ci-mode

# Check exit code
echo $?  # 0 = success, 1 = failure
```

### GitHub Actions Example

```yaml
name: Test Fraud Detection

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

      qdrant:
        image: qdrant/qdrant
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          REDIS_URL: redis://localhost:6379
          QDRANT_URL: http://localhost:6333
        run: |
          python tests/run_all_tests.py --ci-mode
```

## Writing New Tests

### Test Template

```python
"""
Test [Component Name]
Description of what this test does
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_component():
    """Test component functionality"""

    print("\n" + "="*70)
    print("🧪 TESTING [COMPONENT NAME]")
    print("="*70)

    print("\n🧪 Test 1: [Test description]")
    try:
        # Test code here
        print("✅ Test 1 passed")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)

if __name__ == "__main__":
    test_component()
```

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Review test output for specific error messages
3. Refer to main README.md for service-specific troubleshooting
4. Check `.env` file has all required variables

---

**Last Updated**: 2026-01-05
