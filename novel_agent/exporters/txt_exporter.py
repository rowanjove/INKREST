"""Plain text exporter — concatenates chapter final texts."""

from pathlib import Path
from typing import List, Optional

from novel_agent.exporters.chapter_selection import filter_chapter_dirs
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.txt")


def export_txt(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[List[str]] = None,
    include_title: bool = True,
) -> Path:
    """Export chapters as a single plain text file.

    Args:
        root_dir: Project root directory.
        output_path: Where to write the .txt file.
        chapter_ids: Specific chapter IDs to export. None = all chapters.
        include_title: Whether to include chapter titles as headers.

    Returns:
        Path to the generated file.
    """
    chapters_dir = root_dir / "workspace" / "chapters"
    if not chapters_dir.exists():
        raise FileNotFoundError(f"Chapters directory not found: {chapters_dir}")

    chapter_dirs = filter_chapter_dirs(sorted(chapters_dir.glob("chapter_*")), chapter_ids)

    parts: list[str] = []
    for ch_dir in chapter_dirs:
        final_path = ch_dir / "chapter_final.txt"
        if not final_path.exists():
            logger.warning("Skipping %s: no chapter_final.txt", ch_dir.name)
            continue

        text = final_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        chapter_id = ch_dir.name.replace("chapter_", "")
        if include_title:
            plan_path = ch_dir / "plan.json"
            title = ""
            if plan_path.exists():
                import json
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    title = plan.get("chapter_title", "")
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Failed to load chapter plan from %s: %s", plan_path, exc)
            header = f"第 {chapter_id} 章"
            if title:
                header += f"  {title}"
            parts.append(f"{'=' * 40}\n{header}\n{'=' * 40}\n\n{text}")
        else:
            parts.append(text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not parts:
        raise ValueError("No chapters found to export")
    content = "\n\n\n".join(parts)
    output_path.write_text(content, encoding="utf-8")
    logger.info("Exported %d chapters to %s", len(parts), output_path)
    return output_path
