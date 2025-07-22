FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Configure poetry: don't create virtual env, install deps to system python
RUN poetry config virtualenvs.create false

# Copy shared packages first and install them
COPY packages/dota_oracle_common ./packages/dota_oracle_common
RUN cd packages/dota_oracle_common && poetry install --only=main --no-interaction

# Install service dependencies (excluding the local package references)
COPY services/api_service/pyproject.toml ./
RUN poetry install --only=main --no-interaction || true

# Install the remaining dependencies manually
RUN pip install fastapi uvicorn httpx pydantic python-dotenv

# Copy service application code
COPY services/api_service/src/ ./src/

# Set Python path to include shared packages
ENV PYTHONPATH=/app/packages/dota_oracle_common/src:/app/src

EXPOSE 8000

CMD ["python", "-m", "api_service.main"]
