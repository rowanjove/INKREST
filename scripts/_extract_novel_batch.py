"""One-off: extract novel batch methods from orchestrator.py."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "novel_agent/orchestrator.py").read_text(encoding="utf-8")
start = src.index("    async def _run_chapter_briefs")
end = src.index("    def _auto_compress_assets")
block = src[start:end]
block = block.replace(
    "    async def _run_chapter_briefs(\n        self,",
    "async def run_chapter_briefs(\n    orch: \"NovelOrchestrator\",",
)
block = block.replace("    async def arun_arcs(\n        self,", "async def arun_arcs(\n    orch,")
block = block.replace(
    "    async def arun_novel_continue(\n        self,", "async def arun_novel_continue(\n    orch,"
)
block = block.replace("    async def arun_novel(\n        self,", "async def arun_novel(\n    orch,")
block = re.sub(r"\bself\.", "orch.", block)
# Method bodies were indented 8 spaces; module-level uses 4.
lines = []
for line in block.splitlines():
    if line.startswith("        "):
        lines.append(line[4:])
    else:
        lines.append(line)
block = "\n".join(lines) + "\n"
block = block.replace("await orch._run_chapter_briefs(", "await run_chapter_briefs(orch, ")
block = block.replace("return await orch.arun_arcs(", "return await arun_arcs(orch, ")
header = '''"""Multi-chapter and full-novel async orchestration (extracted from orchestrator)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from novel_agent.control.runtime_policy import (
    format_scale_profile_for_chief_editor,
    resolve_runtime_policy,
)
from novel_agent.control.scale_profile import resolve_scale_profile
from novel_agent.logging_config import get_logger
from novel_agent.orchestrator_types import ChapterResult
from novel_agent.progress import emit_error, emit_log, emit_progress

if TYPE_CHECKING:
    from novel_agent.orchestrator import NovelOrchestrator

logger = get_logger("orchestrator.novel_batch")

'''
out = ROOT / "novel_agent/orchestrator_novel_batch.py"
out.write_text(header + block, encoding="utf-8")
print("wrote", out, "lines", (header + block).count("\n"))