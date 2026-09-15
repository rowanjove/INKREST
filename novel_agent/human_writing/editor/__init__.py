"""Editor submodule for Human Writing Engine: patch planning and execution."""

from novel_agent.human_writing.editor.patch_planner import create_patch_plan
from novel_agent.human_writing.editor.patch_runner import run_patch

__all__ = ["create_patch_plan", "run_patch"]
