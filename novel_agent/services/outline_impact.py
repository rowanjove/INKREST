"""Deterministic outline diff and propagation impact classification."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


_CANON_KEYS = {"death", "identity", "secret", "artifact", "injury", "location"}


def analyze_outline_impact(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    written_chapters: Sequence[str] = (),
    canon_events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    changed_keys = sorted(
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    )
    changed_canon = sorted(key for key in changed_keys if key in _CANON_KEYS)
    written = {str(item) for item in written_chapters}
    affected_chapters = sorted(
        {
            str(event.get("chapter_id"))
            for event in canon_events
            if str(event.get("chapter_id") or "") in written
            and any(str(key) in str(event) for key in changed_canon)
        }
    )
    if changed_canon and affected_chapters:
        impact = "invalidates_canon"
    elif written and changed_keys:
        impact = "replan_pending"
    else:
        impact = "future_only"
    return {
        "impact": impact,
        "changed_keys": changed_keys,
        "changed_canon_keys": changed_canon,
        "affected_written_chapters": affected_chapters,
        "requires_confirmation": impact in {"replan_pending", "invalidates_canon"},
    }
