#!/usr/bin/env python3
"""Build .sweep_cache/runs.json from Orchestra MCP list_pipeline_runs pages."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def merge_pages(pages: list[dict]) -> dict:
    results: list[dict] = []
    for page in pages:
        results.extend(page.get("results", []))
    return {"total": len(results), "results": results}


def main() -> int:
    cache = Path(__file__).resolve().parents[1] / ".sweep_cache"
    cache.mkdir(parents=True, exist_ok=True)
    pages_dir = cache / "pages"
    if not pages_dir.exists():
        print(f"Missing {pages_dir}; write page JSON files from MCP first", file=sys.stderr)
        return 1

    pages = []
    for path in sorted(pages_dir.glob("page_*.json")):
        pages.append(json.loads(path.read_text()))
    if not pages:
        print("No page files found", file=sys.stderr)
        return 1

    merged = merge_pages(pages)
    out = cache / "runs.json"
    out.write_text(json.dumps(merged, indent=2))
    print(f"Wrote {len(merged['results'])} runs to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
