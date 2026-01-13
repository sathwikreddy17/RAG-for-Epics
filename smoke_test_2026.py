"""Smoke test for 2026 features.

Runs against a live server (default http://localhost:8000) and validates:
- /api/health is healthy
- 2026 feature flags are enabled
- /api/ask responds for a basic query (requires LM Studio running)

Usage:
  source .venv/bin/activate
  python smoke_test_2026.py

Optional:
  BASE_URL=http://localhost:8000 python smoke_test_2026.py
"""

import os
import sys
import json
import time
from typing import Any, Dict

import httpx


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def get_json(client: httpx.Client, url: str) -> Dict[str, Any]:
    r = client.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def post_json(client: httpx.Client, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = client.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def main() -> int:
    base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

    with httpx.Client(base_url=base_url) as client:
        health = get_json(client, "/api/health")
        _assert(health.get("status") in {"healthy", "degraded"}, f"Unexpected health status: {health}")

        backend = health.get("backend_status") or {}
        _assert(backend.get("database_connected") is True, f"Database not connected: {backend}")

        # 2026 feature flags
        _assert(backend.get("hybrid_search_enabled") is True, f"Hybrid search not enabled: {backend}")
        _assert(backend.get("bm25_available") is True, f"BM25 not available: {backend}")
        _assert(backend.get("query_routing_enabled") is True, f"Query routing not enabled: {backend}")
        _assert(
            backend.get("context_compression_enabled") is True,
            f"Context compression not enabled: {backend}",
        )

        # Basic /api/ask test (requires LM Studio)
        payload = {
            "question": "Give a short summary of the documents available.",
            "include_sources": True,
            "file_filter": "all",
        }

        try:
            result = post_json(client, "/api/ask", payload)
        except Exception as e:
            print("ASK_FAILED")
            print("/api/ask request failed. This usually means LM Studio isn't running.")
            print(f"Error: {e}")
            return 2

        _assert("answer" in result and isinstance(result["answer"], str), f"Invalid answer payload: {result}")
        _assert("metadata" in result and isinstance(result["metadata"], dict), f"Invalid metadata: {result}")
        _assert("sources" in result and isinstance(result["sources"], list), f"Invalid sources: {result}")

        print("SMOKE_OK")
        print(json.dumps({"health": health.get("status"), "sources": len(result.get("sources", []))}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
