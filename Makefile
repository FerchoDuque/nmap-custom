.PHONY: help build up down logs restart clean shell-backend shell-db shell-redis migrate test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker containers
	docker-compose build

build-dev: ## Build development containers
	docker-compose -f docker-compose.dev.yml build

up: ## Start all services (production)
	docker-compose up -d

up-dev: ## Start all services (development)
	docker-compose -f docker-compose.dev.yml up

down: ## Stop all services
	docker-compose down

down-dev: ## Stop development services
	docker-compose -f docker-compose.dev.yml down

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-celery: ## View Celery worker logs
	docker-compose logs -f celery

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

restart: ## Restart all services
	docker-compose restart

restart-backend: ## Restart backend service
	docker-compose restart backend

restart-celery: ## Restart Celery worker
	docker-compose restart celery

clean: ## Stop and remove all containers, networks, and volumes
	docker-compose down -v
	docker system prune -f

shell-backend: ## Access backend container shell
	docker-compose exec backend /bin/bash

shell-db: ## Access PostgreSQL shell
	docker-compose exec db psql -U scanner -d network_scanner

shell-redis: ## Access Redis CLI
	docker-compose exec redis redis-cli

migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	docker-compose exec backend alembic revision --autogenerate -m "$(MESSAGE)"

test: ## Run tests in backend container
	docker-compose exec backend pytest tests/ -v

test-cov: ## Run tests with coverage
	docker-compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

ps: ## Show running containers
	docker-compose ps

stats: ## Show container resource usage
	docker stats

# Development shortcuts
dev: build-dev up-dev ## Build and start development environment

prod: build up ## Build and start production environment

stop: down ## Alias for down
