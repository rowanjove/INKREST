"""Example exporter plugin — TXT with custom header/footer hook."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from novel_agent.exporters.txt_exporter import export_txt
from novel_agent.plugins.base import ExporterPlugin, PluginContext, PluginMeta, PluginType


class TxtExportHookPlugin(ExporterPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="txt-export-hook",
            display_name="TXT 导出钩子（示例）",
            description="演示导出插件：在标准 TXT 前后追加元信息头尾。",
            plugin_type=PluginType.EXPORTER,
            tags=["example", "export"],
        )

    def on_activate(self, context: PluginContext) -> None:
        self._ctx = context

    def get_format(self) -> str:
        return "txt_hook"

    def export(
        self,
        root_dir: Path,
        output_path: Path,
        chapter_ids: Optional[List[str]] = None,
        title: str = "",
        **kwargs,
    ) -> Path:
        tmp = output_path.with_suffix(".body.txt")
        export_txt(root_dir, tmp, chapter_ids=chapter_ids)
        body = tmp.read_text(encoding="utf-8") if tmp.exists() else ""
        if tmp.exists():
            tmp.unlink()
        header = f"# {title or '未命名小说'}\n# 导出插件示例 · txt_export_hook\n\n"
        footer = "\n\n---\n# 栖墨 INKREST · 示例导出钩子\n"
        output_path.write_text(header + body + footer, encoding="utf-8")
        return output_path


PLUGIN_CLASS = TxtExportHookPlugin