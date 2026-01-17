# Production-Grade Fraud Detection System

A production-ready, AI-powered fraud detection system featuring multi-layered analysis with ML, velocity detection, persistent memory, vector search, and autonomous AI agents.

## Features

- **ML-Based Detection** - Isolation Forest anomaly detection
- **Velocity Detection** - Rapid-fire and card-testing detection
- **Redis Memory** - Cross-transaction user & IP flagging
- **Qdrant RAG** - Vector similarity search for fraud patterns
- **AI Agents** - Autonomous investigation with CrewAI or Agno frameworks
- **Langfuse Observability** - Real-time cost & performance monitoring
- **Health API** - Kubernetes-ready health endpoints
- **Fault Tolerance** - Circuit breakers and retry handlers
- **Docker Ready** - One-command containerized deployment

## Tech Stack

| Component | Technology |
|-----------|------------|
| **ML** | scikit-learn (Isolation Forest) |
| **AI Agents** | Agno 2.3+, CrewAI |
| **LLM** | OpenAI GPT |
| **Streaming** | Apache Kafka (Confluent Cloud) |
| **Memory** | Redis |
| **Vector DB** | Qdrant |
| **Database** | PostgreSQL (Supabase) |
| **Observability** | Langfuse |
| **Validation** | Pydantic |
| **Container** | Docker |

## Architecture

```
┌─────────┐
│  Kafka  │    ┌────────────────────────────────────────────────────────────┐
│ (Input) │───▶│                   FRAUD ORCHESTRATOR                       │
└─────────┘    │                                                            │
               │  ┌──────────────────────────────────────────────────────┐  │
               │  │              DETECTION LAYER (Sequential)            │  │
               │  │                                                      │  │
               │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
               │  │  │ 1. Redis    │  │ 2. Velocity │  │ 3. ML       │  │  │
               │  │  │   CHECK     │─▶│   Detector  │─▶│   Detector  │  │  │
               │  │  │             │  │             │  │             │  │  │
               │  │  │ • User flag │  │ • Rapid-fire│  │ • Isolation │  │  │
               │  │  │ • IP flag   │  │ • Card test │  │   Forest    │  │  │
               │  │  │ • Tx count  │  │ • Velocity  │  │ • Score 0-1 │  │  │
               │  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
               │  │                                           │         │  │
               │  │                         ┌─────────────────┘         │  │
               │  │                         ▼                           │  │
               │  │                 ┌─────────────┐                     │  │
               │  │                 │ 4. Qdrant   │                     │  │
               │  │                 │   QUERY     │                     │  │
               │  │                 │             │                     │  │
               │  │                 │ • Similar   │                     │  │
               │  │                 │   cases     │                     │  │
               │  │                 │ • 10 fraud  │                     │  │
               │  │                 │   patterns  │                     │  │
               │  │                 └──────┬──────┘                     │  │
               │  └────────────────────────┼────────────────────────────┘  │
               │                           ▼                               │
               │          ┌─────────────────────────────────┐              │
               │          │    5. SCORE = ML + Velocity     │              │
               │          │         + Redis + Qdrant        │              │
               │          └─────────────────┬───────────────┘              │
               │                            │                              │
               │            ┌───────────────┼───────────────┐              │
               │            ▼               ▼               ▼              │
               │       ┌────────┐     ┌──────────┐    ┌──────────┐         │
               │       │APPROVE │     │ REVIEW   │    │ AGENT    │         │
               │       │ <0.40  │     │0.40-0.70 │    │  >0.70   │         │
               │       └────────┘     └──────────┘    └────┬─────┘         │
               │                                           │               │
               │  ┌────────────────────────────────────────┼────────────┐  │
               │  │           6. AI AGENTS (High Risk Only)│            │  │
               │  │                                        ▼            │  │
               │  │    ┌──────────────┐ ┌────────────┐ ┌──────────┐    │  │
               │  │    │Investigation │▶│   Risk     │▶│ Decision │    │  │
               │  │    │    Agent     │ │   Agent    │ │  Agent   │    │  │
               │  │    └──────────────┘ └────────────┘ └──────────┘    │  │
               │  │                                                     │  │
               │  │    Tools: transaction_analysis, fraud_history,      │  │
               │  │    similar_cases, velocity_check, user_reputation,  │  │
               │  │    fraud_decision                                   │  │
               │  └─────────────────────────────────────────────────────┘  │
               │                            │                              │
               │  ┌─────────────────────────┼───────────────────────────┐  │
               │  │      UPDATE LAYER       │                           │  │
               │  │                         ▼                           │  │
               │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
               │  │  │ 7. Redis    │  │ 8. Qdrant   │  │  Langfuse   │  │  │
               │  │  │   UPDATE    │  │   UPDATE    │  │   TRACK     │  │  │
               │  │  │             │  │             │  │             │  │  │
               │  │  │ • Record tx │  │ • Add fraud │  │ • Costs     │  │  │
               │  │  │ • Flag user │  │   pattern   │  │ • Latency   │  │  │
               │  │  │ • Flag IP   │  │   if >=0.9  │  │ • Metrics   │  │  │
               │  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
               │  └─────────────────────────────────────────────────────┘  │
               └────────────────────────────┬───────────────────────────────┘
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               │                            ▼                            │
               │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
               │  │    Kafka    │    │  Supabase   │    │ Health API  │  │
               │  │  (Output)   │    │ (Postgres)  │    │             │  │
               │  │             │    │             │    │ • /health   │  │
               │  │ • Results   │    │ • transactions  │ • /metrics  │  │
               │  │ • Decisions │    │ • results   │    │ • /stats    │  │
               │  │             │    │ • agent_    │    │             │  │
               │  │             │    │   analysis  │    │             │  │
               │  └─────────────┘    └─────────────┘    └─────────────┘  │
               └─────────────────────────────────────────────────────────┘
```

**Pipeline:** Redis Check → Velocity → ML → Qdrant Query → Score → Triage → Agents (if >0.70) → Update Memory → Output

## Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd fraud-detection-system

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your credentials (OpenAI, Kafka, Supabase, etc.)
```

### 2. Start with Docker

```bash
docker-compose up -d
```

This starts:
- Fraud detection service
- Redis (persistent memory)
- Qdrant (vector database)

### 3. Verify Health

```bash
curl http://localhost:8080/health
```

## Directory Structure

```
├── src/
│   ├── config/
│   │   └── settings.py              # Environment-based configuration
│   │
│   ├── fraud_detection/
│   │   ├── fraud_orchestrator.py    # Main orchestration logic
│   │   ├── ml_detector.py           # Isolation Forest ML model
│   │   ├── velocity_detector.py     # Rapid-fire & card-testing detection
│   │   └── rate_limiter.py          # API rate limiting
│   │
│   ├── agents/                      # CrewAI agent implementation
│   │   ├── crew_manager.py          # CrewAI agent management
│   │   └── prompts/                 # Agent prompt templates
│   │       ├── pattern_detector.md
│   │       ├── risk_quantifier.md
│   │       └── decision_authority.md
│   │
│   ├── agents_agno/                 # Agno agent implementation (recommended)
│   │   ├── fraud_agent_manager.py   # Agno agent orchestration
│   │   ├── agno_crew_adapter.py     # CrewAI compatibility layer
│   │   ├── base_agent.py            # Base agent class
│   │   ├── agents/
│   │   │   ├── investigation_agent.py
│   │   │   ├── risk_agent.py
│   │   │   └── decision_agent.py
│   │   ├── tools/                   # Agent tools
│   │   │   ├── transaction_analysis_tool.py
│   │   │   ├── fraud_history_tool.py
│   │   │   ├── similar_cases_tool.py
│   │   │   ├── velocity_check_tool.py
│   │   │   ├── user_reputation_tool.py
│   │   │   └── fraud_decision_tool.py
│   │   └── config/prompts/          # Agno prompt templates
│   │
│   ├── memory/
│   │   ├── redis_memory.py          # Redis persistent memory
│   │   └── qdrant_knowledge.py      # Vector database RAG
│   │
│   ├── database/
│   │   └── supabase_writer.py       # PostgreSQL persistence
│   │
│   ├── api/
│   │   └── health_server.py         # Health & metrics endpoints
│   │
│   ├── models/
│   │   └── transaction_models.py    # Pydantic data validation
│   │
│   ├── observability/
│   │   └── langfuse_monitor.py      # Cost & performance tracking
│   │
│   └── utils/
│       ├── circuit_breaker.py       # Fault tolerance
│       └── retry_handler.py         # Retry with backoff
│
├── tests/                           # Test suite
│   ├── test_ml_detector.py
│   ├── test_velocity_detector.py
│   ├── test_fraud_orchestrator.py
│   ├── test_redis_memory.py
│   ├── test_qdrant_knowledge.py
│   ├── test_agents.py
│   ├── test_e2e_mock.py
│   ├── agno/
│   │   └── test_agno_agents.py
│   └── run_all_tests.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Components

### ML Detector
Uses Isolation Forest algorithm trained on synthetic fraud patterns to score transactions (0-1).

### Velocity Detector
Detects:
- **Rapid-fire orders**: Multiple transactions within milliseconds
- **Card testing**: 3+ small orders within 5 minutes from same user

### Redis Memory
Persistent cross-transaction context:
- User flagging (24-hour expiry)
- IP reputation tracking (7-day window)
- Transaction history (1-hour rolling window)

### Qdrant RAG
Vector similarity search with 10 pre-loaded fraud patterns. Automatically learns from confirmed fraud cases.

### AI Agents
Two framework options:
- **Agno** (recommended): Production-grade with 6 specialized tools
- **CrewAI**: Legacy support with 3 agents (Pattern, Risk, Decision)

### Health API
Kubernetes-ready endpoints:
- `GET /health` - Overall health status
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

### Fault Tolerance
- **Circuit Breaker**: Prevents cascading failures (CLOSED → OPEN → HALF_OPEN)
- **Retry Handler**: Exponential backoff for transient failures

## Configuration

### Environment Variables

See `.env.example` for all options. Key settings:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-key

# Kafka (Confluent Cloud)
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.cloud:9092
KAFKA_API_KEY=your-key
KAFKA_API_SECRET=your-secret

# PostgreSQL (Supabase)
POSTGRES_CONNECTION_STRING=postgresql://...

# Redis
REDIS_URL=redis://localhost:6379

# Qdrant
QDRANT_URL=http://localhost:6333

# Fraud Thresholds
FRAUD_BLOCK_THRESHOLD=0.70    # Score to block transaction
FRAUD_REVIEW_THRESHOLD=0.40   # Score for manual review

# Rate Limiting
MAX_AI_REQUESTS_PER_MIN=20
AI_REQUEST_DELAY_SEC=3.0

# Agent Framework
USE_AGNO_AGENTS=true          # true=Agno, false=CrewAI
```

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_ml_detector.py

# Run with coverage
python -m pytest tests/ --cov=src
```

## Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale fraud detectors
docker-compose up -d --scale fraud-detector=3

# Stop services
docker-compose down
```

## Health Monitoring

```bash
# Check health
curl http://localhost:8080/health

# Prometheus metrics
curl http://localhost:8080/metrics

# Redis status
docker exec -it redis redis-cli DBSIZE

# Qdrant status
curl http://localhost:6333/collections
```

## Requirements

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- Kafka cluster (Confluent Cloud)
- PostgreSQL database (Supabase)

## License

MIT
