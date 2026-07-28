import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

EXPECTED_DEFAULTS_HASH = "934d4a3ad20e7fb59bb3547d32b1ffd1b3ff477eef781b09c65e5767253c4a47"


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
                logger.warning("Default prompts directory 'prompts/defaults' not found. Skipping integrity check.")
                return

        try:
            files = sorted(defaults_dir.glob("*.md"))
            h = hashlib.sha256()
            for f in files:
                content = f.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
                h.update(content.encode("utf-8"))
            actual_hash = h.hexdigest()
            if actual_hash != EXPECTED_DEFAULTS_HASH:
                logger.warning(
                    f"Default prompts integrity check failed! "
                    f"Expected hash: {EXPECTED_DEFAULTS_HASH}, got: {actual_hash}. "
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


