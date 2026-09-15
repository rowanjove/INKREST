from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from novel_agent.domain.blueprint.blueprint import StoryBlueprint
from novel_agent.domain.blueprint.recipe import TropeRecipe
from novel_agent.domain.blueprint.trope import TropeAtom
from novel_agent.services.blueprint.compiler import BlueprintCompiler
from novel_agent.services.blueprint.compliance import BlueprintComplianceChecker, ComplianceReport
from novel_agent.services.blueprint.preset_adapter import PresetAdapter
from novel_agent.services.blueprint.recommendation import RecommendationItem, TropeRecommender
from novel_agent.services.blueprint.validator import BlueprintValidator, ValidationReport

logger = logging.getLogger(__name__)


class BlueprintService:
    """Manages the lifecycle of Atoms, Recipes, Blueprint compilation and persistence."""

    def __init__(self, projects_root: Optional[Path] = None, presets_root: Optional[Path] = None):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        self.projects_root = projects_root or (repo_root / "projects")
        self.preset_adapter = PresetAdapter(presets_root=presets_root)
        self._validator: Optional[BlueprintValidator] = None
        self._compiler: Optional[BlueprintCompiler] = None
        self._recommender: Optional[TropeRecommender] = None

    def _ensure_engines(self):
        if self._validator is None or self._compiler is None or self._recommender is None:
            atoms = self.preset_adapter.load_atoms()
            recipes = self.preset_adapter.load_recipes()
            self._validator = BlueprintValidator(all_atoms=atoms)
            self._compiler = BlueprintCompiler(all_atoms=atoms, all_recipes=recipes)
            self._recommender = TropeRecommender(all_atoms=atoms)

    def get_components(self) -> dict[str, list[dict[str, Any]]]:
        """Returns atoms grouped by channel, genre, mechanism, cool_point."""
        atoms = self.preset_adapter.load_atoms()
        grouped: dict[str, list[dict[str, Any]]] = {
            "channels": [],
            "genres": [],
            "mechanisms": [],
            "cool_points": [],
        }

        for atom in atoms:
            atom_dict = atom.model_dump()
            if atom.type == "channel":
                grouped["channels"].append(atom_dict)
            elif atom.type == "genre":
                grouped["genres"].append(atom_dict)
            elif atom.type == "mechanism":
                grouped["mechanisms"].append(atom_dict)
            elif atom.type == "cool_point":
                grouped["cool_points"].append(atom_dict)

        return grouped

    def get_recipes(self) -> list[dict[str, Any]]:
        """Returns all pre-configured recipes."""
        recipes = self.preset_adapter.load_recipes()
        return [r.model_dump() for r in recipes]

    def validate_atoms(self, selected_atom_ids: list[str]) -> ValidationReport:
        """Validates selected atoms and detects soft/hard conflicts."""
        self._ensure_engines()
        assert self._validator is not None
        return self._validator.validate_atom_selection(selected_atom_ids)

    def compile(
        self,
        selected_atom_ids: list[str],
        recipe_id: Optional[str] = None,
        user_inputs: Optional[dict[str, Any]] = None,
        project_id: str = "",
    ) -> StoryBlueprint:
        """Compiles intent and atoms into an executable StoryBlueprint."""
        self._ensure_engines()
        assert self._compiler is not None
        return self._compiler.compile(
            selected_atom_ids=selected_atom_ids,
            recipe_id=recipe_id,
            user_inputs=user_inputs,
            project_id=project_id,
        )

    def _resolve_safe_project_dir(self, project_id: str) -> Optional[Path]:
        """Safely resolves project directory, preventing directory traversal attacks."""
        if not project_id or not isinstance(project_id, str):
            return None
        clean_id = project_id.strip()
        if not clean_id or "/" in clean_id or "\\" in clean_id or ".." in clean_id:
            logger.warning("Rejected invalid project_id: %r", project_id)
            return None
        resolved_dir = (self.projects_root / clean_id).resolve()
        resolved_root = self.projects_root.resolve()
        try:
            resolved_dir.relative_to(resolved_root)
        except ValueError:
            logger.warning("Path traversal escape attempt detected: %r", project_id)
            return None
        return resolved_dir

    def save_blueprint_to_project(self, project_id: str, blueprint: StoryBlueprint) -> bool:
        """Persists the blueprint into the project's directory."""
        project_dir = self._resolve_safe_project_dir(project_id)
        if project_dir is None or not project_dir.exists():
            return False

        assets_dir = project_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        blueprint_path = assets_dir / "story_blueprint.json"
        guide_path = assets_dir / "writing_guide.md"

        try:
            with open(blueprint_path, "w", encoding="utf-8") as f:
                json.dump(blueprint.model_dump(), f, ensure_ascii=False, indent=2)

            with open(guide_path, "w", encoding="utf-8") as f:
                f.write(blueprint.writing_guide_markdown)

            return True
        except Exception as e:
            logger.warning("Failed to save blueprint to %s: %s", project_id, e)
            return False

    def load_blueprint_from_project(self, project_id: str) -> Optional[StoryBlueprint]:
        """Loads a persisted blueprint if available."""
        project_dir = self._resolve_safe_project_dir(project_id)
        if project_dir is None or not project_dir.exists():
            return None

        blueprint_path = project_dir / "assets" / "story_blueprint.json"
        if not blueprint_path.exists():
            return None

        try:
            with open(blueprint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StoryBlueprint.model_validate(data)
        except Exception as e:
            logger.warning("Failed to load blueprint from %s: %s", project_id, e)
            return None

    def recommend_atoms(self, selected_atom_ids: list[str], limit: int = 6) -> list[RecommendationItem]:
        """Recommends complementary atoms based on narrative graph synergy."""
        self._ensure_engines()
        assert self._recommender is not None
        return self._recommender.recommend(selected_atom_ids, limit=limit)

    def check_compliance(
        self,
        blueprint: StoryBlueprint,
        draft_summary: str,
        current_chapter_index: int = 1,
        last_payoff_chapter: int = 1,
    ) -> ComplianceReport:
        """Audits chapter drafts or outlines against Story Blueprint constraints."""
        return BlueprintComplianceChecker.audit_draft(
            blueprint=blueprint,
            draft_summary=draft_summary,
            current_chapter_index=current_chapter_index,
            last_payoff_chapter=last_payoff_chapter,
        )

    def incubate_idea(self, idea_text: str):
        """Derives Snowflake story seeds from an idea."""
        from novel_agent.services.blueprint.incubator import InspirationIncubator
        return InspirationIncubator.incubate(idea_text)

    def mutate_atoms(self, current_atom_ids: list[str], locked_dimensions: list[str] | None = None):
        """Generates conservative, moderate, and radical mutation variants."""
        from novel_agent.services.blueprint.mutator import StoryMutator
        return StoryMutator.mutate(current_atom_ids, locked_dimensions=locked_dimensions)

    def analyze_uniqueness(self, selected_atom_ids: list[str]):
        """Evaluates market uniqueness, novelty and crowdedness."""
        from novel_agent.services.blueprint.uniqueness import NovelUniquenessEngine
        return NovelUniquenessEngine.analyze(selected_atom_ids)
