#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "❌ .venv not found. Run ./setup.sh first."
  exit 1
fi

source .venv/bin/activate

# Optional override
export BASE_URL="${BASE_URL:-http://localhost:8000}"

python smoke_test_2026.py
