.PHONY: help proto build-asr build-meet build-all run-asr run-meet run-scrum test clean docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

proto: ## Generate protobuf files
	@echo "Generating proto files..."
	protoc --go_out=. --go_opt=paths=source_relative \
	       --go-grpc_out=. --go-grpc_opt=paths=source_relative \
	       specs/proto/asr/asr.proto
	protoc --go_out=. --go_opt=paths=source_relative \
	       --go-grpc_out=. --go-grpc_opt=paths=source_relative \
	       specs/proto/sso/sso.proto
	@echo "✓ Proto files generated"

build-asr: ## Build ASR service
	@echo "Building ASR service..."
	go build -o bin/asr ./cmd/services/asr/main.go
	@echo "✓ ASR service built"

build-meet: ## Build Meet gateway
	@echo "Building Meet gateway..."
	go build -o bin/meet ./cmd/gateways/meet/main.go
	@echo "✓ Meet gateway built"

build-sso: ## Build SSO service
	@echo "Building SSO service..."
	go build -o bin/sso ./cmd/services/sso/main.go
	@echo "✓ SSO service built"

build-web: ## Build Web gateway
	@echo "Building Web gateway..."
	go build -o bin/web ./cmd/gateways/web/main.go
	@echo "✓ Web gateway built"

build-all: build-asr build-meet build-sso build-web ## Build all services

run-asr: ## Run ASR service locally
	@echo "Starting ASR service on port 50052..."
	PORT=50052 go run ./cmd/services/asr/main.go

run-meet: ## Run Meet gateway locally
	@echo "Starting Meet gateway on port 8096..."
	PORT=8096 \
	ASR_PORT=50052 \
	ASR_URL=localhost \
	SCRUM_PORT=8000 \
	SCRUM_URL=localhost \
	go run ./cmd/gateways/meet/main.go

run-scrum: ## Run Scrum Master service locally
	@echo "Starting Scrum Master service on port 8000..."
	cd services/scrum && PORT=8000 python main.py

test: ## Run test script
	@echo "Running ASR flow test..."
	./scripts/test-asr-flow.sh

docker-up: ## Start all services with Docker Compose
	@echo "Starting services with Docker Compose..."
	docker-compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "Services available at:"
	@echo "  - Meet Gateway:  http://localhost:8096"
	@echo "  - Web Gateway:   http://localhost:8095"
	@echo "  - Scrum Master:  http://localhost:8000"
	@echo "  - ASR Service:   grpc://localhost:50052"
	@echo "  - SSO Service:   grpc://localhost:50051"

docker-down: ## Stop all Docker Compose services
	@echo "Stopping services..."
	docker-compose down
	@echo "✓ Services stopped"

docker-logs: ## Show logs from all services
	docker-compose logs -f

docker-logs-meet: ## Show logs from meet-gateway
	docker-compose logs -f meet-gateway

docker-logs-asr: ## Show logs from asr-service
	docker-compose logs -f asr-service

docker-logs-scrum: ## Show logs from scrum-master
	docker-compose logs -f scrum-master

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf bin/
	@echo "✓ Clean complete"

tidy: ## Run go mod tidy
	@echo "Tidying Go modules..."
	go mod tidy
	@echo "✓ Modules tidied"

fmt: ## Format Go code
	@echo "Formatting Go code..."
	go fmt ./...
	@echo "✓ Code formatted"

lint: ## Run golangci-lint
	@echo "Running linter..."
	golangci-lint run
	@echo "✓ Linting complete"

.DEFAULT_GOAL := help
