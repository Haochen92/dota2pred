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

# --- SIMPLIFIED INSTALLATION ---

# 1. Copy all necessary package source code and configuration files.
#    This includes the main app and the shared packages it depends on.
COPY packages/ ./packages/
COPY live_orchestrator_app/pyproject.toml ./live_orchestrator_app/pyproject.toml
COPY live_orchestrator_app/poetry.lock ./live_orchestrator_app/poetry.lock

COPY live_orchestrator_app/src/ ./live_orchestrator_app/src/
# 2. Run ONE install command from within the main application's directory.
#    Poetry will read the pyproject.toml, see the path dependencies,
#    and install them correctly along with everything else.
RUN cd live_orchestrator_app && poetry install --only=main --no-interaction

# --- END OF SIMPLIFIED INSTALLATION ---

# Copy the rest of the service application code
COPY live_orchestrator_app/entrypoint.sh ./

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
