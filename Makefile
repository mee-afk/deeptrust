.PHONY: help dev build test clean deploy

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.dev.yml
BACKEND_DIR = backend
FRONTEND_DIR = frontend

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# DEVELOPMENT
# ==============================================================================

dev: ## Start all services in development mode
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "Services started. Access:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  API Gateway: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

dev-logs: ## Show logs for all development services
	$(DOCKER_COMPOSE_DEV) logs -f

dev-stop: ## Stop all development services
	$(DOCKER_COMPOSE_DEV) down

dev-restart: ## Restart all development services
	$(DOCKER_COMPOSE_DEV) restart

dev-clean: ## Stop and remove all development containers, networks, and volumes
	$(DOCKER_COMPOSE_DEV) down -v --remove-orphans

# ==============================================================================
# BACKEND
# ==============================================================================

backend-dev: ## Start only backend services
	cd $(BACKEND_DIR) && $(DOCKER_COMPOSE_DEV) up -d postgres redis rabbitmq
	@echo "Backend infrastructure ready"

backend-shell: ## Open shell in backend container
	$(DOCKER_COMPOSE_DEV) exec gateway bash

backend-logs: ## Show backend logs
	$(DOCKER_COMPOSE_DEV) logs -f gateway auth analysis models

backend-test: ## Run backend tests
	cd $(BACKEND_DIR) && pytest tests/ -v --cov=app --cov-report=html

backend-lint: ## Lint backend code
	cd $(BACKEND_DIR) && black app/
	cd $(BACKEND_DIR) && isort app/
	cd $(BACKEND_DIR) && flake8 app/

backend-migrate: ## Run database migrations
	cd $(BACKEND_DIR) && alembic upgrade head

backend-migration: ## Create new migration (usage: make backend-migration MSG="your message")
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(MSG)"

# ==============================================================================
# FRONTEND
# ==============================================================================

frontend-dev: ## Start frontend in development mode
	cd $(FRONTEND_DIR) && npm run dev

frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && npm install

frontend-build: ## Build frontend for production
	cd $(FRONTEND_DIR) && npm run build

frontend-test: ## Run frontend tests
	cd $(FRONTEND_DIR) && npm test

frontend-lint: ## Lint frontend code
	cd $(FRONTEND_DIR) && npm run lint

frontend-format: ## Format frontend code
	cd $(FRONTEND_DIR) && npm run format

# ==============================================================================
# DATABASE
# ==============================================================================

db-shell: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U deeptrust -d deeptrust

db-backup: ## Backup database
	$(DOCKER_COMPOSE_DEV) exec postgres pg_dump -U deeptrust deeptrust > backup_$$(date +%Y%m%d_%H%M%S).sql

db-restore: ## Restore database (usage: make db-restore FILE=backup.sql)
	$(DOCKER_COMPOSE_DEV) exec -T postgres psql -U deeptrust deeptrust < $(FILE)

init-db: ## Initialize database with seed data
	python $(BACKEND_DIR)/scripts/init_db.py
	python $(BACKEND_DIR)/scripts/seed_data.py

# ==============================================================================
# DOCKER
# ==============================================================================

build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

build-no-cache: ## Build all Docker images without cache
	$(DOCKER_COMPOSE) build --no-cache

pull: ## Pull latest Docker images
	$(DOCKER_COMPOSE) pull

push: ## Push Docker images to registry
	$(DOCKER_COMPOSE) push

# ==============================================================================
# TESTING
# ==============================================================================

test: ## Run all tests
	$(MAKE) backend-test
	$(MAKE) frontend-test

test-e2e: ## Run end-to-end tests
	cd tests/e2e && pytest -v

test-integration: ## Run integration tests
	cd tests/integration && pytest -v

test-performance: ## Run performance tests
	cd tests/performance && locust -f locustfile.py

# ==============================================================================
# CODE QUALITY
# ==============================================================================

lint: ## Lint all code
	$(MAKE) backend-lint
	$(MAKE) frontend-lint

format: ## Format all code
	$(MAKE) backend-lint
	$(MAKE) frontend-format

check: ## Run all checks (lint, test, security)
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) security-check

security-check: ## Run security checks
	cd $(BACKEND_DIR) && safety check
	cd $(FRONTEND_DIR) && npm audit

# ==============================================================================
# DEPLOYMENT
# ==============================================================================

deploy-staging: ## Deploy to staging environment
	@echo "Deploying to staging..."
	kubectl apply -f infrastructure/kubernetes/ --namespace=staging
	kubectl rollout status deployment/frontend -n staging
	kubectl rollout status deployment/gateway -n staging

deploy-production: ## Deploy to production environment
	@echo "Deploying to production..."
	kubectl apply -f infrastructure/kubernetes/ --namespace=production
	kubectl rollout status deployment/frontend -n production
	kubectl rollout status deployment/gateway -n production

rollback: ## Rollback to previous version (usage: make rollback VERSION=v1.0.0)
	kubectl rollout undo deployment/frontend --to-revision=$(VERSION) -n production
	kubectl rollout undo deployment/gateway --to-revision=$(VERSION) -n production

# ==============================================================================
# MONITORING
# ==============================================================================

logs: ## Show logs for all services
	$(DOCKER_COMPOSE) logs -f

logs-gateway: ## Show API gateway logs
	$(DOCKER_COMPOSE) logs -f gateway

logs-auth: ## Show auth service logs
	$(DOCKER_COMPOSE) logs -f auth

logs-analysis: ## Show analysis service logs
	$(DOCKER_COMPOSE) logs -f analysis

logs-models: ## Show models service logs
	$(DOCKER_COMPOSE) logs -f models

metrics: ## Open Prometheus metrics
	@open http://localhost:9090

grafana: ## Open Grafana dashboard
	@open http://localhost:3001

# ==============================================================================
# UTILITIES
# ==============================================================================

clean: ## Clean all generated files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete

install: ## Install all dependencies
	$(MAKE) backend-install
	$(MAKE) frontend-install

backend-install: ## Install backend dependencies
	cd $(BACKEND_DIR)/services/auth && pip install -r requirements.txt
	cd $(BACKEND_DIR)/services/analysis && pip install -r requirements.txt
	cd $(BACKEND_DIR)/services/models && pip install -r requirements.txt
	cd $(BACKEND_DIR)/services/gateway && pip install -r requirements.txt

setup: ## Initial project setup
	@echo "Setting up DeepTrust development environment..."
	cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env
	cp $(FRONTEND_DIR)/.env.example $(FRONTEND_DIR)/.env
	$(MAKE) install
	$(MAKE) build
	$(MAKE) init-db
	@echo "Setup complete! Run 'make dev' to start development."

rebuild: ## Rebuild and restart all services
	$(DOCKER_COMPOSE_DEV) down
	$(DOCKER_COMPOSE_DEV) build
	$(DOCKER_COMPOSE_DEV) up -d

shell: ## Open interactive shell in specified service (usage: make shell SERVICE=gateway)
	$(DOCKER_COMPOSE_DEV) exec $(SERVICE) bash

ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

stats: ## Show container resource usage
	docker stats

# ==============================================================================
# ML TRAINING
# ==============================================================================

train-mesonet: ## Train MesoNet model
	cd ml/training && python train_mesonet.py

train-xception: ## Train XceptionNet model
	cd ml/training && python train_xception.py

train-all: ## Train all models
	$(MAKE) train-mesonet
	$(MAKE) train-xception

evaluate: ## Evaluate models
	cd ml/evaluation && python evaluate.py

# ==============================================================================
# DOCUMENTATION
# ==============================================================================

docs-api: ## Generate API documentation
	cd $(BACKEND_DIR) && python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/api/openapi.json

docs-serve: ## Serve documentation locally
	cd docs && python -m http.server 8080

# ==============================================================================
# CI/CD
# ==============================================================================

ci-test: ## Run CI tests
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) security-check

ci-build: ## Build for CI
	$(MAKE) build-no-cache

ci-deploy-staging: ## CI staging deployment
	$(MAKE) deploy-staging

ci-deploy-production: ## CI production deployment
	$(MAKE) deploy-production

