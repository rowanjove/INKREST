"""Lightweight vector store with SQLite and NumPy backend, featuring API fallback.

Supports embedding providers: Zhipu, DashScope/Bailian, OpenAI-compatible, Local (ONNX), Stub.
"""

import os
import json
import re
import threading
import sqlite3
from novel_agent.state.sqlite_store import safe_connection, db_write_lock
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import httpx
import numpy as np

from novel_agent.logging_config import get_logger

logger = get_logger("state.vector_store")

_SQLITE_VECTOR_SCAN_CAP = 2500


def normalize_chapter_id_value(chapter_id: str) -> str:
    value = str(chapter_id or "").strip()
    if value.isdigit():
        return f"{int(value):03d}"
    return value


def chapter_id_from_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    if not metadata:
        return ""
    raw = metadata.get("chapter") or metadata.get("chapter_id") or ""
    text = str(raw).strip().lower().replace("chapter_", "")
    if not text:
        return ""
    return normalize_chapter_id_value(text)


def chapter_num_from_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[int]:
    if not metadata:
        return None
    raw = metadata.get("chapter") or metadata.get("chapter_id") or ""
    text = str(raw).strip().lower().replace("chapter_", "")
    if text.isdigit():
        return int(text)
    return None


def metadata_in_chapter_window(
    metadata: Optional[Dict[str, Any]],
    current_chapter: Optional[str],
    window: int,
) -> bool:
    if not current_chapter or window <= 0:
        return True
    cur = chapter_num_from_metadata({"chapter": current_chapter})
    if cur is None:
        try:
            cur = int(str(current_chapter).lstrip("0") or "0")
        except ValueError:
            return True
    ch = chapter_num_from_metadata(metadata)
    if ch is None:
        return False
    return (cur - window) <= ch <= (cur + 5)


# ---------------------------------------------------------------------------
# Chunk structure
# ---------------------------------------------------------------------------

@dataclass
class VectorChunk:
    id: str
    type: str  # scene_summary, prose_chunk, character_behavior, foreshadow, etc.
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, chunks: List[VectorChunk]) -> None: ...

    def search(
        self,
        query: str,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]: ...

    def delete(self, ids: List[str]) -> None: ...

    def delete_chapter_vectors(self, chapter_id: str) -> None: ...


# ---------------------------------------------------------------------------
# Local ONNX Embedder helper
# ---------------------------------------------------------------------------

class LocalONNXEmbedder:
    """Helper to run a local quantization embedding model (e.g. bge-micro-v2.onnx).

    Dynamically loads onnxruntime and transformers.
    """
    def __init__(self, model_path: str):
        import onnxruntime as ort
        from transformers import AutoTokenizer
        self.model_path = model_path
        self.tokenizer = AutoTokenizer.from_pretrained(os.path.dirname(model_path))
        self.session = ort.InferenceSession(model_path)

    def embed(self, texts: List[str]) -> np.ndarray:
        inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="np")
        # Align inputs with ONNX session input names
        input_names = [i.name for i in self.session.get_inputs()]
        ort_inputs = {k: v for k, v in inputs.items() if k in input_names}

        outputs = self.session.run(None, ort_inputs)
        # Typically BGE-micro outputs token embeddings at index 0
        token_embeddings = outputs[0]
        attention_mask = inputs["attention_mask"]

        # Mean Pooling to get sentence embeddings
        input_mask_expanded = np.expand_dims(attention_mask, -1).astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
        embeddings = sum_embeddings / sum_mask

        # L2 Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return embeddings / norms

from novel_agent.state.sqlite_vector_store import (
    SQLiteEmbeddingVectorStore,
    apply_chapter_distance_penalty,
    create_vector_store,
    metadata_in_chapter_window,
    chapter_id_from_metadata
)

# ---------------------------------------------------------------------------
# SQLite + NumPy + Fallback Embedding Vector Store
# ---------------------------------------------------------------------------
