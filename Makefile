root := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

export PYTHONPATH=$(root)

uv_run := uv run --no-python-downloads
docs_root := $(root)/docs
docs_build_folder := $(root)/build/docs

.PHONY: test test-integration test-all format can-i-push migrate \
	device-multimeter device-thermostat dev-server seed docs-build docs-open

device-multimeter:
	$(uv_run) python -m devsim --profile dev/multimeter.yaml --port 9001

device-thermostat:
	$(uv_run) python -m devsim --profile dev/thermostat.yaml --port 9002

dev-server:
	$(uv_run) tstlan --config config.dev.toml

seed:
	$(uv_run) python -m tstlan.tools.seed --config config.dev.toml

test:
	$(uv_run) pytest -n auto --dist loadscope -ra -q \
    --cov=tstlan --cov-report=term-missing --cov-report=html \
    --timeout=30

test-integration:
	$(uv_run) pytest -m integration

test-all:
	$(uv_run) pytest -m ""

migrate:
	$(uv_run) alembic upgrade head

format:
	$(uv_run) ruff format .
	$(uv_run) ruff check --fix .

can-i-push:
	$(uv_run) ruff format --check .
	$(uv_run) ruff check .
	$(uv_run) ty check
	$(uv_run) pytest

docs-build:
	$(uv_run) --with sphinx sphinx-build -b html $(docs_root) $(docs_build_folder)

docs-open: docs-build
	$(uv_run) python -m webbrowser file://$(docs_build_folder)/index.html
