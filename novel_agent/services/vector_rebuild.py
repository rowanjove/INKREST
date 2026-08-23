"""Resumable vector rebuild checkpoint for large projects."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict

import numpy as np

from novel_agent.state.sqlite_schema import safe_connection


CHECKPOINT_RELATIVE = Path("workspace") / "vector_rebuild_checkpoint.json"


def _chapter_id_from_metadata(raw: Any) -> str:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return ""
    if not isinstance(raw, dict):
        return ""
    for key in ("chapter_id", "chapter", "chapterId"):
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def load_vector_rebuild_checkpoint(root_dir: Path) -> Dict[str, Any]:
    path = Path(root_dir) / CHECKPOINT_RELATIVE
    if not path.is_file():
        return {
            "last_chapter_id": "",
            "last_chunk_id": "",
            "completed": False,
            "processed_rows": 0,
            "backend": "",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "last_chapter_id": "",
            "last_chunk_id": "",
            "completed": False,
            "processed_rows": 0,
            "backend": "",
        }
    if not isinstance(payload, dict):
        return {
            "last_chapter_id": "",
            "last_chunk_id": "",
            "completed": False,
        }
    return {
        "last_chapter_id": str(payload.get("last_chapter_id") or ""),
        "last_chunk_id": str(payload.get("last_chunk_id") or ""),
        "completed": bool(payload.get("completed")),
        "processed_rows": int(payload.get("processed_rows") or 0),
        "backend": str(payload.get("backend") or ""),
    }


def save_vector_rebuild_checkpoint(
    root_dir: Path,
    *,
    last_chapter_id: str,
    last_chunk_id: str = "",
    completed: bool = False,
    processed_rows: int = 0,
    backend: str = "",
) -> Dict[str, Any]:
    payload = {
        "last_chapter_id": str(last_chapter_id or ""),
        "last_chunk_id": str(last_chunk_id or ""),
        "completed": bool(completed),
        "processed_rows": max(0, int(processed_rows)),
        "backend": str(backend or ""),
    }
    path = Path(root_dir) / CHECKPOINT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    return payload


def _persist_hnsw_index(root_dir: Path, dim: int, index: Any, labels: list[str]) -> None:
    data_dir = Path(root_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    bin_path = data_dir / f"hnsw_index_{dim}.bin"
    labels_path = data_dir / f"hnsw_labels_{dim}.json"
    bin_tmp = bin_path.with_name(bin_path.name + ".tmp")
    labels_tmp = labels_path.with_name(labels_path.name + ".tmp")
    index.save_index(str(bin_tmp))
    labels_tmp.write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")
    os.replace(bin_tmp, bin_path)
    os.replace(labels_tmp, labels_path)


def rebuild_vector_index(
    root_dir: Path,
    *,
    chunk_size: int = 500,
    should_abort: Callable[[], bool] | None = None,
    on_progress: Callable[[Dict[str, Any]], None] | None = None,
) -> Dict[str, Any]:
    """Rebuild HNSW from SQLite in resumable chunks.

    The SQLite rows are the source of truth. If hnswlib is unavailable, the
    scan still records a completed checkpoint so callers can report a bounded
    SQLite fallback instead of pretending an index was built.
    """

    root = Path(root_dir)
    checkpoint = load_vector_rebuild_checkpoint(root)
    if checkpoint.get("completed"):
        return checkpoint
    chunk_size = max(1, min(int(chunk_size), 5000))
    db_path = root / "data" / "novel.sqlite"
    with safe_connection(db_path) as conn:
        total_rows = int(
            conn.execute(
                "select count(*) from vector_embeddings where embedding is not null"
            ).fetchone()[0]
        )
    try:
        import hnswlib  # type: ignore
    except ImportError:
        hnswlib = None

    indexes: dict[int, Any] = {}
    labels: dict[int, list[str]] = {}
    capacities: dict[int, int] = {}
    if hnswlib is not None:
        with safe_connection(db_path) as conn:
            for row in conn.execute(
                """
                select length(embedding) / 4 as dim, count(*) as count
                from vector_embeddings
                where embedding is not null and length(embedding) > 0
                group by length(embedding)
                """
            ):
                capacities[int(row[0])] = int(row[1])
        for dim, capacity in capacities.items():
            index = hnswlib.Index(space="cosine", dim=dim)
            bin_path = root / "data" / f"hnsw_index_{dim}.bin"
            labels_path = root / "data" / f"hnsw_labels_{dim}.json"
            if checkpoint.get("last_chunk_id") and bin_path.is_file() and labels_path.is_file():
                try:
                    labels[dim] = json.loads(labels_path.read_text(encoding="utf-8"))
                    index.load_index(str(bin_path), max_elements=max(capacity, len(labels[dim]) + 100))
                except Exception:
                    labels[dim] = []
                    index.init_index(max_elements=max(10000, capacity), ef_construction=200, M=16)
            else:
                labels[dim] = []
                index.init_index(max_elements=max(10000, capacity), ef_construction=200, M=16)
            indexes[dim] = index

    last_id = str(checkpoint.get("last_chunk_id") or "")
    last_chapter_id = str(checkpoint.get("last_chapter_id") or "")
    processed = int(checkpoint.get("processed_rows") or 0)
    while True:
        if should_abort and should_abort():
            return save_vector_rebuild_checkpoint(
                root,
                last_chapter_id=last_chapter_id,
                last_chunk_id=last_id,
                processed_rows=processed,
                backend="hnswlib" if hnswlib is not None else "sqlite",
            )
        with safe_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select id, metadata, chapter_id, embedding
                from vector_embeddings
                where embedding is not null and id > ?
                order by id
                limit ?
                """,
                (last_id, chunk_size),
            ).fetchall()
        if not rows:
            return save_vector_rebuild_checkpoint(
                root,
                last_chapter_id=last_chapter_id,
                last_chunk_id=last_id,
                completed=True,
                processed_rows=processed,
                backend="hnswlib" if hnswlib is not None else "sqlite",
            )

        grouped_vectors: dict[int, list[np.ndarray]] = {}
        grouped_ids: dict[int, list[str]] = {}
        for row in rows:
            last_id = str(row["id"])
            chapter_id = _chapter_id_from_metadata(row["metadata"]) or str(
                row["chapter_id"] or ""
            )
            if chapter_id:
                last_chapter_id = chapter_id
            embedding = row["embedding"]
            if not embedding or len(embedding) % 4:
                continue
            dim = len(embedding) // 4
            if hnswlib is None or dim not in indexes:
                continue
            grouped_vectors.setdefault(dim, []).append(
                np.frombuffer(embedding, dtype=np.float32).copy()
            )
            grouped_ids.setdefault(dim, []).append(last_id)
        for dim, vectors in grouped_vectors.items():
            if not vectors:
                continue
            index = indexes[dim]
            if index.get_current_count() + len(vectors) >= index.get_max_elements():
                index.resize_index(max(index.get_max_elements() * 2, index.get_current_count() + len(vectors) + 100))
            start_label = len(labels[dim])
            index.add_items(np.asarray(vectors, dtype=np.float32), np.arange(start_label, start_label + len(vectors)))
            labels[dim].extend(grouped_ids[dim])
            _persist_hnsw_index(root, dim, index, labels[dim])
        processed += len(rows)
        checkpoint = save_vector_rebuild_checkpoint(
            root,
            last_chapter_id=last_chapter_id,
            last_chunk_id=last_id,
            processed_rows=processed,
            backend="hnswlib" if hnswlib is not None else "sqlite",
        )
        if on_progress:
            on_progress(
                {
                    "step": "vector_rebuild",
                    "status": "running",
                    "progress": round(processed * 100 / total_rows) if total_rows else 100,
                    "processed_rows": processed,
                    "last_chunk_id": last_id,
                    "last_chapter_id": last_chapter_id,
                }
            )
