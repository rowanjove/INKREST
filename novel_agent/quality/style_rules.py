"""Report-only AI-style and paragraph/layout checks."""

import re
from typing import Any, Dict, List, Optional

# Common AI-generated phrases that indicate low-quality output
import os
from pathlib import Path

# Common AI-generated phrases that indicate low-quality output
AI_STYLE_PATTERNS = [
    ("style_word_bujin", re.compile(r"不禁"), "高频AI词：不禁"),
    ("style_word_jingran", re.compile(r"竟然"), "高频AI词：竟然"),
    ("style_word_juran", re.compile(r"居然"), "高频AI词：居然"),
    ("style_pattern_fangfo", re.compile(r"仿佛.*一般"), "AI句式：仿佛...一般"),
    ("style_pattern_rutong", re.compile(r"如同.*似的"), "AI句式：如同...似的"),
    ("style_internal_dao", re.compile(r"心中暗道"), "AI内心独白：心中暗道"),
    ("style_internal_xiang", re.compile(r"暗暗想道"), "AI内心独白：暗暗想道"),
    ("style_action_xi", re.compile(r"深吸一口气"), "AI动作：深吸一口气"),
    ("style_desc_yanzhong", re.compile(r"眼中闪过一丝"), "AI描写：眼中闪过一丝"),
    ("style_desc_zuijiao", re.compile(r"嘴角微微上扬"), "AI描写：嘴角微微上扬"),
]

EMOTION_WORDS = (
    "震惊", "惊讶", "痛苦", "悲伤", "难过", "委屈", "愤怒", "恐惧", "害怕",
    "紧张", "不安", "心痛", "绝望", "复杂", "莫名", "感慨", "羞愧",
)

ABSTRACT_PATTERNS = [
    (re.compile(r"(复杂|难以言说|莫名|无比|极了|无法形容|说不清)"), "抽象修饰词"),
    (re.compile(r"(空气中|气氛).*?(弥漫|凝固|压抑|紧张)"), "空泛氛围描写"),
    (re.compile(r"(时间|这一刻).*?(静止|凝固)"), "模板化时间描写"),
]

EMOTION_TELLING_PATTERNS = [
    re.compile(r"(感到|感受到|感觉到|涌起|充满|满是|心中|内心)[^。！？\n]{0,12}(" + "|".join(EMOTION_WORDS) + r")"),
    re.compile(r"(" + "|".join(EMOTION_WORDS) + r")[^。！？\n]{0,8}(涌上心头|在.*心中|席卷)"),
]

BAD_ENDING_PATTERNS = [
    (re.compile(r"(终于|总算).{0,12}(结束|落下帷幕|告一段落)"), "总结式结尾"),
    (re.compile(r"(望着|看向).{0,12}(远方|天际|夜色).{0,20}(感慨|复杂|充满)"), "感慨式结尾"),
    (re.compile(r"(做好了准备|下定决心|准备迎接|未来的路)"), "决心式结尾"),
    (re.compile(r"(心中|内心).{0,8}(充满|涌起|满是)"), "情绪收束结尾"),
]

HOOK_ENDING_PATTERNS = [
    re.compile(r"(拿起|拨通|推开|打开|拆开|按下|走向|站起|回头|递给).{0,16}(电话|门|信|按钮|她|他|桌|窗|入口)?[。！？]?$"),
    re.compile(r"(不是我|是他|是她|不见了|还活着|门开了|灯灭了|响了)[。！？]?$"),
    re.compile(r"(脚步声|敲门声|短信|来电|枪声|警报|提示音).{0,12}[。！？]?$"),
]


def load_style_rules_config(root_dir: Path) -> Dict[str, Any]:
    import logging
    logger = logging.getLogger(__name__)
    config_path = root_dir / "assets" / "style_rules_config.yaml"
    
    default_config = {
        "rules": {
            "style_word_bujin": {"enabled": True, "weight": 1.0},
            "style_word_jingran": {"enabled": True, "weight": 1.0},
            "style_word_juran": {"enabled": True, "weight": 1.0},
            "style_pattern_fangfo": {"enabled": True, "weight": 1.0},
            "style_pattern_rutong": {"enabled": True, "weight": 1.0},
            "style_internal_dao": {"enabled": True, "weight": 1.0},
            "style_internal_xiang": {"enabled": True, "weight": 1.0},
            "style_action_xi": {"enabled": True, "weight": 1.0},
            "style_desc_yanzhong": {"enabled": True, "weight": 1.0},
            "style_desc_zuijiao": {"enabled": True, "weight": 1.0},
            "anti_ai_emotion_telling": {"enabled": True, "weight": 1.0},
            "anti_ai_abstract_modifier": {"enabled": True, "weight": 1.0},
            "anti_ai_dialogue_overcomplete": {"enabled": True, "weight": 1.0},
            "anti_ai_ending_summary": {"enabled": True, "weight": 1.0},
            "anti_ai_ending_sigh": {"enabled": True, "weight": 1.0},
            "anti_ai_ending_decision": {"enabled": True, "weight": 1.0},
            "anti_ai_ending_emotion": {"enabled": True, "weight": 1.0},
            "paragraph_layout_limit": {"enabled": True, "weight": 1.0, "max_chars": 150}
        }
    }

    if not config_path.exists():
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            import yaml
            config_path.write_text(yaml.safe_dump(default_config, allow_unicode=True), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to create default style rules config: {e}")
        return default_config
        
    try:
        import yaml
        content = config_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        if parsed and isinstance(parsed, dict) and "rules" in parsed:
            return parsed
        logger.warning("Style rules config is malformed. Using default config.")
        return default_config
    except Exception as e:
        logger.warning(f"Failed to load style rules config: {e}. Using default style rules.")
        return default_config


def check_reference_similarity(text: str, root_dir: Path) -> Dict[str, Any]:
    ref_path = root_dir / "assets" / "sample_prose.txt"
    if not ref_path.exists():
        return {"enabled": False, "score": 100, "similarity": 1.0, "details": "未提供参考语料"}
        
    try:
        import numpy as np
        ref_text = ref_path.read_text(encoding="utf-8").strip()
        if not ref_text:
            return {"enabled": False, "score": 100, "similarity": 1.0, "details": "参考语料为空"}
            
        punctuations = "，。！？；：“”‘’（）——……"
        def get_punc_freq(t: str) -> Dict[str, float]:
            if not t:
                return {p: 0.0 for p in punctuations}
            counts = {p: t.count(p) for p in punctuations}
            total = sum(counts.values()) or 1
            return {p: counts[p] / total for p in punctuations}
            
        ref_punc = get_punc_freq(ref_text)
        text_punc = get_punc_freq(text)
        
        v_ref = np.array([ref_punc[p] for p in punctuations])
        v_text = np.array([text_punc[p] for p in punctuations])
        
        norm_ref = np.linalg.norm(v_ref)
        norm_text = np.linalg.norm(v_text)
        if norm_ref * norm_text > 0:
            sim = float(np.dot(v_ref, v_text) / (norm_ref * norm_text))
        else:
            sim = 1.0
            
        ref_paras = [p.strip() for p in ref_text.split("\n") if p.strip()]
        text_paras = [p.strip() for p in text.split("\n") if p.strip()]
        avg_ref_len = sum(len(p) for p in ref_paras) / max(1, len(ref_paras))
        avg_text_len = sum(len(p) for p in text_paras) / max(1, len(text_paras))
        
        len_ratio = min(avg_ref_len, avg_text_len) / max(1, max(avg_ref_len, avg_text_len))
        
        combined_sim = sim * 0.7 + len_ratio * 0.3
        score = int(combined_sim * 100)
        
        return {
            "pass": score >= 60,
            "enabled": True,
            "score": score,
            "similarity": round(combined_sim, 3),
            "details": [f"标点特征重合度: {sim:.2f}", f"平均段长重合度: {len_ratio:.2f}"]
        }
    except Exception as e:
        return {"enabled": False, "score": 100, "similarity": 1.0, "details": f"计算失败: {e}"}


def check_ai_style(text: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check for AI-style phrases in the text. Report-only."""
    if not text:
        return {"pass": True, "level": "none", "score": 100, "details": [], "total_hits": 0, "hits": []}

    rules_cfg = (config or {}).get("rules", {})
    details: List[str] = []
    total_hits = 0
    weighted_hits = 0.0
    hits: List[str] = []

    for rule_id, pattern, desc in AI_STYLE_PATTERNS:
        cfg = rules_cfg.get(rule_id, {"enabled": True, "weight": 1.0})
        if not cfg.get("enabled", True):
            continue
            
        weight = float(cfg.get("weight", 1.0))
        rule_hits = 0
        for m in pattern.finditer(text):
            hits.append(m.group(0))
            rule_hits += 1
            
        if rule_hits > 0:
            total_hits += rule_hits
            weighted_hits += rule_hits * weight
            details.append(f"{desc} x{rule_hits} (权重: {weight})")

    text_len = len(text)
    hit_density = weighted_hits / max(1, text_len / 1000)  # hits per 1000 chars
    score = max(0, int(100 - hit_density * 15))

    if score >= 80:
        level = "none"
    elif score >= 60:
        level = "warning"
    elif score >= 40:
        level = "review"
    else:
        level = "fail"

    return {
        "pass": level in ("none", "warning"),
        "level": level,
        "score": score,
        "details": details,
        "total_hits": total_hits,
        "hits": hits,
    }


def _sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？!?])\s*|\n+", text or "") if part.strip()]


def _last_sentence(text: str) -> str:
    sentences = _sentences(text)
    return sentences[-1] if sentences else ""


def check_anti_ai_flavor(text: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check concrete anti-AI-flavor rules from online-fiction writing practice."""
    if not text:
        return {
            "pass": True,
            "level": "none",
            "score": 100,
            "details": [],
            "emotion_telling_hits": 0,
            "abstract_modifier_hits": 0,
            "dialogue_overcomplete_hits": 0,
            "ending_type": "empty",
            "hits": [],
        }

    rules_cfg = (config or {}).get("rules", {})
    details: List[str] = []
    hits: List[str] = []

    emotion_hits = 0
    cfg_emotion = rules_cfg.get("anti_ai_emotion_telling", {"enabled": True, "weight": 1.0})
    if cfg_emotion.get("enabled", True):
        weight_emotion = float(cfg_emotion.get("weight", 1.0))
        for pattern in EMOTION_TELLING_PATTERNS:
            for m in pattern.finditer(text):
                hits.append(m.group(0))
                emotion_hits += 1
    else:
        weight_emotion = 0.0

    if emotion_hits:
        details.append(f"情绪直写 x{emotion_hits}")

    abstract_hits = 0
    cfg_abstract = rules_cfg.get("anti_ai_abstract_modifier", {"enabled": True, "weight": 1.0})
    if cfg_abstract.get("enabled", True):
        weight_abstract = float(cfg_abstract.get("weight", 1.0))
        for pattern, desc in ABSTRACT_PATTERNS:
            count = 0
            for m in pattern.finditer(text):
                hits.append(m.group(0))
                count += 1
            if count:
                abstract_hits += count
                details.append(f"{desc} x{count}")
    else:
        weight_abstract = 0.0

    dialogue_overcomplete_hits = 0
    cfg_dialogue = rules_cfg.get("anti_ai_dialogue_overcomplete", {"enabled": True, "weight": 1.0})
    if cfg_dialogue.get("enabled", True):
        weight_dialogue = float(cfg_dialogue.get("weight", 1.0))
        for m in re.finditer(r"[“\"]([^”\"]+)[”\"]", text):
            block = m.group(1)
            comma_count = len(re.findall(r"[，,；;：:]", block))
            if len(block) >= 24 or comma_count >= 2:
                dialogue_overcomplete_hits += 1
                hits.append(m.group(0))
    else:
        weight_dialogue = 0.0

    if dialogue_overcomplete_hits:
        details.append(f"对话过完整 x{dialogue_overcomplete_hits}")

    ending = _last_sentence(text)
    bad_ending = ""
    ending_weight = 1.0
    for rule_id, pattern, desc in [
        ("anti_ai_ending_summary", BAD_ENDING_PATTERNS[0][0], BAD_ENDING_PATTERNS[0][1]),
        ("anti_ai_ending_sigh", BAD_ENDING_PATTERNS[1][0], BAD_ENDING_PATTERNS[1][1]),
        ("anti_ai_ending_decision", BAD_ENDING_PATTERNS[2][0], BAD_ENDING_PATTERNS[2][1]),
        ("anti_ai_ending_emotion", BAD_ENDING_PATTERNS[3][0], BAD_ENDING_PATTERNS[3][1]),
    ]:
        cfg_end = rules_cfg.get(rule_id, {"enabled": True, "weight": 1.0})
        if not cfg_end.get("enabled", True):
            continue
        if pattern.search(ending):
            bad_ending = desc
            ending_weight = float(cfg_end.get("weight", 1.0))
            hits.append(ending)
            break

    has_hook_ending = any(pattern.search(ending) for pattern in HOOK_ENDING_PATTERNS)
    if bad_ending:
        ending_type = "bad"
        details.append(bad_ending)
    elif has_hook_ending:
        ending_type = "hook"
    else:
        ending_type = "neutral"

    weighted_hits = (
        emotion_hits * weight_emotion +
        abstract_hits * weight_abstract +
        dialogue_overcomplete_hits * weight_dialogue
    )
    if ending_type == "bad":
        weighted_hits += 2 * ending_weight

    total_hits = emotion_hits + abstract_hits + dialogue_overcomplete_hits
    if ending_type == "bad":
        total_hits += 2

    text_len = len(text)
    density = weighted_hits / max(1, text_len / 1000)
    score = max(0, int(100 - density * 12))

    if score >= 85 and ending_type != "bad":
        level = "none"
    elif score >= 70 and ending_type != "bad":
        level = "warning"
    elif score >= 45:
        level = "review"
    else:
        level = "fail"

    return {
        "pass": level in ("none", "warning"),
        "level": level,
        "score": score,
        "details": details,
        "total_hits": total_hits,
        "emotion_telling_hits": emotion_hits,
        "abstract_modifier_hits": abstract_hits,
        "dialogue_overcomplete_hits": dialogue_overcomplete_hits,
        "ending_type": ending_type,
        "ending": ending,
        "hits": hits,
    }


def check_paragraph_layout(text: str, config: Optional[Dict[str, Any]] = None, max_chars: int = 150) -> Dict[str, Any]:
    """Check paragraph length distribution. Report-only."""
    rules_cfg = (config or {}).get("rules", {})
    cfg_layout = rules_cfg.get("paragraph_layout_limit", {"enabled": True, "weight": 1.0, "max_chars": max_chars})
    
    if not cfg_layout.get("enabled", True):
        return {"pass": True, "level": "none", "score": 100, "details": ["段落长度检测已禁用"]}
        
    limit_chars = int(cfg_layout.get("max_chars", max_chars))
    weight = float(cfg_layout.get("weight", 1.0))
    
    if not text:
        return {"pass": True, "level": "none", "score": 100, "details": []}

    paragraphs = re.split(r"\n{1,2}", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return {"pass": True, "level": "none", "score": 100, "details": []}

    long_paras = []
    for i, para in enumerate(paragraphs):
        if len(para) > limit_chars:
            long_paras.append({"index": i + 1, "length": len(para)})

    long_ratio = len(long_paras) / len(paragraphs)
    weighted_ratio = long_ratio * weight

    if weighted_ratio <= 0.1:
        level = "none"
        score = 100
    elif weighted_ratio <= 0.25:
        level = "warning"
        score = 75
    elif weighted_ratio <= 0.5:
        level = "review"
        score = 50
    else:
        level = "fail"
        score = 25

    return {
        "pass": level in ("none", "warning"),
        "level": level,
        "score": score,
        "total_paragraphs": len(paragraphs),
        "long_paragraphs": len(long_paras),
        "long_ratio": round(long_ratio, 3),
        "details": [f"段落 {p['index']}: {p['length']} 字" for p in long_paras[:5]],
    }
