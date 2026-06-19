#!/usr/bin/env bash
set -e

# Run ruff lint and pytest
if ! command -v ruff >/dev/null 2>&1; then
  echo "ruff not found, installing..."
  pip install ruff
fi

echo "Running ruff..."
ruff check .

echo "Running pytest..."
pytest -q
