.PHONY: test format can-i-push

test:
	uv run pytest

format:
	uv run ruff format .
	uv run ruff check --fix .

can-i-push:
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check
	uv run pytest
