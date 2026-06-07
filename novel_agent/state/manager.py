from pathlib import Path
from typing import Any, Dict
import os
import tempfile

import yaml

from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.update_validator import validate_state_update


def _safe_write_yaml(path: Path, data: Any) -> None:
    """Atomically write YAML by writing to temp file then renaming."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    # Write to temp file in same directory, then atomic rename
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        # Atomic rename on same filesystem
        Path(tmp_path).replace(path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


class StateManager:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.store = SQLiteStateStore(self.root_dir)

    def _build_candidates(self, chapter_id: str, update: Dict[str, Any], status: str) -> list:
        candidates = []

        # 1. events
        for item in update.get("events", []):
            if isinstance(item, dict) and item.get("id"):
                candidates.append({
                    "entity_type": "event",
                    "entity_id": item["id"],
                    "change_type": "add",
                    "old_value": None,
                    "new_value": item,
                    "evidence_quote": item.get("evidence") or item.get("summary") or "",
                    "confidence": float(item.get("confidence") or 1.0),
                    "status": status
                })

        # 2. characters
        characters = update.get("characters") or {}
        if isinstance(characters, dict):
            for char_name, val in characters.items():
                candidates.append({
                    "entity_type": "character",
                    "entity_id": char_name,
                    "change_type": "update",
                    "old_value": None,
                    "new_value": val,
                    "evidence_quote": val.get("evidence") or "",
                    "confidence": float(val.get("confidence") or 1.0),
                    "status": status
                })

        # 3. objects
        for item in update.get("objects", []):
            if isinstance(item, dict) and (item.get("id") or item.get("name")):
                eid = item.get("id") or item.get("name")
                candidates.append({
                    "entity_type": "object",
                    "entity_id": eid,
                    "change_type": "update",
                    "old_value": None,
                    "new_value": item,
                    "evidence_quote": item.get("evidence") or "",
                    "confidence": float(item.get("confidence") or 1.0),
                    "status": status
                })

        # 4. threads
        for item in update.get("threads", []):
            if isinstance(item, dict) and item.get("id"):
                candidates.append({
                    "entity_type": "thread",
                    "entity_id": item["id"],
                    "change_type": "update",
                    "old_value": None,
                    "new_value": item,
                    "evidence_quote": item.get("evidence") or "",
                    "confidence": float(item.get("confidence") or 1.0),
                    "status": status
                })

        # 5. foreshadows, hooks, reader_promises, secrets
        for etype in ("foreshadow", "hook", "reader_promise", "secret"):
            plural = etype + "s"
            for item in update.get(plural, []):
                if isinstance(item, dict) and item.get("id"):
                    candidates.append({
                        "entity_type": etype,
                        "entity_id": item["id"],
                        "change_type": "update",
                        "old_value": None,
                        "new_value": item,
                        "evidence_quote": item.get("evidence") or item.get("description") or "",
                        "confidence": float(item.get("confidence") or 1.0),
                        "status": status
                    })

        # 6. character_relations
        for item in update.get("character_relations", []):
            if isinstance(item, dict):
                source = item.get("source_char") or item.get("source")
                target = item.get("target_char") or item.get("target")
                if source and target:
                    candidates.append({
                        "entity_type": "character_relation",
                        "entity_id": f"{source}->{target}",
                        "change_type": "update",
                        "old_value": None,
                        "new_value": item,
                        "evidence_quote": item.get("evidence") or item.get("description") or "",
                        "confidence": float(item.get("confidence") or 1.0),
                        "status": status
                    })

        # 7. timeline_nodes & timeline_edges
        for item in update.get("timeline_nodes", []):
            if isinstance(item, dict) and item.get("id"):
                candidates.append({
                    "entity_type": "timeline_node",
                    "entity_id": item["id"],
                    "change_type": "update",
                    "old_value": None,
                    "new_value": item,
                    "evidence_quote": item.get("evidence") or item.get("description") or "",
                    "confidence": float(item.get("confidence") or 1.0),
                    "status": status
                })
        for item in update.get("timeline_edges", []):
            if isinstance(item, dict) and item.get("id"):
                candidates.append({
                    "entity_type": "timeline_edge",
                    "entity_id": item["id"],
                    "change_type": "update",
                    "old_value": None,
                    "new_value": item,
                    "evidence_quote": item.get("evidence") or item.get("description") or "",
                    "confidence": float(item.get("confidence") or 1.0),
                    "status": status
                })

        return candidates

    def apply_update(
        self,
        chapter_id: str,
        update: Dict[str, Any],
        interactive: bool = False,
        auto_accept: bool = True,
    ) -> None:
        self.store.create_snapshot(chapter_id)

        hold_for_review = interactive and not auto_accept
        status = "pending" if hold_for_review else "accepted"
        candidates = self._build_candidates(chapter_id, update, status)
        self.store.save_state_change_candidates(chapter_id, candidates)

        if not hold_for_review:
            safe_update = self._validated_update(chapter_id, update)
            self.store.sync_state_update(chapter_id, safe_update)
            self._apply_yaml_compat_update(safe_update)

        self._merge_character_memories(update.get("character_memories", []))

    async def aapply_update(
        self,
        chapter_id: str,
        update: Dict[str, Any],
        interactive: bool = False,
        auto_accept: bool = True,
    ) -> None:
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.store.create_snapshot, chapter_id)

        hold_for_review = interactive and not auto_accept
        status = "pending" if hold_for_review else "accepted"
        candidates = self._build_candidates(chapter_id, update, status)

        db_res = self.store.save_state_change_candidates(chapter_id, candidates)
        if asyncio.isfuture(db_res) or asyncio.iscoroutine(db_res):
            await db_res

        if not hold_for_review:
            safe_update = self._validated_update(chapter_id, update)
            db_res2 = self.store.sync_state_update(chapter_id, safe_update)
            if asyncio.isfuture(db_res2) or asyncio.iscoroutine(db_res2):
                await db_res2

            await loop.run_in_executor(None, self._apply_yaml_compat_update, safe_update)

        await loop.run_in_executor(None, self._merge_character_memories, update.get("character_memories", []))

    def _validated_update(self, chapter_id: str, update: Dict[str, Any]) -> Dict[str, Any]:
        return validate_state_update(
            chapter_id,
            update,
            db_path=self.store.db_path,
        )

    def get_state(self) -> Dict[str, Any]:
        return self.store.get_continuity_state()

    async def aget_state(self) -> Dict[str, Any]:
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.store.get_continuity_state)

    def _apply_yaml_compat_update(self, update: Dict[str, Any]) -> None:
        """Keep legacy YAML state files in sync for existing projects and tools."""
        state_dir = self.root_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        self._merge_yaml_list(state_dir / "events.yaml", "events", update.get("events", []))
        self._merge_yaml_list(state_dir / "objects.yaml", "objects", update.get("objects", []))
        self._merge_yaml_list(state_dir / "foreshadows.yaml", "foreshadows", update.get("foreshadows", []))
        self._merge_yaml_list(state_dir / "hooks.yaml", "hooks", update.get("hooks", []))

    def _merge_yaml_list(self, path: Path, key: str, items: Any) -> None:
        if not items:
            return
        current = {}
        if path.exists():
            current = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        existing_items = current.get(key, [])
        if not isinstance(existing_items, list):
            existing_items = []
        by_id = {
            item.get("id"): item
            for item in existing_items
            if isinstance(item, dict) and item.get("id")
        }
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                by_id[item["id"]] = {**by_id.get(item["id"], {}), **item}
            else:
                existing_items.append(item)
        merged_without_id = [
            item
            for item in existing_items
            if not (isinstance(item, dict) and item.get("id"))
        ]
        current[key] = merged_without_id + list(by_id.values())
        _safe_write_yaml(path, current)

    def _load_initial_character_info(self, char_name: str) -> Dict[str, Any]:
        cards_path = self.root_dir / "assets" / "character_cards.yaml"
        if not cards_path.exists():
            return {"core_traits": [], "speech_patterns": []}
        try:
            cards = yaml.safe_load(cards_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {"core_traits": [], "speech_patterns": []}
        for char in cards.get("characters", []):
            if not isinstance(char, dict):
                continue
            if char.get("name") == char_name or char.get("id") == char_name:
                return {
                    "core_traits": char.get("personality_constraints", []),
                    "speech_patterns": char.get("speech_style", []),
                }
        return {"core_traits": [], "speech_patterns": []}

    def _merge_character_memories(self, memories: list) -> None:
        if not memories:
            return
        memories_path = self.root_dir / "assets" / "character_memories.yaml"
        current = {}
        if memories_path.exists():
            try:
                current = yaml.safe_load(memories_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                current = {}
        chars_mem = current.setdefault("characters", {})
        for item in memories:
            if not isinstance(item, dict) or not item.get("character"):
                continue
            name = item["character"]
            if name not in chars_mem:
                chars_mem[name] = self._load_initial_character_info(name)
            char_data = chars_mem[name]
            char_mem_list = char_data.setdefault("memories", [])
            if not any(m.get("summary") == item.get("summary") for m in char_mem_list if isinstance(m, dict)):
                char_mem_list.append({
                    "summary": item.get("summary", ""),
                    "emotional_impact": item.get("emotional_impact", "")
                })
        _safe_write_yaml(memories_path, current)
