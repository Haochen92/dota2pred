# Dota Oracle: Real-Time Match Prediction Platform

A microservices platform that predicts Dota 2 match outcomes in real time. It ingests live match data from the Steam API, engineers time-decayed features from player and hero histories, runs inference through trained classifiers, and streams predictions to a React frontend via SSE. It also serves an interactive draft predictor and a model-performance dashboard, and optionally captures betting-market odds for offline paper-betting analysis.

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

The central real-time pipeline. Runs as a Prefect flow on a 2-minute polling cycle. Each cycle begins with a DLQ retry sweep, then processes matches through five stages connected by Redis Streams with consumer groups:

```
Steam API ─► New Match Detection ─► Feature Engineering ─► Prediction ─► Completion ─► Odds Capture
                  │                       │                    │             │            (optional)
                  ▼                       ▼                    ▼             ▼              ▼
             STREAM_NEW_           STREAM_PENDING_       STREAM_PENDING_  Match outcome  STREAM_PENDING_
             MATCHES               PREDICTION            COMPLETION       stored         ODDS
```

Each stage follows the same pattern: **Data Provider** (reads from stream/API) → **Event Processor** (business logic) → **Orchestrator** (coordinates and publishes to the next stream).

Key design decisions:
- **Redis Streams with consumer groups** — at-least-once delivery with ACKs, combined with idempotent `INSERT...ON CONFLICT` upserts to make reprocessing safe (effective exactly-once).
- **Dead Letter Queue with automatic retry** — failed events are moved to per-stage DLQ hashes. A `DlqRetryService` sweeps all DLQ hashes at the start of each cycle, reinjecting events that haven't exhausted their retry limit (default 3). Retry counts are tracked in a separate Redis hash (`dlq:retry_counts`) to decouple retry logic from the failure-recording path. Events that exceed max retries remain in the DLQ for manual inspection via a CLI tool.
- **Concurrent event processing** within each stage using `TaskRunner` with semaphore-based concurrency.
- **Stale event recovery** — events stuck for >90 minutes are reclaimed with exponential backoff (5 retries).
- **Isolated terminal odds stage** — the optional odds-capture stage (see below) has its own stream and consumer group and never writes the shared match-status hash, so it cannot interfere with the prediction path. It is gated by `ODDS_CAPTURE_ENABLED` (off by default).
- **DI container** (`dependency-injector`) wires all clients, services, and orchestrators, making the dependency graph explicit and testable.

### Odds Capture & Paper-Betting (optional, off by default)

When `ODDS_CAPTURE_ENABLED` is set, the fifth pipeline stage snapshots Polymarket order-book odds for a pro match at the moment its draft-time prediction is generated, storing them in `match_odds_snapshots`. A separate daily Prefect flow (`paper_bet_replay`, 07:00) joins those snapshots with model predictions and final outcomes and replays a betting rule (edge threshold + fractional Kelly, with a configurable confidence floor) to record hypothetical profit/loss in `match_paper_bets`. No real money is involved; capture and decision are decoupled so the rule can be re-tuned and replayed without re-fetching. Results are surfaced on a Grafana dashboard.

### API Service (`services/api_service/`)

FastAPI gateway with three main concerns:

- **Inference endpoints** (`/inference/`) — accept hero drafts, transform features via the shared pipeline package, call BentoML, return predictions.
- **Match data** (`/matches/`) — paginated match history with eager-loaded relationships (`selectinload`) to avoid N+1 queries.
- **Live streaming** (`/streaming/`) — SSE endpoint backed by a `PubSubHub` that fans out Redis pub/sub messages to connected clients. Sends a cached snapshot on connect, then streams updates with a 30s heartbeat.

Request-scoped database sessions with automatic commit/rollback. App-scoped singletons for Redis, HTTP clients, and service instances managed via FastAPI's lifespan context manager.

### Scheduler (`dota_oracle_schedules/`)

Prefect-based batch ETL for data that doesn't need real-time processing. All flows are deployed to the `dota_oracle_scheduler` work pool.

| Schedule (UTC) | Flow | Purpose |
|---|---|---|
| Every 3h | `fetch_completed_matches` | Ingest completed-match outcomes from OpenDota (skips already-stored, falls back to paid key on 429) |
| 00:30, 12:30 | `scheduled_feature_engineering_and_inference_backfill` | Generate features and run inference for newly completed matches |
| 01:00, 13:00 | `fetch_heros_data` | Sync hero metadata |
| 02:00, 14:00 | `fetch_patch_data` | Sync patch metadata |
| 03:00 | `fetch_league_data` | Sync league metadata |
| 05:00 | `collect_public_matches_incremental` | Daily top-up of public matches (feeds the public model's win-rate feature) |
| 07:00 | `paper_bet_replay` | Replay the paper-betting rule over captured odds (active only when odds capture is enabled) |
| Every 3 days, 02:00 | `clear_prefect_cache` | Maintenance |
| Manual | `sync_pro_matches`, `backfill_public_matches_by_patches`, `backup_db` | On-demand flows (no schedule) |

The feature-engineering/inference backfill is the most involved flow: it determines feature coverage gaps, warms up decay-state history (5× the 60-day half-life ≈ 300 days), processes in 2000-match batches, and runs inference on the backfilled features.

### ML Inference (`services/inference_service/`)

BentoML service hosting two scikit-learn classifiers, each returning `P(radiant_win)` via `predict_proba`:
- `/predict/pro` — professional-match predictions (full match context: team, player-hero, hero, and matchup features).
- `/predict/public` — public-match / draft predictions (hero-only features, since a draft is all the input available).

The API service prepares features; BentoML handles raw inference only. Both models compute their features at request time from recent match history rather than encoding patch-specific patterns in their weights, so they are not retrained on a per-patch cadence. The professional model has held ~57–58% accuracy (Brier ≈ 0.24) across patches over roughly a year.

### Frontend (`frontend/`)

Next.js 15 (App Router) with React 19, TypeScript, and Mantine v7:

- **Match Tracker** — live + historical matches in a unified paginated view. Live matches stream via SSE; completed matches are fetched via SWR with `keepPreviousData`.
- **Draft Predictor** — interactive hero draft tool. Pick 10 heroes, get a win-probability prediction.
- **Model History** — performance analytics with calibration plots, time-series accuracy, ROC-AUC, and Brier score (computed with pandas/sklearn on the backend), shown in a parallel-route intercepting modal.

State management: Zustand for global constants (heroes, patches, leagues), React Context for draft state, React Query + SWR for server state. Mobile-responsive with separate desktop/mobile component variants.

## Shared Packages

### `dota_oracle_common`

Data layer shared by all Python services:

- **Models** — SQLModel tables (ORM + Pydantic validation in one class). Schema/table split: Pydantic DTOs for API contracts, SQLModel classes for persistence.
- **Repositories** — generic `BaseRepository` with batched inserts, upserts (`INSERT...ON CONFLICT`), time-range queries, and eager-loading. Specialized repositories per domain entity.
- **Infrastructure** — async PostgreSQL (SQLAlchemy), Redis connection pooling, S3 client, HTTP client provider, Loki-integrated logging.

### `dota_oracle_pipeline`

ETL and feature engineering:

- **Extraction** — async clients for the Steam Web API, OpenDota API, and Polymarket, with retry logic (tenacity) and rate limiting.
- **Feature Engineering** — time-decayed features:
  - **Hero features**: global hero win rates with exponential decay (configurable half-life).
  - **Team features**: team win rates + head-to-head matchup history with Bayesian priors.
  - **Player-hero features**: per-player hero proficiency with two-level Bayesian smoothing (player prior → hero prior → global prior).
- **Inference** — client for BentoML with retry and backoff.

The decay formula uses configurable half-lives to weight recent matches more heavily. History state is stored per-entity per-match for causally correct "time-travel" feature lookups, using only information available at prediction time to avoid data leakage.

## Testing

Test files across five levels, plus shared test infrastructure:

```
tests/
├── unit_test/      47 files — business logic, feature engineering, services
├── integration/    39 files — real PostgreSQL + Redis via TestContainers
├── end_to_end/      6 files — full Docker Compose stack
├── contract/        4 files — external API contract validation
├── factories/       5 files — Polyfactory-based test data generation
└── fixtures/       13 files — pytest fixture infrastructure
```

CI runs on every push/PR: Ruff → Black → MyPy → unit tests → integration tests → E2E tests.

## Infrastructure

- **Docker Compose** with multi-stage builds (slim Python base, separate build/runtime stages).
- **Caddy** reverse proxy with Cloudflare origin TLS certificates.
- **Alembic** for database migrations.
- **Grafana + Loki** for centralized logging and dashboards (pipeline health, model performance, paper-betting).
- **Pre-commit hooks**: Black, Ruff, YAML validation, large-file checks.

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
The `prefect-server` container gradually grows in memory over time, from ~200MB at startup to several GB over days — a known upstream issue with the Prefect scheduler.

**Mitigation**: a `mem_limit: 512m` is set on the container in `docker-compose.yml`. When the container exceeds this limit, Docker OOM-kills it and `restart: always` brings it back up within ~10–15 seconds. In the worst case this drops one 2-minute polling cycle. The scheduling flows and workers in `live-orchestrator-app` are unaffected during the restart.

## License

This project is for portfolio demonstration purposes.
