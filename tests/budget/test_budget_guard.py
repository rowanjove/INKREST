"""Unit tests for BudgetGuard cost estimation and limit enforcement."""

from novel_agent.budget.budget_guard import BudgetGuard


def test_budget_guard_limits():
    guard = BudgetGuard(daily_budget_cny=30.0, task_budget_cny=10.0)

    # Within limits: 1000 input, 500 output with deepseek-chat
    ok, msg, est = guard.check_pre_flight("deepseek-chat", 1000, 500)
    assert ok is True
    assert est < 1.0

    # Record usage
    guard.record_usage("deepseek-chat", 1000, 500)
    assert guard.get_today_spent_cny() > 0

    # Over per-task limit: 1M input with gpt-4o
    ok2, msg2, est2 = guard.check_pre_flight("gpt-4o", 100000, 50000)
    assert ok2 is False
    assert "超出单任务预算上限" in msg2

    # Batch estimation
    batch_info = guard.estimate_batch(
        num_chapters=20,
        avg_input_tokens=4000,
        avg_output_tokens=1500,
        model="deepseek-chat",
    )
    assert batch_info["num_chapters"] == 20
    assert batch_info["total_input_tokens"] == 80000
    assert batch_info["total_output_tokens"] == 30000
    assert batch_info["estimated_cost_cny"] < 5.0
    assert batch_info["is_within_daily_budget"] is True
