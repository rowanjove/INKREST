"""Safely remove unregistered project folders and explicit runtime roots."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

CONFIRMATION = "CLEAN V2 RUNTIME"
RUNTIME_ROOTS = ("data", "state", "workspace", "logs")


class UnsafeCleanupTarget(RuntimeError):
    pass


@dataclass
class CleanupReport:
    root: str
    execute: bool
    orphan_projects: list[str]
    runtime_roots: list[str]
    registered_projects: list[str]


def _direct_child(parent: Path, child: Path) -> Path:
    if child.is_symlink():
        raise UnsafeCleanupTarget(f"Refusing symbolic link: {child}")
    resolved_parent = parent.resolve(strict=True)
    resolved_child = child.resolve(strict=True)
    if resolved_child.parent != resolved_parent:
        raise UnsafeCleanupTarget(f"Target is not a direct child of {parent}: {child}")
    return resolved_child


def _registered_ids(root: Path) -> set[str]:
    registry_path = root / "projects.json"
    if not registry_path.is_file():
        return set()
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    projects = data.get("projects", {})
    if not isinstance(projects, dict):
        raise UnsafeCleanupTarget("projects.json has an invalid projects object")
    return {str(project_id) for project_id in projects}


def cleanup_root(
    root: Path,
    *,
    execute: bool = False,
    remove_runtime_roots: bool = False,
) -> CleanupReport:
    root = Path(root).resolve(strict=True)
    registered = _registered_ids(root)
    orphan_projects: list[str] = []
    runtime_roots: list[str] = []

    projects_root = root / "projects"
    if projects_root.exists():
        if projects_root.is_symlink() or not projects_root.is_dir():
            raise UnsafeCleanupTarget(f"Unsafe projects root: {projects_root}")
        for child in sorted(projects_root.iterdir(), key=lambda item: item.name):
            if not child.is_dir() or child.name in registered:
                continue
            target = _direct_child(projects_root, child)
            orphan_projects.append(child.name)
            if execute:
                shutil.rmtree(target)

    if remove_runtime_roots:
        for name in RUNTIME_ROOTS:
            child = root / name
            if not child.exists():
                continue
            target = _direct_child(root, child)
            runtime_roots.append(name)
            if execute:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

    return CleanupReport(
        root=str(root),
        execute=execute,
        orphan_projects=orphan_projects,
        runtime_roots=runtime_roots,
        registered_projects=sorted(registered),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--remove-runtime-roots", action="store_true")
    parser.add_argument("--confirmation", default="")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.execute and args.confirmation != CONFIRMATION:
        raise SystemExit(f"--confirmation must exactly equal: {CONFIRMATION}")
    reports = [
        cleanup_root(
            root,
            execute=args.execute,
            remove_runtime_roots=args.remove_runtime_roots,
        )
        for root in args.roots
    ]
    print(json.dumps([asdict(report) for report in reports], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
