#!/usr/bin/env python3
"""Fail CI when frontend JS bundles exceed checked-in byte budgets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUDGET = ROOT / "benchmarks" / "frontend_bundle_budget.json"
DEFAULT_DIST = ROOT / "web" / "frontend" / "dist"


def _load_budget(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("budget file must be a JSON object")
    return data


def _js_files(dist_dir: Path) -> list[Path]:
    assets = dist_dir / "assets"
    if not assets.is_dir():
        return []
    return sorted(assets.glob("*.js"))


def check_bundle(dist_dir: Path, budget_path: Path) -> list[str]:
    budget = _load_budget(budget_path)
    js_files = _js_files(dist_dir)
    if not js_files:
        return [f"no JS assets under {dist_dir / 'assets'} — run npm run build first"]

    sizes = {p.name: p.stat().st_size for p in js_files}
    total = sum(sizes.values())
    element_plus = max(
        (size for name, size in sizes.items() if "element-plus" in name),
        default=0,
    )
    index_js = max(
        (size for name, size in sizes.items() if name.startswith("index-")),
        default=0,
    )
    vendor_markers = (
        "element-plus",
        "vue-",
        "axios-",
        "rolldown-runtime",
        "tiptap-",
        "prosemirror-",
        "tanstack-virtual",
    )
    route_sizes = [
        size
        for name, size in sizes.items()
        if not any(marker in name for marker in vendor_markers)
    ]
    largest_route = max(route_sizes) if route_sizes else 0

    issues: list[str] = []
    checks = [
        ("max_total_js_bytes", total, "total JS"),
        ("max_element_plus_js_bytes", element_plus, "element-plus chunk"),
        ("max_index_js_bytes", index_js, "index chunk"),
        ("max_single_js_bytes", largest_route, "largest route JS chunk"),
    ]
    for key, value, label in checks:
        limit = int(budget.get(key, 0) or 0)
        if limit and value > limit:
            issues.append(f"{label}: {value} bytes > budget {limit} ({key})")
    return issues


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dist_dir",
        nargs="?",
        default=str(DEFAULT_DIST),
        help="Vite dist directory (default: web/frontend/dist)",
    )
    parser.add_argument(
        "--budget",
        default=str(DEFAULT_BUDGET),
        help="JSON budget file",
    )
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir)
    budget_path = Path(args.budget)
    if not budget_path.is_file():
        print(f"Missing budget file: {budget_path}", file=sys.stderr)
        return 2

    issues = check_bundle(dist_dir, budget_path)
    if issues:
        print("Frontend bundle budget exceeded:", file=sys.stderr)
        for item in issues:
            print(f"  - {item}", file=sys.stderr)
        return 1

    js_files = _js_files(dist_dir)
    total = sum(p.stat().st_size for p in js_files)
    print(f"OK: {len(js_files)} JS chunks, {total} bytes total (within budget)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
