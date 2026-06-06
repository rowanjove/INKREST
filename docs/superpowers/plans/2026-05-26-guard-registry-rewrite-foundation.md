# Guard Registry And Rewrite Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn scattered chapter checks into one visible guard summary, with hard failures for empty/invalid chapters and a foundation for later user-approved rewrites.

**Architecture:** Add a small `novel_agent.quality.guard_registry` module that defines one normalized `GuardSummary` shape and adapts current checks into it. Keep existing `quality.json`, `audit.json`, and `continuity.json` behavior, but enrich `quality.json` with `guard_summary` so the current UI can show a single truth source. This phase avoids schema migration and full diff-based rewrite adoption; it makes the gate system reliable first.

**Tech Stack:** Python 3, pytest/unittest, existing NovelAgent orchestrator, Vue 3 + Element Plus for display.

---

## Source Article: Usable Parts

- Use a single guard registry as the truth source for chapter validation.
- Standardize each check result with status, severity, code, message, evidence, suggestion, confidence, and location.
- Separate hard gates from soft gates. Hard failures block or clearly fail quality; soft gates warn without stopping generation.
- Treat rewriting as a controlled loop with reports and user approval, not silent overwrites.
- Preserve old artifacts while adding richer reports.

## Current Project Fit

- Existing quality checks live in `novel_agent/quality/report.py`.
- Existing safety audit and continuity checks run in `novel_agent/orchestrator.py`.
- Existing chapter detail UI already renders `quality_report`, so phase 1 can expose guard data without a new page.
- Empty text currently passes some checks because individual checks return pass on empty input. A hard `non_empty_final_text` guard fixes the user-visible bug directly.

## File Structure

- Create `novel_agent/quality/guard_registry.py`
  - Defines `GuardFinding`, `GuardResult`, `GuardSummary`.
  - Registers hard and soft guards.
  - Converts existing quality checks into normalized guard results.
  - Builds a serializable guard summary.
- Modify `novel_agent/quality/report.py`
  - Add `guard_summary` to the returned quality report.
  - Derive `overall_pass` from the guard summary when hard failures exist.
- Modify `novel_agent/orchestrator.py`
  - Keep writing `quality.json`; later phases can use the same summary to decide approval/rewrite behavior.
- Modify `web/frontend/src/components/ChapterQualityReport.vue`
  - Show hard/soft guard summary above the existing check cards.
  - Display hard failures clearly so “0 字符合要求” cannot appear as success.
- Test in `tests/test_pipeline.py`
  - Unit tests for guard summary shape.
  - Regression test for empty chapter hard failure.
  - Regression test that non-empty text can pass hard guards while retaining soft warnings.

---

### Task 1: Guard Registry Core

**Files:**
- Create: `novel_agent/quality/guard_registry.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests to `PipelineTests`:

```python
def test_guard_summary_marks_empty_chapter_as_hard_fail(self):
    from novel_agent.quality.guard_registry import build_guard_summary

    summary = build_guard_summary("", checks={})

    self.assertEqual(summary["overall_status"], "FAIL")
    self.assertIn("non_empty_final_text", summary["blocked_by"])
    result = summary["results"][0]
    self.assertEqual(result["guard"], "non_empty_final_text")
    self.assertEqual(result["status"], "FAIL")
    self.assertEqual(result["level"], 1)

def test_guard_summary_allows_non_empty_chapter_without_hard_fail(self):
    from novel_agent.quality.guard_registry import build_guard_summary

    summary = build_guard_summary("林澈推开门，雨水从袖口滴到地上。", checks={})

    self.assertNotIn("non_empty_final_text", summary["blocked_by"])
    self.assertNotEqual(summary["overall_status"], "FAIL")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "guard_summary"
```

Expected: FAIL because `novel_agent.quality.guard_registry` does not exist.

- [ ] **Step 3: Implement minimal registry**

Create `novel_agent/quality/guard_registry.py` with dataclasses, status aggregation, and `non_empty_final_text`.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "guard_summary"
```

Expected: PASS.

### Task 2: Quality Report Integration

**Files:**
- Modify: `novel_agent/quality/report.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests:

```python
def test_quality_report_includes_guard_summary(self):
    from novel_agent.quality.report import build_quality_report

    report = build_quality_report("林澈推开门，雨水从袖口滴到地上。")

    self.assertIn("guard_summary", report)
    self.assertIn("results", report["guard_summary"])

def test_quality_report_empty_text_is_not_overall_pass(self):
    from novel_agent.quality.report import build_quality_report

    report = build_quality_report("")

    self.assertFalse(report["overall_pass"])
    self.assertEqual(report["guard_summary"]["overall_status"], "FAIL")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "quality_report"
```

Expected: FAIL because `guard_summary` is not present and empty text currently passes several checks.

- [ ] **Step 3: Integrate guard summary**

Call `build_guard_summary(final_text, checks)` inside `build_quality_report`, include it in the returned dict, and make `overall_pass` false if `overall_status == "FAIL"`.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "guard_summary or quality_report"
```

Expected: PASS.

### Task 3: Frontend Guard Visibility

**Files:**
- Modify: `web/frontend/src/components/ChapterQualityReport.vue`

- [ ] **Step 1: Add computed guard summary**

Expose `guardSummary`, `guardResults`, `blockedBy`, and Chinese labels for `PASS`, `WARN`, `FAIL`.

- [ ] **Step 2: Render summary panel**

Place a compact guard panel above existing check cards. Show:
- overall status
- hard blockers
- result cards with guard name, status, message, suggestion

- [ ] **Step 3: Build frontend**

Run:

```powershell
npm run build
```

from `web/frontend`.

Expected: build succeeds with only existing non-blocking warnings.

### Task 4: Verification

**Files:**
- Existing test and build outputs only.

- [ ] **Step 1: Run targeted tests**

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "guard_summary or quality_report"
```

- [ ] **Step 2: Run full backend tests**

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q
```

- [ ] **Step 3: Run frontend build**

```powershell
npm run build
```

from `web/frontend`.

- [ ] **Step 4: Package desktop if verification passes**

```powershell
npm run electron:build
```

from `web/frontend`. If old `NovelAgent.exe` locks `win-unpacked`, stop only the running packaged app processes and rerun.

---

## Later Phases

- Add `chapter_versions` persistence for draft/revised/adopted versions.
- Add backend rewrite task endpoints and diff reports.
- Add front-end rewrite button with reason presets, generated revised text, diff preview, and explicit adopt action.
- Add richer guards: protagonist/name drift, chapter-goal fulfillment, reader-promise overload, scene causality, dialogue naturalness.

