"""Migrate YAML state files to SQLite."""

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from novel_agent.state.sqlite_store import SQLiteStateStore


def migrate_yaml_to_sqlite(root_dir: Path) -> Dict[str, int]:
    root_dir = Path(root_dir)
    state_dir = root_dir / "state"
    store = SQLiteStateStore(root_dir)
    counts = {"events": 0, "objects": 0, "threads": 0, "characters": 0,
              "timeline_nodes": 0, "timeline_edges": 0, "foreshadows": 0, "hooks": 0}

    events = _read_yaml_list(state_dir / "events.yaml", "events")
    objects = _read_yaml_list(state_dir / "objects.yaml", "objects")
    threads = _read_yaml_list(state_dir / "threads.yaml", "threads")
    timeline_nodes = _read_yaml_list(state_dir / "timeline_nodes.yaml", "timeline_nodes")
    timeline_edges = _read_yaml_list(state_dir / "timeline_edges.yaml", "timeline_edges")
    foreshadows = _read_yaml_list(state_dir / "foreshadows.yaml", "foreshadows")
    hooks = _read_yaml_list(state_dir / "hooks.yaml", "hooks")
    cont = _read_yaml(state_dir / "continuity_state.yaml")
    characters = cont.get("characters", {})

    update = {
        "events": events,
        "objects": objects,
        "threads": threads,
        "timeline_nodes": timeline_nodes,
        "timeline_edges": timeline_edges,
        "foreshadows": foreshadows,
        "hooks": hooks,
        "characters": characters,
    }

    store.sync_state_update("migrate", update)

    counts["events"] = len(events)
    counts["objects"] = len(objects)
    counts["threads"] = len(threads)
    counts["characters"] = len(characters)
    counts["timeline_nodes"] = len(timeline_nodes)
    counts["timeline_edges"] = len(timeline_edges)
    counts["foreshadows"] = len(foreshadows)
    counts["hooks"] = len(hooks)

    return counts


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_yaml_list(path: Path, key: str) -> list:
    data = _read_yaml(path)
    items = data.get(key, [])
    return items if isinstance(items, list) else []


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    result = migrate_yaml_to_sqlite(root)
    print(json.dumps(result, indent=2))
