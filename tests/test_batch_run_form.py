"""Unit tests for batch run form helpers (mirrors frontend batchRunForm.ts)."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BATCH_FORM_TS = ROOT / "web" / "frontend" / "src" / "utils" / "batchRunForm.ts"


def _read_ts() -> str:
    return BATCH_FORM_TS.read_text(encoding="utf-8")


def test_batch_form_storage_key_pattern() -> None:
    source = _read_ts()
    assert "inkrest_batch_form_" in source
    assert "batchFormStorageKey" in source


def test_cancel_messages_cover_phases() -> None:
    source = _read_ts()
    assert "已取消加载开书状态" in source
    assert "已取消同步卷队列" in source
    assert "任务可能仍在后台" in source


def test_round_progress_label_template() -> None:
    source = _read_ts()
    assert "本轮上限" in source
    assert re.search(r"computeRoundProgress", source)