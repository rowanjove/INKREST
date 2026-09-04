"""Stat-FSM: Deterministic progression and cultivation realm finite state machine.

Guards against sudden power level collapse, illegal realm jumps, or phantom item consumption
in long-form web serial novels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


# 标准通用玄幻/修仙进阶阶梯
DEFAULT_CULTIVATION_LADDER: List[str] = [
    "凡人",
    "炼气一层", "炼气二层", "炼气三层", "炼气四层", "炼气五层",
    "炼气六层", "炼气七层", "炼气八层", "炼气九层", "炼气圆满",
    "筑基初期", "筑基中期", "筑基后期", "筑基圆满",
    "金丹初期", "金丹中期", "金丹后期", "金丹圆满",
    "元婴初期", "元婴中期", "元婴后期", "元婴圆满",
    "化神初期", "化神中期", "化神后期", "化神圆满",
    "炼虚期", "合体期", "大乘期", "渡劫飞升",
]


@dataclass
class RealmLadder:
    """Ordered cultivation hierarchy allowing index-based distance and transition checks."""

    ranks: List[str] = field(default_factory=lambda: list(DEFAULT_CULTIVATION_LADDER))

    def index_of(self, realm: str) -> Optional[int]:
        if not realm:
            return None
        trimmed = realm.strip()
        if trimmed in self.ranks:
            return self.ranks.index(trimmed)
        # 归一化精准匹配（如“金丹期初期”去除“期”后精准匹配“金丹初期”）
        normalized = trimmed.replace("期", "")
        for i, rank in enumerate(self.ranks):
            if rank.replace("期", "") == normalized:
                return i
        # 模糊最长公共匹配：限制最小长度 >= 2，按匹配覆盖长度优先，防止短词碰撞
        best_match: Optional[int] = None
        best_len = 0
        for i, rank in enumerate(self.ranks):
            if len(rank) >= 2 and rank in trimmed:
                if len(rank) > best_len:
                    best_len = len(rank)
                    best_match = i
            elif len(trimmed) >= 2 and trimmed in rank:
                if len(trimmed) > best_len:
                    best_len = len(trimmed)
                    best_match = i
        return best_match

    def validate_transition(
        self,
        current_realm: str,
        target_realm: str,
        *,
        allow_drop: bool = False,
        max_step: int = 2,
    ) -> Tuple[bool, str]:
        """Validate if transition between two realms is legally permitted.
        
        Rules:
        - Must be known realms.
        - Advancement cannot exceed max_step (default: 2 sub-levels, prevents e.g. Qi -> Core jumps).
        - Demotion is strictly forbidden unless allow_drop is set (e.g. severe injury / dantian shattered).
        """
        curr_idx = self.index_of(current_realm)
        tgt_idx = self.index_of(target_realm)

        if curr_idx is None:
            return True, f"未知当前境界: {current_realm}，跳过硬校验"
        if tgt_idx is None:
            return True, f"未知目标境界: {target_realm}，跳过硬校验"

        if curr_idx == tgt_idx:
            return True, "境界持平，无需转移"

        # 境界倒退校验
        if tgt_idx < curr_idx:
            if allow_drop:
                return True, f"因特殊剧情事件修为倒退：{current_realm} -> {target_realm}"
            return False, f"非法修为倒退：从 {current_realm} 倒退至 {target_realm}，未授权重伤或废功标记！"

        # 越级跳跃校验
        step = tgt_idx - curr_idx
        if step > max_step:
            return (
                False,
                f"非法越级跳跃：从 {current_realm} 跳过 {step} 级直接升至 {target_realm}，超过单次最大进阶限度 ({max_step})！",
            )

        return True, f"合法进阶：{current_realm} -> {target_realm} (跨越 {step} 阶)"


def extract_mentioned_ranks(
    text: str,
    ranks: Optional[Sequence[str]] = None,
) -> List[str]:
    """Return cultivation ranks mentioned in text, left-to-right, longest match first."""
    source = text or ""
    ladder_ranks = list(ranks) if ranks is not None else list(DEFAULT_CULTIVATION_LADDER)
    spans: List[Tuple[int, int, str]] = []
    for rank in sorted(ladder_ranks, key=len, reverse=True):
        if len(rank) < 3:
            continue
        start = 0
        while True:
            idx = source.find(rank, start)
            if idx < 0:
                break
            end = idx + len(rank)
            if any(idx < existing_end and end > existing_start for existing_start, existing_end, _ in spans):
                start = idx + 1
                continue
            spans.append((idx, end, rank))
            start = end
    spans.sort(key=lambda item: item[0])
    return [rank for _, _, rank in spans]


def audit_realm_transitions(
    text: str,
    *,
    ladder: Optional[RealmLadder] = None,
    max_step: int = 2,
) -> Dict[str, Any]:
    """Report-only scan of consecutive realm mentions. Never fails the chapter."""
    resolved = ladder or RealmLadder()
    mentioned = extract_mentioned_ranks(text, resolved.ranks)
    details: List[str] = []
    for current_realm, target_realm in zip(mentioned, mentioned[1:]):
        ok, message = resolved.validate_transition(
            current_realm,
            target_realm,
            max_step=max_step,
        )
        if not ok:
            details.append(message)
    return {
        "pass": True,
        "level": "warning" if details else "none",
        "score": 80 if details else 100,
        "details": details,
        "metrics": {
            "mentioned_ranks": mentioned,
            "issue_count": len(details),
        },
    }


@dataclass
class ItemLedger:
    """Tracks consumable items and prevents phantom usage."""

    inventory: Dict[str, int] = field(default_factory=dict)

    def add_item(self, item_name: str, count: int = 1) -> None:
        if count <= 0 or not item_name:
            return
        self.inventory[item_name] = self.inventory.get(item_name, 0) + count

    def consume_item(self, item_name: str, count: int = 1) -> Tuple[bool, str]:
        if not item_name or count <= 0:
            return False, "无效道具名或消耗数量"
        current_qty = self.inventory.get(item_name, 0)
        if current_qty < count:
            return False, f"道具不足：拥有 {item_name} x{current_qty}，无法消耗 x{count}"
        self.inventory[item_name] = current_qty - count
        return True, f"成功消耗 {item_name} x{count}，剩余 x{self.inventory[item_name]}"
