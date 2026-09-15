"""AI Cost Center and Budget Guard (Milestone E).

Tracks token expenditures, enforces daily and per-task budget limits,
and estimates batch production costs before execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.pricing import resolve_model_prices_usd, usd_to_cny


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class UsageRecord:
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_cny: float
    task_id: str = ""


class BudgetGuard:
    """Monitors AI token expenditure and prevents cost overruns."""

    def __init__(
        self,
        daily_budget_cny: float = 50.0,
        task_budget_cny: float = 15.0,
    ) -> None:
        self.daily_budget_cny = daily_budget_cny
        self.task_budget_cny = task_budget_cny
        self.records: List[UsageRecord] = []

    def calculate_cost_cny(self, model: str, input_tokens: int, output_tokens: int) -> float:
        in_usd, out_usd = resolve_model_prices_usd(model)
        cost_usd = (input_tokens / 1000.0) * in_usd + (output_tokens / 1000.0) * out_usd
        return round(usd_to_cny(cost_usd), 4)

    def get_today_spent_cny(self) -> float:
        prefix = today_str()
        return sum(
            r.cost_cny for r in self.records if r.timestamp.startswith(prefix)
        )

    def check_pre_flight(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> Tuple[bool, str, float]:
        """Verify estimated request cost against task and daily limits."""
        est_cost = self.calculate_cost_cny(model, estimated_input_tokens, estimated_output_tokens)

        # 1. Per-task budget
        if est_cost > self.task_budget_cny:
            return (
                False,
                f"预估单次任务费用 (¥{est_cost:.2f}) 超出单任务预算上限 (¥{self.task_budget_cny:.2f})",
                est_cost,
            )

        # 2. Daily budget
        today_spent = self.get_today_spent_cny()
        if today_spent + est_cost > self.daily_budget_cny:
            return (
                False,
                f"今日累计消费 (¥{today_spent:.2f}) 加上本次预估费用 (¥{est_cost:.2f}) 将超出每日预算上限 (¥{self.daily_budget_cny:.2f})",
                est_cost,
            )

        return True, "预算检验通过", est_cost

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_id: str = "",
    ) -> UsageRecord:
        cost = self.calculate_cost_cny(model, input_tokens, output_tokens)
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cny=cost,
            task_id=task_id,
        )
        self.records.append(record)
        return record

    def estimate_batch(
        self,
        num_chapters: int,
        avg_input_tokens: int,
        avg_output_tokens: int,
        model: str,
    ) -> Dict[str, Any]:
        """Estimate the total tokens and cost for a batch chapter production task."""
        total_input = num_chapters * avg_input_tokens
        total_output = num_chapters * avg_output_tokens
        cost_cny = self.calculate_cost_cny(model, total_input, total_output)

        return {
            "num_chapters": num_chapters,
            "model": model,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "estimated_cost_cny": cost_cny,
            "is_within_daily_budget": (self.get_today_spent_cny() + cost_cny) <= self.daily_budget_cny,
        }
