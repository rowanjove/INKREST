"""Resumable vector maintenance contract tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from novel_agent.services.vector_rebuild import (
    load_vector_rebuild_checkpoint,
    rebuild_vector_index,
)
from novel_agent.state.vector_store import SQLiteEmbeddingVectorStore


def test_vector_rebuild_records_checkpoint_and_resumes_without_hnsw(tmp_path: Path) -> None:
    store = SQLiteEmbeddingVectorStore({"provider": "stub"}, root_dir=tmp_path)
    vector = np.ones(4, dtype=np.float32).tobytes()
    with sqlite3.connect(store.db_path) as conn:
        for index in range(5):
            conn.execute(
                "insert into vector_embeddings (id, type, text, embedding, metadata, chapter_id) values (?, ?, ?, ?, ?, ?)",
                (f"v{index}", "summary", f"文本{index}", vector, "{}", str(index + 1)),
            )
        conn.commit()

    calls = 0

    def abort_after_first_chunk() -> bool:
        nonlocal calls
        calls += 1
        return calls > 1

    partial = rebuild_vector_index(
        tmp_path,
        chunk_size=2,
        should_abort=abort_after_first_chunk,
    )
    assert partial["completed"] is False
    assert partial["processed_rows"] == 2
    assert load_vector_rebuild_checkpoint(tmp_path)["last_chunk_id"] == "v1"
    assert load_vector_rebuild_checkpoint(tmp_path)["last_chapter_id"] == "2"

    completed = rebuild_vector_index(tmp_path, chunk_size=2)
    assert completed["completed"] is True
    assert completed["processed_rows"] == 5
