import json
from pathlib import Path
from typing import Any, Dict

import yaml
from novel_agent.agents.base import PromptAgent
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger
from novel_agent.state.sqlite_store import SQLiteStateStore

logger = get_logger("agents.asset_compressor")


class AssetCompressorAgent(PromptAgent):
    """Compresses state files: archives closed threads, removes stale entries."""

    def __init__(self, llm, prompts=None):
        super().__init__("asset_compressor", llm)
        self.prompts = prompts

    def compress(self, state_summary: str) -> dict:
        template = self.prompts.load("asset_compressor") if self.prompts else ""
        prompt = (
            f"{template}\n\n"
            "以下是当前小说状态汇总，请输出压缩建议 JSON。\n\n"
            f"{state_summary}"
        ).strip()
        raw = self.run(prompt)
        try:
            return loads_json_object(raw)
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Failed to parse asset compressor output: %s", exc)
            return {"compressed": False, "archived_threads": [], "removed_events": []}


def compress_assets(root_dir: Path, llm, prompts=None) -> dict:
    """CLI entry point: read state from SQLite, compress, write back."""
    root_dir = Path(root_dir)
    store = SQLiteStateStore(root_dir)

    # Gather current state into a summary
    state = store.get_continuity_state()
    summary = json.dumps(state, ensure_ascii=False, indent=2)

    agent = AssetCompressorAgent(llm, prompts)
    result = agent.compress(summary)

    # Archive closed threads to file (for reference)
    archive_dir = root_dir / "state" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived = result.get("archived_threads", [])
    if archived:
        archive_path = archive_dir / "closed_threads.yaml"
        existing = []
        if archive_path.exists():
            existing = (yaml.safe_load(archive_path.read_text(encoding="utf-8")) or {}).get("threads", [])
        existing.extend(archived)
        archive_path.write_text(
            yaml.safe_dump({"threads": existing}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    removed_events = set(result.get("removed_events", []))
    events_path = root_dir / "state" / "events.yaml"
    if removed_events and events_path.exists():
        data = yaml.safe_load(events_path.read_text(encoding="utf-8")) or {}
        events = data.get("events", [])
        if isinstance(events, list):
            data["events"] = [
                event
                for event in events
                if not (isinstance(event, dict) and event.get("id") in removed_events)
            ]
            events_path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )

    return result
