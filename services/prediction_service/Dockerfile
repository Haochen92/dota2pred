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

# Copy shared packages first
COPY packages/ ./packages/

# Install shared packages
RUN cd packages/dota_oracle_common && poetry install --only=main --no-interaction

# Copy service poetry files and install dependencies
COPY services/prediction_service/pyproject.toml services/prediction_service/pyproject.toml
RUN cd services/prediction_service && poetry install --only=main --no-interaction

# Copy service application code
COPY services/prediction_service/src/ ./src/
COPY services/prediction_service/models/ ./models/
COPY services/prediction_service/requirements.txt ./requirements.txt
COPY services/prediction_service/save_model.py ./save_model.py

# Set Python path to include shared packages
ENV PYTHONPATH=/app/packages/dota_oracle_common/src:/app/src

# Save the model to BentoML store
RUN python save_model.py

EXPOSE 3000

CMD ["bentoml", "serve", "src.service:svc", "--host", "0.0.0.0", "--port", "3000"]