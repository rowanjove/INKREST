from __future__ import annotations

from typing import Any, Dict

PLATFORM_PROFILES: Dict[str, Dict[str, Any]] = {
    "qidian": {
        "name": "qidian",
        "label": "起点中文网",
        "pacing_density": 2,
        "setting_detail_weight": 5,
        "dialogue_ratio_range": [0.15, 0.40],
        "style_prompt": "文笔需沉稳扎实，侧重细致的环境描写、人物心理活动、精密的设定铺垫。配角智商在线，剧情逻辑合理性强，避免无脑降智与突兀的冲突爆发。",
        "golden_three_rules": "第一章通过日常生活或合理的情境引入故事背景、主角身份与世界观基础，可埋下长线伏笔；第二章展示日常升级/职业轨迹，并合理引出主角的特质或微小的奇遇；第三章建立明确的近期目标与外部压力，通过合乎逻辑的利益冲突树立第一阶段的期待感。",
        "rules_blacklist": [
            "严禁无脑装逼打脸",
            "主角行事须合乎情理逻辑",
            "避免纯对话水字数"
        ]
    },
    "fanqie": {
        "name": "fanqie",
        "label": "番茄小说",
        "pacing_density": 4,
        "setting_detail_weight": 2,
        "dialogue_ratio_range": [0.25, 0.50],
        "style_prompt": "文字通俗易懂，节奏流畅欢快。重点突出故事的冲突与主角的强力反击。铺垫要少，期待感要强，多动作描写与爽点反馈。",
        "golden_three_rules": "第一章必须在 500 字内交代主角困境，并迅速以戏剧性的方式激活金手指（如绑定系统、重生觉醒）；第二章立即展示金手指的初步神奇功效，带来强烈的爽感反馈，并引出首个对立小冲突（如被嘲讽或遭遇危机）；第三章通过第一波小爽点的彻底爆发或危机的戏剧性化解，树立小说第一个明确的长线宏大目标，并留下极富悬念的结尾钩子以勾住留存。",
        "rules_blacklist": [
            "严禁连续三章主角处于压抑吃瘪状态",
            "避免过度复杂的长句描写与抽象设定",
            "禁止虐主或送女毒点"
        ]
    },
    "feilu": {
        "name": "feilu",
        "label": "飞卢小说网",
        "pacing_density": 5,
        "setting_detail_weight": 1,
        "dialogue_ratio_range": [0.30, 0.60],
        "style_prompt": "文字极致直白，情绪张力极大。严禁长篇大论的世界观铺垫，剧情必须开局即无敌、闪击打脸。人物对话紧密，情绪宣泄直接，情节要爽、要快、要爆。",
        "golden_three_rules": "第一章首段直切主题，直接展示逆天外挂或金手指觉醒，同时迅速爆发激烈的冲突（如直接打脸或无敌碾压），不加任何累赘背景介绍；第二章金手指持续升级或爆发性使用，爽点成倍叠加，主角地位急剧攀升；第三章引出更高层次的绝对爽点或碾压局，悬念直接挂钩后面的暴爽剧情，将读者情绪彻底拉满。",
        "rules_blacklist": [
            "主角绝不能受到任何实质委屈",
            "禁止出现长篇大论的设定铺垫",
            "严禁拖沓日常，每一章必须有爆点"
        ]
    },
    "jinjiang": {
        "name": "jinjiang",
        "label": "晋江文学城",
        "pacing_density": 3,
        "setting_detail_weight": 3,
        "dialogue_ratio_range": [0.35, 0.55],
        "style_prompt": "文字优美细腻，充满画面感与情绪流动。侧重于人设互动、眼神微表情、幽默或隐忍的对话交互。极其注重主角间的宿命感、人际羁绊与情感张力。",
        "golden_three_rules": "第一章重点立人设，展现主角独特的性格魅力或身处的情感/身世风暴中心，并引出另一核心人物（配角/CP）的侧面信息或初次交集；第二章通过两人的戏剧性互动或命运交错，碰撞出细腻的情感火花或张力；第三章引入外部的环境反转、情感冲突升级（如修罗场或立场对立），建立强烈的宿命追读钩子。",
        "rules_blacklist": [
            "严禁主角人设扁平无脑化",
            "避免过度暴力的打脸降智冲突",
            "禁止忽略角色情感逻辑的生硬剧情推进"
        ]
    }
}


def resolve_platform_profile(platform_name: str) -> Dict[str, Any]:
    """Retrieve platform profile parameters by key, defaulting to qidian if not found."""
    platform_id = platform_name.lower().strip() if platform_name else "qidian"
    if platform_id not in PLATFORM_PROFILES:
        platform_id = "qidian"
    return PLATFORM_PROFILES[platform_id]
