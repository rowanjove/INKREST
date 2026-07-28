# Scale-Adaptive Novel Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn NovelAgent from a single heavy generation pipeline into a scale-adaptive novel system that chooses the right outline, state, calibration, and scheduling strategy from the target story size.

**Architecture:** Add a small `scale_profile` control layer that maps user-facing length choices to internal architecture profiles. Store the chosen profile in project metadata and pipeline config, then route planning and longform controls through the profile without rewriting the whole orchestrator at once. Phase 1 makes profiles visible and enforceable; later phases add dynamic volume generation and state compression.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLite/state files, Vue 3, Element Plus, existing NovelAgent agent pipeline and pytest.

---

## Source Article: Usable Parts

### Use Now

- **Unified user entry, hidden architecture complexity.** Users choose a natural length option; the system maps it to a profile.
- **Scale bands.** `micro`, `short`, `medium`, `long`, `epic`, `infinite` should become first-class project metadata.
- **Profile config.** Each band defines planning mode, max chapters, vector usage, state mode, planning window, and calibration interval.
- **Short works stay light.** `micro` and `short` should avoid expensive longform controls unless requested.
- **Medium uses current system.** The current L0 genre genes + chapter queue + state + quality + calibration stack is best treated as the `medium` profile.
- **Long uses dynamic volumes.** `long` should not pretend it knows the full ending; it should keep global direction and generate volumes dynamically.
- **Epic uses tiered compression.** `epic` needs hot/warm/cold/archive state tiers before supporting 500+ chapters seriously.
- **Scale upgrade.** Projects should be able to move from short to medium or medium to long without recreating the project.
- **Control page visibility.** The existing `长篇控制` page should show current scale profile, planning mode, calibration interval, and upgrade pressure.

### Use Later

- **True micro single-shot generation.** Useful, but should land after profiles exist so it has a clean dispatch point.
- **Full hot/warm/cold/archive compression.** Important for `epic`, but requires schema and context-builder changes.
- **Infinite-flow container and episode isolation.** Strong idea, but it is a separate subsystem. First phase should only preserve config shape and UI language for it.
- **Automatic scale migration implementation.** Phase 1 should detect and recommend; phase 2 can perform migrations.

### Do Not Copy Blindly

- Do not disable state/vector features globally just because a profile says `vector_enabled: false`; existing projects and manual workflows may rely on them.
- Do not replace current `run_novel` in one pass. Wrap it with profile-aware decisions, then split specialized paths incrementally.
- Do not expose technical labels like `L1_lite` to normal users. Keep those in config/reporting only.

---

## Current Project Fit

- `web/models.py` currently caps backend `target_chapters` at 500, while `web/frontend/src/components/AiChatGuide.vue` allows 2000. This mismatch must be fixed first.
- `novel_agent/orchestrator.py::run_novel` always runs the heavy multi-agent path. That should become the default for `medium`, not for every scale.
- Existing `novel_agent/control/*` already gives us L0 genre genes, rolling chapter windows, pacing reports, narrative debt, and calibration. These become profile-aware rather than replaced.
- Existing project metadata in `web/server.py` already stores `target_chapters`; it should also store `scale_profile`.

---

## File Structure

- Create `novel_agent/control/scale_profile.py`
  - Owns profile definitions, user option mapping, target chapter mapping, upgrade pressure, and serialization-safe profile dicts.
- Modify `web/models.py`
  - Add optional `scale` / `scale_label` to novel plan/run/project-create request models.
  - Raise backend chapter upper bound to match UI-supported `epic` ranges.
- Modify `web/server.py`
  - Store profile metadata during project creation and novel planning.
  - Add `GET /api/control/scale-profile`.
  - Include profile data in calibration/control responses.
- Modify `novel_agent/orchestrator.py`
  - Resolve scale profile at `run_novel` start.
  - Use profile calibration interval instead of hard-coded 10.
  - Limit first-phase behavioral change to routing metadata and interval control.
- Modify `novel_agent/control/calibration.py`
  - Include scale profile and upgrade recommendation in the report.
- Modify `web/frontend/src/components/AiChatGuide.vue`
  - Replace raw chapter-number-first UX with natural scale choices while keeping numeric override.
- Modify `web/frontend/src/views/ControlPlaneView.vue`
  - Show current scale, planning mode, calibration interval, and upgrade pressure.
- Modify `web/frontend/src/api.ts`
  - Add `getScaleProfile()`.
- Test in `tests/test_pipeline.py`
  - Unit tests for profile mapping and upgrade pressure.
  - API tests for saved project profile.
  - Regression for frontend/backend max chapter mismatch via model validation.

---

## Task 1: Scale Profile Core

**Files:**
- Create: `novel_agent/control/scale_profile.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests to `tests/test_pipeline.py`:

```python
def test_scale_profile_maps_target_chapters_to_profile(self):
    from novel_agent.control.scale_profile import resolve_scale_profile

    self.assertEqual(resolve_scale_profile(target_chapters=1)["scale"], "micro")
    self.assertEqual(resolve_scale_profile(target_chapters=12)["scale"], "short")
    self.assertEqual(resolve_scale_profile(target_chapters=80)["scale"], "medium")
    self.assertEqual(resolve_scale_profile(target_chapters=300)["scale"], "long")
    self.assertEqual(resolve_scale_profile(target_chapters=800)["scale"], "epic")

def test_scale_profile_maps_user_length_label(self):
    from novel_agent.control.scale_profile import resolve_scale_profile

    self.assertEqual(resolve_scale_profile(scale_label="一章以内")["scale"], "micro")
    self.assertEqual(resolve_scale_profile(scale_label="几章")["scale"], "short")
    self.assertEqual(resolve_scale_profile(scale_label="几十章")["scale"], "medium")
    self.assertEqual(resolve_scale_profile(scale_label="一两百章")["scale"], "long")
    self.assertEqual(resolve_scale_profile(scale_label="几百上千章")["scale"], "epic")
    self.assertEqual(resolve_scale_profile(scale_label="一直更新下去")["scale"], "infinite")

def test_scale_profile_reports_upgrade_pressure(self):
    from novel_agent.control.scale_profile import build_upgrade_pressure

    pressure = build_upgrade_pressure({"scale": "short", "max_chapters": 20}, current_chapter_count=18)

    self.assertTrue(pressure["should_prompt"])
    self.assertEqual(pressure["recommended_scale"], "medium")
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "scale_profile"
```

Expected: fails because `novel_agent.control.scale_profile` does not exist.

- [ ] **Step 3: Implement `scale_profile.py`**

Create `novel_agent/control/scale_profile.py`:

```python
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

SCALE_PROFILES: Dict[str, Dict[str, Any]] = {
    "micro": {
        "scale": "micro",
        "label": "一章以内",
        "chapter_range": [1, 3],
        "max_chapters": 3,
        "planning_mode": "single_shot",
        "outline_layers": [],
        "state_layers": [],
        "vector_enabled": False,
        "calibration_interval": 0,
    },
    "short": {
        "scale": "short",
        "label": "几章",
        "chapter_range": [4, 20],
        "max_chapters": 20,
        "planning_mode": "full_upfront",
        "outline_layers": ["L0", "L3"],
        "state_layers": ["high_freq"],
        "vector_enabled": False,
        "calibration_interval": 0,
    },
    "medium": {
        "scale": "medium",
        "label": "几十章",
        "chapter_range": [21, 100],
        "max_chapters": 100,
        "planning_mode": "rolling_window",
        "outline_layers": ["L0", "L1", "L2", "L3"],
        "state_layers": ["high_freq", "mid_freq", "low_freq"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
    },
    "long": {
        "scale": "long",
        "label": "一两百章",
        "chapter_range": [101, 500],
        "max_chapters": 500,
        "planning_mode": "dynamic_volume",
        "outline_layers": ["L0", "L1_lite", "L2_dynamic", "L3"],
        "state_layers": ["hot", "warm"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
        "episode_volume": [50, 100],
    },
    "epic": {
        "scale": "epic",
        "label": "几百上千章",
        "chapter_range": [501, 3000],
        "max_chapters": 3000,
        "planning_mode": "fractal_dynamic_volume",
        "outline_layers": ["L0", "L1_minimal", "L2_dynamic", "L3"],
        "state_layers": ["hot", "warm", "cold", "archive"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
        "compress_hot_every": 10,
        "compress_warm_every": 50,
    },
    "infinite": {
        "scale": "infinite",
        "label": "一直更新下去",
        "chapter_range": [1, 999999],
        "max_chapters": 999999,
        "planning_mode": "container_episode",
        "outline_layers": ["container", "mainline", "episode", "L3"],
        "state_layers": ["persistent", "episode_temp"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
        "episode_chapters": [20, 50],
    },
}

LABEL_TO_SCALE = {profile["label"]: scale for scale, profile in SCALE_PROFILES.items()}
NEXT_SCALE = {
    "micro": "short",
    "short": "medium",
    "medium": "long",
    "long": "epic",
    "epic": "infinite",
}


def resolve_scale_profile(
    target_chapters: Optional[int] = None,
    scale: str = "",
    scale_label: str = "",
) -> Dict[str, Any]:
    resolved = scale or LABEL_TO_SCALE.get(scale_label, "")
    if not resolved:
        resolved = _scale_for_target(int(target_chapters or 20))
    profile = deepcopy(SCALE_PROFILES.get(resolved, SCALE_PROFILES["medium"]))
    if target_chapters:
        profile["target_chapters"] = int(target_chapters)
    return profile


def build_upgrade_pressure(profile: Dict[str, Any], current_chapter_count: int) -> Dict[str, Any]:
    max_chapters = int(profile.get("max_chapters") or 0)
    scale = profile.get("scale", "medium")
    if not max_chapters or max_chapters >= 999999:
        return {"should_prompt": False, "ratio": 0, "recommended_scale": ""}
    ratio = current_chapter_count / max_chapters
    recommended = NEXT_SCALE.get(scale, "")
    return {
        "should_prompt": ratio >= 0.8 and bool(recommended),
        "ratio": round(ratio, 3),
        "recommended_scale": recommended,
    }


def _scale_for_target(target: int) -> str:
    if target <= 3:
        return "micro"
    if target <= 20:
        return "short"
    if target <= 100:
        return "medium"
    if target <= 500:
        return "long"
    return "epic"
```

- [ ] **Step 4: Run tests and confirm pass**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "scale_profile"
```

Expected: all new scale profile tests pass.

---

## Task 2: Backend Models And Metadata

**Files:**
- Modify: `web/models.py`
- Modify: `web/server.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests:

```python
def test_novel_plan_request_accepts_epic_target_and_scale_label(self):
    from web.models import NovelPlanRequest

    req = NovelPlanRequest(theme="无限升级", genre="玄幻", target_chapters=1200, scale_label="几百上千章")

    self.assertEqual(req.target_chapters, 1200)
    self.assertEqual(req.scale_label, "几百上千章")

def test_plan_novel_saves_scale_profile_metadata(self):
    import web.server as web_server
    from web.models import NovelPlanRequest

    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        (self.tmpdir / "config").mkdir(parents=True)
        (self.tmpdir / "config" / "pipeline.yaml").write_text(
            "llm:\n  provider: static\nruntime:\n  max_workers: 1\nembedding:\n  provider: stub\n",
            encoding="utf-8",
        )

        result = web_server.plan_novel(NovelPlanRequest(
            theme="无限升级",
            genre="玄幻",
            target_chapters=1200,
            scale_label="几百上千章",
        ))

        self.assertEqual(result["scale_profile"]["scale"], "epic")
        saved = json.loads((self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["scale_profile"]["scale"], "epic")
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "epic_target or scale_profile_metadata"
```

Expected: fails because models do not expose `scale_label` and backend caps at 500.

- [ ] **Step 3: Update models**

Modify `web/models.py`:

```python
class NovelPlanRequest(BaseModel):
    """Request to generate a novel outline."""
    theme: str = Field(..., min_length=1)
    genre: str = Field(default="玄幻")
    target_chapters: int = Field(default=20, ge=1, le=3000)
    scale: str = ""
    scale_label: str = ""
    special_requirements: str = ""
    overwrite: bool = False


class NovelRunRequest(BaseModel):
    """Request to run the full novel generation pipeline."""
    theme: str = Field(..., min_length=1)
    genre: str = Field(default="玄幻")
    target_chapters: int = Field(default=20, ge=1, le=3000)
    scale: str = ""
    scale_label: str = ""
    special_requirements: str = ""
    dry_run: bool = False
```

- [ ] **Step 4: Save profile in `plan_novel`**

In `web/server.py`, import:

```python
from novel_agent.control.scale_profile import resolve_scale_profile
```

Inside `plan_novel`, before writing `outline.json`, add:

```python
scale_profile = resolve_scale_profile(
    target_chapters=req.target_chapters,
    scale=req.scale,
    scale_label=req.scale_label,
)
outline["scale_profile"] = scale_profile
```

- [ ] **Step 5: Run tests and confirm pass**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "epic_target or scale_profile_metadata"
```

Expected: pass.

---

## Task 3: Scale Profile API And Control Report

**Files:**
- Modify: `web/server.py`
- Modify: `novel_agent/control/calibration.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests:

```python
def test_get_scale_profile_returns_outline_profile_and_upgrade_pressure(self):
    import web.server as web_server

    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        (self.tmpdir / "workspace").mkdir(parents=True)
        (self.tmpdir / "workspace" / "outline.json").write_text(json.dumps({
            "scale_profile": {"scale": "short", "max_chapters": 20, "label": "几章"},
        }, ensure_ascii=False), encoding="utf-8")
        chapters_dir = self.tmpdir / "workspace" / "chapters"
        for i in range(1, 19):
            chapter_dir = chapters_dir / f"chapter_{i:03d}"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "chapter_final.txt").write_text("正文", encoding="utf-8")

        result = web_server.get_scale_profile()

        self.assertEqual(result["profile"]["scale"], "short")
        self.assertTrue(result["upgrade_pressure"]["should_prompt"])
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "get_scale_profile"
```

Expected: fails because endpoint/helper does not exist.

- [ ] **Step 3: Implement API helper and endpoint**

In `web/server.py`, add:

```python
@app.get("/api/control/scale-profile")
def get_scale_profile() -> Dict[str, Any]:
    outline = _read_json(get_root_dir() / "workspace" / "outline.json")
    chapters = list_chapters()
    profile = outline.get("scale_profile") or resolve_scale_profile(
        target_chapters=outline.get("target_chapters") or len(chapters) or 20
    )
    return {
        "profile": profile,
        "current_chapter_count": len(chapters),
        "upgrade_pressure": build_upgrade_pressure(profile, len(chapters)),
    }
```

Also import:

```python
from novel_agent.control.scale_profile import build_upgrade_pressure, resolve_scale_profile
```

- [ ] **Step 4: Include scale in calibration**

Modify `novel_agent/control/calibration.py` so returned reports include:

```python
"scale_profile": outline.get("scale_profile", {}),
```

- [ ] **Step 5: Run tests and confirm pass**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "get_scale_profile or calibration_report"
```

Expected: pass.

---

## Task 4: Profile-Aware Orchestrator

**Files:**
- Modify: `novel_agent/orchestrator.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add tests:

```python
def test_orchestrator_writes_scale_profile_to_outline(self):
    config = PipelineConfig.dry_run(self.tmpdir)
    orchestrator = NovelOrchestrator(config)

    orchestrator.run_novel(theme="短篇测试", genre="悬疑", target_chapters=2)

    outline = json.loads((self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8"))
    self.assertEqual(outline["scale_profile"]["scale"], "micro")

def test_orchestrator_uses_profile_calibration_interval(self):
    from novel_agent.control.scale_profile import resolve_scale_profile

    profile = resolve_scale_profile(target_chapters=80)

    self.assertEqual(profile["calibration_interval"], 20)
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "orchestrator_writes_scale_profile or profile_calibration_interval"
```

Expected: first test fails until `run_novel` writes profile.

- [ ] **Step 3: Resolve profile in `run_novel`**

In `novel_agent/orchestrator.py`, import:

```python
from novel_agent.control.scale_profile import resolve_scale_profile
```

After outline generation:

```python
scale_profile = resolve_scale_profile(target_chapters=target_chapters)
outline["scale_profile"] = scale_profile
```

Replace the hard-coded calibration interval:

```python
calibration_interval = int(scale_profile.get("calibration_interval") or 0)
...
if calibration_interval and chapter_num % calibration_interval == 0:
    self._write_calibration_report(chapter_id, all_chapters[: chapter_num])
```

- [ ] **Step 4: Run tests and confirm pass**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q tests/test_pipeline.py -k "orchestrator_writes_scale_profile or profile_calibration_interval"
```

Expected: pass.

---

## Task 5: Frontend Scale Choice

**Files:**
- Modify: `web/frontend/src/components/AiChatGuide.vue`
- Modify: `web/frontend/src/api.ts`
- Modify: `web/frontend/src/views/ControlPlaneView.vue`

- [ ] **Step 1: Add frontend API**

In `web/frontend/src/api.ts`, add:

```ts
export const getScaleProfile = () => api.get('/control/scale-profile')
```

- [ ] **Step 2: Replace raw-only scale UX**

In `AiChatGuide.vue`, add:

```ts
const scaleOptions = [
  { label: '一章以内', scale: 'micro', target_chapters: 1, hint: '热点、单场景、快速成稿' },
  { label: '几章', scale: 'short', target_chapters: 12, hint: '完整短篇，一次规划完' },
  { label: '几十章', scale: 'medium', target_chapters: 80, hint: '标准网文结构' },
  { label: '一两百章', scale: 'long', target_chapters: 200, hint: '分卷和滚动规划' },
  { label: '几百上千章', scale: 'epic', target_chapters: 800, hint: '长期连载，状态压缩' },
  { label: '一直更新下去', scale: 'infinite', target_chapters: 1200, hint: '无限流/副本制预留' },
]
const selectedScale = ref(scaleOptions[3])
```

When confirming, send:

```ts
ctxToSend.scale = selectedScale.value.scale
ctxToSend.scale_label = selectedScale.value.label
ctxToSend.target_chapters = scaleConfig.value.target_chapters
```

And include `scale` / `scale_label` in `user_input`.

- [ ] **Step 3: Add scale display to Control Plane**

In `ControlPlaneView.vue`, call `getScaleProfile()` with existing control data and display:

```vue
<section class="panel">
  <h2>体量架构</h2>
  <dl>
    <div><dt>当前档位</dt><dd>{{ scaleProfile.profile?.label || scaleProfile.profile?.scale || '未设定' }}</dd></div>
    <div><dt>规划模式</dt><dd>{{ scaleProfile.profile?.planning_mode || '未设定' }}</dd></div>
    <div><dt>校准间隔</dt><dd>{{ scaleProfile.profile?.calibration_interval || '关闭' }}</dd></div>
  </dl>
  <p v-if="scaleProfile.upgrade_pressure?.should_prompt" class="muted-line">
    已接近当前体量上限，建议升档到 {{ scaleProfile.upgrade_pressure.recommended_scale }}。
  </p>
</section>
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
npm run build
```

Expected: build exits 0. Existing Rolldown annotation/chunk warnings may remain.

---

## Task 6: Full Verification And Desktop Package

**Files:**
- No source edits unless verification fails.

- [ ] **Step 1: Run full backend tests**

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path; pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
npm run build
```

from `web/frontend`.

Expected: build exits 0.

- [ ] **Step 3: Package desktop app**

Run:

```powershell
npm run electron:build
```

from `web/frontend`.

Expected:

- `web/frontend/dist-desktop/win-unpacked/NovelAgent.exe` exists.
- `web/frontend/dist-desktop/NovelAgent Setup 1.0.0.exe` exists.

- [ ] **Step 4: Verify packaged resources**

Run:

```powershell
rg -n "scale_profile|planning_mode|一章以内|一直更新下去" web/frontend/dist-desktop/win-unpacked/resources -S
```

Expected: matches in packaged backend/frontend resources.

- [ ] **Step 5: Launch packaged app**

Run:

```powershell
$exe = 'D:\path\to\novel-agent\web\frontend\dist-desktop\win-unpacked\NovelAgent.exe'
Start-Process -FilePath $exe -WindowStyle Hidden
Start-Sleep -Seconds 8
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'NovelAgent|novel-agent-backend' } | Select-Object ProcessId,Name,ExecutablePath
```

Expected: NovelAgent and `novel-agent-backend.exe` processes are present.

---

## Phase 2 Backlog

- Add `micro` single-shot generator path.
- Add `short` full-upfront chapter generation without vector/state overhead.
- Add `long` dynamic next-volume generation when current volume has 10 chapters remaining.
- Add hot/warm state compression for `long`.
- Add cold/archive state compression for `epic`.
- Add an explicit scale-up migration endpoint:
  - `POST /api/control/scale-profile/upgrade`
  - short → medium: backfill L1/L2 and initialize vector summaries.
  - medium → long: mark ending anchor fuzzy and enable dynamic volumes.
  - long → epic: enable cold/archive compression.
- Add infinite-flow container/episode subsystem as a separate plan.

---

## Self-Review Notes

- The plan covers the article's immediately usable concepts: scale bands, config profiles, unified entry, upgrade pressure, control visibility, and profile-aware orchestration.
- The plan deliberately postpones true micro single-shot, epic compression, and infinite-flow isolation because each is a dedicated subsystem.
- No placeholders are left in task steps; each task has concrete files, tests, commands, and expected results.
