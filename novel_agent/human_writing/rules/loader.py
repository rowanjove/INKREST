"""Rule loader for Human Writing Engine (HWE)."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from novel_agent.human_writing.schemas import HWERule

logger = logging.getLogger(__name__)

DEFAULT_RULES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "hwe" / "rules"


def compute_ruleset_hash(rules: List[HWERule]) -> str:
    """Compute deterministic SHA256 fingerprint of the current rule set."""
    h = hashlib.sha256()
    for rule in sorted(rules, key=lambda r: r.id):
        h.update(f"{rule.id}:{rule.version}:{rule.severity}:{rule.confidence}".encode("utf-8"))
        for p in rule.patterns:
            h.update(p.encode("utf-8"))
    return h.hexdigest()[:12]


def load_rules_from_dir(rules_dir: Optional[Path] = None) -> List[HWERule]:
    """Load all valid HWE rules from the given or default directory."""
    target_dir = rules_dir or DEFAULT_RULES_DIR
    if not target_dir.exists() or not target_dir.is_dir():
        logger.warning("HWE rules directory not found: %s", target_dir)
        return []

    loaded_rules: List[HWERule] = []
    seen_ids = set()

    for yaml_path in sorted(target_dir.glob("**/*.yaml")):
        if yaml_path.name.startswith((".", "_")):
            continue
        try:
            content = yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                continue
            raw_rules = data.get("rules", [])
            if not isinstance(raw_rules, list):
                continue

            for raw in raw_rules:
                if not isinstance(raw, dict):
                    continue
                try:
                    rule = HWERule.model_validate(raw)
                    if rule.id in seen_ids:
                        logger.warning("Duplicate rule ID skipped: %s in %s", rule.id, yaml_path)
                        continue
                    seen_ids.add(rule.id)
                    loaded_rules.append(rule)
                except Exception as ex:
                    logger.error("Failed to parse rule in %s: %s", yaml_path, ex)
        except Exception as ex:
            logger.error("Failed to read rules file %s: %s", yaml_path, ex)

    logger.info("Loaded %d HWE rules from %s", len(loaded_rules), target_dir)
    return loaded_rules
