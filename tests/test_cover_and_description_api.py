import json
import tempfile
import unittest
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import web.server as web_server
from web.llm_errors import model_provider_http_error
from web.server import app as web_app


class CoverAndDescriptionApiTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-cover-test-"))
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        self.original_project_manager = web_server.project_manager
        
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        web_server.project_manager = web_server.ProjectManager(self.tmpdir)
        
        # 创建测试项目
        self.project = web_server.project_manager.create_project("测试小说", "初始简介")
        self.pid = self.project["id"]
        web_server.project_manager.switch_project(self.pid)
        web_server._active_project_id = self.pid

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        web_server.project_manager = self.original_project_manager

    def test_get_cover_returns_404_when_missing(self):
        client = TestClient(web_app)
        response = client.get(f"/api/projects/{self.pid}/cover")
        self.assertEqual(response.status_code, 404)

    def test_save_cover_and_get_cover_success(self):
        client = TestClient(web_app)
        
        # 模拟 1x1 的最小透明 PNG base64
        dummy_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        
        save_resp = client.post(
            f"/api/projects/{self.pid}/save-cover",
            json={"cover": dummy_base64}
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertEqual(save_resp.json()["status"], "saved")
        
        # 验证文件是否已存在
        cover_path = self.tmpdir / "projects" / self.pid / "cover.png"
        self.assertTrue(cover_path.exists())
        
        # 获取封面
        get_resp = client.get(f"/api/projects/{self.pid}/cover")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.headers.get("content-type"), "image/png")

    def test_suggest_cover_prompt(self):
        client = TestClient(web_app)
        
        with patch("novel_agent.pipeline.PipelineConfig.from_config") as mock_from_config:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = "Generated prompt by AI"
            mock_config = MagicMock()
            mock_config.get_llm.return_value = mock_llm
            mock_from_config.return_value = mock_config
            
            response = client.post(f"/api/projects/{self.pid}/suggest-cover-prompt")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["prompt"], "Generated prompt by AI")

    def test_model_provider_auth_errors_are_actionable_bad_gateway(self):
        error = model_provider_http_error(
            "生成画图提示词",
            Exception("Non-retryable HTTP 401: Authentication Fails"),
        )

        self.assertEqual(error.status_code, 502)
        self.assertIn("模型鉴权失败", error.detail)
        self.assertIn("API Key", error.detail)

    def test_generate_cover_with_image_model(self):
        client = TestClient(web_app)
        
        # 先保存一个模拟的图像模型到模型库
        model_lib = web_server.ModelLibrary(self.tmpdir / "projects" / self.pid)
        model_lib.save_model("flux-test", {
            "name": "Flux Image Model",
            "provider": "openai",
            "base_url": "https://api.test.com/v1",
            "api_key": "test-key",
            "model": "flux-schnell",
            "type": "image"
        })
        
        # Mock cover route HTTP client
        with patch("web.routes.covers.httpx.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client_instance
            
            # 模拟 post 方法
            mock_resp_post = MagicMock()
            mock_resp_post.status_code = 200
            mock_resp_post.json.return_value = {
                "data": [{"url": "https://image.test.com/img.png"}]
            }
            mock_client_instance.post.return_value = mock_resp_post
            
            with patch(
                "web.routes.covers._download_remote_image",
                return_value=(b"fake image bytes", "image/png"),
            ):
                response = client.post(
                    f"/api/projects/{self.pid}/generate-cover",
                    json={
                        "model_id": "flux-test",
                        "prompt": "cat sketch"
                    }
                )
            
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["image"].startswith("data:image/png;base64,"))
            self.assertIn("fake image bytes", base64.b64decode(response.json()["image"].split(",")[1]).decode("latin1", errors="ignore"))

    def test_generate_cover_rejects_private_image_url(self):
        client = TestClient(web_app)
        model_lib = web_server.ModelLibrary(self.tmpdir / "projects" / self.pid)
        model_lib.save_model("flux-test", {
            "name": "Flux Image Model",
            "provider": "openai",
            "base_url": "https://api.test.com/v1",
            "api_key": "test-key",
            "model": "flux-schnell",
            "type": "image",
        })

        with patch("web.routes.covers.httpx.Client") as mock_client_class:
            mock_client = mock_client_class.return_value.__enter__.return_value
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"url": "http://127.0.0.1/internal"}]}
            mock_client.post.return_value = mock_response

            response = client.post(
                f"/api/projects/{self.pid}/generate-cover",
                json={"model_id": "flux-test", "prompt": "cat sketch"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("private", response.json()["detail"].lower())

    def test_generate_cover_rejects_oversized_base64_image(self):
        client = TestClient(web_app)
        model_lib = web_server.ModelLibrary(self.tmpdir / "projects" / self.pid)
        model_lib.save_model("flux-test", {
            "name": "Flux Image Model",
            "provider": "openai",
            "base_url": "https://api.test.com/v1",
            "api_key": "test-key",
            "model": "flux-schnell",
            "type": "image",
        })
        oversized = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"a" * 64).decode("ascii")

        with patch("web.routes.covers.MAX_COVER_BYTES", 16):
            with patch("web.routes.covers.httpx.Client") as mock_client_class:
                mock_client = mock_client_class.return_value.__enter__.return_value
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": [{"b64_json": oversized}]}
                mock_client.post.return_value = mock_response

                response = client.post(
                    f"/api/projects/{self.pid}/generate-cover",
                    json={"model_id": "flux-test", "prompt": "cat sketch"},
                )

        self.assertEqual(response.status_code, 413)

    def test_rewrite_description_api(self):
        client = TestClient(web_app)
        
        with patch("novel_agent.pipeline.PipelineConfig.from_config") as mock_from_config:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = "AI rewritten novel description"
            mock_config = MagicMock()
            mock_config.get_llm.return_value = mock_llm
            mock_from_config.return_value = mock_config
            
            response = client.post(
                f"/api/projects/{self.pid}/rewrite-description",
                json={
                    "old_description": "初始简介",
                    "style": "悬疑勾人",
                    "user_preference": "突出恐怖气氛"
                }
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["description"], "AI rewritten novel description")

    def test_update_description_api(self):
        client = TestClient(web_app)
        
        response = client.post(
            f"/api/projects/{self.pid}/update-description",
            json={"description": "新的简介内容"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "updated")
        
        # 验证中央注册表
        registry = web_server.project_manager._read_registry()
        self.assertEqual(registry["projects"][self.pid]["description"], "新的简介内容")
        
        # 验证 project_meta.json
        meta_path = self.tmpdir / "projects" / self.pid / "config" / "project_meta.json"
        self.assertTrue(meta_path.exists())
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(meta["description"], "新的简介内容")
