import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import web.routes.config as config_routes


class _Response:
    status_code = 200
    headers = {}

    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def iter_bytes(self, chunk_size=16384):
        yield self.content


class _Client:
    def __init__(self, content: bytes, **_kwargs):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def stream(self, *_args, **_kwargs):
        return _Response(self.content)


class LocalModelIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-model-test-"))
        self.original_base = config_routes.BASE_DIR
        config_routes.BASE_DIR = self.tmpdir

    def tearDown(self):
        config_routes.BASE_DIR = self.original_base
        shutil.rmtree(self.tmpdir)

    def test_manifest_is_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Missing model SHA-256 manifest"):
                config_routes._load_model_sha256()

    def test_manifest_loads_from_environment(self):
        digest = "a" * 64
        manifest = {"files": {name: digest for name in config_routes.MODEL_FILES}}
        with patch.dict(os.environ, {config_routes.MODEL_SHA256_ENV: json.dumps(manifest)}):
            self.assertEqual(config_routes._load_model_sha256()["vocab.txt"], digest)

    def test_download_hash_mismatch_removes_temporary_file(self):
        temp_path = self.tmpdir / "model.tmp"
        with patch.object(config_routes.httpx, "Client", lambda **kwargs: _Client(b"content", **kwargs)):
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                config_routes._do_stream_download("https://example.com/model", temp_path, 0, 100, "0" * 64)
        self.assertFalse(temp_path.exists())

    def test_download_accepts_matching_hash(self):
        content = b"content"
        temp_path = self.tmpdir / "model.tmp"
        expected = hashlib.sha256(content).hexdigest()
        with patch.object(config_routes.httpx, "Client", lambda **kwargs: _Client(content, **kwargs)):
            config_routes._do_stream_download("https://example.com/model", temp_path, 0, 100, expected)
        self.assertEqual(temp_path.read_bytes(), content)

    def test_setup_endpoint_marks_running_before_thread_start(self):
        original_state = dict(config_routes.setup_state)
        config_routes.setup_state.update({"status": "idle", "step": "", "progress": 0, "message": "", "error": None})
        try:
            with patch.dict(os.environ, {config_routes.ALLOW_RUNTIME_INSTALL_ENV: "1"}):
                with patch.object(config_routes.threading, "Thread") as thread_class:
                    response = config_routes.post_setup_local()
            self.assertEqual(response["status"], "started")
            self.assertEqual(config_routes.setup_state["status"], "running")
            thread_class.return_value.start.assert_called_once()
        finally:
            config_routes.setup_state.update(original_state)


if __name__ == "__main__":
    unittest.main()
