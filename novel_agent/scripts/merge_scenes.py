from pathlib import Path


def merge_scene_texts(scene_dir: Path) -> str:
    scene_dir = Path(scene_dir)
    parts = []
    for path in sorted(scene_dir.glob("scene_*.txt")):
        content = path.read_text(encoding="utf-8").strip()
        if content:
            parts.append(content)
    return "\n\n".join(parts)

