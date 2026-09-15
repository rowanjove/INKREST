"""Adaptive Preference Learning for Human Writing Engine (PRD §28.4, §59)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from novel_agent.human_writing.schemas import HWEIssue, HWERule

if TYPE_CHECKING:
    from novel_agent.state.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


class HWEPreferenceManager:
    """Manages project-level author preferences, rule suppressions, and adaptive calibrations."""

    def __init__(
        self,
        store: Optional[SQLiteStateStore] = None,
        project_id: str = "",
    ):
        self.store = store
        self.project_id = project_id
        # In-memory fallback if store is not attached
        self._memory_suppressed: Set[str] = set()
        self._memory_weights: Dict[str, float] = {}
        self._memory_fp_counts: Dict[str, int] = {}

    def suppress_rule(self, rule_id: str, reason: str = "") -> None:
        """Suppress a rule so it is ignored in scanning and compiler prompt injection."""
        self._memory_suppressed.add(rule_id)
        if self.store:
            try:
                self.store.save_hwe_preference(
                    preference_key="suppressed_rules",
                    value={"suppressed": True, "reason": reason},
                    rule_id=rule_id,
                    project_id=self.project_id,
                )
            except Exception as ex:
                logger.error("Failed to persist rule suppression for %s: %s", rule_id, ex)

    def unsuppress_rule(self, rule_id: str) -> None:
        """Un-suppress a previously suppressed rule."""
        self._memory_suppressed.discard(rule_id)
        if self.store:
            try:
                self.store.save_hwe_preference(
                    preference_key="suppressed_rules",
                    value={"suppressed": False, "reason": ""},
                    rule_id=rule_id,
                    project_id=self.project_id,
                )
            except Exception as ex:
                logger.error("Failed to unsuppress rule %s: %s", rule_id, ex)

    def adjust_rule_weight(self, rule_id: str, weight: float, reason: str = "") -> None:
        """Adjust a rule's weight multiplier (e.g. 0.5 to soften, 1.5 to amplify)."""
        self._memory_weights[rule_id] = float(weight)
        if self.store:
            try:
                self.store.save_hwe_preference(
                    preference_key="rule_weights",
                    value={"weight": float(weight), "reason": reason},
                    rule_id=rule_id,
                    project_id=self.project_id,
                )
            except Exception as ex:
                logger.error("Failed to persist rule weight for %s: %s", rule_id, ex)

    def record_issue_feedback(
        self,
        issue_id: str,
        action: str,
        rule_id: str = "",
        note: str = "",
    ) -> None:
        """Record user feedback on an issue (e.g. 'ignore', 'false_positive', 'allow_rule').

        - If action is 'false_positive', tracks frequency and auto-softens rule weight.
        - If action is 'allow_rule', permanently suppresses rule for this project.
        """
        status_map = {
            "ignore": "ignored",
            "false_positive": "false_positive",
            "allow_rule": "ignored",
            "resolved": "resolved",
        }
        status = status_map.get(action, action)

        if self.store and issue_id:
            try:
                self.store.resolve_hwe_issue(issue_id, status=status, resolution_note=note)
            except Exception as ex:
                logger.error("Failed to resolve issue %s: %s", issue_id, ex)

        if action == "allow_rule" and rule_id:
            self.suppress_rule(rule_id, reason=note or "User explicitly allowed rule")

        elif action == "false_positive" and rule_id:
            count = self._memory_fp_counts.get(rule_id, 0) + 1
            self._memory_fp_counts[rule_id] = count
            if self.store:
                try:
                    self.store.save_hwe_preference(
                        preference_key="fp_count",
                        value={"count": count},
                        rule_id=rule_id,
                        project_id=self.project_id,
                    )
                except Exception:
                    pass

            # If marked false positive >= 3 times, automatically soft-calibrate
            if count >= 3:
                current_weight = self.get_rule_weights().get(rule_id, 1.0)
                new_weight = max(0.2, round(current_weight * 0.5, 2))
                self.adjust_rule_weight(
                    rule_id,
                    new_weight,
                    reason=f"Auto-calibrated due to {count} false-positive reports",
                )

    def get_suppressed_rules(self) -> Set[str]:
        """Get all suppressed rule IDs for this project."""
        suppressed = set(self._memory_suppressed)
        if self.store:
            try:
                rows = self.store.get_hwe_preferences(
                    project_id=self.project_id,
                    preference_key="suppressed_rules",
                )
                for r in rows:
                    rule_id = r.get("rule_id")
                    val = r.get("value", {})
                    if rule_id and isinstance(val, dict) and val.get("suppressed"):
                        suppressed.add(rule_id)
                    elif rule_id and not (isinstance(val, dict) and val.get("suppressed")):
                        suppressed.discard(rule_id)
            except Exception as ex:
                logger.error("Failed to load suppressed rules: %s", ex)
        return suppressed

    def get_rule_weights(self) -> Dict[str, float]:
        """Get all custom rule weights."""
        weights = dict(self._memory_weights)
        if self.store:
            try:
                rows = self.store.get_hwe_preferences(
                    project_id=self.project_id,
                    preference_key="rule_weights",
                )
                for r in rows:
                    rule_id = r.get("rule_id")
                    val = r.get("value", {})
                    if rule_id and isinstance(val, dict) and "weight" in val:
                        weights[rule_id] = float(val["weight"])
            except Exception as ex:
                logger.error("Failed to load rule weights: %s", ex)
        return weights

    def filter_issues(self, issues: List[HWEIssue]) -> List[HWEIssue]:
        """Filter out issues matching suppressed rules and apply weights."""
        suppressed = self.get_suppressed_rules()
        weights = self.get_rule_weights()

        filtered: List[HWEIssue] = []
        for issue in issues:
            rid = issue.hwe.rule_id
            if rid in suppressed:
                continue
            if rid in weights:
                # Modulate issue confidence by weight multiplier
                factor = weights[rid]
                issue.hwe.confidence = round(issue.hwe.confidence * factor, 4)
            filtered.append(issue)
        return filtered

    def filter_rules_for_compiler(self, rules: List[HWERule]) -> List[HWERule]:
        """Filter out suppressed rules before compiler prompt generation."""
        suppressed = self.get_suppressed_rules()
        return [r for r in rules if r.id not in suppressed]

    def export_profile(self) -> Dict[str, Any]:
        """Export current preference profile as JSON-serializable dictionary."""
        return {
            "project_id": self.project_id,
            "suppressed_rules": list(self.get_suppressed_rules()),
            "rule_weights": self.get_rule_weights(),
        }

    def import_profile(self, profile: Dict[str, Any]) -> None:
        """Import preference profile."""
        suppressed = profile.get("suppressed_rules", [])
        for r in suppressed:
            self.suppress_rule(r, reason="Imported preference profile")

        weights = profile.get("rule_weights", {})
        for r, w in weights.items():
            self.adjust_rule_weight(r, float(w), reason="Imported preference profile")
