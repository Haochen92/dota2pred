.PHONY: help build test lint clean install-deps

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-deps: ## Install all dependencies for the monorepo
	poetry install
	cd packages/dota_oracle_common && poetry install
	cd packages/dota_oracle_etl && poetry install
	cd pipelines/training_pipeline && poetry install
	cd services/prediction_service && poetry install
	cd services/pipeline_service && poetry install
	cd services/api_service && poetry install
	cd frontend && npm install

build: ## Build all Docker images
	docker-compose build

test: ## Run all tests
	cd packages/dota_oracle_common && poetry run pytest
	cd packages/dota_oracle_etl && poetry run pytest
	cd pipelines/training_pipeline && poetry run pytest
	cd services/prediction_service && poetry run pytest
	cd services/pipeline_service && poetry run pytest
	cd services/api_service && poetry run pytest

test-e2e: ## Run end-to-end tests
	cd e2e-tests && poetry run pytest

lint: ## Run linting for all Python packages
	cd packages/dota_oracle_common && poetry run ruff check . && poetry run mypy .
	cd packages/dota_oracle_etl && poetry run ruff check . && poetry run mypy .
	cd pipelines/training_pipeline && poetry run ruff check . && poetry run mypy .
	cd services/prediction_service && poetry run ruff check . && poetry run mypy .
	cd services/pipeline_service && poetry run ruff check . && poetry run mypy .
	cd services/api_service && poetry run ruff check . && poetry run mypy .

format: ## Format all Python code
	cd packages/dota_oracle_common && poetry run black .
	cd packages/dota_oracle_etl && poetry run black .
	cd pipelines/training_pipeline && poetry run black .
	cd services/prediction_service && poetry run black .
	cd services/pipeline_service && poetry run black .
	cd services/api_service && poetry run black .

start: ## Start all services with Docker Compose
	docker-compose up -d

stop: ## Stop all services
	docker-compose down

logs: ## Show logs for all services
	docker-compose logs -f

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

migrate: ## Run database migrations
	cd alembic && alembic upgrade head