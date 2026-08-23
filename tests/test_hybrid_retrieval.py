from __future__ import annotations

from pathlib import Path

from novel_agent.retrieval.context_pack import build_context_pack
from novel_agent.retrieval.fusion import reciprocal_rank_fusion
from novel_agent.retrieval.hybrid import hybrid_search
from novel_agent.retrieval.models import RetrievalCandidate
from novel_agent.state.sqlite_store import SQLiteStateStore


def test_rrf_deduplicates_and_preserves_all_routes() -> None:
    results = reciprocal_rank_fusion(
        {
            "fts": [{"memory_id": "event:E1", "kind": "canon_fact", "text": "事实"}],
            "vector": [{"memory_id": "event:E1", "kind": "canon_fact", "text": "事实"}],
        }
    )
    assert len(results) == 1
    assert set(results[0].routes) == {"fts", "vector"}
    assert results[0].fused_score > 0


def test_hybrid_search_keeps_fts_when_optional_route_fails(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path)
    store.sync_state_update("001", {"events": [{"id": "E1", "summary": "蓝鳞剑事实"}]})
    results = hybrid_search(store, "蓝鳞剑", route_results={"vector": []})
    assert results
    assert "fts" in results[0].routes


def test_context_pack_is_fail_closed_for_required_facts() -> None:
    items = [
        RetrievalCandidate("required", "canon_fact", "必须保留的事实", hardness="required"),
        RetrievalCandidate("style", "style", "很长的参考文本" * 10, hardness="style"),
    ]
    pack = build_context_pack(items, required_memory_ids=["required"], max_chars=4)
    assert pack["status"] == "error"
    assert pack["coverage"] == 0
    assert "required" in pack["missing_required_memory_ids"]
