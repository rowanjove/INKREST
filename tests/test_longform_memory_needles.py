from pathlib import Path

from scripts.evaluate_retrieval import evaluate_cases, load_cases


def test_retrieval_ablation_reports_all_modes_and_required_coverage():
    cases = load_cases(Path("benchmarks/longform/retrieval-cases.jsonl"))
    result = evaluate_cases(cases, top_k=3)
    assert result["case_count"] >= 5
    assert set(result["modes"]) == {"adjacent-only", "vector-only", "fts-only", "hybrid", "hybrid+rerank"}
    assert result["modes"]["fts-only"]["required_fact_coverage"] == 1.0
    assert result["modes"]["adjacent-only"]["required_fact_coverage"] == 0.0
    assert all("latency_ms" in row and "mrr" in row for row in result["cases"])
