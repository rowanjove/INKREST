from typing import Any, Dict, List, Optional
from novel_agent.agents.base import PromptAgent
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger
logger = get_logger("agents.auditor")


class AuditorAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("auditor", llm)
        self.prompts = prompts

    def _build_prompt(self, chapter_text: str) -> str:
        template = self.prompts.load("auditor") if self.prompts else ""
        return (
            f"{template}\n\n"
            "请审校章节，输出 JSON，包含 risk_level、issues、state_update、narrative_hooks。\n"
            "如果发现在情节、逻辑、事实等方面存在具体问题，请在 issues 中列出。若是 text 级别的文本细节问题，必须在 issue 中提供 target_text 字段，指定正文里需要被替换修复的精准文字片段（最好是不包含引号的完整句子或词组）。\n"
            "narrative_hooks 是本章结尾留下的未完成动作、悬念、伤势或重要承诺数组。\n\n"
            + chapter_text
        ).strip()

    def _parse_and_validate_audit(
        self,
        raw: str,
        chapter_text: str,
        state: Optional[dict] = None,
        target_chars: Optional[List[int]] = None,
        sensitive_words: Optional[List[str]] = None,
        plan: Optional[dict] = None
    ) -> dict:
        try:
            result = loads_json_object(raw)
            # Normalize risk_level to standard Chinese values
            _risk_map = {
                "high": "高", "High": "高", "HIGH": "高", "高风险": "高",
                "medium": "中", "Medium": "中", "MEDIUM": "中", "中等": "中",
                "low": "低", "Low": "低", "LOW": "低",
            }
            risk = result.get("risk_level", "")
            result["risk_level"] = _risk_map.get(risk, risk)
            # Validate state_update structure
            state_update = result.get("state_update")
            if not isinstance(state_update, dict):
                logger.warning("state_update is not a dict, resetting to empty")
                result["state_update"] = {"events": [], "objects": [], "threads": [], "characters": {}}
            # Normalize narrative_hooks
            hooks = result.get("narrative_hooks", [])
            if not isinstance(hooks, list):
                hooks = []
            result["narrative_hooks"] = hooks
            
            # Normalize target_text on issues
            issues = result.get("issues", [])
            if isinstance(issues, list):
                for issue in issues:
                    if isinstance(issue, dict):
                        if "target_text" not in issue:
                            issue["target_text"] = issue.get("text", "")
            
            rule_checks = self._augment_ai_flavor(result, chapter_text)
            result["style_rule_checks"] = rule_checks

            # 运行硬规则库校验 (混合审计)
            if state is not None:
                from novel_agent.quality.hard_rules import run_hard_rule_audit
                hard_issues = run_hard_rule_audit(
                    final_text=chapter_text,
                    state=state,
                    target_chars=target_chars or [1200, 2200],
                    sensitive_words=sensitive_words or [],
                    state_update=result.get("state_update"),
                    plan=plan
                )
                
                issues = result.setdefault("issues", [])
                for hi in hard_issues:
                    # 避免重复
                    if not any(x.get("type") == hi["type"] and x.get("text") == hi["text"] for x in issues if isinstance(x, dict)):
                        issues.append(hi)
                
                # 如果包含 CRITICAL 问题，风险硬判定为高风险
                has_critical = any(hi.get("audit_class") == "CRITICAL" for hi in hard_issues)
                if has_critical:
                    result["risk_level"] = "高"

            # 归口等级划分 (CRITICAL / WARNING / INFO)
            issues = result.setdefault("issues", [])
            critical_list = []
            warning_list = []
            info_list = []
            
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                audit_class = issue.get("audit_class")
                if not audit_class:
                    # 映射 LLM issues 严重度
                    sev = issue.get("severity", "low")
                    if sev == "high":
                        audit_class = "CRITICAL"
                    elif sev == "medium":
                        audit_class = "WARNING"
                    else:
                        audit_class = "INFO"
                    issue["audit_class"] = audit_class
                    
                if audit_class == "CRITICAL":
                    critical_list.append(issue)
                elif audit_class == "WARNING":
                    warning_list.append(issue)
                else:
                    info_list.append(issue)
                    
            result["audit_classification"] = {
                "CRITICAL": critical_list,
                "WARNING": warning_list,
                "INFO": info_list
            }

            return result
        except Exception as exc:
            logger.error("Failed to parse auditor output: %s", exc)
            return {
                "risk_level": "unknown",
                "issues": [{"type": "parse_error", "severity": "low", "text": "", "why": str(exc), "fix": "重新运行审校"}],
                "state_update": {"events": [], "objects": [], "threads": [], "characters": {}},
                "narrative_hooks": [],
                "audit_classification": {"CRITICAL": [], "WARNING": [], "INFO": []}
            }

    def audit(
        self,
        chapter_text: str,
        state: Optional[dict] = None,
        target_chars: Optional[List[int]] = None,
        sensitive_words: Optional[List[str]] = None,
        plan: Optional[dict] = None
    ) -> dict:
        prompt = self._build_prompt(chapter_text)
        raw = self.run(prompt)
        return self._parse_and_validate_audit(raw, chapter_text, state, target_chars, sensitive_words, plan)

    async def aaudit(
        self,
        chapter_text: str,
        state: Optional[dict] = None,
        target_chars: Optional[List[int]] = None,
        sensitive_words: Optional[List[str]] = None,
        plan: Optional[dict] = None
    ) -> dict:
        prompt = self._build_prompt(chapter_text)
        raw = await self.arun(prompt)
        return self._parse_and_validate_audit(raw, chapter_text, state, target_chars, sensitive_words, plan)

    def _augment_ai_flavor(self, result, chapter_text: str) -> Dict[str, Any]:
        from novel_agent.quality.style_precheck import compute_style_rule_checks

        root_dir = getattr(self, "root_dir", None)
        rule_checks = compute_style_rule_checks(chapter_text, root_dir)
        local_check = rule_checks["anti_ai_flavor"]
        ai_style_check = rule_checks["style"]
        result["ai_flavor"] = {
            "risk_level": self._ai_flavor_risk(local_check),
            "emotion_telling_hits": local_check.get("emotion_telling_hits", 0),
            "abstract_modifier_hits": local_check.get("abstract_modifier_hits", 0),
            "dialogue_overcomplete_hits": local_check.get("dialogue_overcomplete_hits", 0),
            "ending_type": local_check.get("ending_type", "neutral"),
            "score": local_check.get("score", 0),
            "details": local_check.get("details", []),
            "fix_priority": ["emotion", "ending", "dialogue", "abstract", "pacing"],
        }
        
        hits = list(local_check.get("hits", [])) + list(ai_style_check.get("hits", []))
        if local_check.get("pass", True) and ai_style_check.get("pass", True) and not hits:
            return rule_checks

        issues = result.get("issues")
        if not isinstance(issues, list):
            issues = []
            
        # Create a detailed issue for each unique matching target_text segment
        for hit in sorted(list(set(hits))):
            issues.append({
                "type": "ai_flavor",
                "issue_layer": "text",
                "severity": "high" if (local_check.get("level") == "fail" or ai_style_check.get("level") == "fail") else "medium",
                "text": f"文本片段违规：{hit}",
                "target_text": hit,
                "why": "该片段存在情绪直写、抽象修饰、对话过完整或高频 AI 腔词语。",
                "fix": "改为通过客观物理动作细节描写渲染氛围和内心反应，削减汇报式长台词。"
            })
        result["issues"] = issues
        
        highest_level = "低"
        if local_check.get("level") == "fail" or ai_style_check.get("level") == "fail":
            highest_level = "高"
        elif local_check.get("level") == "review" or ai_style_check.get("level") == "review":
            highest_level = "中"
        elif local_check.get("level") == "warning" or ai_style_check.get("level") == "warning":
            highest_level = "中"
            
        current_risk = result.get("risk_level", "低")
        risk_order = {"低": 0, "中": 1, "高": 2, "unknown": 0, "pending": 0}
        if risk_order.get(highest_level, 0) > risk_order.get(current_risk, 0):
            result["risk_level"] = highest_level
        return rule_checks

    def _ai_flavor_risk(self, check) -> str:
        level = check.get("level")
        if level == "fail":
            return "高"
        if level == "review":
            return "中"
        return "低"
