"""HumanContextCompiler: compiles dynamic, budgeted writing constraints before generation (PRD §7, §41)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from novel_agent.human_writing.rules.registry import RuleRegistry, get_rule_registry
from novel_agent.human_writing.schemas import HWERule


@dataclass
class HumanPromptContext:
    """Input specification for compiling pre-generation human writing constraints."""

    role: str = "writer"
    genre: Optional[str] = None
    scene_type: Optional[str] = None
    pov: Optional[str] = None
    characters: List[str] = field(default_factory=list)
    character_voice: Dict[str, Any] = field(default_factory=dict)
    author_style_profile: Dict[str, Any] = field(default_factory=dict)
    recent_expression_memory: List[str] = field(default_factory=list)
    active_rule_packs: List[str] = field(default_factory=list)
    user_constraints: List[str] = field(default_factory=list)
    suppressed_rules: List[str] = field(default_factory=list)
    max_chars_budget: int = 1200

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HumanPromptContext:
        """Create HumanPromptContext from a generic mapping."""
        return cls(
            role=str(data.get("role", "writer")),
            genre=data.get("genre"),
            scene_type=data.get("scene_type"),
            pov=data.get("pov"),
            characters=[str(c) for c in (data.get("characters") or [])],
            character_voice=dict(data.get("character_voice") or {}),
            author_style_profile=dict(data.get("author_style_profile") or {}),
            recent_expression_memory=[str(m) for m in (data.get("recent_expression_memory") or [])],
            active_rule_packs=[str(p) for p in (data.get("active_rule_packs") or [])],
            user_constraints=[str(u) for u in (data.get("user_constraints") or [])],
            suppressed_rules=[str(s) for s in (data.get("suppressed_rules") or [])],
            max_chars_budget=int(data.get("max_chars_budget", 1200)),
        )


@dataclass
class RankedConstraint:
    """Individual constraint with priority tier (1=User to 7=Generic HWE)."""

    priority: int
    category: str
    text: str
    weight: float = 1.0


class HumanContextCompiler:
    """Compiles high-signal writing constraints dynamically into writer prompt blocks."""

    # Priority ranking tiers conforming to PRD §7.2
    PRIORITY_USER = 1
    PRIORITY_AUTHOR_STYLE = 2
    PRIORITY_CHARACTER_VOICE = 3
    PRIORITY_SCENE = 4
    PRIORITY_MEMORY = 5
    PRIORITY_GENRE = 6
    PRIORITY_GENERIC_HWE = 7

    def __init__(
        self,
        registry: Optional[RuleRegistry] = None,
        default_budget: int = 1200,
    ):
        self.registry = registry or get_rule_registry()
        self.default_budget = default_budget

    def compile(self, ctx: HumanPromptContext | Mapping[str, Any]) -> str:
        """Compile context into a formatted constraint block strictly within character budget."""
        if isinstance(ctx, Mapping):
            context = HumanPromptContext.from_dict(ctx)
        else:
            context = ctx

        budget = context.max_chars_budget or self.default_budget

        # 1. Resolve Character Voice and detect conflicts with generic rules
        voice_constraints, suppressed_rule_ids = self._resolve_character_voice(context)

        # 2. Collect constraints across all 7 priority tiers
        ranked: List[RankedConstraint] = []

        # Tier 1: User explicit constraints (highest)
        for u in context.user_constraints:
            text = str(u).strip()
            if text:
                ranked.append(
                    RankedConstraint(
                        priority=self.PRIORITY_USER,
                        category="user",
                        text=f"【用户要求】{text}",
                        weight=10.0,
                    )
                )

        # Tier 2: Author Style Bible / Profile
        style_items = self._resolve_author_style(context.author_style_profile)
        for s in style_items:
            ranked.append(
                RankedConstraint(
                    priority=self.PRIORITY_AUTHOR_STYLE,
                    category="author_style",
                    text=s,
                    weight=8.0,
                )
            )

        # Tier 3: Character Voice (Voice Profile > Generic Rule)
        for v in voice_constraints:
            ranked.append(
                RankedConstraint(
                    priority=self.PRIORITY_CHARACTER_VOICE,
                    category="character_voice",
                    text=v,
                    weight=7.0,
                )
            )

        # Tier 4: Scene-Specific Rules & POV
        scene_items = self._resolve_scene_and_pov(context.scene_type, context.pov)
        for sc in scene_items:
            ranked.append(
                RankedConstraint(
                    priority=self.PRIORITY_SCENE,
                    category="scene",
                    text=sc,
                    weight=6.0,
                )
            )

        # Tier 5: Recent Expression Saturation Memory
        memory_item = self._resolve_expression_memory(context.recent_expression_memory)
        if memory_item:
            ranked.append(
                RankedConstraint(
                    priority=self.PRIORITY_MEMORY,
                    category="memory",
                    text=memory_item,
                    weight=5.0,
                )
            )

        # Tier 6: Genre Presets
        if context.genre:
            genre_item = self._resolve_genre_preset(context.genre)
            if genre_item:
                ranked.append(
                    RankedConstraint(
                        priority=self.PRIORITY_GENRE,
                        category="genre",
                        text=genre_item,
                        weight=4.0,
                    )
                )

        # Tier 7: Dynamic Top-K Generic HWE Rules (Filtered for conflicts)
        baseline_phrase_rule = "【避免AI模板短语】严禁使用“不禁”、“竟然”、“仿佛…一般”、“心中暗道”、“眼中闪过一丝”等模板化短语与机械动作。"
        ranked.append(
            RankedConstraint(
                priority=self.PRIORITY_GENERIC_HWE,
                category="generic_hwe",
                text=baseline_phrase_rule,
                weight=3.5,
            )
        )
        generic_rules = self._select_top_k_rules(
            scene_type=context.scene_type,
            active_packs=context.active_rule_packs,
            suppressed_rule_ids=suppressed_rule_ids,
            top_k=10,
        )
        for r in generic_rules:
            ranked.append(
                RankedConstraint(
                    priority=self.PRIORITY_GENERIC_HWE,
                    category="generic_hwe",
                    text=r,
                    weight=3.0,
                )
            )

        # 3. Assemble and apply budget limit
        return self._assemble_and_budget(ranked, max_budget=budget)

    def _resolve_character_voice(
        self, context: HumanPromptContext
    ) -> Tuple[List[str], Set[str]]:
        """Extract character voice rules and identify suppressed generic rule IDs."""
        voice_constraints: List[str] = []
        suppressed_rules: Set[str] = set(context.suppressed_rules)

        voice_map = context.character_voice or {}
        active_chars = set(context.characters) if context.characters else set(voice_map.keys())

        for char_name, profile in voice_map.items():
            if active_chars and char_name not in active_chars:
                continue

            if isinstance(profile, str):
                voice_constraints.append(f"【角色声线·{char_name}】{profile}")
                continue

            if not isinstance(profile, dict):
                continue

            tone = profile.get("tone") or profile.get("style") or ""
            catchphrases = profile.get("catchphrases") or profile.get("habits") or []
            speech_patterns = profile.get("speech_patterns") or []

            items = []
            if tone:
                items.append(f"说话风格：{tone}")
            if catchphrases:
                cp_str = "、".join(str(c) for c in catchphrases[:4])
                items.append(f"特有口头禅/句式：【{cp_str}】")
            if speech_patterns:
                sp_str = "；".join(str(p) for p in speech_patterns[:3])
                items.append(f"言语特征：{sp_str}")

            # Check conflict with generic rules
            all_traits = f"{tone} {' '.join(str(c) for c in catchphrases)} {' '.join(str(p) for p in speech_patterns)}"

            has_conflict = False
            # If character habitually uses rhetorical questions, suppress rhetorical slop rule
            if any(k in all_traits for k in ("反问", "质问", "问句", "设问")):
                suppressed_rules.add("HWE.DIALOGUE.RHETORICAL_OVERUSE")
                has_conflict = True

            # If character uses deliberate antithesis or binary contrast
            if any(k in all_traits for k in ("不是", "而是", "思辨", "对比", "两分", "不仅")):
                suppressed_rules.add("HWE.STAGING.BINARY_CONTRAST")
                has_conflict = True

            # If character uses intellectual or editorial faux insight
            if any(k in all_traits for k in ("社论", "说教", "分析腔", "论断", "关键在于")):
                suppressed_rules.add("HWE.STAGING.FAUX_INSIGHT")
                has_conflict = True

            tail_note = "（注：该角色固有口吻优先，不受通用句式规避限制）" if has_conflict else ""
            summary = "；".join(items)
            if summary:
                voice_constraints.append(f"【角色声线·{char_name}】{summary}。{tail_note}".strip())

        return voice_constraints, suppressed_rules

    def _resolve_author_style(self, style_profile: Dict[str, Any]) -> List[str]:
        """Extract author style bible and preference directives."""
        if not style_profile:
            return []

        results: List[str] = []
        tone = style_profile.get("tone") or style_profile.get("style_notes")
        if tone:
            results.append(f"【作品风格基调】{tone}")

        forbidden = style_profile.get("forbidden_tropes") or style_profile.get("forbidden_patterns")
        if forbidden and isinstance(forbidden, (list, tuple)):
            f_str = "、".join(str(x) for x in forbidden[:8])
            results.append(f"【作者禁忌套路】严禁套用：{f_str}")

        preferred = style_profile.get("preferred_patterns")
        if preferred:
            if isinstance(preferred, (list, tuple)):
                p_str = "、".join(str(x) for x in preferred[:6])
                results.append(f"【作者文风偏好】鼓励表现：{p_str}")
            elif isinstance(preferred, str):
                results.append(f"【作者文风偏好】{preferred}")

        return results

    def _resolve_scene_and_pov(
        self, scene_type: Optional[str], pov: Optional[str]
    ) -> List[str]:
        """Generate scene dynamics and POV constraints."""
        results: List[str] = []

        if scene_type:
            st = str(scene_type)
            if any(k in st for k in ("对峙", "交锋", "谈判", "质问", "争吵", "对话")):
                results.append("【场景重点·高压对峙】台词精炼锋利，保留潜台词与试探空间，严禁对白变成背景说明书或情绪直叙。")
            elif any(k in st for k in ("战斗", "打斗", "动作", "追逐", "逃亡", "刺杀")):
                results.append("【场景重点·动作交锋】动词干脆利落，强化力量传递与空间位移，避免冗长定语与慢动作无意义修辞。")
            elif any(k in st for k in ("推理", "复盘", "独白", "思考", "调查", "心理")):
                results.append("【场景重点·推理与内省】依靠感官注意与事实推演推进，严禁作者以全知姿态对读者阐释‘这代表着什么’。")
            elif any(k in st for k in ("转场", "日常", "环境", "休息")):
                results.append("【场景重点·空间氛围】通过具体器物、气味、光影等五感细节落地，避免‘空气仿佛凝固’等陈腐空洞比喻。")
            else:
                results.append(f"【场景重点·{st}】动作推进果断，聚焦人物当下目标，避免无意义铺垫。")

        if pov:
            pv = str(pov)
            if any(k in pv for k in ("限知", "第三人称限知")):
                results.append("【视角规范·第三人称限知】严格收敛在主角当下视听感知与认知边界内，禁止上帝视角穿透至他人未表现的心理。")
            elif "第一人称" in pv:
                results.append("【视角规范·第一人称】完全通过‘我’的主观感知与情绪滤镜行文，禁止使用上帝视角描写他人微表情心理。")

        return results

    def _resolve_expression_memory(
        self, recent_memory: Sequence[str]
    ) -> Optional[str]:
        """Generate saturation warning for recently repeated phrases."""
        if not recent_memory:
            return None

        # Clean and deduplicate
        seen = set()
        cleaned: List[str] = []
        for item in recent_memory:
            phrase = str(item).strip().strip("“”\"'【】")
            if phrase and phrase not in seen:
                seen.add(phrase)
                cleaned.append(phrase)

        if not cleaned:
            return None

        phrases_str = "、".join(f"“{p}”" for p in cleaned[:6])
        return f"【近期表达饱和预警】近几章已多次出现{phrases_str}，本章严格避免再次使用相同身体微动作与模板比喻。"

    def _resolve_genre_preset(self, genre: str) -> Optional[str]:
        """Provide genre-specific slop prevention advice."""
        g = str(genre).strip()
        if any(k in g for k in ("悬疑", "推理", "谍战", "刑侦", "都市")):
            return "【悬疑质感】强化物理细节、时间线与逻辑咬合，杜绝‘眼中闪过一丝精芒’或无证据的灵光直觉断案。"
        elif any(k in g for k in ("玄幻", "仙侠", "修真", "奇幻")):
            return "【玄幻质感】突出招式交锋的实质代价与环境破坏力，严禁‘倒吸一口凉气’‘恐怖如斯’等过载旁观反应。"
        elif any(k in g for k in ("科幻", "末世", "赛博")):
            return "【科幻质感】机械与技术描写需具备扎实逻辑与物质质感，避免漂浮的伪科技术语连珠炮轰。"
        return f"【文风规范】保持【{g}】核心基调，注重情节冲突与人物主动性，杜绝流水账与解释腔。"

    def _select_top_k_rules(
        self,
        scene_type: Optional[str],
        active_packs: Sequence[str],
        suppressed_rule_ids: Set[str],
        top_k: int = 10,
    ) -> List[str]:
        """Dynamically pick Top-K generic HWE rules ranked by relevance and severity."""
        all_rules = self.registry.list_rules(enabled_only=True)
        active_pack_set = set(active_packs or [])

        scored_rules: List[Tuple[float, HWERule]] = []

        st = str(scene_type or "")
        for r in all_rules:
            if r.id in suppressed_rule_ids:
                continue

            # Base severity score
            sev_scores = {"high": 8.0, "medium": 5.0, "low": 2.0}
            score = sev_scores.get(r.severity, 5.0)

            # Scene-specific relevance bonus
            if any(k in st for k in ("对峙", "交锋", "对话", "谈判")) and r.family in ("dialogue", "staging"):
                score += 5.0
            elif any(k in st for k in ("战斗", "打斗", "动作", "追逐")) and r.family in ("rhythm", "staging"):
                score += 5.0
            elif any(k in st for k in ("推理", "思考", "心理")) and r.family in ("narration", "staging"):
                score += 5.0
            elif any(k in st for k in ("转场", "日常", "环境")) and r.family in ("imagery", "rhythm"):
                score += 5.0

            # Active pack bonus
            if r.family in active_pack_set or r.id in active_pack_set:
                score += 3.0

            scored_rules.append((score, r))

        # Sort descending by score
        scored_rules.sort(key=lambda x: x[0], reverse=True)

        selected: List[str] = []
        for _, rule in scored_rules[:top_k]:
            directive = rule.suggestion.strip() if rule.suggestion else rule.why.strip()
            if not directive:
                directive = f"避免{rule.title}套路表达"
            selected.append(f"【{rule.title}】{directive}")

        return selected

    def _assemble_and_budget(
        self, ranked_items: List[RankedConstraint], max_budget: int = 1200
    ) -> str:
        """Assemble constraints into a numbered list, trimming lower priority tiers if over budget."""
        header = "[本章文风与去套路约束]\n"

        # Deduplicate identical text
        unique_items: List[RankedConstraint] = []
        seen_texts: Set[str] = set()
        for item in ranked_items:
            t = item.text.strip()
            if t and t not in seen_texts:
                seen_texts.add(t)
                unique_items.append(item)

        # Truncate lowest-priority items until char budget fits
        def format_output(items: Sequence[RankedConstraint]) -> str:
            lines = [header]
            for idx, c in enumerate(items, 1):
                lines.append(f"{idx}. {c.text}")
            return "\n".join(lines)

        current_items = list(unique_items)
        rendered = format_output(current_items)

        # Drop from lowest priority (tier 7 first, then tier 6, etc.)
        while len(rendered) > max_budget and current_items:
            max_p = max(c.priority for c in current_items)
            drop_idx = -1
            for i in range(len(current_items) - 1, -1, -1):
                if current_items[i].priority == max_p:
                    drop_idx = i
                    break

            if drop_idx >= 0:
                current_items.pop(drop_idx)
                rendered = format_output(current_items)
            else:
                break

        # If even high-priority items still exceed budget, hard-slice with ellipsis
        if len(rendered) > max_budget:
            rendered = rendered[: max_budget - 3] + "..."

        return rendered


def compile_human_writing_prompt(
    root_dir: Optional[Path] = None,
    scene: Optional[Mapping[str, Any]] = None,
    plan: Optional[Mapping[str, Any]] = None,
    user_constraints: Optional[Sequence[str]] = None,
    max_budget: int = 1200,
    **kwargs: Any,
) -> str:
    """Convenience factory function for compiling HWE prompt constraints for a chapter or scene."""
    scene_data = dict(scene or {})
    plan_data = dict(plan or {})

    # Extract scene metadata
    scene_type = kwargs.get("scene_type") or scene_data.get("type") or scene_data.get("scene_type")
    pov = kwargs.get("pov") or plan_data.get("pov")
    genre = kwargs.get("genre")
    characters = list(kwargs.get("characters") or scene_data.get("characters") or [])

    character_voice = dict(kwargs.get("character_voice") or {})
    recent_memory = list(kwargs.get("recent_expression_memory") or [])
    author_style = dict(kwargs.get("author_style_profile") or {})

    # Pull project assets if root_dir is provided
    if root_dir:
        rpath = Path(root_dir)
        try:
            from novel_agent.quality.character_voice import load_character_voice_profiles

            profiles = load_character_voice_profiles(rpath)
            for c in characters:
                if c in profiles and c not in character_voice:
                    character_voice[c] = profiles[c]
        except Exception:
            pass

        try:
            from novel_agent.quality.expression_memory import load_expression_memory

            mem_index = load_expression_memory(rpath)
            if mem_index and not recent_memory:
                entries = mem_index.get("entries", [])
                recent_memory.extend(
                    [
                        e.get("canonical")
                        for e in entries[-20:]
                        if isinstance(e, dict) and e.get("canonical")
                    ]
                )
        except Exception:
            pass

        try:
            from novel_agent.pipeline import load_pipeline_settings

            settings = load_pipeline_settings(rpath)
            if not genre:
                genre = settings.get("novel", {}).get("genre") or settings.get("genre")
        except Exception:
            pass

    ctx = HumanPromptContext(
        genre=genre,
        scene_type=scene_type,
        pov=pov,
        characters=characters,
        character_voice=character_voice,
        author_style_profile=author_style,
        recent_expression_memory=recent_memory,
        user_constraints=list(user_constraints or []),
        max_chars_budget=max_budget,
    )

    compiler = HumanContextCompiler(default_budget=max_budget)
    return compiler.compile(ctx)
