.PHONY: test format can-i-push migrate

test:
	uv run pytest

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
