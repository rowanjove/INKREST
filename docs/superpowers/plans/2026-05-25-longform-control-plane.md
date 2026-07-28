# Longform Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn NovelAgent from a chapter generator into a longform control system that can preserve genre identity, maintain a rolling chapter window, enforce pacing, track narrative debt, and run periodic drift calibration.

**Architecture:** Add a small “control plane” above the existing agents. The control plane stores stable L0 genre genes in `outline.json`, normalizes rolling chapter-plan items into structured machine fields, enriches narrative debt with deadlines, converts recall into constraints, and produces calibration reports without replacing the existing `NovelOrchestrator` pipeline.

**Tech Stack:** Python 3.8+/FastAPI/Pydantic/SQLite, existing `novel_agent` agents and state store, Vue 3/Element Plus frontend, pytest and `npm run build`.

---

## File Structure

- Create `novel_agent/control/__init__.py`: control-plane package marker.
- Create `novel_agent/control/genre_genes.py`: validates and fills L0 genre genes from an outline.
- Create `novel_agent/control/chapter_window.py`: normalizes structured rolling chapter-plan items and checks pacing ratios.
- Create `novel_agent/control/narrative_debt.py`: computes due/overdue status for foreshadows, secrets, and reader promises.
- Create `novel_agent/control/constraint_synthesizer.py`: converts state and vector recall snippets into writer-facing constraints.
- Create `novel_agent/control/calibration.py`: builds every-10-chapter drift and pacing reports.
- Modify `novel_agent/agents/chief_editor.py`: ensure generated outlines include `genre_genes`.
- Modify `novel_agent/agents/managing_editor.py`: preserve chapter structure fields when splitting arcs.
- Modify `novel_agent/agents/context_builder.py`: add synthesized constraints block above raw vector recall.
- Modify `novel_agent/orchestrator.py`: run window/debt/calibration hooks after chapter generation.
- Modify `novel_agent/state/sqlite_store.py`: extend narrative-debt records with chapter deadlines and related metadata.
- Modify `web/models.py`: add request/response models for rolling windows, calibration, and debt views.
- Modify `web/server.py`: expose control-plane API endpoints.
- Create `web/frontend/src/views/ControlPlaneView.vue`: longform control dashboard.
- Modify `web/frontend/src/App.vue` and `web/frontend/src/router.ts`: add sidebar route “长篇控制”.
- Test in `tests/test_pipeline.py`: backend unit tests for all control-plane behavior.

---

### Task 1: Add L0 Genre Genes

**Files:**
- Create: `novel_agent/control/__init__.py`
- Create: `novel_agent/control/genre_genes.py`
- Modify: `novel_agent/agents/chief_editor.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `PipelineTests`:

```python
def test_genre_genes_fill_defaults_and_preserve_existing_values(self):
    from novel_agent.control.genre_genes import ensure_genre_genes
    outline = {
        "core_theme": "电竞逆袭",
        "genre_positioning": "电竞女频",
        "genre_genes": {"pleasure_mechanism": "碾压型"}
    }

    result = ensure_genre_genes(outline)

    self.assertEqual(result["genre_genes"]["pleasure_mechanism"], "碾压型")
    self.assertEqual(result["genre_genes"]["protagonist_arc"], "从弱到强")
    self.assertIn("不要把电竞逆袭写成纯恋爱日常", result["genre_genes"]["drift_guards"])

def test_chief_editor_outline_contains_genre_genes(self):
    from novel_agent.agents.chief_editor import ChiefEditorAgent
    llm = StaticLLM({"chief_editor": json.dumps({
        "title_options": ["《枪声破晓》"],
        "protagonist": {"name": "沈星璃"},
        "macro_outline": [{"arc_id": "A01", "chapters": "1-20", "goal": "打进职业圈"}]
    }, ensure_ascii=False)})

    outline = ChiefEditorAgent(llm).plan_novel("电竞逆袭", "电竞", 20)

    self.assertIn("genre_genes", outline)
    self.assertIn("pleasure_mechanism", outline["genre_genes"])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "genre_genes"
```

Expected: import failure for `novel_agent.control.genre_genes`.

- [ ] **Step 3: Implement `genre_genes.py`**

```python
from copy import deepcopy
from typing import Any, Dict


DEFAULT_GENRE_GENES = {
    "pleasure_mechanism": "逆袭型",
    "protagonist_arc": "从弱到强",
    "romance_weight": "辅助线",
    "pacing_baseline": "快节奏爽文",
    "drift_guards": [
        "不要把电竞逆袭写成纯恋爱日常",
        "不要让主角核心目标脱离职业成长",
        "不要连续三章没有外部压力或可见进展",
    ],
}


def ensure_genre_genes(outline: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(outline)
    current = result.get("genre_genes")
    if not isinstance(current, dict):
        current = {}
    genes = deepcopy(DEFAULT_GENRE_GENES)
    genes.update({k: v for k, v in current.items() if v not in (None, "", [])})
    result["genre_genes"] = genes
    return result
```

- [ ] **Step 4: Wire into `ChiefEditorAgent._validate_outline`**

At the end of `_validate_outline`, before `return outline`, add:

```python
from novel_agent.control.genre_genes import ensure_genre_genes

outline = ensure_genre_genes(outline)
return outline
```

If the file already has top-level imports only, place the import at the top.

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "genre_genes"
```

Expected: 2 passed.

---

### Task 2: Upgrade Chapter Plans Into Rolling Window Items

**Files:**
- Create: `novel_agent/control/chapter_window.py`
- Modify: `web/server.py`
- Modify: `web/models.py`
- Modify: `web/frontend/src/views/Dashboard.vue`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
def test_normalize_chapter_window_adds_pacing_fields(self):
    from novel_agent.control.chapter_window import normalize_chapter_window
    raw = [{"chapter_id": "001", "title": "开播", "goal": "主角首次证明自己"}]

    result = normalize_chapter_window(raw)

    item = result[0]
    self.assertEqual(item["chapter_id"], "001")
    self.assertEqual(item["chapter_type"], "铺垫章")
    self.assertEqual(item["plot_task"]["what_happens"], "主角首次证明自己")
    self.assertEqual(item["payoff_task"]["has_payoff"], False)
    self.assertIn("hook", item)

def test_pacing_report_flags_too_many_setup_chapters(self):
    from novel_agent.control.chapter_window import build_pacing_report
    items = [{"chapter_type": "铺垫章"} for _ in range(5)] + [{"chapter_type": "爆发章"}]

    report = build_pacing_report(items)

    self.assertFalse(report["pass"])
    self.assertIn("铺垫章过多", report["issues"][0])
```

- [ ] **Step 2: Implement `chapter_window.py`**

```python
from typing import Any, Dict, List


DEFAULT_TYPES = ("铺垫章", "蓄力章", "爆发章", "过渡章")


def normalize_chapter_window(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for index, item in enumerate(items):
        goal = item.get("goal") or item.get("chapter_goal") or item.get("title") or ""
        chapter_type = item.get("chapter_type") or ("爆发章" if (index + 1) % 5 == 0 else "铺垫章")
        normalized.append({
            "chapter_id": item.get("chapter_id", f"{index + 1:03d}"),
            "title": item.get("title") or item.get("chapter_title") or "",
            "goal": goal,
            "chapter_type": chapter_type if chapter_type in DEFAULT_TYPES else "铺垫章",
            "plot_task": item.get("plot_task") or {
                "what_happens": goal,
                "result": item.get("output_state", ""),
            },
            "character_task": item.get("character_task") or {
                "focus": item.get("focus_characters", []),
                "change": item.get("character_change", ""),
            },
            "payoff_task": item.get("payoff_task") or {
                "has_payoff": chapter_type == "爆发章",
                "type": "",
                "setup": "",
            },
            "hook": item.get("hook", ""),
            "foreshadow": item.get("foreshadow") or {
                "plant": item.get("foreshadow_plant", []),
                "reveal": item.get("foreshadow_reveal", []),
            },
        })
    return normalized


def build_pacing_report(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    first_ten = items[:10]
    setup_count = sum(1 for item in first_ten if item.get("chapter_type") == "铺垫章")
    burst_count = sum(1 for item in first_ten if item.get("chapter_type") == "爆发章")
    issues = []
    if setup_count > 3:
        issues.append("铺垫章过多：每 10 章建议不超过 3 章")
    if burst_count < 2 and len(first_ten) >= 10:
        issues.append("爆发章不足：每 10 章建议至少 2 章")
    return {"pass": not issues, "issues": issues, "counts": {"setup": setup_count, "burst": burst_count}}
```

- [ ] **Step 3: Wire API normalization**

In `web/server.py`, after `generate_chapter_plan()` receives AI chapters, call:

```python
from novel_agent.control.chapter_window import normalize_chapter_window, build_pacing_report

normalized = normalize_chapter_window(chapters)
return {"chapters": normalized, "outline": outline, "pacing_report": build_pacing_report(normalized)}
```

- [ ] **Step 4: Update Dashboard batch fill**

In `Dashboard.vue`, when applying AI-generated chapters, keep existing `goal` behavior but store the full item in row metadata if the component already has an extensible row object. If it does not, use goal text:

```ts
goal: `${item.chapter_type || '章节'}：${item.goal || item.plot_task?.what_happens || ''}`
```

- [ ] **Step 5: Run backend and frontend checks**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "chapter_window or pacing"
cd web/frontend; npm run build
```

Expected: tests pass and frontend builds.

---

### Task 3: Extend Narrative Debt With Deadlines

**Files:**
- Modify: `novel_agent/state/sqlite_store.py`
- Create: `novel_agent/control/narrative_debt.py`
- Modify: `novel_agent/agents/state_extractor.py`
- Modify: `web/server.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
def test_narrative_debt_marks_overdue_items(self):
    from novel_agent.control.narrative_debt import classify_debt
    items = [{"id": "F001", "status": "open", "deadline_chapter": "010", "title": "短信号码"}]

    result = classify_debt(items, current_chapter="012")

    self.assertEqual(result[0]["debt_status"], "overdue")

def test_sqlite_store_preserves_deadline_metadata_for_foreshadows(self):
    store = SQLiteStateStore(self.tmpdir)
    store.sync_state_update("001", {
        "foreshadows": [{
            "id": "F001",
            "title": "短信号码",
            "status": "open",
            "description": "未知号码发来提醒",
            "deadline_chapter": "010",
            "related_characters": ["沈星璃"],
        }]
    })

    item = store.list_foreshadows()[0]

    self.assertEqual(item["deadline_chapter"], "010")
    self.assertEqual(item["related_characters"], ["沈星璃"])
```

- [ ] **Step 2: Extend SQLite schema**

Add nullable columns to `foreshadows`, `hooks`, `reader_promises`, and `secrets`:

```sql
deadline_chapter text,
reveal_chapter text,
pressure_level text,
related_characters text
```

In `_ensure_schema`, after table creation, call a helper that runs `alter table` only when a column is missing.

- [ ] **Step 3: Update marker upsert/list serialization**

Store `related_characters` as JSON text with `ensure_ascii=False`. Return it as a list from list methods. Return deadline fields as strings.

- [ ] **Step 4: Implement `narrative_debt.py`**

```python
from typing import Any, Dict, List


def _to_int(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def classify_debt(items: List[Dict[str, Any]], current_chapter: str) -> List[Dict[str, Any]]:
    current = _to_int(current_chapter)
    result = []
    for item in items:
        deadline = _to_int(item.get("deadline_chapter"))
        status = item.get("status", "")
        debt_status = "resolved" if status in ("resolved", "revealed", "closed") else "open"
        if deadline and current > deadline and debt_status == "open":
            debt_status = "overdue"
        elif deadline and current >= deadline - 2 and debt_status == "open":
            debt_status = "due_soon"
        result.append({**item, "debt_status": debt_status})
    return result
```

- [ ] **Step 5: Add API endpoint**

In `web/server.py`:

```python
@app.get("/api/control/narrative-debt")
def get_narrative_debt(current_chapter: str = "") -> Dict[str, Any]:
    store = SQLiteStateStore(get_root_dir())
    chapter = current_chapter or "000"
    return {
        "foreshadows": classify_debt(store.list_foreshadows(), chapter),
        "reader_promises": classify_debt(store.list_reader_promises(), chapter),
        "secrets": classify_debt(store.list_secrets(), chapter),
    }
```

- [ ] **Step 6: Run tests**

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "narrative_debt or deadline_metadata"
```

Expected: tests pass.

---

### Task 4: Convert Recall Into Constraints

**Files:**
- Create: `novel_agent/control/constraint_synthesizer.py`
- Modify: `novel_agent/agents/context_builder.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
def test_constraint_synthesizer_turns_secret_into_constraint(self):
    from novel_agent.control.constraint_synthesizer import synthesize_constraints
    state = {"secrets": [{"title": "真实身份", "status": "hidden", "description": "沈星璃不能知道父亲身份"}]}

    constraints = synthesize_constraints(state=state, recall_items=[], scene={})

    self.assertIn("不可提前揭露：真实身份", constraints[0])

def test_context_builder_includes_synthesized_constraints(self):
    store = SQLiteStateStore(self.tmpdir)
    store.upsert_secret({
        "id": "SEC_001",
        "title": "真实身份",
        "status": "hidden",
        "description": "沈星璃不能知道父亲身份",
        "chapter_id": "001",
    })
    agent = ContextBuilderAgent(self.tmpdir)

    context = agent.build("测试目标", {"scene_id": "002-01", "purpose": "测试"})

    self.assertIn("本章硬约束", context)
    self.assertIn("不可提前揭露：真实身份", context)
```

- [ ] **Step 2: Implement synthesizer**

```python
from typing import Any, Dict, List


def synthesize_constraints(
    state: Dict[str, Any],
    recall_items: List[Dict[str, Any]],
    scene: Dict[str, Any],
) -> List[str]:
    constraints: List[str] = []
    for secret in state.get("secrets", []):
        if secret.get("status") in ("hidden", "open"):
            constraints.append(f"不可提前揭露：{secret.get('title', '')}。{secret.get('description', '')}".strip())
    for promise in state.get("reader_promises", []):
        if promise.get("debt_status") in ("due_soon", "overdue"):
            constraints.append(f"需要推进读者承诺：{promise.get('title', '')}。{promise.get('description', '')}".strip())
    for item in recall_items[:3]:
        text = item.get("text", "")
        if text:
            constraints.append(f"历史一致性参考：{text[:120]}")
    return [item for item in constraints if item]
```

- [ ] **Step 3: Insert constraints block in context builder**

In `ContextBuilderAgent.build`, after state/debt blocks:

```python
from novel_agent.control.constraint_synthesizer import synthesize_constraints

constraints = synthesize_constraints(state=state, recall_items=[], scene=scene)
if constraints:
    blocks.append(("本章硬约束", self._bullets(constraints), PRIORITY_HIGH))
```

- [ ] **Step 4: Run tests**

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "constraint"
```

Expected: tests pass.

---

### Task 5: Add 10-Chapter Calibration Reports

**Files:**
- Create: `novel_agent/control/calibration.py`
- Modify: `web/server.py`
- Modify: `novel_agent/orchestrator.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
def test_calibration_report_detects_genre_drift_and_debt(self):
    from novel_agent.control.calibration import build_calibration_report
    outline = {"genre_genes": {"drift_guards": ["不要连续三章没有外部压力或可见进展"]}}
    chapters = [{"chapter_id": "001", "chapter_type": "过渡章"} for _ in range(4)]
    debt = {"foreshadows": [{"id": "F001", "debt_status": "overdue", "title": "短信号码"}]}

    report = build_calibration_report(outline, chapters, debt)

    self.assertFalse(report["pass"])
    self.assertIn("存在过期叙事债务", report["issues"])
```

- [ ] **Step 2: Implement `calibration.py`**

```python
from typing import Any, Dict, List

from novel_agent.control.chapter_window import build_pacing_report


def build_calibration_report(
    outline: Dict[str, Any],
    chapters: List[Dict[str, Any]],
    debt: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    issues: List[str] = []
    pacing = build_pacing_report(chapters[-10:])
    if not pacing["pass"]:
        issues.extend(pacing["issues"])
    overdue = []
    for items in debt.values():
        overdue.extend([item for item in items if item.get("debt_status") == "overdue"])
    if overdue:
        issues.append("存在过期叙事债务")
    return {
        "pass": not issues,
        "issues": issues,
        "pacing": pacing,
        "overdue_debt_count": len(overdue),
        "genre_genes": outline.get("genre_genes", {}),
    }
```

- [ ] **Step 3: Add API endpoint**

In `web/server.py`, add:

```python
@app.get("/api/control/calibration")
def get_calibration_report() -> Dict[str, Any]:
    outline = get_outline()
    chapters = [item.model_dump() for item in list_chapters()]
    debt = get_narrative_debt(current_chapter=chapters[-1]["chapter_id"] if chapters else "000")
    return build_calibration_report(outline, chapters, debt)
```

- [ ] **Step 4: Hook periodic report after chapters**

In `NovelOrchestrator.run_novel`, after each successful chapter:

```python
if chapter_num % 10 == 0:
    self._write_calibration_report(chapter_id)
```

Implement `_write_calibration_report()` by reading `outline.json`, chapter summaries, debt state, calling `build_calibration_report`, and writing `workspace/reports/calibration_chapter_<id>.json`.

- [ ] **Step 5: Run tests**

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "calibration"
```

Expected: tests pass.

---

### Task 6: Add Longform Control Dashboard

**Files:**
- Create: `web/frontend/src/views/ControlPlaneView.vue`
- Modify: `web/frontend/src/api.ts`
- Modify: `web/frontend/src/App.vue`
- Modify: `web/frontend/src/router.ts`

- [ ] **Step 1: Add API client methods**

In `api.ts`:

```ts
export const getNarrativeDebt = (currentChapter = '') =>
  api.get('/control/narrative-debt', { params: { current_chapter: currentChapter } })

export const getCalibrationReport = () =>
  api.get('/control/calibration')
```

- [ ] **Step 2: Add route and sidebar item**

In `router.ts`:

```ts
{ path: '/control', name: 'control-plane', component: () => import('./views/ControlPlaneView.vue') },
```

In `App.vue`, import an Element Plus icon such as `SetUp`, then add after 阅读:

```ts
{ path: '/control', label: '长篇控制', icon: SetUp },
```

- [ ] **Step 3: Create dashboard view**

The page should show four compact panels:

```vue
<template>
  <section class="control-page">
    <header class="page-head">
      <h1>长篇控制</h1>
      <el-button type="primary" @click="loadAll">刷新</el-button>
    </header>
    <div class="control-grid">
      <article class="panel">
        <h2>类型基因</h2>
        <pre>{{ JSON.stringify(outline.genre_genes || {}, null, 2) }}</pre>
      </article>
      <article class="panel">
        <h2>校准报告</h2>
        <el-tag :type="calibration.pass ? 'success' : 'warning'">
          {{ calibration.pass ? '稳定' : '需校准' }}
        </el-tag>
        <p v-for="issue in calibration.issues || []" :key="issue">{{ issue }}</p>
      </article>
      <article class="panel">
        <h2>叙事债务</h2>
        <p>伏笔：{{ debt.foreshadows?.length || 0 }}</p>
        <p>秘密：{{ debt.secrets?.length || 0 }}</p>
        <p>读者承诺：{{ debt.reader_promises?.length || 0 }}</p>
      </article>
      <article class="panel">
        <h2>节奏提醒</h2>
        <p v-for="issue in calibration.pacing?.issues || []" :key="issue">{{ issue }}</p>
      </article>
    </div>
  </section>
</template>
```

Use the same panel/card style already used in `ChapterDetail.vue` and `ConfigView.vue`; do not create nested cards.

- [ ] **Step 4: Build frontend**

```powershell
cd web/frontend; npm run build
```

Expected: build succeeds.

---

### Task 7: Full Verification and Packaging

**Files:**
- No source edits unless verification fails.

- [ ] **Step 1: Run Python tests**

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend build**

```powershell
cd web/frontend; npm run build
```

Expected: build succeeds. Existing Rolldown pure-annotation and chunk-size warnings are acceptable unless they become errors.

- [ ] **Step 3: Package desktop software**

```powershell
cd web/frontend; npm run electron:build
```

Expected: `web/frontend/dist-desktop/win-unpacked/NovelAgent.exe` and `web/frontend/dist-desktop/NovelAgent Setup 1.0.0.exe` are regenerated.

- [ ] **Step 4: Smoke-test packaged app**

Run:

```powershell
Start-Process "D:\path\to\novel-agent\web\frontend\dist-desktop\win-unpacked\NovelAgent.exe"
```

Verify:
- Sidebar includes `阅读` and `长篇控制`.
- `长篇控制` loads type genes, debt counts, and calibration report.
- Existing chapter generation still works.
- Chapter detail still shows `重写本章`.

---

## Execution Order

1. Task 1: L0 Genre Genes.
2. Task 2: Structured rolling chapter window.
3. Task 3: Narrative debt deadlines.
4. Task 4: Constraint synthesis.
5. Task 5: 10-chapter calibration.
6. Task 6: Frontend control dashboard.
7. Task 7: Full verification and packaging.

This order keeps each feature independently testable and avoids a risky full rewrite of the existing generation pipeline.

## Self-Review

- Spec coverage: The plan covers the article’s L0-L3 split, rolling window, pacing hard constraints, narrative debt ledger, constraint-based recall usage, active compression/calibration direction, and a human-facing control dashboard.
- Scope control: The plan does not replace the existing orchestrator, prompt system, model library, or reader page.
- Type consistency: Shared names are `genre_genes`, `chapter_type`, `plot_task`, `character_task`, `payoff_task`, `foreshadow`, `deadline_chapter`, `debt_status`, and `calibration`.
