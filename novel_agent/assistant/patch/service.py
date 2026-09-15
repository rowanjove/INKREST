"""PatchService - Manages lifecycle and application of AssistantPatch modifications."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import AssistantPatch, EditorRange, PatchStatus


class PatchService:
    def __init__(self, root_dir: Optional[Path]):
        self.root_dir = Path(root_dir) if root_dir else None
        self.store = AssistantStore(self.root_dir)
        self.adapter = StoryAdapter(self.root_dir)

    def create_patch(
        self,
        project_id: Optional[str] = None,
        chapter_id: str = "",
        original_text: str = "",
        proposed_text: str = "",
        reason: str = "",
        skill_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        source_range: Optional[EditorRange] = None,
    ) -> AssistantPatch:
        pid = project_id or (self.root_dir.name if self.root_dir else "default")
        patch_id = f"patch_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        patch = AssistantPatch(
            id=patch_id,
            project_id=pid,
            chapter_id=str(chapter_id),
            thread_id=thread_id,
            source_range=source_range,
            original_text=original_text,
            proposed_text=proposed_text,
            reason=reason,
            skill_id=skill_id,
            status=PatchStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )
        self.store.save_patch(patch)
        return patch

    def get_patch(self, patch_id: str) -> Optional[AssistantPatch]:
        return self.store.get_patch(patch_id)

    def list_patches(
        self,
        project_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AssistantPatch]:
        return self.store.list_patches(project_id, chapter_id, limit)

    def reject_patch(self, patch_id: str) -> Optional[AssistantPatch]:
        return self.store.update_patch_status(patch_id, PatchStatus.REJECTED)

    def apply_patch(self, patch_id: str) -> Dict[str, Any]:
        """Applies proposed text to the chapter file and updates status to ACCEPTED."""
        patch = self.store.get_patch(patch_id)
        if not patch:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        if patch.status == PatchStatus.ACCEPTED:
            return {"success": True, "message": "Already accepted", "patch": patch}

        chapter_text = self.adapter.get_chapter_text(patch.chapter_id)
        if not chapter_text and patch.original_text:
            return {"success": False, "error": f"Chapter {patch.chapter_id} content not found"}

        new_text = self._replace_text(chapter_text, patch.original_text, patch.proposed_text)
        if new_text is None:
            return {
                "success": False,
                "error": "Original text segment could not be reliably located in chapter",
            }

        self._save_chapter_text(patch.chapter_id, new_text)
        updated_patch = self.store.update_patch_status(patch_id, PatchStatus.ACCEPTED)
        return {"success": True, "patch": updated_patch, "new_text": new_text}

    def revert_patch(self, patch_id: str) -> Dict[str, Any]:
        """Reverts previously accepted patch back to original text and updates status to REVERTED."""
        patch = self.store.get_patch(patch_id)
        if not patch:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        if patch.status != PatchStatus.ACCEPTED:
            return {"success": False, "error": f"Patch status is {patch.status}, cannot revert"}

        chapter_text = self.adapter.get_chapter_text(patch.chapter_id)
        new_text = self._replace_text(chapter_text, patch.proposed_text, patch.original_text)
        if new_text is None:
            return {
                "success": False,
                "error": "Proposed text segment could not be located to revert",
            }

        self._save_chapter_text(patch.chapter_id, new_text)
        updated_patch = self.store.update_patch_status(patch_id, PatchStatus.REVERTED)
        return {"success": True, "patch": updated_patch, "reverted_text": new_text}

    def _replace_text(self, full_text: str, target: str, replacement: str) -> Optional[str]:
        if not target:
            # If target is empty, append at the end
            return full_text + ("\n\n" if full_text else "") + replacement
        if target in full_text:
            # Single exact match
            return full_text.replace(target, replacement, 1)
        # Normalize whitespace fallback
        norm_full = " ".join(full_text.split())
        norm_target = " ".join(target.split())
        if norm_target in norm_full:
            # If normalized exists, do a best-effort line-based match
            lines = full_text.splitlines()
            target_lines = [l.strip() for l in target.splitlines() if l.strip()]
            if target_lines and target_lines[0] in full_text:
                start_idx = full_text.find(target_lines[0])
                end_idx = full_text.find(target_lines[-1], start_idx) + len(target_lines[-1])
                return full_text[:start_idx] + replacement + full_text[end_idx:]
        return None

    def _save_chapter_text(self, chapter_id: str, text: str) -> None:
        if not self.root_dir:
            return
        safe_id = str(chapter_id).replace("/", "").replace("\\", "").strip()
        ch_dir = self.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
        if not ch_dir.is_dir():
            for p in (self.root_dir / "workspace" / "chapters").glob("chapter_*"):
                if p.is_dir() and p.name.endswith(safe_id):
                    ch_dir = p
                    break
        ch_dir.mkdir(parents=True, exist_ok=True)
        (ch_dir / "chapter.txt").write_text(text, encoding="utf-8")

        # Also update chapter.json if present
        json_file = ch_dir / "chapter.json"
        if json_file.is_file():
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data["content"] = text
                    data["updated_at"] = datetime.now().isoformat()
                    json_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
