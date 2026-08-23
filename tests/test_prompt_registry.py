import os
from pathlib import Path

from novel_agent.prompt_registry import inspect_prompt_sources, prompt_manifest, prompt_sha256
from novel_agent.prompts import PromptRepository


def test_prompt_registry_matches_repository_precedence(tmp_path: Path):
    prompts = tmp_path / "prompts"
    (prompts / "defaults").mkdir(parents=True)
    (prompts / "defaults" / "writer.md").write_text("default", encoding="utf-8")
    (prompts / "writer.md").write_text("project", encoding="utf-8")

    env_root = tmp_path / "templates"
    (env_root / "prompts").mkdir(parents=True)
    (env_root / "prompts" / "writer.md").write_text("environment", encoding="utf-8")

    info = inspect_prompt_sources(tmp_path, "writer", env_templates=env_root)
    assert info["selected_source"] == "project"
    assert info["selected_sha256"] == prompt_sha256("project")
    assert any(item["type"] == "project_override_differs_from_default" for item in info["drift"])

    (prompts / "writer.md").unlink()
    info = inspect_prompt_sources(tmp_path, "writer", env_templates=env_root)
    assert info["selected_source"] == "environment"

    repo = PromptRepository(tmp_path)
    with _temporary_env("NOVEL_AGENT_TEMPLATES", str(env_root)):
        assert repo.load("writer") == "environment"


def test_prompt_manifest_is_json_serialisable_and_reports_roles(tmp_path: Path):
    prompts = tmp_path / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "writer.md").write_text("writer", encoding="utf-8")
    manifest = prompt_manifest(tmp_path, roles=["writer"])
    assert manifest["schema_version"] == 1
    assert manifest["resolution_order"] == ["project", "environment", "package"]
    assert manifest["roles"][0]["role"] == "writer"
    assert manifest["roles"][0]["selected_source"] == "project"


def test_prompt_repository_exposes_manifest_without_changing_load(tmp_path: Path):
    prompts = tmp_path / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "writer.md").write_text("写作规则", encoding="utf-8")
    repo = PromptRepository(tmp_path)
    assert repo.load("writer") == "写作规则"
    assert repo.describe("writer")["selected_source"] == "project"
    assert repo.manifest(["writer"])["roles"][0]["selected_sha256"] == prompt_sha256("写作规则")


class _temporary_env:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value
        self.previous = None

    def __enter__(self):
        self.previous = os.environ.get(self.key)
        os.environ[self.key] = self.value

    def __exit__(self, exc_type, exc, tb):
        if self.previous is None:
            os.environ.pop(self.key, None)
        else:
            os.environ[self.key] = self.previous
