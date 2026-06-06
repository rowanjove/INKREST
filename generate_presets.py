"""Generate composable preset components (channels, themes, mechanisms, cool_points).

Replaces the old flat preset system with a layered combinatorial system.
Loads preset components from presets/presets_source.json and regenerates
all individual component files under presets/.
"""

import json
from pathlib import Path

PRESETS_DIR = Path(__file__).parent / "presets"


def generate_component_files(base_dir: Path, component_type: str, components: list):
    """Generate .json and .md files for a component type."""
    comp_dir = base_dir / component_type
    comp_dir.mkdir(parents=True, exist_ok=True)

    for comp in components:
        meta = comp["meta"]
        comp_id = meta["id"]

        # Write meta.json
        (comp_dir / f"{comp_id}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Write guide.md
        (comp_dir / f"{comp_id}.md").write_text(
            comp["guide"].strip(), encoding="utf-8"
        )

    print(f"  Generated {len(components)} {component_type} files")


def main():
    print("Generating composable preset components from presets_source.json...")
    source_path = PRESETS_DIR / "presets_source.json"
    if not source_path.exists():
        print(f"Error: Source presets JSON not found at {source_path}")
        return

    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Failed to read presets source data: {exc}")
        return

    channels = data.get("CHANNELS", [])
    themes = data.get("THEMES", [])
    mechanisms = data.get("MECHANISMS", [])
    cool_points = data.get("COOL_POINTS", [])

    generate_component_files(PRESETS_DIR, "channels", channels)
    generate_component_files(PRESETS_DIR, "themes", themes)
    generate_component_files(PRESETS_DIR, "mechanisms", mechanisms)
    generate_component_files(PRESETS_DIR, "cool_points", cool_points)

    total = len(channels) + len(themes) + len(mechanisms) + len(cool_points)
    print(f"\nTotal: {total} components generated")
    print(f"  Channels: {len(channels)}")
    print(f"  Themes: {len(themes)}")
    print(f"  Mechanisms: {len(mechanisms)}")
    print(f"  Cool Points: {len(cool_points)}")


if __name__ == "__main__":
    main()
