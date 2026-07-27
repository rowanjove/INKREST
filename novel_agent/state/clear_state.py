"""SQLite table groups for controlled narrative database resets."""

from __future__ import annotations

from typing import Tuple

# Core narrative graph and chapter index (user-visible "story state").
NARRATIVE_STATE_TABLES: Tuple[str, ...] = (
    "events",
    "objects",
    "threads",
    "character_state",
    "chapters",
    "chapter_summaries",
    "timeline_nodes",
    "timeline_edges",
    "foreshadows",
    "hooks",
    "reader_promises",
    "secrets",
    "vector_embeddings",
    "state_change_candidates",
    "character_relations",
    "reader_feedback",
    "chapter_versions",
    "chapter_rewrites",
    "document_revisions",
    "documents",
)

# Task queue, cost logs, prompt/asset version history (kept unless include_operational).
OPERATIONAL_TABLES: Tuple[str, ...] = (
    "tasks",
    "task_logs",
    "llm_cost_log",
    "prompt_versions",
    "asset_versions",
)
