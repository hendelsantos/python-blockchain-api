.PHONY: install run test lint format migrate docker compose

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn blockchain_api.main:app --reload

migrate:
	alembic upgrade head

test:
	pytest

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

docker:
	docker build -t python-blockchain-api .
	docker run --rm -p 8000:8000 python-blockchain-api

compose:
	docker compose up --build

