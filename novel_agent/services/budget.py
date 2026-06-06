"""Chapter cost budget estimation and smart downgrade services."""

import json
from pathlib import Path
import logging

logger = logging.getLogger("novel_agent.services.budget")


def get_scene_count(root_dir: Path, chapter_id: str) -> int:
    chapter_dir = root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    plan_path = chapter_dir / "plan.json"
    scene_count = 3
    if plan_path.exists():
        try:
            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            scene_count = len(plan_data.get("scenes", []))
        except Exception:
            pass
    return scene_count


def calculate_estimated_tokens(avg_in: float, avg_out: float, scene_count: int) -> tuple:
    est_calls = scene_count * 2 + 6
    est_in_tokens = int(avg_in * est_calls)
    est_out_tokens = int(avg_out * est_calls)
    est_total = est_in_tokens + est_out_tokens
    est_cost = (est_in_tokens / 1000) * 0.001 + (est_out_tokens / 1000) * 0.003
    return est_calls, est_in_tokens, est_out_tokens, est_total, est_cost


def estimate_and_budget_chapter_logic(
    chapter_id: str,
    root_dir: Path,
    avg_in: float,
    avg_out: float,
    max_tokens_per_chapter: int,
) -> tuple:
    """Calculate budget estimations and return if smart downgrade is required.
    
    Returns:
        (est_total, skip_style_edit)
    """
    scene_count = get_scene_count(root_dir, chapter_id)
    est_calls, est_in_tokens, est_out_tokens, est_total, est_cost = calculate_estimated_tokens(
        avg_in, avg_out, scene_count
    )

    logger.info("=== CHAPTER GENERATION BUDGET ESTIMATION ===")
    logger.info("Chapter: %s, Scene count: %d, Estimated LLM calls: %d", chapter_id, scene_count, est_calls)
    logger.info("Estimated Token consumption: %d (Input: %d, Output: %d)", est_total, est_in_tokens, est_out_tokens)
    logger.info("Estimated cost (DeepSeek Rate): %.4f CNY", est_cost)
    logger.info("============================================")

    skip_style_edit = False
    if max_tokens_per_chapter > 0 and est_total > max_tokens_per_chapter:
        logger.warning("Estimated Token %d exceeds max_tokens_per_chapter %d. Activating smart downgrade: skipping Style Editor.", est_total, max_tokens_per_chapter)
        skip_style_edit = True
    
    return est_total, skip_style_edit
