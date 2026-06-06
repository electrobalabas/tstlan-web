.PHONY: test test-integration test-all format can-i-push migrate

test:
	uv run pytest -n auto --dist loadscope -ra -q \
    --cov=tstlan --cov-report=term-missing --cov-report=html \
    --timeout=30

test-integration:
	uv run pytest -m integration

test-all:
	uv run pytest -m ""

migrate:
	uv run alembic upgrade head

format:
	uv run ruff format .
	uv run ruff check --fix .

can-i-push:
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check
	uv run pytest
