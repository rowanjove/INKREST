"""Novel Agent Dashboard HTML generator."""

import html
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml
from novel_agent.state.sqlite_store import SQLiteStateStore

logger = logging.getLogger("novel_agent.dashboard")


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("Failed to read YAML %s: %s", path, exc)
        return {}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read JSON %s: %s", path, exc)
        return {}


def _legacy_chapters(root_dir: Path) -> List[Dict[str, Any]]:
    chapters_dir = root_dir / "workspace" / "chapters"
    rows: List[Dict[str, Any]] = []
    if not chapters_dir.exists():
        return rows
    for chapter_dir in sorted(chapters_dir.glob("chapter_*")):
        if not chapter_dir.is_dir():
            continue
        wordcount = _read_json(chapter_dir / "reports" / "wordcount.json")
        audit = _read_json(chapter_dir / "reports" / "audit.json")
        rows.append(
            {
                "id": chapter_dir.name,
                "word_count": " ".join(
                    str(part)
                    for part in (wordcount.get("count", ""), wordcount.get("status", ""))
                    if part != ""
                ),
                "risk_level": audit.get("risk_level", ""),
            }
        )
    return rows


def build_dashboard_html(root_dir: Path) -> str:
    """Build the dashboard HTML, gracefully degrading when data sources fail."""
    root_dir = Path(root_dir)
    state_dir = root_dir / "state"

    try:
        store = SQLiteStateStore(root_dir)
    except Exception as exc:
        logger.error("Failed to open SQLite state store: %s", exc)
        store = None

    # --- helper: safely resolve a list of rows ---
    def _safe_list(getter, fallback) -> List[Any]:
        if store is None:
            return fallback
        try:
            result = getter()
            return result or fallback
        except Exception as exc:
            logger.warning("Dashboard data fetch failed: %s", exc)
            return fallback

    # Chapter reports table
    chapters = _safe_list(store.get_chapters, _legacy_chapters(root_dir)) if store else _legacy_chapters(root_dir)
    chapter_rows = []
    for ch in chapters:
        chapter_rows.append(
            "<tr>"
            f"<td>{html.escape(str(ch.get('id', '')))}</td>"
            f"<td>{html.escape(str(ch.get('word_count', '')))}</td>"
            f"<td>{html.escape(str(ch.get('risk_level', '')))}</td>"
            "</tr>"
        )
    chapter_table = "\n".join(chapter_rows) or "<tr><td colspan=\"3\">暂无章节</td></tr>"

    # Foreshadows table
    foreshadows = _safe_list(store.list_foreshadows, _read_yaml(state_dir / "foreshadows.yaml").get("foreshadows", [])) if store else _read_yaml(state_dir / "foreshadows.yaml").get("foreshadows", [])
    foreshadow_rows = []
    for f in foreshadows:
        status = f.get("status", "")
        status_class = "open" if status == "open" else "resolved" if status == "resolved" else ""
        foreshadow_rows.append(
            "<tr>"
            f"<td>{html.escape(str(f.get('id', '')))}</td>"
            f"<td>{html.escape(f.get('title', ''))}</td>"
            f"<td class=\"status-{status_class}\">{html.escape(status)}</td>"
            f"<td>{html.escape(f.get('description', ''))}</td>"
            "</tr>"
        )
    foreshadow_table = "\n".join(foreshadow_rows) or "<tr><td colspan=\"4\">暂无伏笔</td></tr>"

    # Hooks table
    hooks = _safe_list(store.list_hooks, _read_yaml(state_dir / "hooks.yaml").get("hooks", [])) if store else _read_yaml(state_dir / "hooks.yaml").get("hooks", [])
    hook_rows = []
    for h in hooks:
        hook_rows.append(
            "<tr>"
            f"<td>{html.escape(str(h.get('id', '')))}</td>"
            f"<td>{html.escape(h.get('title', ''))}</td>"
            f"<td>{html.escape(h.get('status', ''))}</td>"
            f"<td>{html.escape(h.get('description', ''))}</td>"
            "</tr>"
        )
    hook_table = "\n".join(hook_rows) or "<tr><td colspan=\"4\">暂无钩子</td></tr>"

    # Character state table
    characters = _safe_list(store.list_characters, _read_yaml(state_dir / "continuity_state.yaml").get("characters", {})) if store else _read_yaml(state_dir / "continuity_state.yaml").get("characters", {})
    char_rows = []
    for char_id, char_data in characters.items():
        if isinstance(char_data, dict):
            char_rows.append(
                "<tr>"
                f"<td>{html.escape(str(char_id))}</td>"
                f"<td>{html.escape(char_data.get('location', ''))}</td>"
                f"<td>{html.escape(char_data.get('emotion', ''))}</td>"
                f"<td>{html.escape(char_data.get('physical_state', ''))}</td>"
                "</tr>"
            )
    char_table = "\n".join(char_rows) or "<tr><td colspan=\"4\">暂无人物状态</td></tr>"

    # Events timeline
    events = _safe_list(lambda: store.list_events(limit=20), _read_yaml(state_dir / "events.yaml").get("events", [])) if store else _read_yaml(state_dir / "events.yaml").get("events", [])
    event_rows = []
    for e in events:
        event_rows.append(
            "<tr>"
            f"<td>{html.escape(str(e.get('id', '')))}</td>"
            f"<td>{html.escape(str(e.get('summary', '')))}</td>"
            "</tr>"
        )
    event_table = "\n".join(event_rows) or "<tr><td colspan=\"2\">暂无事件</td></tr>"

    # Objects table
    objects = _safe_list(store.list_objects, _read_yaml(state_dir / "objects.yaml").get("objects", [])) if store else _read_yaml(state_dir / "objects.yaml").get("objects", [])
    object_rows = []
    for o in objects:
        object_rows.append(
            "<tr>"
            f"<td>{html.escape(str(o.get('id', '')))}</td>"
            f"<td>{html.escape(o.get('name', ''))}</td>"
            f"<td>{html.escape(o.get('holder', ''))}</td>"
            f"<td>{html.escape(o.get('status', ''))}</td>"
            "</tr>"
        )
    object_table = "\n".join(object_rows) or "<tr><td colspan=\"4\">暂无道具</td></tr>"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Novel Agent Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #1f2937; background: #f9fafb; }}
    h1 {{ color: #111827; }}
    h2 {{ color: #374151; margin-top: 32px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px 12px; text-align: left; }}
    th {{ background: #f3f4f6; font-weight: 600; }}
    tr:hover {{ background: #f9fafb; }}
    .status-open {{ color: #dc2626; font-weight: 600; }}
    .status-resolved {{ color: #16a34a; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>Novel Agent Dashboard</h1>

  <h2>章节报告</h2>
  <table>
    <thead>
      <tr><th>章节</th><th>字数</th><th>风险等级</th></tr>
    </thead>
    <tbody>
      {chapter_table}
    </tbody>
  </table>

  <div class="grid">
    <div>
      <h2>伏笔状态</h2>
      <table>
        <thead><tr><th>ID</th><th>标题</th><th>状态</th><th>描述</th></tr></thead>
        <tbody>{foreshadow_table}</tbody>
      </table>
    </div>

    <div>
      <h2>钩子状态</h2>
      <table>
        <thead><tr><th>ID</th><th>标题</th><th>状态</th><th>描述</th></tr></thead>
        <tbody>{hook_table}</tbody>
      </table>
    </div>
  </div>

  <h2>人物状态</h2>
  <table>
    <thead><tr><th>人物</th><th>位置</th><th>情绪</th><th>身体状态</th></tr></thead>
    <tbody>{char_table}</tbody>
  </table>

  <h2>道具归属</h2>
  <table>
    <thead><tr><th>ID</th><th>名称</th><th>持有者</th><th>状态</th></tr></thead>
    <tbody>{object_table}</tbody>
  </table>

  <h2>事件时间线（最近 20 条）</h2>
  <table>
    <thead><tr><th>ID</th><th>摘要</th></tr></thead>
    <tbody>{event_table}</tbody>
  </table>
</body>
</html>
"""


def write_dashboard(root_dir: Path) -> Path:
    """Write dashboard HTML, creating directory if needed.

    Raises OSError only when the filesystem is truly unusable.
    """
    root_dir = Path(root_dir)
    dashboard_dir = root_dir / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    path = dashboard_dir / "index.html"
    try:
        path.write_text(build_dashboard_html(root_dir), encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to write dashboard: %s", exc)
        raise
    return path
