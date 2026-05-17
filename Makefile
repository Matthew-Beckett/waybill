test:
	uv run pytest -n auto

deps:
	uv sync --group dev --group bundle

schemas:
	uv run generate_schema.py

build: deps check schemas test
	uv build --wheel

check:
	pre-commit run --all-files
