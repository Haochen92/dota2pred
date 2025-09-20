# Dota Oracle: Real-Time Match Prediction Platform

A sophisticated microservices-based platform for real-time Dota 2 match prediction, featuring advanced machine learning pipelines, distributed architecture, and comprehensive monitoring capabilities.

## 🏗️ Architecture Overview

This project demonstrates enterprise-level software architecture through a distributed microservices ecosystem designed for scalability, maintainability, and reliability.

### System Architecture Diagram

```
┌─────────────────┐    ┌───────────────────┐    ┌─────────────────────┐
│   Frontend      │    │   API Gateway     │    │ Live Orchestrator   │
│   (Next.js)     │◄───┤   (FastAPI)       │    │ (Event-Driven)      │
└─────────────────┘    └───────────────────┘    └─────────────────────┘
         │                        │                         │
         │                        ▼                         │
         │              ┌───────────────────┐               │
         │              │ BentoML Inference │               │
         │              │    Service        │               │
         │              └───────────────────┘               │
         │                        │                         │
         ▼                        ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                        │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────────┐  │
│  │ PostgreSQL  │ │    Redis    │ │   Prefect Orchestration  │  │
│  │  Database   │ │   PubSub    │ │      Workflows           │  │
│  └─────────────┘ └─────────────┘ └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Microservices Architecture

### Core Services

#### 1. **API Service** (`services/api_service/`)
**FastAPI-based API Gateway**
- **Responsibility**: External API interface and request routing
- **Key Features**:
  - RESTful endpoints for match data and predictions
  - Real-time streaming via Server-Sent Events (SSE)
  - Redis pub/sub integration for live updates
  - Comprehensive dependency injection and lifecycle management
- **Endpoints**:
  - `/inference/` - Match prediction APIs
  - `/matches/` - Match data retrieval with pagination
  - `/streaming/` - Real-time match updates
- **Port**: 8000

#### 2. **Live Orchestrator App** (`live_orchestrator_app/`)
**Event-Driven Match Processing Pipeline**
- **Responsibility**: Real-time match data processing and prediction orchestration
- **Architecture**: Multi-stage pipeline with orchestrators for each phase
- **Processing Stages**:
  1. **New Match Detection**: Identifies and onboards live matches
  2. **Feature Engineering**: Transforms raw match data into ML features
  3. **Prediction**: Generates match outcome predictions using ML models
  4. **Completion**: Tracks match outcomes and updates predictions
- **Design Pattern**: Event-driven architecture with dependency injection container
- **Key Components**:
  - Data providers for each stage
  - Event processors for business logic
  - Orchestrators for workflow management

#### 3. **Data Scheduling Service** (`dota_oracle_schedules/`)
**Prefect-Based Data Pipeline**
- **Responsibility**: Scheduled batch data processing and maintenance
- **Workflows**:
  - Hero data synchronization (daily)
  - Completed match batch processing (bi-daily)
  - Cache maintenance and cleanup
- **Orchestration**: Prefect 3.x with cron scheduling
- **Deployment**: Automated deployment management

#### 4. **ML Inference Service** (`services/inference_service/`)
**BentoML Model Serving**
- **Responsibility**: Machine learning model hosting and inference
- **Technology**: BentoML for model deployment and serving
- **Models**: Separate endpoints for public and professional matches
- **Port**: 3333 (mapped from container port 3000)

#### 5. **Frontend Application** (`frontend/`)
**Next.js React Application**
- **Technology**: Next.js 15 with React 19
- **UI Framework**: Mantine components library
- **Features**:
  - Real-time match dashboard
  - Match history with pagination
  - Interactive match prediction simulator
  - Responsive design with modern UI components

## 📦 Shared Packages Architecture

### 1. **dota-oracle-common** (`packages/dota_oracle_common/`)
**Core Infrastructure Package**
- **Models**: Comprehensive data models using SQLModel/Pydantic
  - Hero data, match data, prediction schemas
  - API schemas and pagination models
  - Database table definitions
- **Repositories**: Generic repository pattern implementation
  - `BaseRepository` with common CRUD operations
  - Specialized repositories for each domain entity
  - PostgreSQL-specific optimizations (upserts, batch operations)
- **Infrastructure Components**:
  - Redis client factory and connection management
  - PostgreSQL connection management
  - HTTP client providers with proper lifecycle
  - Logging utilities and environment configuration

### 2. **dota-oracle-pipeline** (`packages/dota_oracle_pipeline/`)
**Data Processing and ML Pipeline**
- **Data Extraction**: API clients for Steam and OpenDota APIs
- **Data Transformation**: Raw data parsers and normalizers
- **Feature Engineering**:
  - Team-based feature creation
  - Player-hero combination features
  - Advanced preprocessing and encoding
- **ML Inference**: Model inference service with metadata handling

## 🎯 Design Principles & Patterns

### 1. **Microservices Architecture**
- **Separation of Concerns**: Each service handles a specific domain
- **Loose Coupling**: Services communicate via well-defined APIs and message queues
- **Independent Deployability**: Each service can be deployed and scaled independently

### 2. **Repository Pattern**
- **Data Access Abstraction**: Repository classes abstract database operations
- **Generic Base Implementation**: `BaseRepository` provides common CRUD operations
- **Type Safety**: Full TypeScript-like type safety with Python generics
- **Batch Operations**: Optimized batch inserts and upserts for performance

### 3. **Dependency Injection**
- **Container-Based IoC**: Using `dependency-injector` for sophisticated DI
- **Lifecycle Management**: Proper resource initialization and cleanup
- **Testing Support**: Easy mocking and testing through DI container overrides

### 4. **Event-Driven Architecture**
- **Pipeline Orchestration**: Multi-stage processing with clear event boundaries
- **Redis Pub/Sub**: Real-time communication between services
- **Workflow Management**: Prefect for complex workflow orchestration

### 5. **Infrastructure as Code**
- **Docker Compose**: Complete environment definition
- **Service Health Checks**: Comprehensive health monitoring
- **Development/Production Parity**: Consistent environments across stages

## 📊 Data Flow & Processing Complexity

### Real-Time Match Processing Pipeline

```
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ Live Match Data │───►│ Feature Engineering │───►│ ML Prediction    │
│ Ingestion       │    │ & Transformation    │    │ Generation       │
└─────────────────┘    └─────────────────────┘    └──────────────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ Data Validation │    │ Complex Feature     │    │ Result Storage   │
│ & Normalization │    │ Calculations        │    │ & Distribution   │
└─────────────────┘    └─────────────────────┘    └──────────────────┘
```

### Feature Engineering Complexity
- **Multi-dimensional Features**: Team compositions, player histories, hero synergies
- **Time-series Processing**: Historical performance trends and meta analysis
- **Real-time Calculations**: Dynamic feature generation during live matches
- **Advanced Encodings**: Custom encoding strategies for categorical gaming data

## 🧪 Comprehensive Testing Strategy

Our testing approach demonstrates enterprise-level quality assurance with **92 test files** covering multiple testing levels:

### Test Architecture
```
tests/
├── unit_test/           # 27 files - Unit tests with mocking
├── integration/         # 33 files - Service integration tests
├── end_to_end/         # 5 files - Full system E2E tests
├── contract/           # 1 file - External API contract tests
├── factories/          # 4 files - Test data factories
└── fixtures/           # 10 files - Test infrastructure
```

### Testing Levels & Coverage

#### 1. **Unit Testing** (27 test files)
- **Business Logic**: Core algorithms and data transformations
- **Service Layer**: Individual service components with mocked dependencies
- **Feature Engineering**: Complex ML feature generation algorithms
- **Pipeline Components**: Data providers, event processors, orchestrators

#### 2. **Integration Testing** (33 test files)
- **Database Operations**: Repository pattern with real PostgreSQL
- **Redis Integration**: Pub/sub messaging and caching scenarios
- **API Endpoints**: FastAPI router testing with realistic data
- **Cross-Service Communication**: Service-to-service interaction testing

#### 3. **End-to-End Testing** (5 test files)
- **Full System Tests**: Complete workflows using Docker Compose
- **Real Infrastructure**: PostgreSQL, Redis, BentoML containers
- **Data Flow Validation**: End-to-end data processing pipelines
- **API Contract Validation**: External service integration testing

### Advanced Testing Infrastructure
- **Test Containers**: Dockerized test environment with PostgreSQL and Redis
- **Fixture Management**: Sophisticated pytest fixture architecture
- **Factory Pattern**: Test data generation using Polyfactory
- **Test Isolation**: Per-module database cleanup and Redis flashing
- **Mocking Strategy**: Comprehensive mocking for external dependencies

### Test Quality Indicators
- **Modular Test Structure**: Clear separation between test types
- **Comprehensive Fixtures**: 18 fixture modules for different testing scenarios
- **Factory-based Data Generation**: Type-safe test data creation
- **Container-based Testing**: Production-like test environments
- **Automated Test Infrastructure**: Docker Compose for consistent test environments

## 🛠️ Technology Stack

### Backend Technologies
- **Python 3.11**: Core runtime with modern async/await patterns
- **FastAPI**: High-performance API framework with automatic OpenAPI docs
- **SQLModel**: Type-safe ORM combining SQLAlchemy and Pydantic
- **Dependency Injector**: Professional IoC container for dependency management
- **Prefect 3.x**: Modern workflow orchestration and scheduling
- **BentoML**: ML model serving and deployment platform

### Frontend Technologies
- **Next.js 15**: React framework with App Router and server-side rendering
- **React 19**: Latest React with concurrent features
- **Mantine**: Professional component library with modern design
- **TypeScript**: Type-safe frontend development

### Infrastructure & DevOps
- **PostgreSQL 14**: Primary database with advanced SQL features
- **Redis**: In-memory data structure store for caching and pub/sub
- **Docker & Docker Compose**: Containerization and orchestration
- **Grafana + Loki**: Centralized logging and monitoring
- **pgAdmin**: Database administration interface

### Development & Testing
- **Poetry**: Dependency management and virtual environment handling
- **pytest**: Comprehensive testing framework with async support
- **TestContainers**: Integration testing with real services
- **Black + Ruff**: Code formatting and linting
- **MyPy**: Static type checking for Python
- **Pre-commit Hooks**: Automated code quality enforcement

## 📈 Scalability & Performance Features

### Database Optimization
- **Batch Operations**: Optimized batch inserts/updates using PostgreSQL-specific features
- **Connection Pooling**: Async connection pooling for high concurrency
- **Indexing Strategy**: Strategic database indexes for query performance
- **Migration Management**: Alembic for schema version control

### Caching & Performance
- **Redis Caching**: Multi-layer caching strategy
- **Connection Reuse**: HTTP client connection pooling
- **Async Processing**: Full async/await implementation throughout
- **Batch Processing**: Efficient batch operations for data processing

### Monitoring & Observability
- **Structured Logging**: Centralized logging with Loki
- **Health Checks**: Comprehensive service health monitoring
- **Performance Metrics**: Application performance monitoring
- **Error Tracking**: Detailed error logging and tracking

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)
- Poetry (for dependency management)

### Quick Start
```bash
# Start infrastructure services
docker-compose up -d db redis pgadmin loki grafana

# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start API service
poetry run uvicorn api_service.main:app --host 0.0.0.0 --port 8000

# Start live orchestrator (in separate terminal)
poetry run python live_orchestrator_app/src/live_orchestrator_app/app.py

# Start frontend (in separate terminal)
cd frontend && npm install && npm run dev
```

### Running Tests
```bash
# Unit tests
poetry run pytest tests/unit_test/

# Integration tests (requires Docker)
poetry run pytest tests/integration/

# End-to-end tests (requires Docker Compose)
poetry run pytest tests/end_to_end/
```

This project represents a production-ready, enterprise-level application demonstrating mastery of modern software development practices, architectural patterns, and technological integration.

## 📄 License

This project is for portfolio demonstration purposes.

---

