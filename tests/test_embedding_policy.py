"""Scale-aware embedding backend resolution (phase 3: long/epic → ChromaDB)."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import patch

import yaml

from novel_agent.pipeline import PipelineConfig, load_pipeline_settings
from novel_agent.services.embedding_policy import (
    resolve_embedding_config,
    should_prefer_chromadb_backend,
)


def _seed_project(
    root: Path,
    *,
    scale: str = "medium",
    target_chapters: int = 50,
    embedding: Optional[Dict] = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    pipeline = {"llm": {"default": {"provider": "static"}}}
    if embedding is not None:
        pipeline["embedding"] = embedding
    (root / "config" / "pipeline.yaml").write_text(
        yaml.safe_dump(pipeline, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    outline = {
        "chosen_title": "体量测试",
        "target_chapters": target_chapters,
        "scale_profile": {"scale": scale, "target_chapters": target_chapters},
    }
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False),
        encoding="utf-8",
    )


class EmbeddingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="embedding-policy-"))

    def test_medium_scale_keeps_sqlite_backend(self):
        _seed_project(self.tmpdir, scale="medium", target_chapters=50)
        settings = load_pipeline_settings(self.tmpdir)
        with patch("novel_agent.services.embedding_policy.CHROMA_AVAILABLE", True):
            emb = resolve_embedding_config(settings, self.tmpdir)
        self.assertEqual(emb.get("backend", "sqlite"), "sqlite")
        self.assertFalse(should_prefer_chromadb_backend(self.tmpdir))

    @patch("novel_agent.services.embedding_policy.CHROMA_AVAILABLE", True)
    def test_long_scale_prefers_chromadb_for_real_provider(self):
        _seed_project(
            self.tmpdir,
            scale="long",
            target_chapters=200,
            embedding={"provider": "openai", "api_key": "sk-test"},
        )
        settings = load_pipeline_settings(self.tmpdir)
        emb = resolve_embedding_config(settings, self.tmpdir)
        self.assertEqual(emb["backend"], "chromadb")
        self.assertTrue(should_prefer_chromadb_backend(self.tmpdir))

    @patch("novel_agent.services.embedding_policy.CHROMA_AVAILABLE", True)
    def test_long_scale_stub_provider_still_uses_chromadb_storage(self):
        _seed_project(
            self.tmpdir,
            scale="long",
            target_chapters=200,
            embedding={"provider": "stub"},
        )
        settings = load_pipeline_settings(self.tmpdir)
        emb = resolve_embedding_config(settings, self.tmpdir)
        self.assertEqual(emb["backend"], "chromadb")

    @patch("novel_agent.services.embedding_policy.CHROMA_AVAILABLE", False)
    def test_long_scale_hints_when_chromadb_missing(self):
        _seed_project(
            self.tmpdir,
            scale="epic",
            target_chapters=1200,
            embedding={"provider": "openai", "api_key": "sk-test"},
        )
        settings = load_pipeline_settings(self.tmpdir)
        emb = resolve_embedding_config(settings, self.tmpdir)
        self.assertEqual(emb.get("backend", "sqlite"), "sqlite")
        self.assertIn("chromadb", emb.get("_backend_hint", "").lower())

    def test_explicit_sqlite_override_on_long_scale(self):
        _seed_project(
            self.tmpdir,
            scale="long",
            target_chapters=200,
            embedding={"provider": "openai", "backend": "sqlite", "api_key": "sk-test"},
        )
        settings = load_pipeline_settings(self.tmpdir)
        with patch("novel_agent.services.embedding_policy.CHROMA_AVAILABLE", True):
            emb = resolve_embedding_config(settings, self.tmpdir)
        self.assertEqual(emb["backend"], "sqlite")

    @patch("novel_agent.services.embedding_policy.CHROMA_AVAILABLE", True)
    def test_pipeline_config_inherits_chromadb_for_long_project(self):
        _seed_project(
            self.tmpdir,
            scale="long",
            target_chapters=200,
            embedding={"provider": "stub"},
        )
        (self.tmpdir / "config" / "models.json").write_text("{}", encoding="utf-8")
        cfg = PipelineConfig.from_config(self.tmpdir)
        self.assertEqual(cfg.embedding_config.get("backend"), "chromadb")
        self.assertEqual(cfg.embedding_config.get("_scale_hnsw_rebuild_every"), 50)


if __name__ == "__main__":
    unittest.main()