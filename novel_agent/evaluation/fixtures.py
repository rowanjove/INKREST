"""Small deterministic synthetic fixtures for consistency regression tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .taxonomy import CONSISTENCY_TAXONOMY, ConsistencyCase, VARIANTS, iter_taxonomy, normalise_case


def _text(category: str, subtype: str, variant: str) -> tuple[dict[str, Any], ...]:
    base = f"林舟记录{category}-{subtype}：灯塔钥匙在北门，数量为一。"
    if variant == "single_point_mutation":
        return ({"chapter_id": "005", "text": base}, {"chapter_id": "006", "text": base.replace("北门", "南门")})
    if variant == "cross_chapter_mutation":
        return ({"chapter_id": "005", "text": base}, {"chapter_id": "100", "text": base.replace("一", "两")})
    if variant == "false_positive":
        return ({"chapter_id": "005", "text": base}, {"chapter_id": "006", "text": "另一条时间线中，南门有两把备用钥匙。"})
    return ({"chapter_id": "005", "text": base}, {"chapter_id": "006", "text": base})


def build_consistency_fixtures() -> list[ConsistencyCase]:
    cases: list[ConsistencyCase] = []
    for category, subtype in iter_taxonomy():
        for variant in VARIANTS:
            expected = "fail" if variant in {"single_point_mutation", "cross_chapter_mutation"} else "pass"
            evidence = () if variant in {"normal", "false_positive"} else ({"chapter_id": "006" if variant == "single_point_mutation" else "100", "field": subtype, "reason": "synthetic mutation"},)
            cases.append(ConsistencyCase(
                case_id=f"{category}:{subtype}:{variant}",
                category=category,
                subtype=subtype,
                variant=variant,
                chapters=_text(category, subtype, variant),
                query=f"{category} {subtype}",
                expected_label=expected,
                expected_evidence=evidence,
                notes="自建中文最小样本；反例使用显式另一条时间线以避免误报。",
            ))
    return cases


def load_fixture_file(path: Path) -> list[ConsistencyCase]:
    result: list[ConsistencyCase] = []
    source = Path(path)
    if not source.is_file():
        return result
    for index, line in enumerate(source.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        value = json.loads(line)
        if isinstance(value, Mapping):
            result.append(normalise_case(value, index))
    return result


def save_fixture_file(path: Path, cases: Iterable[ConsistencyCase]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(json.dumps(case.to_dict(), ensure_ascii=False) for case in cases) + "\n", encoding="utf-8")
    return target


__all__ = ["build_consistency_fixtures", "load_fixture_file", "save_fixture_file"]
