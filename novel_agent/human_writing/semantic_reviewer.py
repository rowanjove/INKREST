"""Layer 3 Semantic Reviewer for Human Writing Engine (PRD §8.1, §39, §40)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from novel_agent.human_writing.schemas import HWEIssue, HWEIssueDetail


def should_run_semantic_review(
    template_risk: float = 0.0,
    mode: str = "normal",
    user_requested: bool = False,
    is_publish: bool = False,
    style_ran: bool = False,
) -> bool:
    """PRD §39: Trigger conditions for Layer 3 Semantic Review.

    Avoid expensive model calls on clean text. Trigger ONLY when:
    - local template risk > 35
    - OR strict mode
    - OR user requested deep review
    - OR style editor ran
    - OR chapter is being finalized for publication.
    """
    if user_requested:
        return True
    if mode == "strict":
        return True
    if template_risk > 35.0:
        return True
    if is_publish:
        return True
    if style_ran:
        return True
    return False


SEMANTIC_REVIEW_SYSTEM_PROMPT = """你是一位挑剔且经验丰富的顶级中文严肃文学与长篇网文终审编辑。
你的任务是进行 HWE Layer 3 模型语义审校，专注识别纯规则匹配无法准确捕捉的“AI 文风瑕疵与虚假深刻”：

审查重点：
1. 【作者越位解释情绪】：文本是否直接写“他意识到自己害怕了”“一种难以言喻的悲伤涌上心头”，而不是通过人物动作、选择与感官细节呈现？
2. 【上帝视角越权与限知泄露】：在限知视角中，叙述者是否违规洞悉了其他角色的隐秘心理？
3. 【社论总结腔与虚假深刻】：叙事是否突然抽离情节，替读者做人生感慨或哲学升华（如“正如世间所有的重逢……”）？
4. 【无机质装饰性修辞】：比喻是否只是为了显得文笔好而强行添加，对刻画人物和氛围没有任何实质推进？
5. 【缺乏潜台词的白开水对白】：台词是否直接把潜台词、背景说明或内心活动和盘托出？

请仅返回严格的 JSON 数组，每个元素包含：
- "type": 规则类别代码，如 "HWE.SEMANTIC.EMOTION_EXPLANATION", "HWE.SEMANTIC.POV_LEAK", "HWE.SEMANTIC.AUTHOR_EDITORIAL", "HWE.SEMANTIC.DECORATIVE_METAPHOR"
- "text": 存在问题的具体文本原文（必须完全精准摘自正文）
- "why": 详细且尖锐的审校理由，指出为什么属于 AI 腔/无机质写作
- "fix": 具体修改建议，给出更具活人感、以动作/潜台词带动的修改方向
- "line": 行号（基于正文 1-indexed）

若未发现上述明显语义问题，请直接输出空数组 []。不输出任何 Markdown 格式包裹外的说明。"""


class HWESemanticReviewer:
    """Performs Layer 3 on-demand model semantic audit for prose quality."""

    def __init__(self, llm_client: Optional[Any] = None, model_name: Optional[str] = None):
        self.llm_client = llm_client
        self.model_name = model_name or "gemini-2.5-flash"

    def review(
        self,
        text: str,
        *,
        pov: Optional[str] = None,
        characters: Optional[Sequence[str]] = None,
        template_risk: float = 0.0,
        mode: str = "normal",
        user_requested: bool = False,
        is_publish: bool = False,
    ) -> List[HWEIssue]:
        """Run Layer 3 semantic scan if gating conditions met."""
        if not should_run_semantic_review(
            template_risk=template_risk,
            mode=mode,
            user_requested=user_requested,
            is_publish=is_publish,
        ):
            return []

        if not text or not text.strip():
            return []

        # If LLM client is provided and callable, run remote model review
        if self.llm_client is not None:
            try:
                return self._call_model_review(text, pov=pov, characters=characters)
            except Exception:
                pass  # Fall back to deterministic semantic heuristic scan

        # Local semantic heuristic fallback (dry-run / offline)
        return self._run_heuristic_semantic_scan(text, pov=pov)

    def _call_model_review(
        self,
        text: str,
        pov: Optional[str] = None,
        characters: Optional[Sequence[str]] = None,
    ) -> List[HWEIssue]:
        """Execute review via LLM."""
        prompt = f"视角设定：{pov or '第三人称限知'}\n在场主要人物：{', '.join(characters or ['未指定'])}\n\n待审校正文：\n{text}"
        response_text = ""
        if hasattr(self.llm_client, "generate"):
            response_text = self.llm_client.generate(SEMANTIC_REVIEW_SYSTEM_PROMPT, prompt)
        elif hasattr(self.llm_client, "chat"):
            response_text = self.llm_client.chat(
                [{"role": "system", "content": SEMANTIC_REVIEW_SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )

        return self._parse_review_response(response_text, text)

    def _parse_review_response(self, raw_response: str, full_text: str) -> List[HWEIssue]:
        """Parse LLM JSON response into validated HWEIssue objects."""
        clean_json = raw_response.strip()
        # Strip potential markdown fences
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```[a-zA-Z]*\n", "", clean_json)
            clean_json = re.sub(r"\n```$", "", clean_json).strip()

        try:
            data = json.loads(clean_json)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        issues: List[HWEIssue] = []
        lines = full_text.splitlines()

        for item in data:
            if not isinstance(item, dict):
                continue
            matched = str(item.get("text") or "").strip()
            if not matched or matched not in full_text:
                continue

            start = full_text.find(matched)
            end = start + len(matched)
            line_idx = item.get("line") or 1
            rule_id = str(item.get("type") or "HWE.SEMANTIC.GENERIC")

            issues.append(
                HWEIssue(
                    type=rule_id,
                    issue_layer="text",
                    severity="high",
                    audit_class="WARNING",
                    text=matched,
                    why=str(item.get("why") or "模型识别到明显的语义层 AI 腔/虚假深刻。"),
                    fix=str(item.get("fix") or "通过具象动作与人物当下动机重新编写。"),
                    hwe=HWEIssueDetail(
                        rule_id=rule_id,
                        family="narration",
                        confidence=0.88,
                        start=start,
                        end=end,
                        line=line_idx,
                        paragraph=1,
                        matched_text=matched,
                        autofix="model_patch",
                        source="semantic_model",
                    ),
                )
            )

        return issues

    def _run_heuristic_semantic_scan(self, text: str, pov: Optional[str] = None) -> List[HWEIssue]:
        """Heuristic semantic detector for offline and test runs."""
        issues: List[HWEIssue] = []
        lines = text.splitlines()

        # 1. Author editorializing / meta conclusions
        editorial_patterns = [
            (
                r"(?:他意识到自己(?:其实)?(?:正在|早已)?(?:恐惧|害怕|动摇|爱上|沦陷))",
                "HWE.SEMANTIC.EMOTION_EXPLANATION",
                "作者直接下达情绪诊断书，剥夺了读者通过动作与选择自行感知的阅读乐趣。",
                "删除直白心理解释，改写为微颤的手指、视线躲闪或下意识的防卫动作。",
            ),
            (
                r"(?:在这一瞬间|殊不知)，命运的齿轮(?:已经|早已)?悄然转动",
                "HWE.SEMANTIC.AUTHOR_EDITORIAL",
                "陈腐的宿命论社论式旁白，严重破坏限知视角的代入感与现场感。",
                "直接删除该句，紧扣角色眼前的实际危机推进。",
            ),
            (
                r"(?:这不仅是一场|这从来都不是单纯的).{2,20}(?:，更是|而是)",
                "HWE.SEMANTIC.BINARY_CONTRAST_ANALYSIS",
                "社论式论述腔调，在故事关键节点强行对读者进行意义灌输。",
                "将焦点落在人物的选择代价上，避免论文式结构定性。",
            ),
        ]

        for idx, line in enumerate(lines, 1):
            for pat, rule_id, why, fix in editorial_patterns:
                m = re.search(pat, line)
                if m:
                    matched = m.group(0)
                    start = text.find(matched)
                    end = start + len(matched)
                    issues.append(
                        HWEIssue(
                            type=rule_id,
                            issue_layer="text",
                            severity="high",
                            audit_class="WARNING",
                            text=matched,
                            why=why,
                            fix=fix,
                            hwe=HWEIssueDetail(
                                rule_id=rule_id,
                                family="narration",
                                confidence=0.90,
                                start=start,
                                end=end,
                                line=idx,
                                paragraph=idx,
                                matched_text=matched,
                                autofix="model_patch",
                                source="semantic_model",
                            ),
                        )
                    )

        return issues
