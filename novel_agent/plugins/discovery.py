import importlib.util
import sys
from importlib.metadata import entry_points
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

from novel_agent.logging_config import get_logger
from novel_agent.plugins.base import PluginBase
from novel_agent.plugins.manifest import find_manifest_path, load_manifest, ManifestError

logger = get_logger("plugins.discovery")


class PluginEntry:
    def __init__(self, name: str, load_fn: Callable[[], Type[PluginBase]], source: str, path: Optional[Path] = None):
        self.name = name
        self.load_fn = load_fn
        self.source = source  # "local", "entry_point", "config"
        self.path = path


class PluginDiscovery:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def discover_all(self) -> Dict[str, PluginEntry]:
        """Discovers all plugins from local directory, entry points, and returns them as a dict.

        Duplicates are resolved based on priority: local > entry_point.
        """
        discovered: Dict[str, PluginEntry] = {}

        try:
            for entry in self._scan_entry_points():
                discovered[entry.name] = entry
        except Exception as e:
            logger.error("Failed to scan entry points: %s", e)

        try:
            for entry in self._scan_local_dir():
                discovered[entry.name] = entry
        except Exception as e:
            logger.error("Failed to scan local plugins directory: %s", e)

        return discovered

    def _scan_local_dir(self) -> List[PluginEntry]:
        """Scans the local plugins/ directory for .py files or packages."""
        plugins_dir = self.root_dir / "plugins"
        if not plugins_dir.exists():
            return []

        entries: List[PluginEntry] = []
        for path in plugins_dir.iterdir():
            if path.name.startswith("_") or path.name.startswith("."):
                continue

            entry = None
            if path.is_dir() and find_manifest_path(path):
                entry = self._load_from_manifest_dir(path)
            elif path.is_file() and path.suffix == ".py":
                entry = self._load_from_single_file(path)
            elif path.is_dir() and (path / "__init__.py").exists():
                entry = self._load_from_package(path)

            if entry:
                entries.append(entry)

        return entries

    def _load_from_manifest_dir(self, path: Path) -> Optional[PluginEntry]:
        try:
            manifest = load_manifest(path)
        except ManifestError as exc:
            logger.warning("Invalid manifest in %s: %s", path, exc)
            return None
        plugin_id = manifest["id"]
        entry_spec = manifest["entry"]
        class_name = self._class_name_from_entry(entry_spec)
        module_path = self._module_path_for_entry(path, entry_spec)

        def load_fn() -> Type[PluginBase]:
            return self._import_plugin_class(path, module_path, plugin_id, class_name)

        return PluginEntry(name=plugin_id, load_fn=load_fn, source="local", path=path)

    @staticmethod
    def _class_name_from_entry(entry_spec: str) -> str:
        if entry_spec.startswith("plugin:"):
            return entry_spec.split(":", 1)[1].strip()
        if entry_spec.startswith("package:"):
            return entry_spec.rsplit(":", 1)[1].strip()
        raise ValueError(f"Unsupported entry: {entry_spec}")

    @staticmethod
    def _module_path_for_entry(path: Path, entry_spec: str) -> Path:
        if entry_spec.startswith("plugin:"):
            if (path / "plugin.py").is_file():
                return path / "plugin.py"
            return path / "__init__.py"
        if entry_spec.startswith("package:"):
            mod = entry_spec.split(":", 1)[1].rsplit(":", 1)[0].strip()
            rel = Path(*mod.split("."))
            candidate = path / f"{rel}.py"
            if candidate.is_file():
                return candidate
            return path / rel / "__init__.py"
        raise ValueError(f"Unsupported entry: {entry_spec}")

    def _import_plugin_class(
        self, plugin_root: Path, module_path: Path, plugin_id: str, class_name: str
    ) -> Type[PluginBase]:
        mod_name = f"novel_agent.plugins.local.{plugin_id}"
        spec = importlib.util.spec_from_file_location(mod_name, module_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load spec for {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(plugin_root))
        try:
            spec.loader.exec_module(module)
        finally:
            if str(plugin_root) in sys.path:
                sys.path.remove(str(plugin_root))
        plugin_class = getattr(module, class_name, None)
        if not plugin_class:
            raise AttributeError(f"Module {module_path.name} does not define {class_name}")
        if not issubclass(plugin_class, PluginBase):
            raise TypeError(f"{class_name} is not a subclass of PluginBase")
        return plugin_class

    def _load_from_single_file(self, path: Path) -> Optional[PluginEntry]:
        name = path.stem

        def load_fn() -> Type[PluginBase]:
            return self._import_plugin_class(path.parent, path, name, "PLUGIN_CLASS")

        return PluginEntry(name=name, load_fn=load_fn, source="local", path=path)

    def _load_from_package(self, path: Path) -> Optional[PluginEntry]:
        name = path.name

        def load_fn() -> Type[PluginBase]:
            init_path = path / "__init__.py"
            return self._import_plugin_class(path, init_path, name, "PLUGIN_CLASS")

        return PluginEntry(name=name, load_fn=load_fn, source="local", path=path)

    def _scan_entry_points(self) -> List[PluginEntry]:
        """Discovers plugins declared via pip entry_points."""
        entries: List[PluginEntry] = []
        try:
            try:
                eps = entry_points(group="novel_agent.plugins")
            except TypeError:
                all_eps = entry_points()
                if hasattr(all_eps, "select"):
                    eps = all_eps.select(group="novel_agent.plugins")
                else:
                    eps = all_eps.get("novel_agent.plugins", [])

            for ep in eps:
                def load_fn(entry_point=ep) -> Type[PluginBase]:
                    plugin_class = entry_point.load()
                    if not issubclass(plugin_class, PluginBase):
                        raise TypeError(f"Entry point {entry_point.name} is not a subclass of PluginBase")
                    return plugin_class

                entries.append(PluginEntry(name=ep.name, load_fn=load_fn, source="entry_point"))
        except Exception as e:
            logger.warning("Error reading entry points: %s", e)
        return entries