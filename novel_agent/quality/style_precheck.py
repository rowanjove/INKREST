"""Shared style / anti-AI rule checks with optional report cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from novel_agent.quality.style_rules import check_ai_style, check_anti_ai_flavor, load_style_rules_config

PRECHECK_FILENAME = "style_precheck.json"


def text_fingerprint(text: str) -> str:
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()[:24]


def compute_style_rule_checks(
    text: str,
    root_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if root_dir:
        try:
            config = load_style_rules_config(Path(root_dir))
        except Exception:
            config = {}
    return {
        "fingerprint": text_fingerprint(text),
        "style": check_ai_style(text, config),
        "anti_ai_flavor": check_anti_ai_flavor(text, config),
    }


def write_style_precheck_cache(
    reports_dir: Path,
    text: str,
    root_dir: Optional[Path] = None,
    *,
    checks: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    if checks is None:
        checks = compute_style_rule_checks(text, root_dir)
    elif checks.get("fingerprint") != text_fingerprint(text):
        checks = compute_style_rule_checks(text, root_dir)
    doc = {
        "fingerprint": checks["fingerprint"],
        "checks": {
            "style": checks["style"],
            "anti_ai_flavor": checks["anti_ai_flavor"],
        },
    }
    path = reports_dir / PRECHECK_FILENAME
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def load_style_precheck_cache(
    reports_dir: Path,
    text: str,
) -> Optional[Dict[str, Dict[str, Any]]]:
    path = Path(reports_dir) / PRECHECK_FILENAME
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if doc.get("fingerprint") != text_fingerprint(text):
        return None
    checks = doc.get("checks")
    if not isinstance(checks, dict):
        return None
    return checks