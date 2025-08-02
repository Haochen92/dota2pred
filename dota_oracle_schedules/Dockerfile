FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (these can likely remain the same)
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# --- INSTALLATION FOR THE BATCH APP ---

# 1. Copy all necessary package source code and configuration files.
#    This includes the shared packages it depends on.
COPY packages/ ./packages/

# 2. Copy the configuration and source for the NEW batch app.
COPY dota_oracle_schedules/pyproject.toml ./dota_oracle_schedules/pyproject.toml
COPY dota_oracle_schedules/poetry.lock ./dota_oracle_schedules/poetry.lock
COPY dota_oracle_schedules/src/ ./dota_oracle_schedules/src/

# 3. Run ONE install command from within the new batch app's directory.
RUN cd dota_oracle_schedules && poetry install --only=main --no-interaction

# --- END OF INSTALLATION ---

# Copy the entrypoint script for the batch service
# Note: We copy it from its new home in the dota_oracle_schedules directory
COPY dota_oracle_schedules/entrypoint.sh ./entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# EXPOSE 8000 <-- This is no longer needed for a background worker.

ENTRYPOINT ["/app/entrypoint.sh"]
