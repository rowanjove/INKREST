from pathlib import Path


from typing import Iterable, Optional


def merge_scene_texts(scene_dir: Path, scene_ids: Optional[Iterable[str]] = None) -> str:
    scene_dir = Path(scene_dir)
    if scene_ids is None:
        paths = sorted(scene_dir.glob("scene_*.txt"))
    else:
        paths = [scene_dir / f"scene_{scene_id}.txt" for scene_id in scene_ids]
    parts = []
    for path in paths:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8").strip()
        if content:
            parts.append(content)
    return "\n\n".join(parts)

