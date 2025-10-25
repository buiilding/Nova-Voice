# Makefile for Speech Microservices

.PHONY: help build up down logs test scale clean

help: ## Show this help message
	@echo "Speech Microservices Management"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	cd infra && docker-compose build

up: ## Start all services
	cd infra && docker-compose up -d

down: ## Stop all services
	cd infra && docker-compose down

logs: ## Show logs from all services
	cd infra && docker-compose logs -f

test: ## Run end-to-end tests
	python tests/test_end_to_end.py

demo: ## Run demo client test
	cd demos && python demo_client.py --clients 5

scale-stt: ## Scale STT workers to 3 instances
	./scripts/scale_workers.sh --stt 3

scale-translation: ## Scale translation workers to 2 instances
	./scripts/scale_workers.sh --translation 2

scale-gateway: ## Scale gateway to 2 instances
	./scripts/scale_workers.sh --gateway 2

scale-all: ## Scale all services to 3 instances each
	./scripts/scale_workers.sh --all 3

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8080/health | jq .status || echo "Gateway: DOWN"
	@curl -s http://localhost:8081/health | jq .status || echo "STT Worker: DOWN"
	@curl -s http://localhost:8082/health | jq .status || echo "Translation Worker: DOWN"

status: ## Show status of all services
	cd infra && docker-compose ps

clean: ## Clean up containers and volumes
	cd infra && docker-compose down -v
	docker system prune -f

# Development targets
dev-up: ## Start services for development
	cd infra && docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

dev-logs: ## Show development logs
	cd infra && docker-compose -f docker-compose.yml -f docker-compose.override.yml logs -f

# GPU targets (requires nvidia-docker)
gpu-up: ## Start services with GPU support
	cd infra && docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Load testing
load-test: ## Run load test with 10 clients, 5 batches
	cd demos && python demo_client.py --load-test --clients 10 --batches 5

# Setup
setup: ## Initial setup - generate test audio
	cd demos && python generate_audio.py

# Full test suite
full-test: setup test load-test ## Run full test suite

