"""SQLite vector fallback scan-cap and scale-aware readiness."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

SQLITE_VECTOR_SCAN_CAP = 50000
_CHROMA_REQUIRED_SCALES = frozenset({"epic", "infinite"})


def vector_fallback_readiness(
    root_dir: Optional[Path] = None,
    *,
    scale: str = "medium",
    backend: str = "sqlite",
    scanned_rows: int = 0,
    scan_cap: int = SQLITE_VECTOR_SCAN_CAP,
    capped: Optional[bool] = None,
) -> Dict[str, Any]:
    """Describe whether SQLite linear scan is acceptable for this project."""

    del root_dir  # reserved for reading project embedding config
    was_capped = (
        bool(capped) if capped is not None else int(scanned_rows) > int(scan_cap)
    )
    backend_name = str(backend or "sqlite").strip().lower()
    requires_chroma = scale in _CHROMA_REQUIRED_SCALES and backend_name != "chromadb"
    warning = ""
    if was_capped:
        warning = (
            f"SQLite 向量扫描已达到 {scan_cap} 条上限；"
            "超长篇/无限连载请启用 ChromaDB，或明确接受降级召回。"
        )
    elif requires_chroma:
        warning = (
            "超长篇/无限连载默认要求 ChromaDB；当前为 SQLite fallback，检索可能不完整。"
        )
    return {
        "backend": backend_name,
        "scale": scale,
        "scanned_rows": int(scanned_rows),
        "scan_cap": int(scan_cap),
        "capped": was_capped,
        "requires_chroma": requires_chroma,
        "warning": warning,
    }
