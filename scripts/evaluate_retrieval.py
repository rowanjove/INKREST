#!/usr/bin/env python3
"""Evaluate retrieval ablations on copyright-safe JSONL needle cases.

The evaluator is deterministic and does not instantiate an embedding model.
Case files provide route candidates; this keeps CI useful offline while still
exercising the same RRF, rerank and Context Pack contracts as production.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from novel_agent.retrieval.context_pack import build_context_pack
from novel_agent.retrieval.fusion import reciprocal_rank_fusion
from novel_agent.retrieval.models import RetrievalCandidate
from novel_agent.retrieval.reranker import deterministic_rerank


MODES = ("adjacent-only", "vector-only", "fts-only", "hybrid", "hybrid+rerank")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        value = json.loads(line)
        if isinstance(value, Mapping):
            cases.append(dict(value))
    return cases


def _route(candidates: Iterable[Mapping[str, Any]], route: str) -> list[RetrievalCandidate]:
    return [RetrievalCandidate.from_mapping(dict(item), route=route) for item in candidates if isinstance(item, Mapping)]


def rank_case(case: Mapping[str, Any], mode: str, *, limit: int = 20) -> tuple[list[RetrievalCandidate], dict[str, Any]]:
    routes_raw = case.get("routes") if isinstance(case.get("routes"), Mapping) else {}
    route_names = {"adjacent-only": ("adjacent",), "vector-only": ("vector",), "fts-only": ("fts",), "hybrid": ("adjacent", "entity", "vector", "fts"), "hybrid+rerank": ("adjacent", "entity", "vector", "fts")}[mode]
    routes = {name: _route(routes_raw.get(name) or [], name) for name in route_names}
    started = time.perf_counter()
    ranked = reciprocal_rank_fusion(routes, limit=limit)
    if mode == "hybrid+rerank":
        ranked = deterministic_rerank(ranked, limit=limit)
    elapsed = (time.perf_counter() - started) * 1000.0
    pack = build_context_pack(ranked, required_memory_ids=[str(item) for item in case.get("required_ids") or []], max_chars=int(case.get("max_context_chars") or 12000))
    return ranked, {"latency_ms": round(elapsed, 4), "context_tokens": round(len(pack["text"]) / 4.0, 2), "context_pack": pack}


def evaluate_cases(cases: Iterable[Mapping[str, Any]], *, top_k: int = 5, limit: int = 20) -> dict[str, Any]:
    all_cases = [dict(item) for item in cases]
    results: dict[str, Any] = {"schema_version": 1, "case_count": len(all_cases), "top_k": top_k, "modes": {}, "cases": []}
    for mode in MODES:
        rows: list[dict[str, Any]] = []
        for case in all_cases:
            ranked, extra = rank_case(case, mode, limit=limit)
            ids = [item.memory_id for item in ranked]
            relevant = {str(item) for item in case.get("relevant_ids") or []}
            required = {str(item) for item in case.get("required_ids") or []}
            top = ids[: max(1, int(top_k))]
            first_rank = next((index + 1 for index, item in enumerate(ids) if item in relevant), None)
            wrong = {str(item) for item in case.get("wrong_fact_ids") or []}
            rows.append({
                "case_id": str(case.get("case_id") or ""),
                "mode": mode,
                "recall_at_k": 1.0 if relevant.intersection(top) else 0.0,
                "required_fact_coverage": len(required.intersection(top)) / len(required) if required else 1.0,
                "mrr": 1.0 / first_rank if first_rank else 0.0,
                "wrong_fact_entry": 1.0 if wrong.intersection(top) else 0.0,
                "context_tokens": extra["context_tokens"],
                "latency_ms": extra["latency_ms"],
                "top_ids": top,
                "missing_required_ids": sorted(required - set(top)),
            })
        n = len(rows) or 1
        summary = {
            "case_count": len(rows),
            "recall_at_k": round(sum(row["recall_at_k"] for row in rows) / n, 6),
            "required_fact_coverage": round(sum(row["required_fact_coverage"] for row in rows) / n, 6),
            "mrr": round(sum(row["mrr"] for row in rows) / n, 6),
            "wrong_fact_entry": round(sum(row["wrong_fact_entry"] for row in rows) / n, 6),
            "avg_context_tokens": round(sum(row["context_tokens"] for row in rows) / n, 4),
            "avg_latency_ms": round(sum(row["latency_ms"] for row in rows) / n, 4),
        }
        results["modes"][mode] = summary
        results["cases"].extend(rows)
    return results


def write_csv(path: Path, result: Mapping[str, Any]) -> None:
    fields = ["case_id", "mode", "recall_at_k", "required_fact_coverage", "mrr", "wrong_fact_entry", "context_tokens", "latency_ms", "top_ids", "missing_required_ids"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in result.get("cases") or []:
            item = dict(row)
            item["top_ids"] = "|".join(item.get("top_ids") or [])
            item["missing_required_ids"] = "|".join(item.get("missing_required_ids") or [])
            writer.writerow({key: item.get(key) for key in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate long-form retrieval ablations")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    result = evaluate_cases(load_cases(args.cases), top_k=max(1, args.top_k), limit=max(1, args.limit))
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        write_csv(args.csv, result)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
