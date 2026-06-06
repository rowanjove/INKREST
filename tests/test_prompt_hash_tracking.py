import os
import unittest
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch
from novel_agent.prompts import PromptRepository
from novel_agent.state.sqlite_store import SQLiteStateStore

class TestPromptHashTracking(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-prompt-test-"))
        self.store = SQLiteStateStore(self.tmpdir)
        self.prompts_dir = self.tmpdir / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.defaults_dir = self.prompts_dir / "defaults"
        self.defaults_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_default_hash_verification_warning(self):
        mock_file = self.defaults_dir / "writer.md"
        mock_file.write_text("Modified default prompt content", encoding="utf-8")
        
        logger = logging.getLogger("novel_agent.prompts")
        
        # Patch Path.exists to redirect default package search to root_dir
        with patch.object(Path, "exists", autospec=True) as mock_exists:
            def side_effect(path_obj):
                path_str = str(path_obj.resolve())
                if str(self.defaults_dir.resolve()) in path_str:
                    return True
                if "prompts" in path_str and "defaults" in path_str:
                    return False
                # check file system directly for other cases
                return os.path.exists(path_obj)
            
            mock_exists.side_effect = side_effect
            
            with self.assertLogs(logger, level="WARNING") as cm:
                PromptRepository(root_dir=self.tmpdir, store=self.store)
                
            self.assertTrue(any("integrity check failed" in log for log in cm.output))

    def test_prompt_version_tracking(self):
        writer_prompt_path = self.prompts_dir / "writer.md"
        writer_prompt_path.write_text("Original Writer Prompt V1", encoding="utf-8")
        
        repo = PromptRepository(root_dir=self.tmpdir, store=self.store)
        
        # 1. First load: should insert to db, version 1
        content_1 = repo.load("writer")
        self.assertEqual(content_1, "Original Writer Prompt V1")
        
        latest_1 = self.store.get_latest_prompt_version("writer")
        self.assertEqual(latest_1["version"], 1)
        self.assertEqual(latest_1["content"], "Original Writer Prompt V1")
        
        # 2. Second load (from cache): should not add new version
        content_2 = repo.load("writer")
        self.assertEqual(content_2, "Original Writer Prompt V1")
        
        latest_2 = self.store.get_latest_prompt_version("writer")
        self.assertEqual(latest_2["version"], 1)
        
        # 3. Third load after clearing cache with same content: should not add new version
        repo.clear_cache()
        content_3 = repo.load("writer")
        self.assertEqual(content_3, "Original Writer Prompt V1")
        latest_3 = self.store.get_latest_prompt_version("writer")
        self.assertEqual(latest_3["version"], 1)
        
        # 4. Content changed, clear cache and load: should insert new version 2
        writer_prompt_path.write_text("Modified Writer Prompt V2", encoding="utf-8")
        repo.clear_cache()
        content_4 = repo.load("writer")
        self.assertEqual(content_4, "Modified Writer Prompt V2")
        
        latest_4 = self.store.get_latest_prompt_version("writer")
        self.assertEqual(latest_4["version"], 2)
        self.assertEqual(latest_4["content"], "Modified Writer Prompt V2")

if __name__ == "__main__":
    unittest.main()
