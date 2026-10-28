.PHONY: install run test lint format docker

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn blockchain_api.main:app --reload

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

