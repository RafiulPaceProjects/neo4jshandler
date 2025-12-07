.PHONY: help install dev-install test lint format clean docker-build docker-run docker-up docker-down

help:
	@echo "Neo4j GraphBot - Available commands:"
	@echo "  make install       - Install the package"
	@echo "  make dev-install   - Install with development dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code with black"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run Docker container"
	@echo "  make docker-up     - Start with docker-compose"
	@echo "  make docker-down   - Stop docker-compose"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=graphbot --cov-report=html

lint:
	flake8 src/ scripts/
	mypy src/

format:
	black src/ scripts/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t neo4j-graphbot .

docker-run:
	docker run -it --rm --network host -v $(PWD)/config/config.env:/app/config/config.env:ro neo4j-graphbot

docker-up:
	docker-compose up

docker-down:
	docker-compose down

