import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from novel_agent.prompt_registry import inspect_prompt_sources, prompt_manifest

logger = logging.getLogger(__name__)

DEFAULTS_HASH_MANIFEST = ".integrity.sha256"


class PromptRepository:
    def __init__(self, root_dir: Path, store: Optional[Any] = None):
        self.root_dir = Path(root_dir)
        self.store = store
        self._cache: Dict[str, str] = {}
        self._verify_defaults_integrity()

    def _verify_defaults_integrity(self) -> None:
        fallback_dir = Path(__file__).resolve().parent.parent / "prompts"
        defaults_dir = fallback_dir / "defaults"
        if not defaults_dir.exists():
            defaults_dir = self.root_dir / "prompts" / "defaults"
            if not defaults_dir.exists():
                return

        try:
            manifest_path = defaults_dir / DEFAULTS_HASH_MANIFEST
            if not manifest_path.is_file():
                manifest_path = fallback_dir / "defaults" / DEFAULTS_HASH_MANIFEST
            if not manifest_path.is_file():
                return
            expected_hash = manifest_path.read_text(encoding="utf-8").strip().split()[0]
            if not expected_hash:
                return

            files = sorted(defaults_dir.glob("*.md"))
            h = hashlib.sha256()
            for f in files:
                content = f.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
                h.update(content.encode("utf-8"))
            actual_hash = h.hexdigest()

            if actual_hash != expected_hash:
                logger.warning(
                    f"Default prompts integrity check failed! "
                    f"Expected hash: {expected_hash}, got: {actual_hash}. "
                    f"It seems default prompts have been modified."
                )
        except Exception as e:
            logger.warning(f"Error verifying default prompts integrity: {e}")

    def load(self, role: str) -> str:
        if role in self._cache:
            return self._cache[role]

        content = ""
        # 1. Try to load from project-specific local templates/prompts
        path = self.root_dir / "prompts" / f"{role}.md"
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        # 2. Try to load from the NOVEL_AGENT_TEMPLATES environment path
        if not content:
            env_templates = os.environ.get("NOVEL_AGENT_TEMPLATES")
            if env_templates:
                alt_path = Path(env_templates) / "prompts" / f"{role}.md"
                if alt_path.exists():
                    try:
                        content = alt_path.read_text(encoding="utf-8").strip()
                    except Exception:
                        pass

        # 3. Fallback to package-level default prompts directory
        if not content:
            try:
                fallback_dir = Path(__file__).resolve().parent.parent / "prompts"
                fallback_path = fallback_dir / f"{role}.md"
                if fallback_path.exists():
                    content = fallback_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        if content:
            self._cache[role] = content
            if getattr(self, "store", None):
                try:
                    self.store.save_prompt_version(role, content)
                except Exception as e:
                    logger.warning(f"Failed to save prompt version for {role}: {e}")
            return content

        return ""

    def clear_cache(self) -> None:
        """Clear the prompt cache. Useful when prompts are updated at runtime."""
        self._cache.clear()

    def describe(self, role: str) -> Dict[str, Any]:
        """Return source/digest metadata without loading or mutating prompt state."""

        return inspect_prompt_sources(self.root_dir, role)

    def manifest(self, roles: Optional[list[str]] = None) -> Dict[str, Any]:
        """Return a project prompt manifest for UI/diagnostic consumers."""

        return prompt_manifest(self.root_dir, roles)
