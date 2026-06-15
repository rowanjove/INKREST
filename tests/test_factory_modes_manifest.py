import json
import unittest
from pathlib import Path

from web.factory_modes import (
    DEFAULT_FACTORY_MODE,
    FACTORY_MODE_IDS,
    FACTORY_MODE_LABELS,
    factory_mode_profiles,
)


class FactoryModesManifestTests(unittest.TestCase):
    def test_python_manifest_matches_frontend_json(self):
        root = Path(__file__).resolve().parents[1]
        backend_path = root / "web" / "factory_modes.json"
        frontend_path = root / "web" / "frontend" / "src" / "constants" / "factoryModes.json"
        backend = json.loads(backend_path.read_text(encoding="utf-8"))
        frontend = json.loads(frontend_path.read_text(encoding="utf-8"))
        self.assertEqual(backend, frontend)

        self.assertEqual(list(FACTORY_MODE_IDS), frontend["modes"])
        self.assertEqual(DEFAULT_FACTORY_MODE, frontend["default"])
        self.assertEqual(FACTORY_MODE_LABELS, frontend["labels"])
        for mode in FACTORY_MODE_IDS:
            profile = factory_mode_profiles()[mode]
            self.assertEqual(
                {key: value for key, value in profile.items() if key != "mode"},
                frontend["profiles"][mode],
            )


if __name__ == "__main__":
    unittest.main()