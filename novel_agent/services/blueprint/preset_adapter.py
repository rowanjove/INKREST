from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from novel_agent.domain.blueprint.recipe import TropeRecipe
from novel_agent.domain.blueprint.trope import TropeAtom
from novel_agent.services.blueprint.schemas import get_trope_schema


class PresetAdapter:
    """Discovers and parses local preset assets into TropeAtom and TropeRecipe collections."""

    def __init__(self, presets_root: Optional[Path] = None):
        if presets_root is None:
            # Default to repo root presets directory
            presets_root = Path(__file__).resolve().parent.parent.parent.parent / "presets"
        self.presets_root = presets_root
        self._cached_atoms: Optional[list[TropeAtom]] = None
        self._cached_recipes: Optional[list[TropeRecipe]] = None

    def load_atoms(self, force_reload: bool = False) -> list[TropeAtom]:
        """Loads all trope atoms from channels, themes, mechanisms, and cool_points."""
        if self._cached_atoms is not None and not force_reload:
            return self._cached_atoms

        atoms: list[TropeAtom] = []
        if not self.presets_root.exists():
            self._cached_atoms = atoms
            return atoms

        type_map = {
            "channels": "channel",
            "themes": "genre",
            "mechanisms": "mechanism",
            "cool_points": "cool_point",
        }

        for folder_name, atom_type in type_map.items():
            folder_path = self.presets_root / folder_name
            if not folder_path.is_dir():
                continue

            for json_file in folder_path.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    atom_id = data.get("id") or json_file.stem
                    name = data.get("name") or data.get("label") or atom_id
                    description = data.get("description", "")
                    tags = data.get("tags", [])
                    channels = data.get("channels", ["male", "female", "general"])
                    requires = data.get("requires", [])
                    recommended_with = data.get("recommended_with", [])
                    conflicts_with = data.get("conflicts_with", [])
                    raw_schema = data.get("parameters_schema", {})
                    schema = raw_schema if isinstance(raw_schema, dict) and raw_schema else (get_trope_schema(atom_id) or {})

                    # Enrich recommended_with defaults if not specified
                    enriched_recommended = list(recommended_with) if isinstance(recommended_with, list) else []
                    if atom_id == "xitong" and not enriched_recommended:
                        enriched_recommended = ["dalian", "shengji"]
                    elif atom_id == "chongsheng" and not enriched_recommended:
                        enriched_recommended = ["fuchou", "dalian"]
                    elif atom_id == "wudiliu" and not enriched_recommended:
                        enriched_recommended = ["zhuangbi", "dalian"]

                    atoms.append(
                        TropeAtom(
                            id=atom_id,
                            name=name,
                            type=atom_type,
                            category=data.get("category", ""),
                            tags=tags if isinstance(tags, list) else [],
                            channels=channels if isinstance(channels, list) else ["general"],
                            description=description,
                            requires=requires if isinstance(requires, list) else [],
                            recommended_with=enriched_recommended,
                            conflicts_with=conflicts_with if isinstance(conflicts_with, list) else [],
                            parameters_schema=schema,
                            built_in=True,
                        )
                    )
                except Exception:
                    continue

        self._cached_atoms = atoms
        return atoms

    def load_recipes(self, force_reload: bool = False) -> list[TropeRecipe]:
        """Loads full recipes (e.g. male_xianxia_fanliu, female_xiandai_majia) from presets."""
        if self._cached_recipes is not None and not force_reload:
            return self._cached_recipes

        recipes: list[TropeRecipe] = []
        if not self.presets_root.exists():
            self._cached_recipes = recipes
            return recipes

        reserved_folders = {"channels", "themes", "mechanisms", "cool_points"}

        for sub_dir in self.presets_root.iterdir():
            if not sub_dir.is_dir() or sub_dir.name in reserved_folders:
                continue

            meta_path = sub_dir / "meta.json"
            guide_path = sub_dir / "guide.md"

            if not meta_path.exists():
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                recipe_id = meta.get("id") or sub_dir.name
                name = meta.get("name") or recipe_id
                channel = meta.get("channel", "general")
                category = meta.get("category", "")
                subcategory = meta.get("subcategory", "")
                description = meta.get("description", "")
                tags = meta.get("tags", [])

                guide_content = ""
                if guide_path.exists():
                    with open(guide_path, "r", encoding="utf-8") as gf:
                        guide_content = gf.read()

                # Infer atoms from category, subcategory and tags
                inferred_atoms = []
                if channel:
                    inferred_atoms.append(channel)
                if category:
                    inferred_atoms.append(category)

                recipes.append(
                    TropeRecipe(
                        id=recipe_id,
                        name=name,
                        channel=channel,
                        category=category,
                        subcategory=subcategory,
                        description=description,
                        tags=tags if isinstance(tags, list) else [],
                        atoms=inferred_atoms,
                        writing_guide=guide_content,
                        built_in=meta.get("built_in", True),
                    )
                )
            except Exception:
                continue

        self._cached_recipes = recipes
        return recipes
