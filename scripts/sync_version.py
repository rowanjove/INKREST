#!/usr/bin/env python3
"""Sync root VERSION into frontend package.json and FastAPI app metadata."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
PACKAGE_JSON = ROOT / "web" / "frontend" / "package.json"
APP_PY = ROOT / "web" / "app.py"


def read_version() -> str:
    if not VERSION_FILE.is_file():
        raise SystemExit(f"Missing version file: {VERSION_FILE}")
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Invalid VERSION format: {version!r}")
    return version


def sync_package_json(version: str) -> None:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    data["version"] = version
    PACKAGE_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_app_py(version: str) -> None:
    text = APP_PY.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'FastAPI\(title="Novel Agent API", version="[^"]+"',
        f'FastAPI(title="Novel Agent API", version="{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit("Could not update FastAPI version in web/app.py")
    APP_PY.write_text(updated, encoding="utf-8")


def main() -> int:
    version = read_version()
    sync_package_json(version)
    sync_app_py(version)
    print(f"Synced version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())