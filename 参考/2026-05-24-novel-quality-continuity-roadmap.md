# Novel Quality And Continuity Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the current Novel Agent by adding practical continuity hooks, vector recall distance controls, quality reports, and later narrative-debt management without destabilizing the existing desktop app.

**Architecture:** Build on the current pipeline instead of replacing it: `NovelOrchestrator` remains the owner of chapter stages, `ContextBuilderAgent` owns context injection, `SQLiteStateStore` owns persistent state, and the frontend reads reports through the existing chapter-detail API. Quality gates start in report-only mode, then can be promoted to rewrite/blocking mode after real generated chapters prove the thresholds.

**Tech Stack:** Python 3.8, FastAPI backend, SQLite state store, numpy vector store, Vue 3 + Element Plus frontend, unittest/Vue build/Electron packaging verification.

---

## Reality Check From Current Code

- Existing tests are not absent: `tests/test_pipeline.py` already covers 58 pipeline/state/vector/web cases.
- Existing state persistence is SQLite-backed: `novel_agent/state/sqlite_store.py` already has chapters, summaries, events, characters, foreshadows, and hooks.
- Existing generation has checkpoint stages: `generation`, `audit`, `state_update` in `novel_agent/orchestrator.py`.
- Existing vector recall is simple cosine search with `chapter_lt`, but no distance penalty or rewrite hint.
- Existing quality package only contains audit schema validation, not physical guards.
- Existing chapter detail page already has tabs for final text, summary, plan, audit, continuity, and state update, so guard reports can fit there without new navigation.
- Several Python/Vue files still contain mojibake in display/prompt strings. New work should use clean UTF-8 files and avoid broad unrelated rewrites unless a touched file must be cleaned for correctness.

## Planned File Structure

- Create `novel_agent/quality/hooks.py`: deterministic hook extraction from chapter tails and current chapter heads.
- Create `novel_agent/quality/style_rules.py`: report-only AI-style and paragraph/layout checks.
- Create `novel_agent/quality/scene_delta.py`: report-only scene-progress checks.
- Create `novel_agent/quality/report.py`: common `QualityReport` shape and aggregation helpers.
- Modify `novel_agent/quality/__init__.py`: export guard helpers.
- Modify `novel_agent/agents/auditor.py`: request and normalize `narrative_hooks` while preserving old schema compatibility.
- Modify `novel_agent/agents/planner.py`: accept optional continuity hints and inject them into the planning prompt.
- Modify `novel_agent/agents/context_builder.py`: add previous-tail hook block and distance-aware vector recall labels.
- Modify `novel_agent/state/vector_store.py`: support distance penalty helper without changing existing `search()` callers.
- Modify `novel_agent/orchestrator.py`: run report-only guards after final text exists, write `reports/quality.json`, feed hooks into rewrite/planning later.
- Modify `web/models.py` and `web/server.py`: expose `quality_report` in chapter detail payload.
- Modify `web/frontend/src/views/ChapterDetail.vue`: add a `质量报告` tab.
- Modify `tests/test_pipeline.py` initially; split into focused test files only if the file becomes painful during execution.

---

## Phase 0: Safety Baseline

### Task 0.1: Establish Verification Commands

**Files:**
- No code changes.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all current tests pass.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
cd web/frontend
npm run build
```

Expected: Vue/TypeScript build succeeds. Vite chunk warnings are acceptable.

- [ ] **Step 3: Record current branch status**

Run:

```powershell
git status --short
```

Expected: if this workspace is not a git repo, skip commit steps in later tasks and keep a file-level summary instead.

---

## Phase 1: Continuity Hooks First

### Task 1.1: Add Deterministic Hook Extraction

**Files:**
- Create: `novel_agent/quality/hooks.py`
- Modify: `novel_agent/quality/__init__.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add failing hook extraction tests**

Append tests covering:

```python
from novel_agent.quality.hooks import extract_tail_hooks, check_head_continuity

def test_extract_tail_hooks_detects_unfinished_action_and_injury(self):
    text = "林澈正要推开石门，忽然听见井下传来脚步声。\n他的左臂仍在流血。"
    hooks = extract_tail_hooks(text)
    self.assertTrue(hooks["unfinished_actions"])
    self.assertTrue(hooks["injuries"])

def test_check_head_continuity_reports_missing_state(self):
    prev = {"unfinished_actions": ["正要推开石门"], "injuries": ["流血"], "keywords": []}
    report = check_head_continuity(prev, "林澈回到客栈，点了一壶茶。")
    self.assertFalse(report["pass"])
    self.assertGreaterEqual(len(report["missing_hooks"]), 1)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m unittest tests.test_pipeline.PipelineTests.test_extract_tail_hooks_detects_unfinished_action_and_injury tests.test_pipeline.PipelineTests.test_check_head_continuity_reports_missing_state -v
```

Expected: import or function-not-found failure.

- [ ] **Step 3: Implement `hooks.py`**

Implement:

```python
import re
from typing import Any, Dict, List

ACTION_HOOKS = re.compile(r"(正要|准备|打算|决定|即将|就要|刚想|刚准备|开始|试图).{0,24}(?:[。！？\n]|$)")
INJURY_HOOKS = re.compile(r"(受伤|流血|伤口|疼痛|昏迷|中毒|发热|发冷|虚弱|透支|内伤)")
PERCEPTION_HOOKS = re.compile(r"(发现|察觉|注意|看出|感觉到|意识到|听到|闻到|看到).{0,24}(?:了|到|出)")

def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result

def extract_tail_hooks(text: str, tail_chars: int = 500) -> Dict[str, Any]:
    tail = (text or "")[-tail_chars:]
    return {
        "unfinished_actions": _unique(ACTION_HOOKS.findall(tail)),
        "injuries": _unique(INJURY_HOOKS.findall(tail)),
        "perceptions": _unique(PERCEPTION_HOOKS.findall(tail)),
        "keywords": _unique(re.findall(r"[\u4e00-\u9fff]{2,4}", tail))[:40],
    }

def check_head_continuity(prev_hooks: Dict[str, Any], current_text: str, head_chars: int = 700) -> Dict[str, Any]:
    head = (current_text or "")[:head_chars]
    missing = []
    for hook_type in ("unfinished_actions", "injuries", "perceptions"):
        for hook in prev_hooks.get(hook_type, []) or []:
            if hook not in head:
                missing.append({"type": hook_type, "text": hook})
    score = max(0.0, 1.0 - len(missing) / max(1, sum(len(prev_hooks.get(k, []) or []) for k in ("unfinished_actions", "injuries", "perceptions"))))
    return {"pass": len(missing) <= 1 and score >= 0.65, "score": round(score, 3), "missing_hooks": missing}
```

- [ ] **Step 4: Export helpers**

In `novel_agent/quality/__init__.py`, export:

```python
from .hooks import extract_tail_hooks, check_head_continuity
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

### Task 1.2: Store Auditor Narrative Hooks

**Files:**
- Modify: `novel_agent/agents/auditor.py`
- Modify: `novel_agent/state/sqlite_store.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add test for fallback narrative hooks**

Add a test that Auditor output missing `narrative_hooks` is normalized to an empty list and does not break existing tests.

- [ ] **Step 2: Update Auditor prompt contract**

Modify the prompt text so it requests:

```text
输出 JSON，包含 risk_level、issues、state_update、narrative_hooks。
narrative_hooks 是本章结尾留下的未完成动作、悬念、伤势或重要承诺数组。
```

- [ ] **Step 3: Normalize result**

After parsing:

```python
hooks = result.get("narrative_hooks", [])
if not isinstance(hooks, list):
    hooks = []
result["narrative_hooks"] = hooks
```

- [ ] **Step 4: Persist hooks through existing `hooks` table**

In `orchestrator.py`, merge `audit["narrative_hooks"]` into `extracted_state["hooks"]` before `state_manager.apply_update()` and `store.sync_state_update()` paths.

Expected hook item shape:

```python
{
    "id": f"H_{chapter_id}_{idx + 1:02d}",
    "title": item.get("title") or item.get("text") or str(item)[:24],
    "status": "open",
    "description": item.get("description") or item.get("text") or str(item),
}
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

---

## Phase 2: Distance-Aware Vector Recall

### Task 2.1: Add Distance Penalty Helper

**Files:**
- Modify: `novel_agent/state/vector_store.py`
- Modify: `novel_agent/agents/context_builder.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add tests for chapter distance behavior**

Add tests using an in-memory fake vector store:

```python
class FakeVectorStore:
    def search(self, query, top_k=8, filters=None):
        return [
            {"id": "recent", "text": "最近章节内容", "metadata": {"chapter": "009"}, "score": 0.9},
            {"id": "mid", "text": "中距离内容", "metadata": {"chapter": "006"}, "score": 0.8},
            {"id": "old", "text": "旧内容", "metadata": {"chapter": "001"}, "score": 0.7},
        ]
```

For current chapter `010`, expect chapter `009` to be filtered, chapter `006` to have rewrite hint, chapter `001` to be normal.

- [ ] **Step 2: Implement helper**

Add a pure helper function rather than changing `search()` signature:

```python
def apply_chapter_distance_penalty(results, current_chapter, top_k=5, recent_cutoff=3, rewrite_cutoff=5):
    filtered = []
    current = CloudEmbeddingVectorStore._chapter_value(current_chapter, 0)
    for item in results:
        meta = item.get("metadata", {})
        chapter = CloudEmbeddingVectorStore._chapter_value(meta.get("chapter"), 0)
        delta = current - chapter
        copied = dict(item)
        copied["metadata"] = dict(meta)
        if chapter and delta <= recent_cutoff:
            continue
        if chapter and delta <= rewrite_cutoff:
            copied["rewrite_hint"] = "REQUIRE_REWRITE_40%"
        else:
            copied["rewrite_hint"] = None
        filtered.append(copied)
        if len(filtered) >= top_k:
            break
    return filtered
```

- [ ] **Step 3: Use in `ContextBuilderAgent._vector_recall()`**

Parse current chapter from `scene["chapter_id"]` or `scene["scene_id"]`. Search with `top_k=15`, apply penalty to final `top_k=5`.

Output labels:

```text
- [第006章 / 需改写引用] ...
- [第001章] ...
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

---

## Phase 3: Report-Only Quality Guards

### Task 3.1: Add Style And Layout Guards

**Files:**
- Create: `novel_agent/quality/style_rules.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add tests**

Cover:

- clean text passes
- repeated AI phrase patterns produce warnings
- long paragraph ratio is reported

- [ ] **Step 2: Implement report-only checks**

Functions:

```python
def check_ai_style(text: str) -> dict: ...
def check_paragraph_layout(text: str, max_chars: int = 150) -> dict: ...
```

Rules must return:

```python
{"pass": bool, "level": "none|warning|review|fail", "score": int, "details": [...]}
```

- [ ] **Step 3: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

### Task 3.2: Add Scene Delta Guard

**Files:**
- Create: `novel_agent/quality/scene_delta.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add tests**

Test a chapter with plot/action changes passes and a static introspection-only chapter gets a warning/review.

- [ ] **Step 2: Implement `check_scene_delta(text, short_chapter=False)`**

Use loose thresholds first:

```python
min_valid = 1 if short_chapter else 2
pass_condition = valid >= min_valid and low_delta_scenes <= 2
```

- [ ] **Step 3: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

### Task 3.3: Aggregate Quality Report In Pipeline

**Files:**
- Create: `novel_agent/quality/report.py`
- Modify: `novel_agent/orchestrator.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add test for `reports/quality.json`**

In an orchestrator dry-run test, assert:

```python
quality = json.loads((chapter_dir / "reports" / "quality.json").read_text(encoding="utf-8"))
self.assertIn("style", quality["checks"])
self.assertIn("layout", quality["checks"])
self.assertEqual(quality["mode"], "report_only")
```

- [ ] **Step 2: Implement aggregation**

Add:

```python
def build_quality_report(final_text, previous_text=""):
    hooks = extract_tail_hooks(previous_text) if previous_text else {}
    return {
        "mode": "report_only",
        "checks": {
            "continuity_physical": check_head_continuity(hooks, final_text) if hooks else {"pass": True, "score": 1.0, "missing_hooks": []},
            "style": check_ai_style(final_text),
            "layout": check_paragraph_layout(final_text),
            "scene_delta": check_scene_delta(final_text),
        },
    }
```

- [ ] **Step 3: Call after final text is written and before sensitive scan**

In `NovelOrchestrator.run_chapter()`, write:

```python
quality_report = build_quality_report(final_text, previous_text=self._previous_chapter_text(chapter_id))
self._write_json(reports_dir / "quality.json", quality_report)
emit_progress("quality_guard", "done", {"mode": "report_only"}, chapter_id)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

---

## Phase 4: Frontend Visibility

### Task 4.1: Expose Quality Report In Chapter API

**Files:**
- Modify: `web/models.py`
- Modify: `web/server.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add model field**

Add optional field to chapter detail response:

```python
quality_report: Dict[str, Any] = {}
```

- [ ] **Step 2: Read report**

In the chapter detail endpoint, read:

```python
quality_report=_read_json(chapter_dir / "reports" / "quality.json", {})
```

- [ ] **Step 3: Add server test**

Assert chapter detail payload includes `quality_report` even when the file is missing.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_pipeline -v
```

Expected: all tests pass.

### Task 4.2: Add Quality Report Tab

**Files:**
- Modify: `web/frontend/src/views/ChapterDetail.vue`
- Optional create: `web/frontend/src/components/ChapterQualityReport.vue`

- [ ] **Step 1: Create focused component**

Create `ChapterQualityReport.vue` that receives `qualityReport` and renders cards for `style`, `layout`, `scene_delta`, and `continuity_physical`.

- [ ] **Step 2: Add tab**

In `ChapterDetail.vue`, add:

```vue
<el-tab-pane label="质量报告" name="quality">
  <ChapterQualityReport :quality-report="chapter.quality_report" />
</el-tab-pane>
```

- [ ] **Step 3: Build frontend**

Run:

```powershell
cd web/frontend
npm run build
```

Expected: build passes.

---

## Phase 5: Narrative Debt, After Reports Are Stable

### Task 5.1: Add Minimal Narrative Debt Tables

**Files:**
- Modify: `novel_agent/state/sqlite_store.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add tables only**

Add `reader_promises` and `secrets`. Defer `pledges` unless UI needs it immediately; current `hooks` and `foreshadows` already cover part of this domain.

- [ ] **Step 2: Add CRUD list/upsert methods**

Methods:

```python
def upsert_reader_promise(self, item: Dict[str, Any]) -> None: ...
def list_reader_promises(self, status: str = "") -> List[Dict[str, Any]]: ...
def upsert_secret(self, item: Dict[str, Any]) -> None: ...
def list_secrets(self, status: str = "") -> List[Dict[str, Any]]: ...
```

- [ ] **Step 3: Tests**

Test table initialization and round-trip CRUD.

### Task 5.2: Prompt Injection

**Files:**
- Modify: `novel_agent/agents/context_builder.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Build debt block**

Add a high-priority block after continuity state:

```text
## 剧情债务约束
### 本章不可提前揭露
...
### 已进入回收窗口
...
```

- [ ] **Step 2: Tests**

Use a temp SQLite store with one promise and one secret; assert context contains both.

---

## Phase 6: Later Engineering Enhancements

Do these only after Phases 1-4 are stable:

- `chapter_versions`: valuable, but touches persistence, API, and UI diff; not first.
- Thinking stripping and multi-key fallback: useful, but should be implemented inside `OpenAILLM` after model routing is stable.
- Hard blocking guards: only after at least 10-20 generated chapters show acceptable false-positive rates in report-only mode.
- Volume bridge: useful for long novels, but depends on narrative debt and stable chapter versions.

---

## Final Verification Before Packaging

Run:

```powershell
python -m unittest tests.test_pipeline -v
cd web/frontend
npm run build
npm run build:backend
npx electron-builder --win dir
```

Then launch:

```powershell
D:\path\to\novel-agent\web\frontend\dist-desktop\win-unpacked\NovelAgent.exe
```

Manual smoke:

- open an existing chapter detail page
- verify `质量报告` tab renders
- verify new reports are generated after running a chapter
- verify settings and new-work creation still open
- verify packaged `/api/health` returns 200
