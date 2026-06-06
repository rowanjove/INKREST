from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "novel_agent/phases/audit.py"
src = path.read_text(encoding="utf-8")
start = src.index("    def _run_rewrite_loop(")
end = src.index("    def _run_continuity_and_summary(")
path.write_text(src[:start] + src[end:], encoding="utf-8")
print("removed sync rewrite block")