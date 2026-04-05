PYTHON ?= python
PIP ?= pip

install:
	$(PIP) install -e .[dev]

dev:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest -q

lint:
	ruff check app tests

format:
	ruff format app tests

docker-build:
	docker build -t agentic-ai-microservice-api .

docker-up:
	docker compose up --build
