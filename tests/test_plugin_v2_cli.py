import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest

from novel_agent.plugins.cli import plugin_init, plugin_validate, plugin_pack, plugin_test


@pytest.fixture
def temp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_cli_plugin_lifecycle_suite(temp_dir: Path):
    # 1. Test plugin init
    plugin_name = "test_cli_plugin"
    created_dir = plugin_init(plugin_name, ptype="pipeline_hook", dest_dir=temp_dir)
    assert created_dir.is_dir()
    assert (created_dir / "inkrest.plugin.json").is_file()
    assert (created_dir / "plugin.py").is_file()
    assert (created_dir / "README.md").is_file()

    # 2. Test plugin validate on directory
    val_res = plugin_validate(created_dir)
    assert val_res["status"] == "valid"
    assert val_res["manifest"]["id"] == plugin_name
    assert val_res["manifest"]["plugin_type"] == "pipeline_hook"

    # 3. Test plugin test
    test_res = plugin_test(created_dir)
    assert test_res["status"] == "passed"
    assert test_res["plugin_id"] == plugin_name

    # 4. Test plugin pack
    zip_path = plugin_pack(created_dir, output_zip=temp_dir / f"{plugin_name}.zip")
    assert zip_path.is_file()
    assert zipfile.is_zipfile(zip_path)

    # Verify contents of zip
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "inkrest.plugin.json" in namelist
        assert "plugin.py" in namelist

    # 5. Test plugin validate on generated zip
    val_zip_res = plugin_validate(zip_path)
    assert val_zip_res["status"] == "valid"
    assert val_zip_res["type"] == "zip"
    assert val_zip_res["manifest"]["id"] == plugin_name


def test_cli_plugin_init_command_plugin(temp_dir: Path):
    created_dir = plugin_init("cmd_plugin", ptype="command", dest_dir=temp_dir)
    val_res = plugin_validate(created_dir)
    assert val_res["manifest"]["plugin_type"] == "command"
    assert "onCommand:cmd_plugin.run" in val_res["manifest"]["activation_events"]

    test_res = plugin_test(created_dir)
    assert test_res["status"] == "passed"
