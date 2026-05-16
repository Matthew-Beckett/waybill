test:
	uv run pytest -n auto

deps:
	uv sync --group dev --group bundle

build: deps test
	uv build --wheel
