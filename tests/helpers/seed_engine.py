"""Seed config/models.json so novel_run_guard treats daily slot as usable."""

from __future__ import annotations

import json
from pathlib import Path


def seed_usable_daily_model(
    root: Path,
    *,
    model_id: str = "test-daily",
    provider: str = "openai",
    model_name: str = "gpt-test",
) -> None:
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    model_id: {
                        "name": model_id,
                        "provider": provider,
                        "model": model_name,
                    }
                },
                "slots": {"daily": model_id, "reasoning": model_id, "backup": []},
                "slots_version": 1,
                "defaults_seeded": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )