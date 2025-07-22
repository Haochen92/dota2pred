FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Copy and install shared packages properly
COPY packages/ ./packages/
RUN pip install -e ./packages/dota_oracle_common
RUN pip install -e ./packages/dota_oracle_etl

# Copy service poetry files and install dependencies
COPY live_orchestrator_app/pyproject.toml live_orchestrator_app/pyproject.toml
RUN cd live_orchestrator_app && poetry install --only=main --no-interaction

# Copy service application code
COPY live_orchestrator_app/src/ ./src/
COPY live_orchestrator_app/entrypoint.sh ./
COPY live_orchestrator_app/deploy_flow.py ./

RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app/src

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
