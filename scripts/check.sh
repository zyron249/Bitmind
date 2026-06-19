#!/usr/bin/env bash
set -e

# Run ruff lint and pytest with coverage
if ! command -v ruff >/dev/null 2>&1; then
  echo "ruff not found, installing..."
  pip install ruff
fi

echo "Running ruff..."
ruff check .

echo "Running pytest with coverage..."
pytest --cov=bitmind --cov-report=term-missing -q
