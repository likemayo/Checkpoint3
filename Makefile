# Makefile for Checkpoint3 Docker operations

.PHONY: help build up down restart logs shell test clean seed

help: ## Show this help message
	@echo "Checkpoint3 Docker Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Application starting at http://localhost:5000"
	@echo "Run 'make logs' to view logs"

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View application logs
	docker-compose logs -f web

logs-worker: ## View worker logs
	docker-compose logs -f worker

shell: ## Open shell in web container
	docker-compose exec web /bin/bash

shell-db: ## Open SQLite shell
	docker-compose exec web sqlite3 /app/data/app.sqlite

test: ## Run tests in container
	docker-compose exec web python -m pytest -v

test-coverage: ## Run tests with coverage
	docker-compose exec web python -m pytest --cov=src --cov-report=html

seed: ## Seed database with sample data
	docker-compose exec web python src/seed.py

migrate: ## Run database migrations
	docker-compose exec web python scripts/run_migrations.py

clean: ## Remove containers, volumes, and images
	docker-compose down -v
	docker system prune -f

status: ## Show status of services
	docker-compose ps

rebuild: clean build up ## Clean rebuild and start

# Development workflow
dev: build up logs ## Build, start, and show logs

# Health check
health: ## Check application health
	@curl -s http://localhost:5000/health | python -m json.tool || echo "Service not ready"

ready: ## Check application readiness
	@curl -s http://localhost:5000/ready | python -m json.tool || echo "Service not ready"
