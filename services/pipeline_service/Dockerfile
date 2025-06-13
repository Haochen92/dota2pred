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

# Configure poetry: don't create virtual env, install deps to system python
RUN poetry config virtualenvs.create false

# Copy shared packages first
COPY packages/ ./packages/

# Install shared packages
RUN cd packages/dota_oracle_common && poetry install --only=main --no-interaction
RUN cd packages/dota_oracle_etl && poetry install --only=main --no-interaction

# Copy service poetry files and install dependencies
COPY services/pipeline_service/pyproject.toml services/pipeline_service/pyproject.toml
RUN cd services/pipeline_service && poetry install --only=main --no-interaction

# Copy service application code
COPY services/pipeline_service/src/ ./src/
COPY services/pipeline_service/entrypoint.sh ./
COPY services/pipeline_service/deploy_flow.py ./

# Ensure that entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

# Set Python path to include shared packages
ENV PYTHONPATH=/app/packages/dota_oracle_common/src:/app/packages/dota_oracle_etl/src:/app/src

# Expose the port your app runs on
EXPOSE 8000

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]