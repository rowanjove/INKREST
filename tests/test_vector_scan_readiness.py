"""SQLite vector fallback scan cap is visible for epic/infinite projects."""

from __future__ import annotations

from pathlib import Path

from novel_agent.state.vector_readiness import (
    SQLITE_VECTOR_SCAN_CAP,
    vector_fallback_readiness,
)


def test_scan_cap_constant_is_exported() -> None:
    assert SQLITE_VECTOR_SCAN_CAP == 50000


def test_epic_sqlite_fallback_requires_chroma_or_explicit_degrade(tmp_path: Path) -> None:
    report = vector_fallback_readiness(
        tmp_path,
        scale="epic",
        backend="sqlite",
        scanned_rows=50001,
    )
    assert report["capped"] is True
    assert report["requires_chroma"] is True
    assert report["scan_cap"] == SQLITE_VECTOR_SCAN_CAP
    assert report["warning"]


def test_short_scale_does_not_require_chroma(tmp_path: Path) -> None:
    report = vector_fallback_readiness(
        tmp_path,
        scale="short",
        backend="sqlite",
        scanned_rows=10,
    )
    assert report["requires_chroma"] is False
    assert report["capped"] is False
