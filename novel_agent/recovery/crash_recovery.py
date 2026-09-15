"""Crash detection and non-destructive draft recovery (Milestone B).

Monitors clean shutdown flags and persists uncommitted auto-save drafts.
Upon unclean termination, exposes drafts with visual diff capability
before applying changes to formal novel chapters.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UnsavedDraft:
    doc_id: str
    project_id: str
    title: str
    content: str
    saved_at: str = field(default_factory=now_iso)
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0:
            self.word_count = len(self.content.strip())

    def to_dict(self) -> Dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "project_id": self.project_id,
            "title": self.title,
            "content": self.content,
            "saved_at": self.saved_at,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> UnsavedDraft:
        return cls(
            doc_id=str(data["doc_id"]),
            project_id=str(data["project_id"]),
            title=str(data.get("title", "")),
            content=str(data.get("content", "")),
            saved_at=str(data.get("saved_at", now_iso())),
            word_count=int(data.get("word_count", 0)),
        )


@dataclass
class CrashReport:
    crashed_at: str
    drafts: List[UnsavedDraft] = field(default_factory=list)
    has_uncommitted_work: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "crashed_at": self.crashed_at,
            "has_uncommitted_work": self.has_uncommitted_work,
            "drafts": [d.to_dict() for d in self.drafts],
        }


class CrashRecoveryManager:
    """Manages crash detection and draft recovery for a specific vault."""

    def __init__(self, vault_dir: Path) -> None:
        self.vault_dir = Path(vault_dir).resolve()
        self.recovery_dir = self.vault_dir / "recovery"
        self.drafts_dir = self.recovery_dir / "drafts"
        self.state_file = self.recovery_dir / "shutdown_state.json"
        self.ensure_dirs()

    def ensure_dirs(self) -> None:
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def record_startup(self) -> None:
        """Called upon application / vault startup. Flags shutdown as unclean until cleanly closed."""
        state = {
            "last_clean_shutdown": False,
            "startup_at": now_iso(),
            "active_session": True,
        }
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def mark_clean_shutdown(self) -> None:
        """Called upon graceful exit. Sets clean shutdown flag."""
        state = {
            "last_clean_shutdown": True,
            "shutdown_at": now_iso(),
            "active_session": False,
        }
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def detect_unclean_shutdown(self) -> Optional[CrashReport]:
        """Check if previous session crashed or terminated unexpectedly."""
        if not self.state_file.is_file():
            return None
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
            if state.get("last_clean_shutdown", True) is True:
                return None
            crashed_at = state.get("startup_at", now_iso())
            drafts = self.list_drafts()
            return CrashReport(
                crashed_at=crashed_at,
                drafts=drafts,
                has_uncommitted_work=len(drafts) > 0,
            )
        except Exception:
            return None

    def save_draft(self, doc_id: str, project_id: str, title: str, content: str) -> UnsavedDraft:
        """Persist an auto-save / in-progress draft."""
        draft = UnsavedDraft(
            doc_id=doc_id,
            project_id=project_id,
            title=title,
            content=content,
        )
        draft_file = self.drafts_dir / f"{project_id}_{doc_id}.json"
        draft_file.write_text(json.dumps(draft.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return draft

    def get_draft(self, doc_id: str, project_id: str) -> Optional[UnsavedDraft]:
        draft_file = self.drafts_dir / f"{project_id}_{doc_id}.json"
        if not draft_file.is_file():
            return None
        try:
            data = json.loads(draft_file.read_text(encoding="utf-8"))
            return UnsavedDraft.from_dict(data)
        except Exception:
            return None

    def list_drafts(self) -> List[UnsavedDraft]:
        results: List[UnsavedDraft] = []
        if not self.drafts_dir.is_dir():
            return results
        for item in sorted(self.drafts_dir.glob("*.json")):
            try:
                data = json.loads(item.read_text(encoding="utf-8"))
                results.append(UnsavedDraft.from_dict(data))
            except Exception:
                pass
        return results

    def discard_draft(self, doc_id: str, project_id: str) -> bool:
        draft_file = self.drafts_dir / f"{project_id}_{doc_id}.json"
        if draft_file.is_file():
            draft_file.unlink()
            return True
        return False

    def clear_all_drafts(self) -> None:
        if self.drafts_dir.is_dir():
            for item in self.drafts_dir.glob("*.json"):
                try:
                    item.unlink()
                except Exception:
                    pass

    def compute_diff(self, original_text: str, draft_text: str) -> str:
        """Generate unified diff between original content and recoverable draft."""
        orig_lines = original_text.splitlines(keepends=True)
        draft_lines = draft_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            draft_lines,
            fromfile="已保存正文 (Original)",
            tofile="崩溃恢复草稿 (Recoverable Draft)",
            lineterm="",
        )
        return "\n".join(diff)
