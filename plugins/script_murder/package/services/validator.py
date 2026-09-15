"""Deterministic local validator for Script Murder projects (Pure Python, 0 LLM Tokens)."""

from __future__ import annotations

import re
from typing import Dict, List, Set

from ..schemas import (
    ScriptMurderWorkspace,
    ValidationIssue,
    ValidationReport,
)


class DeterministicValidator:
    """Performs deterministic graph, timeline, referential, and leakage audits."""

    def __init__(self, workspace: ScriptMurderWorkspace):
        self.ws = workspace

    def validate_all(self) -> ValidationReport:
        issues: List[ValidationIssue] = []

        # Run independent checks
        issues.extend(self.check_canon_completeness())
        issues.extend(self.check_referential_integrity())
        issues.extend(self.check_timeline_and_alibi())
        issues.extend(self.check_clue_graph_closure())
        issues.extend(self.check_visibility_and_leakage())

        # Compile metrics
        blockers = sum(1 for i in issues if i.severity == "BLOCKER")
        errors = sum(1 for i in issues if i.severity == "ERROR")
        warnings = sum(1 for i in issues if i.severity == "WARNING")

        # Metric calculations
        total_mandatory_conclusions = sum(1 for c in self.ws.conclusions if c.is_mandatory)
        covered_conclusions = 0
        if total_mandatory_conclusions > 0:
            existing_clue_ids = {c.id for c in self.ws.clues}
            for concl in self.ws.conclusions:
                if not concl.is_mandatory:
                    continue
                valid_support = [cid for cid in concl.supported_by_clues if cid in existing_clue_ids]
                if valid_support:
                    covered_conclusions += 1
            closure_rate = round(covered_conclusions / total_mandatory_conclusions, 2)
        else:
            closure_rate = 1.0

        orphan_count = sum(1 for i in issues if i.code == "ORPHAN_CLUE")
        temporal_count = sum(1 for i in issues if i.code.startswith("TIMELINE_"))
        leak_count = sum(1 for i in issues if i.code == "VISIBILITY_LEAK")

        return ValidationReport(
            is_valid=(blockers == 0 and errors == 0),
            blocker_count=blockers,
            error_count=errors,
            warning_count=warnings,
            issues=issues,
            metrics={
                "evidence_chain_closure_rate": closure_rate,
                "orphan_clues_count": orphan_count,
                "temporal_conflicts_count": temporal_count,
                "visibility_leak_count": leak_count,
            },
        )

    def check_canon_completeness(self) -> List[ValidationIssue]:
        """Check fields that are required before an auditable case can exist."""
        issues: List[ValidationIssue] = []
        required = {
            "victim": self.ws.canon.victim,
            "killer": self.ws.canon.killer,
            "cause_of_death": self.ws.canon.cause_of_death,
            "crime_scene": self.ws.canon.crime_scene,
            "crime_method": self.ws.canon.crime_method,
            "true_motive": self.ws.canon.true_motive,
        }
        for field_name, value in required.items():
            if not str(value or "").strip():
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        code=f"MISSING_CANON_{field_name.upper()}",
                        message=f"Truth Canon 缺少必填字段：{field_name}",
                        target_id="canon",
                        fix_suggestion=f"在真相板补充 {field_name}",
                    )
                )
        if not self.ws.canon.facts:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    code="MISSING_CANON_FACTS",
                    message="Truth Canon 尚未建立任何原子事实",
                    target_id="canon",
                    fix_suggestion="至少建立一条可引用的 TruthFact",
                )
            )
        return issues

    # -----------------------------------------------------------------------
    # 1. Referential Integrity
    # -----------------------------------------------------------------------
    def check_referential_integrity(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        fact_ids: Set[str] = {f.id for f in self.ws.canon.facts}
        char_ids: Set[str] = {c.id for c in self.ws.characters}
        clue_ids: Set[str] = {c.id for c in self.ws.clues}
        concl_ids: Set[str] = {c.id for c in self.ws.conclusions}

        for label, values in (
            ("Fact", [f.id for f in self.ws.canon.facts]),
            ("Character", [c.id for c in self.ws.characters]),
            ("Clue", [c.id for c in self.ws.clues]),
            ("Conclusion", [c.id for c in self.ws.conclusions]),
        ):
            seen: Set[str] = set()
            for entity_id in values:
                if entity_id in seen:
                    issues.append(
                        ValidationIssue(
                            severity="BLOCKER",
                            code="DUPLICATE_ID",
                            message=f"{label} ID 重复：'{entity_id}'",
                            target_id=entity_id,
                            fix_suggestion="为实体分配稳定且唯一的 ID",
                        )
                    )
                seen.add(entity_id)

        # Check killer definition
        if not self.ws.canon.killer:
            issues.append(
                ValidationIssue(
                    severity="BLOCKER",
                    code="MISSING_KILLER",
                    message="真相板 (Canon) 尚未设定真凶角色",
                    target_id="canon",
                    fix_suggestion="在真相板指定受指控的真凶角色 ID",
                )
            )
        elif self.ws.canon.killer not in char_ids:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="INVALID_KILLER_REF",
                    message=f"设定真凶 '{self.ws.canon.killer}' 不存在于角色列表中",
                    target_id=self.ws.canon.killer,
                    fix_suggestion="修正真凶角色 ID 或补充该角色卡",
                )
            )

        # Check player count match
        if len(self.ws.characters) != self.ws.meta.player_count:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    code="PLAYER_COUNT_MISMATCH",
                    message=(
                        f"企划设定玩家数 ({self.ws.meta.player_count}人) "
                        f"与实际角色数 ({len(self.ws.characters)}人) 不一致"
                    ),
                    target_id="meta",
                    fix_suggestion="调整企划人数或增删角色以保持一致",
                )
            )

        # Check clue references
        for clue in self.ws.clues:
            for fid in clue.fact_refs:
                if fid not in fact_ids:
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            code="DANGLING_FACT_REF",
                            message=f"线索 '{clue.title}' ({clue.id}) 引用了不存在的 Fact: '{fid}'",
                            target_id=clue.id,
                            fix_suggestion=f"在真相板补充 ID 为 '{fid}' 的事实或移除该引用",
                        )
                    )
            for cid in clue.supports_conclusions:
                if cid not in concl_ids:
                    issues.append(
                        ValidationIssue(
                            severity="WARNING",
                            code="DANGLING_CONCLUSION_REF",
                            message=f"线索 '{clue.title}' ({clue.id}) 指向了不存在的结论: '{cid}'",
                            target_id=clue.id,
                            fix_suggestion=f"检查结论列表是否遗漏 '{cid}'",
                        )
                    )
            for did in clue.debunk_clue_refs:
                if did not in clue_ids:
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            code="DANGLING_DEBUNK_REF",
                            message=f"误导线索 '{clue.title}' ({clue.id}) 澄清引用了不存在的线索: '{did}'",
                            target_id=clue.id,
                            fix_suggestion=f"补充澄清线索 '{did}' 或修正 ID",
                        )
                    )

            if clue.required and not clue.fact_refs and not clue.supports_conclusions:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        code="REQUIRED_CLUE_UNGROUNDED",
                        message=f"必需线索 '{clue.title}' ({clue.id}) 没有 Fact 或结论依据",
                        target_id=clue.id,
                        fix_suggestion="补充 fact_refs/supports_conclusions，或取消 required",
                    )
                )

        # Check character knowledge references
        for char in self.ws.characters:
            for km in char.knowledge_map:
                if km.fact_id not in fact_ids:
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            code="DANGLING_CHAR_KNOWLEDGE",
                            message=f"角色 '{char.name}' 的认知表引用了不存在的 Fact: '{km.fact_id}'",
                            target_id=char.id,
                            fix_suggestion=f"修正或移除角色卡中对 '{km.fact_id}' 的认知项",
                        )
                    )

        # Conclusion references must resolve both ways.
        for conclusion in self.ws.conclusions:
            if conclusion.proves_fact_id and conclusion.proves_fact_id not in fact_ids:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        code="DANGLING_CONCLUSION_FACT_REF",
                        message=f"结论 '{conclusion.title}' 引用了不存在的 Fact '{conclusion.proves_fact_id}'",
                        target_id=conclusion.id,
                        fix_suggestion="修正 proves_fact_id 或补充对应 Fact",
                    )
                )
            if conclusion.target_suspect_id and conclusion.target_suspect_id not in char_ids:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        code="DANGLING_CONCLUSION_CHARACTER_REF",
                        message=f"结论 '{conclusion.title}' 指向不存在的角色 '{conclusion.target_suspect_id}'",
                        target_id=conclusion.id,
                        fix_suggestion="修正 target_suspect_id 或补充对应角色",
                    )
                )

        return issues

    # -----------------------------------------------------------------------
    # 2. Timeline & Spatial Feasibility
    # -----------------------------------------------------------------------
    def check_timeline_and_alibi(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Check for multiple locations at same timestamp
        for char in self.ws.characters:
            seen_times: Dict[str, str] = {}
            for ev in char.timeline:
                t = ev.time.strip()
                if not t:
                    continue
                if t in seen_times:
                    if seen_times[t] != ev.location:
                        issues.append(
                            ValidationIssue(
                                severity="ERROR",
                                code="TIMELINE_SPATIAL_SPLIT",
                                message=(
                                    f"角色 '{char.name}' 在时间点 '{t}' 同时出现在不同地点: "
                                    f"'{seen_times[t]}' 与 '{ev.location}' (时空分裂)"
                                ),
                                target_id=char.id,
                                fix_suggestion="调整时间或合并地点事件，避免同一时间出现在两地",
                            )
                        )
                else:
                    seen_times[t] = ev.location

        # Check killer alibi feasibility in crime window
        killer_id = self.ws.canon.killer
        start_w, end_w = self.ws.canon.crime_time_window
        crime_loc = self.ws.canon.crime_scene

        if killer_id:
            killer = next((c for c in self.ws.characters if c.id == killer_id), None)
            if killer and crime_loc:
                # Does killer have physical presence near crime scene during crime window?
                # Check real activities
                has_scene_presence = False
                for ev in killer.timeline:
                    if ev.location == crime_loc:
                        has_scene_presence = True
                        break
                if not has_scene_presence and killer.timeline:
                    issues.append(
                        ValidationIssue(
                            severity="WARNING",
                            code="TIMELINE_KILLER_MISSING_SCENE",
                            message=(
                                f"真凶 '{killer.name}' 的真实时间线中未包含案发现场 "
                                f"'{crime_loc}' 的行动轨迹"
                            ),
                            target_id=killer.id,
                            fix_suggestion=f"在案发窗口 ({start_w}~{end_w}) 内为凶手增添前往现场的真实事件",
                        )
                    )

        return issues

    # -----------------------------------------------------------------------
    # 3. Clue Graph Closure & Orphan Check
    # -----------------------------------------------------------------------
    def check_clue_graph_closure(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        clue_ids = {c.id for c in self.ws.clues}

        # 1. Check orphan clues (no fact ref and no conclusion support)
        for clue in self.ws.clues:
            if not clue.fact_refs and not clue.supports_conclusions and not clue.is_red_herring:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        code="ORPHAN_CLUE",
                        message=f"线索 '{clue.title}' ({clue.id}) 为孤儿线索（无物证关联事实且未支撑任何结论）",
                        target_id=clue.id,
                        fix_suggestion="为其关联对应的 Fact 或归纳为误导项 (is_red_herring=True)",
                    )
                )

        # 2. Check conclusion support
        for concl in self.ws.conclusions:
            valid_clues = [cid for cid in concl.supported_by_clues if cid in clue_ids]
            if not valid_clues:
                issues.append(
                    ValidationIssue(
                        severity="ERROR" if concl.is_mandatory else "WARNING",
                        code="UNSUPPORTED_CONCLUSION",
                        message=f"核心结论 '{concl.title}' ({concl.id}) 缺少任何有效的支撑线索",
                        target_id=concl.id,
                        fix_suggestion="在 supported_by_clues 中添加能够推导出此结论的线索 ID",
                    )
                )

        # Clues must be reachable in the declared game flow when a flow exists.
        round_ids = {r.round_index for r in self.ws.flow.rounds}
        if round_ids:
            for clue in self.ws.clues:
                if clue.round not in round_ids:
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            code="CLUE_ROUND_NOT_IN_FLOW",
                            message=f"线索 '{clue.title}' 声明在第 {clue.round} 轮，但流程未定义该轮",
                            target_id=clue.id,
                            fix_suggestion="调整线索轮次或补充对应 GameRound",
                        )
                    )
            flow_clues = {cid for r in self.ws.flow.rounds for cid in r.search_clue_ids}
            for clue in self.ws.clues:
                if clue.required and clue.id not in flow_clues:
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            code="REQUIRED_CLUE_NOT_UNLOCKED",
                            message=f"必需线索 '{clue.title}' 未被任何流程轮次解锁",
                            target_id=clue.id,
                            fix_suggestion="在对应 GameRound.search_clue_ids 中加入该线索",
                        )
                    )

        return issues

    # -----------------------------------------------------------------------
    # 4. Visibility & Static Leakage Audit
    # -----------------------------------------------------------------------
    def check_visibility_and_leakage(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Find core secrets that non-killer characters must not know
        # e.g. Method, precise motive, or facts with is_core_truth=True not in their knowledge
        core_facts = [f for f in self.ws.canon.facts if f.is_core_truth]
        killer_id = self.ws.canon.killer

        for char in self.ws.characters:
            if char.id == killer_id:
                continue  # Killer naturally has broader awareness

            char_known_facts = {km.fact_id for km in char.knowledge_map}
            unknown_core_facts = [f for f in core_facts if f.id not in char_known_facts]

            # Scan character script text
            script_full = " ".join(char.script_acts.values())
            if not script_full:
                continue

            for fact in unknown_core_facts:
                # Extract salient keywords from fact content (simple significant word check)
                words = re.findall(r"[\u4e00-\u9fa5]{3,8}", fact.content)
                leaked_words = [w for w in words if w in script_full and w not in char.public_identity]
                if len(leaked_words) >= 2:
                    issues.append(
                        ValidationIssue(
                            severity="BLOCKER",
                            code="VISIBILITY_LEAK",
                            message=(
                                f"角色 '{char.name}' 的玩家剧本疑似泄露了其未知的核心真相 "
                                f"'{fact.title}' (匹配涉密特征: {', '.join(leaked_words[:3])})"
                            ),
                            target_id=char.id,
                            fix_suggestion=f"重构角色剧本，删除属于未知事实 '{fact.id}' 的特征词汇",
                        )
                    )

        return issues
