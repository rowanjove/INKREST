"""Canon and structured entity management service for Script Murder."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from ..schemas import (
    CharacterProfile,
    ClueItem,
    DeductiveConclusion,
    GameFlow,
    GameRound,
    ScriptMurderWorkspace,
    TruthCanon,
    TruthFact,
)
from .project_service import ProjectService


class CanonService:
    def __init__(self, project_service: ProjectService):
        self.project_svc = project_service

    def _get_ws(self, project_id: str) -> ScriptMurderWorkspace:
        ws = self.project_svc.get_workspace(project_id)
        if not ws:
            raise ValueError(f"Project '{project_id}' not found")
        return ws

    def calculate_dependency_hash(self, workspace: ScriptMurderWorkspace) -> str:
        """Calculate state fingerprint for stale detection across downstream manuscripts."""
        payload = {
            "canon": workspace.canon.model_dump(),
            "characters_knowledge": [
                {"id": c.id, "km": [k.model_dump() for k in c.knowledge_map]}
                for c in sorted(workspace.characters, key=lambda item: item.id)
            ],
            "clues": [c.model_dump() for c in sorted(workspace.clues, key=lambda item: item.id)],
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def _commit(
        self,
        ws: ScriptMurderWorkspace,
        changed: str,
        stale: List[str],
    ) -> None:
        """Advance the aggregate revision and invalidate dependent artifacts."""
        ws.revision += 1
        ws.revisions[changed] = int(ws.revisions.get(changed, 0)) + 1
        if changed in ws.artifact_status:
            ws.artifact_status[changed] = "current"
        for key in stale:
            ws.artifact_status[key] = "stale"
        ws.dependency_hashes[changed] = self.calculate_dependency_hash(ws)
        self.project_svc.save_workspace(ws)

    # -----------------------------------------------------------------------
    # Canon & Facts
    # -----------------------------------------------------------------------
    def update_canon(self, project_id: str, canon_data: Dict[str, Any]) -> TruthCanon:
        ws = self._get_ws(project_id)
        if "facts" in canon_data:
            facts = [TruthFact.model_validate(f) for f in (canon_data.get("facts") or [])]
        else:
            facts = ws.canon.facts

        ws.canon.victim = str(canon_data.get("victim") or ws.canon.victim)
        ws.canon.killer = str(canon_data.get("killer") or ws.canon.killer)
        ws.canon.cause_of_death = str(canon_data.get("cause_of_death") or ws.canon.cause_of_death)
        if "crime_time_window" in canon_data:
            ws.canon.crime_time_window = tuple(canon_data["crime_time_window"])
        ws.canon.crime_scene = str(canon_data.get("crime_scene") or ws.canon.crime_scene)
        ws.canon.crime_method = str(canon_data.get("crime_method") or ws.canon.crime_method)
        ws.canon.true_motive = str(canon_data.get("true_motive") or ws.canon.true_motive)
        ws.canon.facts = facts
        ws.canon.revision += 1

        self._commit(
            ws,
            "canon",
            ["characters", "clues", "flow", "scripts", "host_guide", "audit", "playtest", "export"],
        )
        return ws.canon

    def replace_characters(self, project_id: str, characters: List[CharacterProfile]) -> List[CharacterProfile]:
        ws = self._get_ws(project_id)
        ws.characters = list(characters)
        self._commit(ws, "characters", ["clues", "flow", "scripts", "host_guide", "audit", "playtest", "export"])
        return ws.characters

    def replace_clues(
        self,
        project_id: str,
        clues: List[ClueItem],
        conclusions: Optional[List[DeductiveConclusion]] = None,
    ) -> List[ClueItem]:
        ws = self._get_ws(project_id)
        ws.clues = list(clues)
        if conclusions is not None:
            ws.conclusions = list(conclusions)
        self._commit(ws, "clues", ["flow", "scripts", "host_guide", "audit", "playtest", "export"])
        return ws.clues

    def add_fact(self, project_id: str, fact: TruthFact) -> TruthFact:
        ws = self._get_ws(project_id)
        # Remove existing fact with same ID if any
        ws.canon.facts = [f for f in ws.canon.facts if f.id != fact.id]
        ws.canon.facts.append(fact)
        ws.canon.revision += 1
        self._commit(
            ws,
            "canon",
            ["characters", "clues", "flow", "scripts", "host_guide", "audit", "playtest", "export"],
        )
        return fact

    # -----------------------------------------------------------------------
    # Characters
    # -----------------------------------------------------------------------
    def upsert_character(self, project_id: str, char: CharacterProfile) -> CharacterProfile:
        ws = self._get_ws(project_id)
        ws.characters = [c for c in ws.characters if c.id != char.id]
        ws.characters.append(char)
        self._commit(ws, "characters", ["clues", "flow", "scripts", "host_guide", "audit", "playtest", "export"])
        return char

    def delete_character(self, project_id: str, char_id: str) -> bool:
        ws = self._get_ws(project_id)
        original_len = len(ws.characters)
        ws.characters = [c for c in ws.characters if c.id != char_id]
        if len(ws.characters) < original_len:
            self._commit(ws, "characters", ["clues", "flow", "scripts", "host_guide", "audit", "playtest", "export"])
            return True
        return False

    # -----------------------------------------------------------------------
    # Clues
    # -----------------------------------------------------------------------
    def upsert_clue(self, project_id: str, clue: ClueItem) -> ClueItem:
        ws = self._get_ws(project_id)
        ws.clues = [c for c in ws.clues if c.id != clue.id]
        ws.clues.append(clue)
        self._commit(ws, "clues", ["flow", "scripts", "host_guide", "audit", "playtest", "export"])
        return clue

    def delete_clue(self, project_id: str, clue_id: str) -> bool:
        ws = self._get_ws(project_id)
        original_len = len(ws.clues)
        ws.clues = [c for c in ws.clues if c.id != clue_id]
        if len(ws.clues) < original_len:
            self._commit(ws, "clues", ["flow", "scripts", "host_guide", "audit", "playtest", "export"])
            return True
        return False

    # -----------------------------------------------------------------------
    # Conclusions
    # -----------------------------------------------------------------------
    def upsert_conclusion(self, project_id: str, conclusion: DeductiveConclusion) -> DeductiveConclusion:
        ws = self._get_ws(project_id)
        ws.conclusions = [c for c in ws.conclusions if c.id != conclusion.id]
        ws.conclusions.append(conclusion)
        self._commit(ws, "clues", ["scripts", "host_guide", "audit", "playtest", "export"])
        return conclusion

    # -----------------------------------------------------------------------
    # Flow
    # -----------------------------------------------------------------------
    def update_flow(self, project_id: str, flow_data: Dict[str, Any]) -> GameFlow:
        ws = self._get_ws(project_id)
        rounds_raw = flow_data["rounds"] if "rounds" in flow_data else [r.model_dump() for r in ws.flow.rounds]
        ws.flow = GameFlow(
            prologue=str(flow_data.get("prologue") or ws.flow.prologue),
            rounds=[GameRound.model_validate(r) for r in rounds_raw],
            epilogue_killer=str(flow_data.get("epilogue_killer") or ws.flow.epilogue_killer),
            epilogue_escape=str(flow_data.get("epilogue_escape") or ws.flow.epilogue_escape),
        )
        self._commit(ws, "flow", ["scripts", "host_guide", "audit", "playtest", "export"])
        return ws.flow
