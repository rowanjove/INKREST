"""The API test harness must restore project-scoped global state between cases."""

from pathlib import Path

from tests.api._base import ApiTestBase, web_server


class TestApiIsolation:
    def test_server_shim_reads_updated_context_attributes(self):
        import shutil
        import tempfile

        original_base = web_server.BASE_DIR
        temporary_base = Path(tempfile.mkdtemp(prefix="novel-agent-shim-"))
        try:
            web_server.BASE_DIR = temporary_base
            assert web_server.BASE_DIR == temporary_base
        finally:
            web_server.BASE_DIR = original_base
            shutil.rmtree(temporary_base, ignore_errors=True)

    def test_global_project_state_is_restored_by_base_teardown(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server.project_manager
        harness = ApiTestBase()
        try:
            harness.setUp()
            web_server.BASE_DIR = harness.tmpdir
            web_server._active_project_id = "temporary"
            web_server.project_manager = web_server.ProjectManager(harness.tmpdir)
        finally:
            harness.tearDown()
            harness.doCleanups()

        assert web_server.BASE_DIR == original_base
        assert web_server._active_project_id == original_active
        assert web_server.project_manager.base_dir == original_manager.base_dir
