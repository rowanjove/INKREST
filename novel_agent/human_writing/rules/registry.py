"""Rule registry for Human Writing Engine (HWE)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, List, Optional

from novel_agent.human_writing.rules.loader import compute_ruleset_hash, load_rules_from_dir
from novel_agent.human_writing.schemas import HWERule


class RuleRegistry:
    """Registry maintaining in-memory HWE rules and applying overrides."""

    def __init__(self, rules_dir: Optional[Path] = None):
        self._rules_dir = rules_dir
        self._rules: Dict[str, HWERule] = {}
        self._ruleset_hash: str = "init"
        self._lock = threading.RLock()
        self.reload()

    def reload(self) -> None:
        """Reload all rules from disk."""
        with self._lock:
            rule_list = load_rules_from_dir(self._rules_dir)
            self._rules = {r.id: r for r in rule_list}
            self._ruleset_hash = compute_ruleset_hash(rule_list)

    @property
    def ruleset_version(self) -> str:
        return self._ruleset_hash

    def get_rule(self, rule_id: str) -> Optional[HWERule]:
        return self._rules.get(rule_id)

    def list_rules(
        self,
        family: Optional[str] = None,
        detector_type: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[HWERule]:
        with self._lock:
            result = list(self._rules.values())
        if enabled_only:
            result = [r for r in result if r.enabled]
        if family:
            result = [r for r in result if r.family == family]
        if detector_type:
            result = [r for r in result if r.detector_type == detector_type]
        return sorted(result, key=lambda r: r.id)

    def count(self) -> int:
        return len(self._rules)


_global_registry: Optional[RuleRegistry] = None
_global_registry_lock = threading.Lock()


def get_rule_registry(rules_dir: Optional[Path] = None) -> RuleRegistry:
    """Obtain or initialize the singleton RuleRegistry."""
    global _global_registry
    if _global_registry is None:
        with _global_registry_lock:
            if _global_registry is None:
                _global_registry = RuleRegistry(rules_dir)
    return _global_registry
