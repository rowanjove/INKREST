import argparse
import json
from pathlib import Path

import pytest

from novel_agent.orchestrator_types import ChapterResult
from scripts.run_longform_acceptance import (
    AcceptanceRunError,
    build_manifest,
    execute_acceptance_run,
)


def test_acceptance_manifest_is_planned_without_explicit_start(tmp_path: Path):
    args = argparse.Namespace(
        chapters=20, model="m", prompt="p", prompt_digest="", embedding="e", embedding_digest="", config="c",
        seed=1, temperature=0.5, budget=0, start=False,
    )
    manifest = build_manifest(args)
    assert manifest["status"] == "planned"
    assert manifest["operator_started"] is False
    assert len(manifest["prompt_digest"]) == 64
    assert manifest["completed_chapters"] == []
    assert manifest["execution"]["requested"] is False


def test_execute_requires_two_explicit_acknowledgements(tmp_path: Path):
    with pytest.raises(AcceptanceRunError, match="--start 和 --execute"):
        execute_acceptance_run(
            argparse.Namespace(
                chapters=20,
                model="m",
                prompt="p",
                prompt_digest="",
                embedding="e",
                embedding_digest="",
                config="c",
                seed=1,
                temperature=0.5,
                budget=1,
                output=tmp_path / "run.json",
                root=tmp_path,
                start=True,
                execute=False,
                resume=True,
                max_retries=1,
            )
        )


class _FakeStore:
    def get_llm_cost_summary(self, project_id: str = ""):
        return {"total_cost_cny": 0.0, "total_tokens": 0}


class _FakeConfig:
    async def close_llm_clients(self):
        return None


class _FakeClient:
    model = "fake-model"
    temperature = 0.7
    seed = None


class _RuntimeConfig(_FakeConfig):
    def __init__(self):
        self.llm = _FakeClient()
        self.llm_registry = {"default": self.llm}
        self.embedding_config = {"provider": "stub"}


class _FakeOrchestrator:
    def __init__(self, _config):
        self.store = _FakeStore()
        self.config = _config
        self.calls = []

    def _chapter_pipeline_complete(self, _chapter_id: str) -> bool:
        return False

    def reset_round_token_accumulator(self):
        return None

    def consume_round_tokens(self) -> int:
        return 100

    async def _run_chapter_briefs(self, briefs, **_kwargs):
        brief = briefs[0]
        chapter_id = str(brief["chapter_id"])
        self.calls.append(chapter_id)
        return [ChapterResult(chapter_id, Path("chapter_final.txt"), {}, [])], False


def _run_args(tmp_path: Path):
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "config" / "pipeline.yaml").write_text("llm: {}\n", encoding="utf-8")
    (root / "workspace").mkdir()
    (root / "workspace" / "arc_main.json").write_text(
        json.dumps({"arc_id": "main", "chapters": [{"chapter_id": f"{i:03d}", "goal": "g"} for i in range(1, 21)]}),
        encoding="utf-8",
    )
    return root, argparse.Namespace(
        chapters=20,
        model="m",
        prompt="p",
        prompt_digest="",
        embedding="e",
        embedding_digest="",
        config="c",
        seed=1,
        temperature=0.5,
        budget=1,
        output=tmp_path / "run.json",
        root=root,
        start=True,
        execute=True,
        resume=True,
        max_retries=1,
    )


def test_execute_writes_atomic_checkpoint_and_quality_checkpoints(tmp_path: Path):
    root, args = _run_args(tmp_path)
    fake = _FakeOrchestrator(_FakeConfig())
    manifest = execute_acceptance_run(
        args,
        config_factory=lambda _root: _FakeConfig(),
        orchestrator_factory=lambda config: fake,
    )
    assert manifest["status"] == "completed"
    assert len(manifest["completed_chapters"]) == 20
    assert len(manifest["quality_trend"]) == 2
    assert manifest["checkpoint"]["completed_count"] == 20
    assert not list(tmp_path.glob("run.json.tmp"))
    persisted = json.loads(args.output.read_text(encoding="utf-8"))
    assert persisted["status"] == "completed"
    assert all("chapter_final" not in row.get("reason", "") for row in persisted["retries"])
    assert fake.calls == [f"{i:03d}" for i in range(1, 21)]


def test_execute_binds_manifest_to_resolved_runtime_contract(tmp_path: Path):
    root, args = _run_args(tmp_path)
    args.model = "fake-model"
    args.temperature = 0.5
    args.config = "configured-pipeline"
    config = _RuntimeConfig()
    fake = _FakeOrchestrator(config)
    manifest = execute_acceptance_run(
        args,
        config_factory=lambda _root: config,
        orchestrator_factory=lambda _config: fake,
    )
    assert manifest["status"] == "completed"
    assert manifest["model"] == "fake-model"
    assert manifest["temperature"] == 0.5
    assert manifest["execution_contract"]["resolved"] is True
    assert config.llm.temperature == 0.5
    assert config.llm.seed == 1
