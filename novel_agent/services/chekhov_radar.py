"""Chekhov's Gun Radar (契诃夫之枪雷达).

Monitors open narrative threads and foreshadowing in long serial novels.
Flags dangling threads that have slept for too many chapters without advancement
and generates actionable recovery recommendations for outline/chapter planning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal


ThreadDormancyStatus = Literal["active", "simmering", "dangling_critical"]


@dataclass
class ChekhovSignal:
    thread_id: str
    title: str
    last_chapter: int
    current_chapter: int
    dormant_distance: int
    status: ThreadDormancyStatus
    recovery_suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def scan_threads_dormancy(
    threads: List[Dict[str, Any]],
    current_chapter: int,
    *,
    simmering_threshold: int = 6,
    critical_threshold: int = 13,
) -> List[ChekhovSignal]:
    """Scan open threads and calculate dormant distances from current chapter.
    
    Status tiers:
    - dormant_distance <= simmering_threshold: 'active'
    - simmering_threshold < dormant_distance < critical_threshold: 'simmering'
    - dormant_distance >= critical_threshold: 'dangling_critical' (requires intervention!)
    """
    signals: List[ChekhovSignal] = []

    for item in threads:
        # 只监测尚未关闭的伏笔/线索
        thread_status = str(item.get("status", "open")).lower()
        if thread_status in ("closed", "resolved", "archived"):
            continue

        thread_id = str(item.get("id") or item.get("thread_id") or "unknown")
        title = str(item.get("title") or item.get("name") or thread_id)
        
        # 获取最后一次被推进或提及的章节编号
        last_chapter_val = item.get("last_chapter") or item.get("last_referenced_chapter")
        if last_chapter_val is not None:
            try:
                last_ch = int(last_chapter_val)
            except (ValueError, TypeError):
                last_ch = 1
        else:
            # 若未显式记录，回退到创建章节或默认第 1 章
            last_ch = int(item.get("origin_chapter", 1))

        dormant_distance = max(0, current_chapter - last_ch)

        if dormant_distance >= critical_threshold:
            status: ThreadDormancyStatus = "dangling_critical"
            suggestion = (
                f"【悬空契诃夫之枪警告】线索「{title}」(ID: {thread_id}) 已长达 {dormant_distance} 章未被提及！"
                f"建议在当前或下 1~2 章的大纲规划中将其注入 must_include，安排相关角色互动、情报揭秘或场景触碰。"
            )
        elif dormant_distance >= simmering_threshold:
            status = "simmering"
            suggestion = (
                f"线索「{title}」已潜伏 {dormant_distance} 章，可作为背景暗流适度点拨，避免彻底边缘化。"
            )
        else:
            status = "active"
            suggestion = "线索近期活跃，叙事节奏健康。"

        signals.append(
            ChekhovSignal(
                thread_id=thread_id,
                title=title,
                last_chapter=last_ch,
                current_chapter=current_chapter,
                dormant_distance=dormant_distance,
                status=status,
                recovery_suggestion=suggestion,
            )
        )

    # 优先展示悬空最危险的线索
    return sorted(signals, key=lambda s: -s.dormant_distance)


def generate_radar_report(signals: List[ChekhovSignal]) -> Dict[str, Any]:
    """Generate summary diagnostics for chapter planning & review."""
    critical = [s.to_dict() for s in signals if s.status == "dangling_critical"]
    simmering = [s.to_dict() for s in signals if s.status == "simmering"]
    active = [s.to_dict() for s in signals if s.status == "active"]

    has_critical = len(critical) > 0

    return {
        "pass": not has_critical,
        "critical_count": len(critical),
        "simmering_count": len(simmering),
        "active_count": len(active),
        "dangling_threads": critical,
        "recommendations": [item["recovery_suggestion"] for item in critical],
    }
