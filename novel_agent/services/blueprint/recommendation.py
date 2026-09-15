"""Narrative Recommendation Engine for Trope Atoms."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from novel_agent.domain.blueprint.trope import TropeAtom


class RecommendationItem(BaseModel):
    atom_id: str
    name: str
    type: str
    score: int  # 0 - 100
    reason: str


class TropeRecommender:
    """Calculates collaborative narrative synergy scores and recommends complementary tropes."""

    def __init__(self, all_atoms: Optional[list[TropeAtom]] = None):
        self.atoms_map = {a.id: a for a in (all_atoms or [])}

    def recommend(self, selected_atom_ids: list[str], limit: int = 6) -> list[RecommendationItem]:
        selected_set = set(selected_atom_ids)
        if not selected_set:
            # Fallback popular defaults
            defaults = ["xitong", "dalian", "chongsheng", "fuchou"]
            return [
                RecommendationItem(
                    atom_id=aid,
                    name=self.atoms_map[aid].name if aid in self.atoms_map else aid,
                    type=self.atoms_map[aid].type if aid in self.atoms_map else "mechanism",
                    score=90,
                    reason="网文起步黄金套路组合",
                )
                for aid in defaults
                if aid in self.atoms_map
            ]

        # Gather conflict sets to strictly avoid
        forbidden_set: set[str] = set()
        for aid in selected_atom_ids:
            atom = self.atoms_map.get(aid)
            if atom:
                forbidden_set.update(atom.conflicts_with)

        scores: dict[str, tuple[int, str]] = {}

        # 1. Direct synergy from recommended_with
        for aid in selected_atom_ids:
            atom = self.atoms_map.get(aid)
            if not atom:
                continue
            for target_id in atom.recommended_with:
                if target_id not in selected_set and target_id not in forbidden_set and target_id in self.atoms_map:
                    target_atom = self.atoms_map[target_id]
                    scores[target_id] = (
                        95,
                        f"与已选「{atom.name}」具有经典协同效应，强化剧情爽快感",
                    )

        # 2. Reverse synergy (where candidate recommends selected)
        for target_id, target_atom in self.atoms_map.items():
            if target_id in selected_set or target_id in forbidden_set or target_id in scores:
                continue
            intersection = set(target_atom.recommended_with).intersection(selected_set)
            if intersection:
                matched_name = self.atoms_map[list(intersection)[0]].name
                scores[target_id] = (
                    88,
                    f"与「{matched_name}」在叙事节奏上互相借力",
                )

        # 3. Categorical balance: if mechanisms exist but cool points are scarce, boost cool points
        has_cool_point = any(self.atoms_map.get(a) and self.atoms_map[a].type == "cool_point" for a in selected_atom_ids)
        if not has_cool_point:
            for target_id, target_atom in self.atoms_map.items():
                if target_atom.type == "cool_point" and target_id not in selected_set and target_id not in forbidden_set:
                    curr_score, curr_reason = scores.get(target_id, (75, "补充必要的核心情绪爽点"))
                    scores[target_id] = (max(curr_score, 85), curr_reason)

        results: list[RecommendationItem] = []
        for aid, (score, reason) in sorted(scores.items(), key=lambda x: x[1][0], reverse=True)[:limit]:
            atom = self.atoms_map[aid]
            results.append(
                RecommendationItem(
                    atom_id=aid,
                    name=atom.name,
                    type=atom.type,
                    score=score,
                    reason=reason,
                )
            )

        return results
