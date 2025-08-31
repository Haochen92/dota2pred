# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies required for Python package compilation
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and configure for system-wide package installation
RUN pip install poetry && \
    poetry config virtualenvs.create false

# Copy shared packages to maintain relative path structure during dependency resolution
COPY packages/ ./packages/

# Create service directory structure required for Poetry to resolve local dependencies
RUN mkdir -p dota_oracle_schedules

# Copy dependency definition files for cached layer optimization
COPY dota_oracle_schedules/pyproject.toml ./dota_oracle_schedules/
COPY dota_oracle_schedules/poetry.lock ./dota_oracle_schedules/

# Install production dependencies only, leveraging Docker layer caching
WORKDIR /app/dota_oracle_schedules
RUN poetry install --no-root --only=main --no-interaction

# Stage 2: Production runtime image
FROM python:3.11-slim AS final

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage for optimal layer size
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy installed binaries from builder stage
COPY --from=builder /usr/local/bin /usr/local/bin

# Configure simplified Python module resolution path
ENV PYTHONPATH=/app

# Copy source code to flat directory structure for simplified container layout
COPY ./packages/dota_oracle_common/src/dota_oracle_common /app/dota_oracle_common
COPY ./packages/dota_oracle_pipeline/src/dota_oracle_pipeline /app/dota_oracle_pipeline
COPY ./dota_oracle_schedules/src/dota_oracle_schedules /app/dota_oracle_schedules

# Copy and configure application entrypoint script
COPY ./dota_oracle_schedules/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
