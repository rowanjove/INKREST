# Novel Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, testable MVP for a multi-agent novel generation pipeline that can produce one chapter workspace from a chapter goal.

**Architecture:** The orchestrator coordinates focused agent wrappers. Deterministic scripts handle word counts and scene merging. Assets and state are plain text/YAML in v1, with a later upgrade path to SQLite and retrieval.

**Tech Stack:** Python 3.8, standard library `unittest`, JSON files, Markdown prompts, YAML-style state files.

---

### Task 1: Core Utility Tests

**Files:**
- Create: `tests/test_pipeline.py`
- Create: `novel_agent/scripts/count_chars.py`
- Create: `novel_agent/scripts/merge_scenes.py`

- [x] **Step 1: Write failing tests for Chinese character counting and scene merging**

Tests assert that only CJK characters are counted and scene files are merged in filename order.

- [x] **Step 2: Run tests to verify import failure**

Run: `python -m unittest tests.test_pipeline -v`

Expected: FAIL because `novel_agent` package does not exist.

- [x] **Step 3: Implement minimal utility functions**

Implemented `count_chinese_chars`, `wordcount_report`, and `merge_scene_texts`.

- [x] **Step 4: Run tests to verify utilities pass**

Run: `python -m unittest tests.test_pipeline -v`

Expected: utility tests pass.

### Task 2: Agent Interfaces and Orchestrator

**Files:**
- Create: `novel_agent/agents/*.py`
- Create: `novel_agent/pipeline.py`
- Create: `novel_agent/orchestrator.py`
- Create: `orchestrator.py`

- [x] **Step 1: Write failing orchestrator test**

The test uses `StaticLLM` responses and expects a chapter workspace with plan, context, scene, final text, wordcount report, audit report, and state update.

- [x] **Step 2: Implement deterministic agent wrappers**

Implemented `PromptAgent`, `StaticLLM`, and focused role classes for planner, writer, length fixer, stitch editor, style editor, and auditor.

- [x] **Step 3: Implement `NovelOrchestrator.run_chapter`**

The method creates chapter directories, runs the agent sequence, writes intermediate artifacts, and returns `ChapterResult`.

- [x] **Step 4: Add CLI entry point**

The root `orchestrator.py` runs the pipeline in dry-run mode.

### Task 3: Project Templates

**Files:**
- Create: `assets/*.md`
- Create: `assets/character_cards.yaml`
- Create: `state/*.yaml`
- Create: `prompts/*.md`
- Create: `README.md`

- [x] **Step 1: Add default assets and state**

Added world, style, character cards, continuity state, threads, objects, and events templates.

- [x] **Step 2: Add prompt templates**

Added role prompts for planner, writer, expander, compressor, stitch editor, style editor, and auditor.

- [x] **Step 3: Document how to run**

Added commands for tests and dry-run chapter generation.

### Task 4: Verification

**Files:**
- Test: `tests/test_pipeline.py`

- [x] **Step 1: Run the full unit test suite**

Run: `python -m unittest tests.test_pipeline -v`

Expected: all tests pass.

- [x] **Step 2: Run one dry chapter**

Run: `python .\orchestrator.py --chapter-id 001 --goal "主角雨夜回到出租屋，并遭遇第一次异常。"`

Expected: `workspace/chapters/chapter_001/chapter_final.txt` is created.
