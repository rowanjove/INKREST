from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple


# 预设的读者评论模板，确保生成极具沉浸感的网文社区氛围
VIRTUAL_COMMENTS_TEMPLATES = {
    "positive": [
        ("太虚神主", "⭐⭐⭐⭐⭐", "节奏起飞！金手指用得太有创意了，一口气看完了，跪求作者大大加更！", 382),
        ("书友98273", "⭐⭐⭐⭐⭐", "爽点十足，主角这个装逼反击极其舒适，毫无违规降智感，催更催更！", 251),
        ("小鸡哔哔", "⭐⭐⭐⭐", "好看的，很久没看到设定这么严密又不拖泥带水的电竞文了，五星支持！", 198),
        ("路过的路人甲", "⭐⭐⭐⭐⭐", "这才是真正的爽文，给作者送花！剧情完全戳中我的爽点，一天十更不过分吧！", 143),
    ],
    "neutral": [
        ("墨色残阳", "⭐⭐⭐", "设定挺新颖的，不过这几章日常描写稍微多了一点点，想看下一场核心比赛/冲突爆发！", 89),
        ("合理党代表", "⭐⭐⭐⭐", "金手指这章怎么没动静，主角不要一直低调啊，赶紧出来打脸展示实力！", 72),
        ("书友54921", "⭐⭐⭐", "文字挺流畅，就是感觉配角废话有点多，剧情推进速度能再加快一点就好了。", 64),
    ],
    "negative": [
        ("毒抗已崩", "⭐", "感觉这几章有点注水啊，剧情卡着不动，主角无端压抑，看得我一肚子气，毒发身亡！", 521),
        ("退款大军一员", "⭐⭐", "主角怎么突然智商下线了？太憋屈了吧！作者这章是在强行喂毒吗？看不下去了。", 412),
        ("神农试百草", "⭐", "弃书了弃书了！日常日常写个没完，核心冲突和金手指几章不出现，严重拖沓！", 328),
        ("纯爱战神", "⭐", "这章逻辑彻底崩了，作者脑子进水了写这种桥段，主角怎么这么憋屈，赶紧滚粗来改文！", 298),
    ]
}


def generate_virtual_comments(chapter_id: str, bounce_rate: float) -> List[Dict[str, Any]]:
    """Simulate reader comments for a chapter based on its bounce rate performance."""
    random.seed(hash(chapter_id) + int(bounce_rate * 1000))
    
    if bounce_rate > 0.35:
        category = "negative"
    elif bounce_rate > 0.25:
        category = "neutral"
    else:
        category = "positive"
        
    templates = VIRTUAL_COMMENTS_TEMPLATES[category]
    # 如果模板不够，混合一点
    if len(templates) < 3:
        templates = templates + VIRTUAL_COMMENTS_TEMPLATES["neutral"]
        
    sampled = random.sample(templates, k=min(len(templates), 3))
    
    comments = []
    import datetime
    for idx, (author, rating, text, base_likes) in enumerate(sampled):
        likes = base_likes + random.randint(-15, 30)
        # 头像占位符，使用免费漂亮的随机头像
        avatar = f"https://api.dicebear.com/7.x/adventurer/svg?seed={author}"
        comments.append({
            "id": f"c_{chapter_id}_{idx}",
            "author": author,
            "avatar": avatar,
            "rating": rating,
            "content": text,
            "likes": max(0, likes),
            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 12))).strftime("%Y-%m-%d %H:%M")
        })
    return comments


def compute_adaptive_outline(
    project_dir: Path,
    store: Any,
    llm: Any
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Analyze pending/future chapter outlines and rewrite them for better pacing if there is a crisis."""
    # 1. 查找所有未生成的章节
    # 从磁盘读取 outline.json 或是 arc_*.json
    outline_path = project_dir / "workspace" / "outline.json"
    if not outline_path.exists():
        return [], []
        
    try:
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    except Exception:
        return [], []
        
    # 读取分卷，组装全部章节列表
    all_chapters = []
    # 我们遍历所有的 arc_*.json 文件
    ws_dir = project_dir / "workspace"
    arc_files = sorted(list(ws_dir.glob("arc_*.json")))
    for arc_file in arc_files:
        try:
            arc_data = json.loads(arc_file.read_text(encoding="utf-8"))
            all_chapters.extend(arc_data.get("chapters", []))
        except Exception:
            pass
            
    if not all_chapters:
        return [], []
        
    # 2. 筛选出尚未生成的章节
    future_chapters = []
    for ch in all_chapters:
        ch_id = ch.get("chapter_id")
        ch_dir = ws_dir / "chapters" / f"chapter_{ch_id}"
        txt_path = ch_dir / "chapter_final.txt"
        
        # 只要 final 文本文件不存在，或者字数非常少（占位符级别），都判定为未来章节
        has_generated = False
        if txt_path.exists():
            try:
                content = txt_path.read_text(encoding="utf-8").strip()
                if len(content) > 100:
                    has_generated = True
            except OSError:
                pass
                
        if not has_generated:
            future_chapters.append(ch)
            
    if not future_chapters:
        # 没有未来章节可供修改
        return [], []
        
    # 我们最多只微调接下来的 3 章大纲，避免改动过大
    target_chapters = future_chapters[:3]
    
    # 3. 读取最近的读者反馈，分析危机
    recent_feedback = store.get_recent_feedback(limit=3)
    avg_bounce = 0.15
    if recent_feedback:
        avg_bounce = sum(r.get("bounce_rate", 0.0) for r in recent_feedback) / len(recent_feedback)
        
    # 仅当跳出率高（即存在警戒或危机）时才需要真正的“冲突补偿重写”。
    # 若数据健康，大模型也应根据读者“催更/正面反馈”微调大纲以承接前面的情节。
    crisis_level = "正常"
    instructions = "读者表现非常满意，请保持既定的大纲节奏，精益求精。"
    if avg_bounce > 0.35:
        crisis_level = "重度危机"
        instructions = "【重度流失警告】：前几章读者跳出率极高，反馈指出剧情注水严重、日常废话多、主角连续憋屈无反击！请你彻底压缩这几章的日常闲聊与景色铺垫，立刻提前爆发核心冲突，让主角的金手指在 3 章内大显神威，强力反击，拉满爽感。"
    elif avg_bounce > 0.25:
        crisis_level = "中度警戒"
        instructions = "【中度警戒】：读者流失有抬头趋势，反馈指出日常铺垫过多，爽点期待感不足。请在本章规划中压缩日常比重，尽早切入金手指的功效验证或激发出局部戏剧冲突。"

    # 4. 组织 LLM 重写 Prompt
    target_json = json.dumps(target_chapters, ensure_ascii=False, indent=2)
    world_rules = outline.get("world_rules", [])
    protagonist = outline.get("protagonist", {})
    conflict = outline.get("conflict", "")
    
    prompt = f"""你是一名极其资深的网文主编。你的任务是针对当前小说项目【最新读者反馈危机】对后续的【未生成章节大纲走向】进行自适应纠偏微调，以提升读者留存。

【小说宏观设定与主角】
主角: {protagonist.get('name', '主角')} ({protagonist.get('identity', '')})
主角金手指与外挂: {protagonist.get('edge', '')}
全书核心矛盾冲突: {conflict}
世界观设定限制: {world_rules}

【当前作品连载反馈】
平均跳出率: {avg_bounce*100:.1f}% (连载状态: {crisis_level})
主编整改指令: {instructions}

【待微调的原章节大纲列表】
{target_json}

【微调输出格式要求】
你必须输出且仅输出与上述【待微调原章节大纲列表】相同 JSON 结构的数组，包含微调修改后的这几章大纲对象（chapter_id 不能修改）。请直接输出合法 JSON，不要带任何 Markdown 包裹标记或前言旁白。
"""
    try:
        response_text = llm.generate("chief_editor", prompt).strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        new_chapters = json.loads(response_text)
        if not isinstance(new_chapters, list):
            new_chapters = target_chapters
        return target_chapters, new_chapters
    except Exception as exc:
        # 降级返回，不修改
        import logging
        logging.getLogger("web.server").warning("Failed to compute adaptive outline: %s", exc)
        return target_chapters, target_chapters
