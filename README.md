# Dota Oracle: Real-Time Match Prediction Platform

A microservices platform that predicts Dota 2 match outcomes in real time. It ingests live match data from the Steam API, engineers time-decayed features from player and hero histories, runs inference through a trained classifier, and streams predictions to a React frontend via SSE.

## Architecture

```
                         ┌──────────────────────────────────────┐
                         │           Caddy (Reverse Proxy)      │
                         └──────┬──────────────────┬────────────┘
                                │                  │
                    ┌───────────▼──────┐  ┌────────▼──────────┐
                    │  Frontend        │  │  API Service       │
                    │  Next.js 15      │  │  FastAPI           │
                    │  React 19 + TS   │  │  SSE Streaming     │
                    └──────────────────┘  └───┬──────────┬─────┘
                                              │          │
              ┌───────────────────────────────┘          │
              ▼                                          ▼
   ┌─────────────────────┐                  ┌────────────────────┐
   │  BentoML Inference  │                  │  Redis             │
   │  Pro + Public models│                  │  Streams / PubSub  │
   └─────────────────────┘                  └──────┬─────────────┘
                                                   │
                               ┌───────────────────┼───────────────────┐
                               ▼                   ▼                   ▼
                    ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
                    │  Live            │ │  Scheduler        │ │  Prefect Server  │
                    │  Orchestrator    │ │  (Batch ETL)      │ │  (Coordination)  │
                    └────────┬─────────┘ └────────┬─────────┘ └──────────────────┘
                             │                    │
                             ▼                    ▼
                    ┌─────────────────────────────────────────┐
                    │  PostgreSQL 14                          │
                    │  Matches, Features, Predictions, State  │
                    └─────────────────────────────────────────┘
```

**Networking**: Services run on an internal Docker bridge network (`dota-pred`). Only the API service and frontend are exposed to the external `shared-caddy-network` for reverse-proxy routing. Grafana, pgAdmin, and Prefect UI are also exposed for observability.

## Core Services

### Live Orchestrator (`live_orchestrator_app/`)

The central real-time pipeline. Runs as a Prefect flow on a 2-minute polling cycle, processing matches through 4 sequential stages connected by Redis Streams with consumer groups:

```
Steam API ──► New Match Detection ──► Feature Engineering ──► Prediction ──► Completion
                  │                        │                     │              │
                  ▼                        ▼                     ▼              ▼
             Redis Stream:            Redis Stream:         Redis Stream:   Match outcome
             STREAM_NEW_MATCHES       STREAM_PENDING_       STREAM_PENDING_ stored, history
                                      PREDICTION            COMPLETION      tables updated
```

Each stage follows the same pattern: **Data Provider** (reads from stream/API) → **Event Processor** (business logic) → **Orchestrator** (coordinates and publishes to next stream).

Key design decisions:
- **Redis Streams with consumer groups** for exactly-once processing semantics via ACKs
- **Dead Letter Queue** per stage — failed events are moved to DLQ hashes rather than blocking the pipeline
- **Concurrent event processing** within each stage using `TaskRunner` with semaphore-based concurrency
- **Stale event recovery** — events stuck for >90 minutes are automatically reclaimed with exponential backoff (5 retries)
- **DI container** (`dependency-injector`) wires all clients, services, and orchestrators — makes the dependency graph explicit and testable

### API Service (`services/api_service/`)

FastAPI gateway with three main concerns:

- **Inference endpoints** (`/inference/`) — accepts hero drafts, transforms features via the shared pipeline package, calls BentoML, returns predictions
- **Match data** (`/matches/`) — paginated match history with eager-loaded relationships (`selectinload`) to avoid N+1 queries
- **Live streaming** (`/streaming/`) — SSE endpoint backed by a `PubSubHub` that fans out Redis pub/sub messages to connected clients. Sends cached snapshot on connect, then streams updates with 30s heartbeat

Request-scoped database sessions with automatic commit/rollback. App-scoped singletons for Redis, HTTP clients, and service instances managed via FastAPI's lifespan context manager.

### Scheduler (`dota_oracle_schedules/`)

Prefect-based batch ETL for data that doesn't need real-time processing:

| Schedule | Flow | Purpose |
|---|---|---|
| 00:00, 12:00 | `fetch_completed_matches` | Ingest match outcomes from OpenDota |
| 00:30, 12:30 | `feature_engineering_backfill` | Generate features for newly completed matches |
| 01:00, 13:00 | `fetch_hero_data` | Sync hero metadata |
| 02:00, 14:00 | `fetch_patch_data` | Sync patch metadata |
| 03:00 | `fetch_league_data` | Sync league metadata |
| Fridays | `collect_public_matches` | Weekly public match collection for training data |
| Every 3 days | `clear_prefect_cache` | Maintenance |

The backfill pipeline is the most complex flow — it determines feature coverage gaps, warms up decay state history (5x half-life window = 300 days), processes in 2000-match batches, and runs inference on the backfilled features.

Scheduling uses separate Prefect work pools: `dota_oracle_scheduler` for batch jobs, `dota-work-pool` for live orchestration.

### ML Inference (`services/inference_service/`)

BentoML service hosting two scikit-learn classifiers:
- `/predict/pro` — professional match predictions
- `/predict/public` — public match predictions

Each model returns `P(radiant_win)` via `predict_proba`. The API service handles feature preparation; BentoML only handles raw inference.

### Frontend (`frontend/`)

Next.js 15 (App Router) with React 19, TypeScript, and Mantine v7:

- **Match Tracker** — live + historical matches in a unified paginated view. Live matches stream via SSE; completed matches fetched via SWR with `keepPreviousData`
- **Draft Predictor** — interactive hero draft tool. Pick 10 heroes, get a real-time win probability prediction
- **Model History** — performance analytics dashboard with calibration plots, time-series accuracy, ROC-AUC, and Brier score (computed from pandas/sklearn on the backend)

State management: Zustand for global constants (heroes, patches, leagues), React Context for draft state, React Query + SWR for server state. Mobile-responsive with separate desktop/mobile component variants.

## Shared Packages

### `dota_oracle_common`

Data layer shared by all Python services:

- **Models** — SQLModel tables (ORM + Pydantic validation in one class). Schema/table split: Pydantic DTOs for API contracts, SQLModel classes for persistence
- **Repositories** — generic `BaseRepository` with batched inserts, upserts (`INSERT...ON CONFLICT`), time-range queries, and eager-loading. Specialized repositories per domain entity
- **Infrastructure** — async PostgreSQL (SQLAlchemy), Redis connection pooling, S3 client, HTTP client provider, Loki-integrated logging

### `dota_oracle_pipeline`

ETL and feature engineering:

- **Extraction** — async clients for Steam Web API and OpenDota API with retry logic (tenacity) and rate limiting
- **Feature Engineering** — three-tier time-decayed features:
  - **Hero features**: global hero win rates with exponential decay (half-life configurable)
  - **Team features**: team win rates + head-to-head matchup history with Bayesian priors
  - **Player-hero features**: per-player hero proficiency with two-level Bayesian smoothing (player prior → hero prior → global prior)
- **Inference** — client for BentoML with retry and backoff

The decay formula uses configurable half-lives to weight recent matches more heavily. History state is stored per-entity per-match for causally correct "time-travel" feature lookups — preventing data leakage by only using information available at prediction time.

## Testing

92 test files across 4 levels:

```
tests/
├── unit_test/      27 files — business logic, feature engineering, services
├── integration/    33 files — real PostgreSQL + Redis via TestContainers
├── end_to_end/      5 files — full Docker Compose stack
├── contract/        1 file  — external API contract validation
├── factories/       4 files — Polyfactory-based test data generation
└── fixtures/       10 files — pytest fixture infrastructure
```

CI runs on every push/PR: Ruff → Black → MyPy → unit tests → integration tests → E2E tests.

## Infrastructure

- **Docker Compose** with multi-stage builds (slim Python base, separate build/runtime stages)
- **Caddy** reverse proxy with Cloudflare origin TLS certificates
- **Alembic** for database migrations
- **Grafana + Loki** for centralized logging
- **Pre-commit hooks**: Black, Ruff, YAML validation, large file checks

## Quick Start

```bash
# Start all services
docker-compose up -d

# Or start infrastructure only for local development
docker-compose up -d db redis loki grafana prefect-server

# Install Python dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start API service locally
poetry run uvicorn api_service.main:app --host 0.0.0.0 --port 8000

# Start frontend locally
cd frontend && npm install && npm run dev
```

### Running Tests

```bash
poetry run pytest tests/unit_test/             # Unit tests
poetry run pytest tests/integration/           # Integration (needs Docker)
poetry run pytest tests/end_to_end/            # E2E (needs full stack)
```

## Known Issues

### Prefect Server Memory Creep
The `prefect-server` container gradually leaks memory over time, growing from ~200MB at startup to several GB over days. This is a known upstream issue with the Prefect scheduler.

**Mitigation**: A `mem_limit: 512m` is set on the container in `docker-compose.yml`. When the container exceeds this limit, Docker OOM-kills it and `restart: always` brings it back up within ~10-15 seconds. This may cause one missed polling cycle (2-minute interval) in the worst case. The scheduling flows and workers in `live-orchestrator-app` are unaffected during the restart.

## License

This project is for portfolio demonstration purposes.
