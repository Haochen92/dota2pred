# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies & poetry
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Copy shared packages to maintain structure for poetry install
COPY packages/ ./packages/

# Create services/api_service directory structure for poetry install
RUN mkdir -p services/api_service

# Copy poetry files
COPY services/api_service/pyproject.toml ./services/api_service/
COPY services/api_service/poetry.lock ./services/api_service/

# Install dependencies from the api_service directory to maintain relative paths
WORKDIR /app/services/api_service
RUN poetry install --no-root --only=main --no-interaction

# Stage 2: Final production image
FROM python:3.11-slim AS final

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy the installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the installed binaries from the builder stage
COPY --from=builder /usr/local/bin /usr/local/bin

# Set a simple, flat PYTHONPATH
ENV PYTHONPATH=/app

# Copy the local common package to a simple, top-level directory
COPY ./packages/dota_oracle_common/src/dota_oracle_common /app/dota_oracle_common

# Copy the local pipeline package to a simple, top-level directory
COPY ./packages/dota_oracle_pipeline/src/dota_oracle_pipeline /app/dota_oracle_pipeline

# Copy the main application source to a simple, top-level directory
COPY ./services/api_service/src/api_service /app/api_service

EXPOSE 8000

CMD ["uvicorn", "api_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
