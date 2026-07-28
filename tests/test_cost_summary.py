"""Unit tests for novel_agent.services.cost_summary."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.services.cost_summary import (
    build_cost_summary,
    query_persisted_cost_summary,
    read_recent_autopilot_rounds,
)
from novel_agent.state.sqlite_store import SQLiteStateStore


class CostSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-cost-"))

    def test_project_id_filter_excludes_other_projects(self):
        store = SQLiteStateStore(self.tmpdir)
        store.log_llm_cost(
            call_id="a",
            model="m",
            input_tokens=100,
            output_tokens=0,
            input_cost=0.1,
            output_cost=0.0,
            project_id=self.tmpdir.name,
        )
        store.log_llm_cost(
            call_id="b",
            model="m",
            input_tokens=999,
            output_tokens=0,
            input_cost=9.0,
            output_cost=0.0,
            project_id="other_proj",
        )
        persisted, err = query_persisted_cost_summary(self.tmpdir, project_id=self.tmpdir.name)
        self.assertIsNone(err)
        self.assertEqual(persisted["call_count"], 1)
        self.assertEqual(persisted["input_tokens"], 100)

    def test_malicious_project_id_does_not_break_query(self):
        store = SQLiteStateStore(self.tmpdir)
        store.log_llm_cost(
            call_id="x",
            model="m",
            input_tokens=10,
            output_tokens=0,
            input_cost=0.01,
            output_cost=0.0,
            project_id="'; DROP TABLE llm_cost_log; --",
        )
        persisted, err = query_persisted_cost_summary(
            self.tmpdir,
            project_id="'; DROP TABLE llm_cost_log; --",
        )
        self.assertIsNone(err)
        self.assertEqual(persisted["call_count"], 1)

    def test_jsonl_rounds_whitelist_fields(self):
        ws = self.tmpdir / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "autopilot_rounds.jsonl").write_text(
            json.dumps(
                {
                    "round": 2,
                    "tokens_used": 100,
                    "chapters_completed": 1,
                    "secret_payload": "should_drop",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rounds = read_recent_autopilot_rounds(self.tmpdir)
        self.assertEqual(len(rounds), 1)
        self.assertEqual(rounds[0]["round"], 2)
        self.assertNotIn("secret_payload", rounds[0])

    def test_build_cost_summary_shape(self):
        summary = build_cost_summary(self.tmpdir)
        self.assertIn("persisted", summary)
        self.assertIn("persisted_error", summary)
        self.assertIn("recent_rounds", summary)

    def test_orchestrator_persists_usd_prices_as_cny(self):
        from novel_agent.agents.base import StaticLLM
        from novel_agent.orchestrator import NovelOrchestrator
        from novel_agent.pipeline import PipelineConfig

        llm = StaticLLM({"default": "ok"})
        llm.call_log = [
            {
                "model": "gpt-4o-mini",
                "prompt_tokens": 1000,
                "completion_tokens": 1000,
            }
        ]
        config = PipelineConfig(
            root_dir=self.tmpdir,
            llm=llm,
            llm_registry={"writer": llm},
            max_workers=1,
        )
        orchestrator = NovelOrchestrator(config)

        orchestrator._persist_llm_cost("001")

        persisted, err = query_persisted_cost_summary(
            self.tmpdir, project_id=self.tmpdir.name
        )
        self.assertIsNone(err)
        # gpt-4o-mini is 0.001 + 0.004 USD per 1k tokens; stored CNY must be * 7.2.
        self.assertAlmostEqual(persisted["total_cost_cny"], 0.036, places=6)


if __name__ == "__main__":
    unittest.main()
