#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Activate the known-good runtime environment
source "${ROOT_DIR}/venv_rag_2026/bin/activate"

# Ensure 2026 flags are enabled even if shell env overrides differ
export USE_HYBRID_SEARCH="${USE_HYBRID_SEARCH:-true}"
export USE_QUERY_ROUTING="${USE_QUERY_ROUTING:-true}"
export USE_CONTEXT_COMPRESSION="${USE_CONTEXT_COMPRESSION:-true}"

# Start server
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
