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
from typing import Any, Dict, List, Optional, Protocol

import httpx
import numpy as np

from novel_agent.logging_config import get_logger

logger = get_logger("state.vector_store")

_SQLITE_VECTOR_SCAN_CAP = 2500


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


# ---------------------------------------------------------------------------
# SQLite + NumPy + Fallback Embedding Vector Store
# ---------------------------------------------------------------------------

class SQLiteEmbeddingVectorStore:
    def __init__(self, config: Dict[str, Any], root_dir: Optional[Path] = None):
        self.config = config
        self.root_dir = Path(root_dir) if root_dir else Path(".")
        self.db_path = self.root_dir / "data" / "novel.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.provider = config.get("provider", "stub")
        self.api_key = config.get("api_key", "").strip()
        self.base_url = config.get("base_url", "").strip()
        self.model = config.get("model", "text-embedding-3-small").strip()
        self.timeout = float(config.get("timeout", 60.0))
        self.max_retries = int(config.get("max_retries", 3))
        self.proxy = config.get("proxy", "").strip()

        self.backend = config.get("backend", "sqlite").strip().lower()

        self._lock = threading.Lock()
        client_kwargs = {"timeout": self.timeout}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
        self._client = httpx.Client(**client_kwargs)

        self._init_db()

        self.chroma_client = None
        self.chroma_collection = None
        if self.backend == "chromadb" and CHROMA_AVAILABLE:
            try:
                chroma_path = self.root_dir / "data" / "chromadb"
                self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="novel_embeddings",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("ChromaDB initialized successfully at %s", chroma_path)
            except Exception as e:
                logger.error("Failed to initialize ChromaDB: %s. Fallback to SQLite.", e)

    def _init_db(self) -> None:
        with self._lock, safe_connection(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_embeddings (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    text TEXT,
                    embedding BLOB,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_type ON vector_embeddings(type)"
            )
            conn.commit()

    def close(self) -> None:
        self._client.close()

    def _tokenize(self, text: str) -> List[str]:
        try:
            import jieba
            return [t for t in jieba.cut(text.lower()) if t.strip() and re.match(r'^[\u4e00-\u9fffA-Za-z0-9]+$', t)]
        except ImportError:
            return re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', text.lower())

    # -- embedding fallback chain --------------------------------------------

    def _embed_with_fallback(self, texts: List[str]) -> Optional[np.ndarray]:
        # Support local embedding model
        if self.provider == "local":
            try:
                model_path = self.config.get("model_path") or str(self.root_dir / "data" / "models" / "bge-micro-v2.onnx")
                if not os.path.exists(model_path):
                    logger.warning("Local ONNX model file not found at %s. Fallback to Stub.", model_path)
                    return None

                logger.info("Attempting Local ONNX Embedding with model: %s...", model_path)
                embedder = LocalONNXEmbedder(model_path)
                return embedder.embed(texts)
            except Exception as e:
                logger.error("Local ONNX Embedding failed: %s. Fallback to Stub.", e)
                return None

        if self.provider == "stub":
            return None

        if not self.api_key:
            logger.warning("Embedding api_key is empty. Fallback to Local Stub.")
            return None

        provider = (self.provider or "openai").strip().lower()

        if provider == "zhipu":
            try:
                logger.info("Embedding via Zhipu (text-embedding-3)...")
                return self._call_embedding_api(
                    base_url="https://open.bigmodel.cn/api/paas/v4",
                    api_key=self.api_key,
                    model=self.model or "text-embedding-3",
                    texts=texts,
                )
            except Exception as e:
                logger.error("Zhipu embedding failed: %s", e)
                return None

        if provider in ("dashscope", "bailian"):
            try:
                base_url = self.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                model = self.model or "text-embedding-v3"
                logger.info("Embedding via DashScope/Bailian: %s / %s...", base_url, model)
                return self._call_embedding_api(
                    base_url=base_url,
                    api_key=self.api_key,
                    model=model,
                    texts=texts,
                )
            except Exception as e:
                logger.error("DashScope embedding failed: %s", e)
                return None

        # openai or legacy custom provider
        try:
            base_url = self.base_url if self.base_url else "https://api.openai.com/v1"
            model = self.model if self.model else "text-embedding-3-small"
            logger.info("Embedding via OpenAI-compatible: %s / %s...", base_url, model)
            return self._call_embedding_api(
                base_url=base_url,
                api_key=self.api_key,
                model=model,
                texts=texts,
            )
        except Exception as e:
            logger.error("OpenAI-compatible embedding failed: %s", e)
            return None

    def _call_embedding_api(
        self, base_url: str, api_key: str, model: str, texts: List[str]
    ) -> np.ndarray:
        import time
        url = f"{base_url.rstrip('/')}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {"model": model, "input": texts}
        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = self._client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                vectors = [item["embedding"] for item in data["data"]]
                return np.array(vectors, dtype=np.float32)
            except Exception as exc:
                last_error = exc
                logger.warning("API Attempt %d/%d failed: %s", attempt + 1, self.max_retries, exc)
                if attempt < self.max_retries - 1:
                    time.sleep(1.0 * (2 ** attempt))
        raise RuntimeError(f"Embedding API failed: {last_error}")

    # -- public CRUD API -----------------------------------------------------

    def _get_hnsw_index(self, dim: int) -> Optional[Any]:
        import hnswlib
        if not hasattr(self, "_hnsw_indices"):
            self._hnsw_indices = {}
            self._hnsw_labels = {}

        if dim in self._hnsw_indices:
            return self._hnsw_indices[dim]

        bin_path = self.root_dir / "data" / f"hnsw_index_{dim}.bin"
        json_path = self.root_dir / "data" / f"hnsw_labels_{dim}.json"

        p = hnswlib.Index(space='cosine', dim=dim)

        # Load from disk if files exist
        if bin_path.exists() and json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self._hnsw_labels[dim] = json.load(f)

                # Set max_elements to at least the number of elements loaded, with room to grow
                max_elements = max(10000, len(self._hnsw_labels[dim]) * 2)
                p.load_index(str(bin_path), max_elements=max_elements)
                self._hnsw_indices[dim] = p
                logger.info("Loaded persistent HNSW index of dim %d with %d items", dim, len(self._hnsw_labels[dim]))
                return p
            except Exception as e:
                logger.warning("Failed to load persistent HNSW index of dim %d: %s. Rebuilding from DB...", dim, e)

        # Rebuild from DB
        logger.info("Rebuilding HNSW index of dim %d from SQLite...", dim)
        self._hnsw_labels[dim] = []
        vectors = []
        candidates_ids = []

        dim_bytes = dim * 4
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, embedding FROM vector_embeddings WHERE embedding IS NOT NULL"
            ).fetchall()
            for r in rows:
                if len(r["embedding"]) == dim_bytes:
                    vec = np.frombuffer(r["embedding"], dtype=np.float32)
                    vectors.append(vec)
                    candidates_ids.append(r["id"])

        if vectors:
            max_elements = max(10000, len(vectors) * 2)
            p.init_index(max_elements=max_elements, ef_construction=200, M=16)
            p.add_items(np.array(vectors, dtype=np.float32), np.arange(len(vectors)))
            self._hnsw_labels[dim] = candidates_ids
            self._hnsw_indices[dim] = p
            self._save_hnsw_index(dim)
            logger.info("Built and saved HNSW index of dim %d with %d items", dim, len(vectors))
            return p
        else:
            # Empty index
            p.init_index(max_elements=10000, ef_construction=200, M=16)
            self._hnsw_labels[dim] = []
            self._hnsw_indices[dim] = p
            return p

    def rebuild_hnsw_indices(self) -> Dict[str, int]:
        """Force rebuild in-memory and on-disk HNSW indices from SQLite embeddings."""
        dims: set = set()
        with self._lock, safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(
                "SELECT length(embedding) as blen FROM vector_embeddings WHERE embedding IS NOT NULL"
            ).fetchall():
                blen = int(row["blen"] or 0)
                if blen > 0 and blen % 4 == 0:
                    dims.add(blen // 4)
        if hasattr(self, "_hnsw_indices"):
            self._hnsw_indices.clear()
            self._hnsw_labels.clear()
        counts: Dict[str, int] = {}
        for dim in sorted(dims):
            for suffix in ("bin",):
                path = self.root_dir / "data" / f"hnsw_index_{dim}.{suffix}"
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
            labels_path = self.root_dir / "data" / f"hnsw_labels_{dim}.json"
            if labels_path.exists():
                try:
                    labels_path.unlink()
                except OSError:
                    pass
            idx = self._get_hnsw_index(dim)
            counts[str(dim)] = idx.get_current_count() if idx is not None else 0
        logger.info("Rebuilt HNSW indices for dims: %s", counts)
        return counts

    def _save_hnsw_index(self, dim: int) -> None:
        if not hasattr(self, "_hnsw_indices") or dim not in self._hnsw_indices:
            return
        p = self._hnsw_indices[dim]
        labels = self._hnsw_labels[dim]

        bin_path = self.root_dir / "data" / f"hnsw_index_{dim}.bin"
        json_path = self.root_dir / "data" / f"hnsw_labels_{dim}.json"

        bin_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.save_index(str(bin_path))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(labels, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save HNSW index of dim %d: %s", dim, e)

    # -- public CRUD API -----------------------------------------------------

    def upsert(self, chunks: List[VectorChunk]) -> None:
        if not chunks:
            return

        texts = [c.text for c in chunks]
        embeddings = self._embed_with_fallback(texts)

        db_res = self._sqlite_upsert(chunks, embeddings)

        if self.chroma_collection is not None and embeddings is not None:
            try:
                ids = [c.id for c in chunks]
                embs_list = embeddings.tolist()
                metadatas = [{**c.metadata, "_type": c.type} for c in chunks]
                documents = [c.text for c in chunks]
                self.chroma_collection.upsert(
                    ids=ids,
                    embeddings=embs_list,
                    metadatas=metadatas,
                    documents=documents
                )
                logger.info("Synced %d embeddings to ChromaDB", len(chunks))
            except Exception as e:
                logger.error("Failed to sync embeddings to ChromaDB: %s", e)

        # Update persistent HNSW cache
        if embeddings is not None:
            try:
                import hnswlib
                dim = embeddings.shape[1]
                p = self._get_hnsw_index(dim)
                if p is not None:
                    for idx, chunk in enumerate(chunks):
                        emb = embeddings[idx].astype(np.float32)
                        if chunk.id in self._hnsw_labels[dim]:
                            label_idx = self._hnsw_labels[dim].index(chunk.id)
                            p.add_items(np.array([emb]), np.array([label_idx]))
                        else:
                            label_idx = len(self._hnsw_labels[dim])
                            current_count = p.get_current_count()
                            max_elements = p.get_max_elements()
                            if current_count >= max_elements - 5:
                                p.resize_index(max_elements * 2)
                            p.add_items(np.array([emb]), np.array([label_idx]))
                            self._hnsw_labels[dim].append(chunk.id)
                    self._save_hnsw_index(dim)
            except Exception as e:
                logger.error("Failed to update HNSW memory cache on upsert: %s", e)
        return db_res

    @db_write_lock
    def _sqlite_upsert(self, chunks: List[VectorChunk], embeddings: Optional[np.ndarray]) -> None:
        with safe_connection(self.db_path) as conn:
            for idx, chunk in enumerate(chunks):
                emb_blob = None
                if embeddings is not None:
                    emb_blob = embeddings[idx].astype(np.float32).tobytes()

                conn.execute(
                    """
                    INSERT INTO vector_embeddings (id, type, text, embedding, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      type=excluded.type,
                      text=excluded.text,
                      embedding=coalesce(excluded.embedding, vector_embeddings.embedding),
                      metadata=excluded.metadata
                    """,
                    (
                        chunk.id,
                        chunk.type,
                        chunk.text,
                        emb_blob,
                        json.dumps(chunk.metadata, ensure_ascii=False)
                    )
                )
            conn.commit()

    def search(
        self,
        query: str,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
        near_chapter_id: Optional[str] = None,
        chapter_window: int = 0,
    ) -> List[Dict[str, Any]]:
        query_vec = self._embed_with_fallback([query])
        if query_vec is not None:
            return self._search_vector(
                query_vec[0],
                top_k,
                filters,
                near_chapter_id=near_chapter_id,
                chapter_window=chapter_window,
            )
        return self._search_stub(
            query,
            top_k,
            filters,
            near_chapter_id=near_chapter_id,
            chapter_window=chapter_window,
        )

    @db_write_lock
    def delete(self, ids: List[str]) -> None:
        if not ids:
            return
        with safe_connection(self.db_path) as conn:
            conn.executemany(
                "DELETE FROM vector_embeddings WHERE id = ?",
                [(i,) for i in ids]
            )
            conn.commit()

        if self.chroma_collection is not None:
            try:
                self.chroma_collection.delete(ids=ids)
                logger.info("Deleted %d vectors from ChromaDB", len(ids))
            except Exception as e:
                logger.error("Failed to delete vectors from ChromaDB: %s", e)

        # Clear HNSW caches
        if hasattr(self, "_hnsw_indices"):
            self._hnsw_indices.clear()
            self._hnsw_labels.clear()
        for dim in [384, 768, 1536, 1024]:
            bin_path = self.root_dir / "data" / f"hnsw_index_{dim}.bin"
            json_path = self.root_dir / "data" / f"hnsw_labels_{dim}.json"
            if bin_path.exists():
                try: bin_path.unlink()
                except: pass
            if json_path.exists():
                try: json_path.unlink()
                except: pass

    @db_write_lock
    def delete_chapter_vectors(self, chapter_id: str) -> None:
        ids_to_delete = []
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, metadata FROM vector_embeddings").fetchall()
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except json.JSONDecodeError:
                        pass
                ch = meta.get("chapter") or meta.get("chapter_id")
                if str(ch) == str(chapter_id):
                    ids_to_delete.append(row["id"])

            if ids_to_delete:
                conn.executemany(
                    "DELETE FROM vector_embeddings WHERE id = ?",
                    [(i,) for i in ids_to_delete]
                )
                conn.commit()
                logger.info("Deleted %d vectors for chapter %s", len(ids_to_delete), chapter_id)

        if self.chroma_collection is not None and ids_to_delete:
            try:
                self.chroma_collection.delete(ids=ids_to_delete)
                logger.info("Deleted %d vectors for chapter %s from ChromaDB", len(ids_to_delete), chapter_id)
            except Exception as e:
                logger.error("Failed to delete chapter vectors from ChromaDB: %s", e)

        # Clear HNSW caches
        if hasattr(self, "_hnsw_indices"):
            self._hnsw_indices.clear()
            self._hnsw_labels.clear()
        for dim in [384, 768, 1536, 1024]:
            bin_path = self.root_dir / "data" / f"hnsw_index_{dim}.bin"
            json_path = self.root_dir / "data" / f"hnsw_labels_{dim}.json"
            if bin_path.exists():
                try: bin_path.unlink()
                except: pass
            if json_path.exists():
                try: json_path.unlink()
                except: pass

    # -- search helpers ------------------------------------------------------

    def _search_vector(
        self,
        query_vec: np.ndarray,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
        near_chapter_id: Optional[str] = None,
        chapter_window: int = 0,
    ) -> List[Dict[str, Any]]:
        if self.chroma_collection is not None:
            try:
                query_res = self.chroma_collection.query(
                    query_embeddings=[query_vec.tolist()],
                    n_results=min(150, self.chroma_collection.count())
                )
                candidates = []
                if query_res and "ids" in query_res and query_res["ids"]:
                    ids = query_res["ids"][0]
                    distances = query_res["distances"][0] if "distances" in query_res else [0.0] * len(ids)
                    metadatas = query_res["metadatas"][0] if "metadatas" in query_res else [{}] * len(ids)
                    documents = query_res["documents"][0] if "documents" in query_res else [""] * len(ids)

                    for idx, doc_id in enumerate(ids):
                        meta = metadatas[idx] or {}
                        type_val = meta.get("_type", "")
                        chunk = {
                            "id": doc_id,
                            "type": type_val,
                            "text": documents[idx],
                            "metadata": {k: v for k, v in meta.items() if k != "_type"},
                        }
                        if filters and not self._match_filters(chunk, filters):
                            continue
                        if not metadata_in_chapter_window(
                            chunk.get("metadata"), near_chapter_id, chapter_window
                        ):
                            continue
                        chunk["score"] = float(1.0 - distances[idx])
                        candidates.append(chunk)
                candidates.sort(key=lambda x: x["score"], reverse=True)
                return candidates[:top_k]
            except Exception as e:
                logger.error("ChromaDB search failed: %s. Fallback to SQLite.", e)

        query_dim = len(query_vec)

        # 1. Try in-memory HNSW index
        try:
            import hnswlib
            p = self._get_hnsw_index(query_dim)
            if p is not None and p.get_current_count() > 0:
                k_search = min(top_k * 10, p.get_current_count())
                labels, distances = p.knn_query(query_vec, k=k_search)

                candidate_ids = []
                label_to_dist = {}
                for label, dist in zip(labels[0], distances[0]):
                    lbl_idx = int(label)
                    if lbl_idx < len(self._hnsw_labels[query_dim]):
                        chunk_id = self._hnsw_labels[query_dim][lbl_idx]
                        candidate_ids.append(chunk_id)
                        label_to_dist[chunk_id] = float(dist)

                if candidate_ids:
                    with self._lock, safe_connection(self.db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        placeholders = ",".join("?" for _ in candidate_ids)
                        rows = conn.execute(
                            f"SELECT id, type, text, metadata FROM vector_embeddings WHERE id IN ({placeholders})",
                            candidate_ids
                        ).fetchall()

                    results = []
                    for r in rows:
                        chunk = {
                            "id": r["id"],
                            "type": r["type"],
                            "text": r["text"],
                            "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                        }
                        if filters and not self._match_filters(chunk, filters):
                            continue
                        if not metadata_in_chapter_window(
                            chunk.get("metadata"), near_chapter_id, chapter_window
                        ):
                            continue
                        dist = label_to_dist.get(r["id"], 0.0)
                        chunk["score"] = float(1.0 - dist)
                        results.append(chunk)

                    results.sort(key=lambda x: x["score"], reverse=True)
                    return results[:top_k]
        except Exception as e:
            logger.debug("HNSW cached search failed: %s. Falling back to SQLite scan.", e)

        return self._search_sqlite_linear(
            query_vec,
            top_k,
            filters,
            near_chapter_id=near_chapter_id,
            chapter_window=chapter_window,
        )

    def _search_sqlite_linear(
        self,
        query_vec: np.ndarray,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        near_chapter_id: Optional[str] = None,
        chapter_window: int = 0,
    ) -> List[Dict[str, Any]]:
        """Bounded SQLite scan with optional chapter window filter."""
        dim_bytes = len(query_vec) * 4
        scanned = 0
        candidates: List[Dict[str, Any]] = []
        vectors: List[np.ndarray] = []
        with self._lock, safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, type, text, embedding, metadata FROM vector_embeddings WHERE embedding IS NOT NULL"
            ).fetchall()
            for r in rows:
                scanned += 1
                if scanned > _SQLITE_VECTOR_SCAN_CAP:
                    logger.warning(
                        "Vector scan capped at %d rows; enable Chroma/HNSW or narrow chapter_window",
                        _SQLITE_VECTOR_SCAN_CAP,
                    )
                    break
                if len(r["embedding"]) != dim_bytes:
                    continue
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
                chunk = {
                    "id": r["id"],
                    "type": r["type"],
                    "text": r["text"],
                    "metadata": meta,
                }
                if filters and not self._match_filters(chunk, filters):
                    continue
                if not metadata_in_chapter_window(meta, near_chapter_id, chapter_window):
                    continue
                vectors.append(np.frombuffer(r["embedding"], dtype=np.float32))
                candidates.append(chunk)

        if not candidates:
            return []

        vectors_arr = np.vstack(vectors)
        norms = np.linalg.norm(vectors_arr, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1.0, norms)
        scores = (vectors_arr @ query_vec) / norms
        results = []
        for idx, chunk in enumerate(candidates):
            chunk["score"] = float(scores[idx])
            results.append(chunk)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _search_stub(
        self,
        query: str,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
        near_chapter_id: Optional[str] = None,
        chapter_window: int = 0,
    ) -> List[Dict[str, Any]]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        with self._lock, safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, type, text, metadata FROM vector_embeddings").fetchall()

            candidates = []
            scanned = 0
            for r in rows:
                scanned += 1
                if scanned > _SQLITE_VECTOR_SCAN_CAP:
                    break
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
                chunk = {
                    "id": r["id"],
                    "type": r["type"],
                    "text": r["text"],
                    "metadata": meta,
                }
                if filters and not self._match_filters(chunk, filters):
                    continue
                if not metadata_in_chapter_window(meta, near_chapter_id, chapter_window):
                    continue
                candidates.append(chunk)

            if not candidates:
                return []

            # 计算 TF-based 相似度
            q_map: Dict[str, int] = {}
            for t in q_tokens:
                q_map[t] = q_map.get(t, 0) + 1
            q_norm = sum(v ** 2 for v in q_map.values()) ** 0.5

            results = []
            for chunk in candidates:
                c_tokens = self._tokenize(chunk["text"])
                if not c_tokens:
                    score = 0.0
                else:
                    c_map: Dict[str, int] = {}
                    for t in c_tokens:
                        c_map[t] = c_map.get(t, 0) + 1
                    dot_product = sum(q_map[t] * c_map.get(t, 0) for t in q_map)
                    c_norm = sum(v ** 2 for v in c_map.values()) ** 0.5
                    score = dot_product / (q_norm * c_norm) if q_norm * c_norm > 0 else 0.0

                if score > 0.0:
                    chunk["score"] = score
                    results.append(chunk)

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]

    @staticmethod
    def _chapter_value(value: Any, default: int) -> int:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            digits = "".join(ch for ch in value if ch.isdigit())
            if digits:
                return int(digits)
        return default

    @classmethod
    def _match_filters(cls, chunk: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        meta = chunk.get("metadata", {})
        for key, value in filters.items():
            if key == "chapter_lt":
                chapter = cls._chapter_value(meta.get("chapter"), 999999)
                filter_chapter = cls._chapter_value(value, 999999)
                if chapter >= filter_chapter:
                    return False
            elif key == "chapter_gt":
                chapter = cls._chapter_value(meta.get("chapter"), 0)
                filter_chapter = cls._chapter_value(value, 0)
                if chapter <= filter_chapter:
                    return False
            elif key == "type":
                if chunk.get("type") != value:
                    return False
            elif key == "status":
                if meta.get("status") != value:
                    return False
            elif key in ("characters", "objects", "threads"):
                chunk_list = meta.get(key, [])
                if isinstance(value, str):
                    value = [value]
                if not any(v in chunk_list for v in value):
                    return False
            elif key == "character":
                if meta.get("character") != value:
                    return False
            else:
                if meta.get(key) != value:
                    return False
        return True


# ---------------------------------------------------------------------------
# Distance penalty helper
# ---------------------------------------------------------------------------

def apply_chapter_distance_penalty(
    results: List[Dict[str, Any]],
    current_chapter: Any,
    top_k: int = 5,
    recent_cutoff: int = 3,
    rewrite_cutoff: int = 5,
) -> List[Dict[str, Any]]:
    current = SQLiteEmbeddingVectorStore._chapter_value(current_chapter, 0)
    if current <= 0:
        unpenalized = []
        for item in results[:top_k]:
            copied = dict(item)
            copied["metadata"] = dict(item.get("metadata", {}))
            copied["rewrite_hint"] = None
            unpenalized.append(copied)
        return unpenalized

    filtered = []
    for item in results:
        meta = item.get("metadata", {})
        chapter = SQLiteEmbeddingVectorStore._chapter_value(meta.get("chapter"), 0)
        delta = current - chapter
        # 排除太近的章节
        if chapter and delta <= recent_cutoff:
            continue
        copied = dict(item)
        copied["metadata"] = dict(meta)
        # 近期需要改写引用的打标
        if chapter and delta <= rewrite_cutoff:
            copied["rewrite_hint"] = "REQUIRE_REWRITE_40%"
        else:
            copied["rewrite_hint"] = None
        filtered.append(copied)
        if len(filtered) >= top_k:
            break
    return filtered


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_vector_store(
    config: Dict[str, Any],
    root_dir: Optional[Path] = None,
) -> VectorStore:
    return SQLiteEmbeddingVectorStore(config, root_dir=root_dir)
