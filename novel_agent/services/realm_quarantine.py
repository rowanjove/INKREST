"""Realm Quarantine (世界域生命周期隔离).

Guards long serial web novels against old-world entity crowding and context pollution
when the protagonist ascends, migrates to a higher world, or switches macro-maps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class RealmSpec:
    realm_id: str
    name: str
    chapter_start: int
    chapter_end: int
    max_realm_tier: str = ""
    cross_realm_companions: List[str] = field(default_factory=list)

    def is_active_for_chapter(self, chapter_number: int) -> bool:
        return self.chapter_start <= chapter_number <= self.chapter_end


class RealmQuarantineManager:
    """Manages world realm progression and isolates archived world context."""

    def __init__(self, realms: Optional[Sequence[RealmSpec]] = None) -> None:
        self.realms: Dict[str, RealmSpec] = {}
        if realms:
            for r in realms:
                self.realms[r.realm_id] = r

    def register_realm(self, spec: RealmSpec) -> None:
        self.realms[spec.realm_id] = spec

    def get_active_realm(self, chapter_number: int) -> Optional[RealmSpec]:
        """Find the active realm covering the specified chapter number."""
        for r in self.realms.values():
            if r.is_active_for_chapter(chapter_number):
                return r
        return None

    def is_quarantined(
        self,
        entity_name: str,
        entity_origin_realm: str,
        current_realm_id: str,
    ) -> bool:
        """Check if an entity from an old world should be quarantined in the new world.
        
        Rules:
        - If entity origin matches current active realm, it is NOT quarantined.
        - If entity is registered in cross_realm_companions for the active realm, it is ALLOWED.
        - Otherwise, if it belongs to an archived older realm, it is QUARANTINED to prevent context clutter.
        """
        if not current_realm_id or entity_origin_realm == current_realm_id:
            return False

        active_spec = self.realms.get(current_realm_id)
        if active_spec:
            # 白名单检查：如果是跨界跟随角色（如灵宠、道侣），放行
            if entity_name in active_spec.cross_realm_companions:
                return False

        return True

    def filter_quarantined_items(
        self,
        items: Sequence[Dict[str, Any]],
        current_realm_id: str,
        entity_key: str = "name",
        origin_realm_key: str = "origin_realm",
    ) -> List[Dict[str, Any]]:
        """Filter a list of entity/character dictionaries, removing quarantined items."""
        if not current_realm_id:
            return list(items)

        active_spec = self.realms.get(current_realm_id)
        companions = set(active_spec.cross_realm_companions) if active_spec else set()

        allowed: List[Dict[str, Any]] = []
        for item in items:
            name = str(item.get(entity_key, "")).strip()
            origin = str(item.get(origin_realm_key, "")).strip()
            if not origin or origin == current_realm_id or name in companions:
                allowed.append(item)
            else:
                # 实体属于不同世界且非白名单伙伴，冷冻隔离
                continue

        return allowed


_PROTECTED_CHARACTER_IDS = frozenset({"protagonist", "主角"})
_CHAPTER_NUMBER_RE = re.compile(r"(\d+)")


def parse_chapter_number(chapter_id: Optional[str]) -> Optional[int]:
    if not chapter_id:
        return None
    match = _CHAPTER_NUMBER_RE.search(str(chapter_id))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def load_realm_specs(root_dir: Path) -> List[RealmSpec]:
    path = Path(root_dir) / "assets" / "realms.yaml"
    if not path.is_file():
        return []
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    raw_items = data.get("realms") if isinstance(data, dict) else data
    if not isinstance(raw_items, list):
        return []
    specs: List[RealmSpec] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        realm_id = str(item.get("realm_id") or "").strip()
        if not realm_id:
            continue
        try:
            chapter_start = int(item.get("chapter_start") or 0)
            chapter_end = int(item.get("chapter_end") or 0)
        except (TypeError, ValueError):
            continue
        companions = item.get("cross_realm_companions") or []
        if isinstance(companions, str):
            companions = [companions]
        specs.append(
            RealmSpec(
                realm_id=realm_id,
                name=str(item.get("name") or realm_id).strip(),
                chapter_start=chapter_start,
                chapter_end=chapter_end,
                max_realm_tier=str(item.get("max_realm_tier") or "").strip(),
                cross_realm_companions=[str(name).strip() for name in companions if str(name).strip()],
            )
        )
    return specs


def _load_character_cards(root_dir: Path) -> List[Dict[str, Any]]:
    path = Path(root_dir) / "assets" / "character_cards.yaml"
    if not path.is_file():
        return []
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    characters = data.get("characters") if isinstance(data, dict) else None
    if not isinstance(characters, list):
        return []
    return [item for item in characters if isinstance(item, dict)]


def _is_protected_character(card: Dict[str, Any]) -> bool:
    char_id = str(card.get("id") or "").strip()
    name = str(card.get("name") or "").strip()
    return char_id in _PROTECTED_CHARACTER_IDS or name in _PROTECTED_CHARACTER_IDS


def _active_realm_for_chapter(root_dir: Path, chapter_id: Optional[str]) -> Optional[RealmSpec]:
    chapter_number = parse_chapter_number(chapter_id)
    if chapter_number is None:
        return None
    manager = RealmQuarantineManager(load_realm_specs(root_dir))
    return manager.get_active_realm(chapter_number)


def _quarantined_roster(
    root_dir: Path,
    chapter_id: Optional[str],
) -> tuple[Optional[RealmSpec], List[str]]:
    active = _active_realm_for_chapter(root_dir, chapter_id)
    if active is None:
        return None, []
    manager = RealmQuarantineManager(load_realm_specs(root_dir))
    names: List[str] = []
    for card in _load_character_cards(root_dir):
        if _is_protected_character(card):
            continue
        name = str(card.get("name") or "").strip()
        origin = str(card.get("origin_realm") or "").strip()
        if not name or not origin:
            continue
        if manager.is_quarantined(name, origin, active.realm_id):
            names.append(name)
    return active, names


def audit_realm_quarantine(
    text: str,
    root_dir: Path,
    chapter_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Report-only: warn if archived-world names leak into the current realm chapter."""
    specs = load_realm_specs(root_dir)
    if not specs:
        return {
            "pass": True,
            "level": "none",
            "score": 100,
            "details": [],
            "metrics": {"skipped": "no_realms_config"},
        }
    active, quarantined = _quarantined_roster(root_dir, chapter_id)
    if active is None:
        return {
            "pass": True,
            "level": "none",
            "score": 100,
            "details": [],
            "metrics": {"skipped": "no_active_realm"},
        }
    leaked = [name for name in quarantined if name and name in (text or "")]
    details = [
        f"旧世界角色出现在当前世界域「{active.name}」：{name}"
        for name in leaked
    ]
    return {
        "pass": True,
        "level": "warning" if details else "none",
        "score": 80 if details else 100,
        "details": details,
        "metrics": {
            "active_realm": active.realm_id,
            "quarantined_count": len(quarantined),
            "leaked": leaked,
        },
    }


def build_realm_quarantine_hint(root_dir: Path, chapter_id: Optional[str] = None) -> str:
    """Short writer-facing hint. Empty when realms.yaml is absent or nothing is quarantined."""
    active, quarantined = _quarantined_roster(root_dir, chapter_id)
    if active is None or not quarantined:
        return ""
    return (
        f"【世界域隔离·仅提示】当前世界域为{active.name}。"
        f"以下旧世界角色默认不应出场（跨界白名单除外）：{'、'.join(quarantined)}"
    )
