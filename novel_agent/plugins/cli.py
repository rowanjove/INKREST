"""CLI handlers for plugin development suite (init, validate, pack, test)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
from typing import Any, Dict, Optional

from novel_agent.plugins.manifest import load_manifest, validate_manifest, ManifestError
from novel_agent.plugins.installer import inspect_plugin_zip
from novel_agent.plugins.testing import PluginTestHost
from novel_agent.version import APP_VERSION, PLUGIN_API_VERSION, PLUGIN_MANIFEST_SCHEMA_VERSION


def plugin_init(name: str, ptype: str = "pipeline_hook", dest_dir: Optional[Path] = None) -> Path:
    """Scaffold a new Inkrest plugin."""
    target_dir = (dest_dir or Path(".")) / name
    if target_dir.exists():
        raise FileExistsError(f"Target directory already exists: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "$schema_version": PLUGIN_MANIFEST_SCHEMA_VERSION,
        "id": name,
        "name": name,
        "display_name": name.replace("-", " ").replace("_", " ").title(),
        "version": "0.1.0",
        "description": "A novel agent plugin created with Inkrest CLI",
        "author": "Inkrest Developer",
        "plugin_type": ptype,
        "entry": "plugin:PluginEntry",
        "engines": {
            "inkrest": f">={APP_VERSION}",
            "plugin_api": f">={PLUGIN_API_VERSION}",
        },
        "capabilities": ["project_read"],
        "activation_events": ["*"] if ptype != "command" else [f"onCommand:{name}.run"],
        "contributes": {
            "commands": [
                {
                    "id": f"{name}.run",
                    "title": f"Run {name}",
                    "category": "Tools",
                }
            ] if ptype == "command" else [],
            "pipeline_hooks": [
                {
                    "name": "before_chapter_generation",
                    "stage": "pre_generate",
                    "priority": 100,
                }
            ] if ptype == "pipeline_hook" else [],
            "navigation": [],
            "views": [],
        },
    }

    (target_dir / "inkrest.plugin.json").write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if ptype == "pipeline_hook":
        code = '''from novel_agent.plugins.base import PipelineHookPlugin, PluginMeta, PluginType
from novel_agent.plugins.hooks import hookimpl

class PluginEntry(PipelineHookPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="{name}",
            display_name="{display_name}",
            version="0.1.0",
            plugin_type=PluginType.PIPELINE_HOOK,
            description="Generated plugin",
        )

    @hookimpl
    def before_chapter_generation(self, chapter_outline: dict) -> dict:
        # Hook implementation
        return chapter_outline

PLUGIN_CLASS = PluginEntry
'''.format(name=name, display_name=manifest_data["display_name"])
    elif ptype == "command":
        code = '''from novel_agent.plugins.base import CommandPlugin, CommandSpec, PluginMeta, PluginType

class PluginEntry(CommandPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="{name}",
            display_name="{display_name}",
            version="0.1.0",
            plugin_type=PluginType.COMMAND,
        )

    def get_commands(self) -> list[CommandSpec]:
        return [
            CommandSpec(
                name="{name}.run",
                description="Run {name}",
            )
        ]

    def execute(self, command: str, args: dict) -> dict:
        return {{"status": "ok", "plugin": "{name}", "command": command}}

PLUGIN_CLASS = PluginEntry
'''.format(name=name, display_name=manifest_data["display_name"])
    else:
        code = '''from novel_agent.plugins.base import BasePlugin, PluginMeta, PluginType

class PluginEntry(BasePlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="{name}",
            display_name="{display_name}",
            version="0.1.0",
            plugin_type=PluginType.WEB_EXTENSION,
        )

PLUGIN_CLASS = PluginEntry
'''.format(name=name, display_name=manifest_data["display_name"])

    (target_dir / "plugin.py").write_text(code, encoding="utf-8")

    readme = f"""# {manifest_data['display_name']}

{manifest_data['description']}

## Development

Run plugin tests:
```bash
python cli.py plugin test {target_dir}
```

Package for distribution:
```bash
python cli.py plugin pack {target_dir}
```
"""
    (target_dir / "README.md").write_text(readme, encoding="utf-8")
    return target_dir


def plugin_validate(target_path: Path) -> Dict[str, Any]:
    """Validate a plugin directory or zip archive."""
    if not target_path.exists():
        raise FileNotFoundError(f"Target not found: {target_path}")

    if target_path.is_file() and target_path.suffix.lower() == ".zip":
        with open(target_path, "rb") as f:
            data = f.read()
        manifest = inspect_plugin_zip(data)
        return {"status": "valid", "type": "zip", "manifest": manifest}

    if target_path.is_dir():
        manifest = load_manifest(target_path)
        return {"status": "valid", "type": "directory", "manifest": manifest}

    raise ValueError(f"Invalid plugin target: {target_path}")


def plugin_pack(source_dir: Path, output_zip: Optional[Path] = None) -> Path:
    """Package a plugin directory into a distributable zip archive."""
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source is not a directory: {source_dir}")

    # Validate first
    manifest = load_manifest(source_dir)
    plugin_id = manifest["id"]
    version = manifest["version"]

    target_zip = output_zip or (source_dir.parent / f"{plugin_id}-{version}.zip")
    if target_zip.exists():
        target_zip.unlink()

    ignore_patterns = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
    }

    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_patterns and not d.startswith(".")]
            for f in files:
                if f.endswith((".pyc", ".pyo")) or f in ignore_patterns:
                    continue
                file_path = Path(root) / f
                arcname = file_path.relative_to(source_dir)
                zf.write(file_path, arcname)

    return target_zip


def plugin_test(plugin_dir: Path) -> Dict[str, Any]:
    """Run basic contract validation on a plugin directory."""
    manifest = load_manifest(plugin_dir)
    entry_str = manifest.get("entry", "plugin:PLUGIN_CLASS")
    module_name, _, class_name = entry_str.partition(":")
    if not class_name:
        class_name = "PLUGIN_CLASS"

    plugin_py = plugin_dir / f"{module_name}.py"
    if not plugin_py.is_file():
        raise FileNotFoundError(f"Entry script {plugin_py} not found")

    spec = importlib.util.spec_from_file_location(f"dynamic_test_{manifest['id']}", plugin_py)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from {plugin_py}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cls = getattr(mod, class_name, None)
    if not cls:
        raise AttributeError(f"Class '{class_name}' not found in {plugin_py}")

    instance = cls()
    meta = instance.get_meta()
    if meta.name != manifest["id"]:
        raise ValueError(f"Metadata name '{meta.name}' does not match manifest id '{manifest['id']}'")

    host = PluginTestHost(plugin_dir)
    ctx = host.create_context(manifest["id"], manifest.get("capabilities", []))
    if hasattr(instance, "activate"):
        instance.activate(ctx)

    return {
        "status": "passed",
        "plugin_id": manifest["id"],
        "version": meta.version,
        "entry_class": class_name,
    }
