# 栖墨 V2 Phase 0 工程与安全基线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 V2 实施前已确认的 P0/P1 缺陷，建立可重复安装、项目级任务隔离、Electron 安全和 Python 3.11/3.12 质量门禁。

**Architecture:** 保留现有 FastAPI、SQLite、Vue 与 Electron 主体，只收紧边界。进度回调改为任务执行上下文而不是 `TaskManager` 构造时覆盖全局单例；项目删除始终查询目标项目的任务管理器；Electron 的 URL、IPC sender 和参数由纯函数安全模块统一校验。所有行为修复先建立失败证据，再做最小实现。

**Tech Stack:** Python 3.11/3.12、FastAPI、pytest、SQLite、Vue 3、TypeScript、Vitest、Electron、GitHub Actions

---

## 文件结构

### 新建

- `web/frontend/electron/security.ts`：应用来源、导航、IPC sender 与 IPC 参数的纯函数校验。
- `web/frontend/electron/security.test.ts`：Electron 安全纯函数单元测试。
- `web/frontend/vitest.electron.config.ts`：Electron 主进程单元测试配置。
- `pyproject.toml`：Ruff 与 Python 版本的工程基线。

### 修改

- `web/frontend/package-lock.json`：与 `package.json` 同步并锁定可干净安装的依赖树。
- `web/frontend/package.json`：加入 Electron 单元测试和审计脚本。
- `.github/workflows/novel-agent-smoke.yml`：Python 3.11/3.12、前端干净安装、Electron 单测与审计门禁。
- `.github/workflows/novel-agent-full.yml`：Python 3.11/3.12 矩阵和 Electron 构建门禁。
- `PROJECT.md`：把正式 Python 支持范围从 3.8+ 改为 3.11/3.12。
- `CONTRIBUTING.md`：移除 `electron_version` 同步说明并记录新门禁。
- `tests/test_brand_contract.py`：品牌测试只读取规范 Electron 源。
- `tests/test_security_regressions.py`：安全测试只读取 Git 跟踪的规范 Electron 源。
- `web/routes/chapters/versions.py`：显式导入并调用章节快照函数。
- `tests/api/test_api_chapters.py`：验证版本激活前一定产生旧正文快照。
- `novel_agent/progress.py`：增加基于 `ContextVar` 的任务级进度与中止处理器。
- `web/tasks.py`：所有后台任务通过统一的任务上下文包装器启动。
- `web/tasks_autopilot.py`：自动续跑任务也通过统一包装器启动。
- `tests/test_project_task_registry.py`：覆盖两个项目同章号并发时的进度隔离。
- `web/routes/projects.py`：删除任意项目之前检查目标项目任务。
- `tests/api/test_api_tasks.py`：覆盖删除非当前但仍有活动任务的项目。
- `web/frontend/electron/main.ts`：启用 sandbox，限制导航/新窗口，校验 IPC。
- `web/frontend/electron/ipc/pet-ipc.ts`：所有宠物 IPC 使用同一 sender 和参数校验。
- `web/frontend/electron/windows/pet-window.ts`：宠物窗口启用 sandbox。
- `web/frontend/electron/windows/bubble-window.ts`：气泡窗口启用 sandbox。
- `web/frontend/electron/preload.ts`：移除未使用章节直连能力并收紧类型。
- `web/frontend/tsconfig.electron.json`：排除 Electron 测试文件的生产编译输出。

### 删除

- `web/frontend/electron/main.cjs`：未被构建入口引用的旧主进程。
- `web/frontend/electron/server/`：已被 TypeScript 配置排除的旧 Express 服务。
- `web/frontend/electron/database/`：只服务于旧 Express 服务的 SQLite 层。
- `scripts/sync_electron_canonical.ps1`：只同步到被忽略 `electron_version` 的旧脚本。
- `scripts/_patch_orchestrator_delegate.py`：一次性补丁脚本。
- `scripts/_extract_novel_batch.py`：一次性抽取脚本。
- `scripts/_trim_audit_sync_rewrite.py`：一次性改写脚本。

## Task 1：恢复干净安装并固定运行时矩阵

**Files:**

- Modify: `web/frontend/package-lock.json`
- Modify: `web/frontend/package.json`
- Modify: `.github/workflows/novel-agent-smoke.yml`
- Modify: `.github/workflows/novel-agent-full.yml`
- Modify: `PROJECT.md`

- [x] **Step 1: 记录干净安装失败**

Run:

```powershell
npm ci --prefix web/frontend
```

Expected: FAIL，错误明确指出 `package.json` 与 `package-lock.json` 不同步，包含 `@emnapi/wasi-threads` 或缺失的 `@emnapi/*` 条目。

- [x] **Step 2: 只重建锁文件**

Run:

```powershell
npm install --prefix web/frontend --package-lock-only --ignore-scripts
```

Expected: exit 0，只有 `web/frontend/package-lock.json` 发生依赖解析相关变化。

- [x] **Step 3: 增加统一前端门禁脚本**

在 `web/frontend/package.json` 的 `scripts` 中加入：

```json
"test:electron": "vitest run --config vitest.electron.config.ts",
"audit:prod": "npm audit --omit=dev --audit-level=high"
```

- [x] **Step 4: 将 CI 改为 Python 3.11/3.12 矩阵**

Python job 使用：

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.11", "3.12"]
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
```

前端 job 在 `npm ci` 后依次运行：

```yaml
- run: npm run test:unit
- run: npm run test:electron
- run: npm run build
- run: npm run build:electron
- run: npm run audit:prod
```

- [x] **Step 5: 更新正式支持版本**

把 `PROJECT.md` 技术栈中的 Python 版本改为：

```markdown
| 后端 | Python 3.11/3.12, FastAPI, uvicorn |
```

- [x] **Step 6: 验证干净安装**

Run:

```powershell
npm ci --prefix web/frontend
```

Expected: PASS，不再出现 lockfile 同步错误。

- [x] **Step 7: 提交**

```powershell
git add web/frontend/package.json web/frontend/package-lock.json .github/workflows/novel-agent-smoke.yml .github/workflows/novel-agent-full.yml PROJECT.md
git commit -m "build: restore reproducible v2 toolchain"
```

## Task 2：移除非自包含 Electron 副本测试与一次性脚本

**Files:**

- Modify: `tests/test_brand_contract.py`
- Modify: `tests/test_security_regressions.py`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/IMPROVEMENT-ROADMAP-2026Q2.md`
- Modify: `docs/ELECTRON-LAYOUT.md`
- Modify: `.gitignore`
- Modify: `web/frontend/tsconfig.electron.json`
- Create: `web/frontend/build/icon.png`
- Create: `web/frontend/build/icon.ico`
- Create: `web/frontend/build/tray_icon.png`
- Delete: `scripts/sync_electron_canonical.ps1`
- Delete: `scripts/_patch_orchestrator_delegate.py`
- Delete: `scripts/_extract_novel_batch.py`
- Delete: `scripts/_trim_audit_sync_rewrite.py`
- Delete: `web/frontend/electron/main.cjs`
- Delete: `web/frontend/electron/server/app.ts`
- Delete: `web/frontend/electron/server/routes/assets.ts`
- Delete: `web/frontend/electron/server/routes/chapters.ts`
- Delete: `web/frontend/electron/server/routes/config.ts`
- Delete: `web/frontend/electron/server/routes/export.ts`
- Delete: `web/frontend/electron/server/routes/state.ts`
- Delete: `web/frontend/electron/database/connection.ts`

- [x] **Step 1: 运行干净工作区中的失败测试**

Run:

```powershell
py -3.12 -m pytest tests/test_brand_contract.py tests/test_security_regressions.py -q --tb=short
```

Expected: FAIL，失败路径包含不存在且被忽略的 `electron_version/`。

- [x] **Step 2: 跟踪规范桌面图标**

在 `.gitignore` 的 `build/` 规则后加入：

```gitignore
!web/frontend/build/
!web/frontend/build/icon.png
!web/frontend/build/icon.ico
!web/frontend/build/tray_icon.png
```

把现有规范图标放入 `web/frontend/build/` 并纳入 Git。它们已经由 `package.json` 的 Electron `files`、`asarUnpack` 和 `win.icon` 引用，不能依赖开发者机器残留。

- [x] **Step 3: 让品牌测试只读取规范目录**

删除 `ELECTRON_COPY`，把所有：

```python
for root in (FRONTEND, ELECTRON_COPY):
```

替换为：

```python
for root in (FRONTEND,):
```

- [x] **Step 4: 让安全测试只读取规范目录**

把旧导出测试改为只检查：

```python
source = (root / "web/frontend/electron/server/routes/export.ts").read_text(
    encoding="utf-8"
)
```

随后在删除旧 server 的同一提交中删除该测试；保留主进程源码扫描时只扫描：

```python
electron_root = root / "web/frontend/electron"
for path in electron_root.rglob("*.ts"):
    ...
```

- [x] **Step 5: 删除无构建引用的旧实现和一次性脚本**

先运行：

```powershell
rg -n "main\\.cjs|electron/server|electron/database|sync_electron_canonical|_patch_orchestrator_delegate|_extract_novel_batch|_trim_audit_sync_rewrite" . -g "!docs/superpowers/**"
```

Expected: 只剩待更新文档、旧测试或文件自身引用。完成对应更新后删除文件。

- [x] **Step 6: 更新贡献文档**

删除 `electron_version` 同步章节，并明确：

```markdown
桌面壳唯一源码位于 `web/frontend/electron/`；测试和打包不得读取本地忽略副本。
```

- [x] **Step 7: 验证**

Run:

```powershell
py -3.12 -m pytest tests/test_brand_contract.py tests/test_security_regressions.py -q --tb=short
npm run build:electron --prefix web/frontend
```

Expected: 两条命令均 PASS。

- [x] **Step 8: 提交**

```powershell
git add .gitignore tests/test_brand_contract.py tests/test_security_regressions.py CONTRIBUTING.md scripts web/frontend/electron
git add -f web/frontend/build/icon.png web/frontend/build/icon.ico web/frontend/build/tray_icon.png
git commit -m "refactor: remove legacy electron source copies"
```

## Task 3：修复版本激活前快照静默失效

**Files:**

- Modify: `tests/api/test_api_chapters.py`
- Modify: `web/routes/chapters/versions.py`

- [x] **Step 1: 写失败的 API 回归测试**

在 `ApiChaptersTests` 中加入：

```python
def test_activate_version_snapshots_current_text_before_replacing_it(self):
    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("旧正文", encoding="utf-8")
        (chapter_dir / "plan.json").write_text(
            json.dumps({"chapter_title": "第一章"}, ensure_ascii=False),
            encoding="utf-8",
        )
        store = SQLiteStateStore(self.tmpdir)
        version_id = store.save_chapter_version(
            chapter_id="001",
            version_name="新分支",
            content="新正文",
            plan="{}",
            is_active=False,
        )

        response = TestClient(web_app).post(
            f"/api/chapters/001/versions/{version_id}/activate"
        )

        self.assertEqual(response.status_code, 200)
        snapshots = list((chapter_dir / ".snapshots").glob("snapshot_*.json"))
        self.assertEqual(len(snapshots), 1)
        payload = json.loads(snapshots[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["final_text"], "旧正文")
        self.assertEqual(
            (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8"),
            "新正文",
        )
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base
```

- [x] **Step 2: 验证测试因缺少导入而失败**

Run:

```powershell
py -3.12 -m pytest tests/api/test_api_chapters.py::ApiChaptersTests::test_activate_version_snapshots_current_text_before_replacing_it -q
```

Expected: FAIL，`.snapshots` 不存在或快照数量为 0。

- [x] **Step 3: 添加显式导入**

在 `web/routes/chapters/versions.py` 中加入：

```python
from web.routes.chapters.snapshots import create_chapter_snapshot
```

保留快照 I/O 失败时的 warning，但不再让编程错误被当作正常 I/O 错误；捕获范围调整为：

```python
except OSError as exc:
    ws_server.logger.warning(
        "Failed to create pre-activation backup snapshot: %s", exc
    )
```

- [x] **Step 4: 验证**

Run:

```powershell
py -3.12 -m pytest tests/api/test_api_chapters.py tests/test_versions.py -q --tb=short
```

Expected: PASS。

- [x] **Step 5: 提交**

```powershell
git add tests/api/test_api_chapters.py web/routes/chapters/versions.py
git commit -m "fix: preserve chapter text before version activation"
```

## Task 4：隔离多项目进度与中止上下文

**Files:**

- Modify: `tests/test_project_task_registry.py`
- Modify: `novel_agent/progress.py`
- Modify: `web/tasks.py`
- Modify: `web/tasks_autopilot.py`

- [x] **Step 1: 写并发隔离失败测试**

加入两个协程同时绑定不同处理器的测试：

```python
async def emit_for(label, received):
    with progress_handlers(
        lambda message: received.append(message["data"]["owner"]),
        lambda: False,
    ):
        await asyncio.sleep(0)
        emit_progress("writer", "running", {"owner": label}, "001")

received_a = []
received_b = []
asyncio.run(
    asyncio.gather(
        emit_for("a", received_a),
        emit_for("b", received_b),
    )
)
self.assertEqual(received_a, ["a"])
self.assertEqual(received_b, ["b"])
```

实际测试使用一个内部 `async scenario()` 后传给 `asyncio.run()`，避免把 `gather()` 建在事件循环外。

- [x] **Step 2: 验证旧全局回调发生覆盖**

Run:

```powershell
py -3.12 -m pytest tests/test_project_task_registry.py -q
```

Expected: FAIL，一个接收列表为空或收到另一个项目的 owner。

- [x] **Step 3: 在 progress 模块增加上下文处理器**

实现：

```python
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator

ProgressCallback = Callable[[Dict[str, Any]], None]
AbortCheck = Callable[[], bool]

_progress_callback_ctx: ContextVar[Optional[ProgressCallback]] = ContextVar(
    "progress_callback", default=None
)
_abort_check_ctx: ContextVar[Optional[AbortCheck]] = ContextVar(
    "abort_check", default=None
)

@contextmanager
def progress_handlers(
    progress_callback: Optional[ProgressCallback],
    abort_check: Optional[AbortCheck],
) -> Iterator[None]:
    progress_token = _progress_callback_ctx.set(progress_callback)
    abort_token = _abort_check_ctx.set(abort_check)
    try:
        yield
    finally:
        _abort_check_ctx.reset(abort_token)
        _progress_callback_ctx.reset(progress_token)
```

`emit_*` 和 `check_aborted()` 优先读取 ContextVar；原 `register_*` 只保留为 CLI 默认处理器，不能覆盖任务上下文。

- [x] **Step 4: 统一后台任务包装器**

在 `TaskManager` 中加入：

```python
async def _run_with_progress_context(self, task_id: str, awaitable):
    with progress_handlers(
        self._on_progress_emitted,
        lambda: self.is_aborted(task_id),
    ):
        return await awaitable

def _create_task(self, task_id: str, awaitable) -> asyncio.Task:
    loop = asyncio.get_running_loop()
    return loop.create_task(
        self._run_with_progress_context(task_id, awaitable)
    )
```

所有章节、批量、卷、全书和 autopilot 的 `create_task()` 都改为调用 `_create_task()`；构造函数删除 `register_progress_callback()` 和 `register_abort_check()`。

- [x] **Step 5: 验证任务隔离**

Run:

```powershell
py -3.12 -m pytest tests/test_project_task_registry.py tests/api/test_api_tasks.py tests/test_full_chain_chaos.py -q --tb=short
```

Expected: PASS。

- [x] **Step 6: 提交**

```powershell
git add tests/test_project_task_registry.py novel_agent/progress.py web/tasks.py web/tasks_autopilot.py
git commit -m "fix: isolate progress handlers by task context"
```

## Task 5：阻止删除仍有后台任务的任意项目

**Files:**

- Modify: `tests/api/test_api_tasks.py`
- Modify: `web/routes/projects.py`

- [x] **Step 1: 写失败测试**

测试建立 A、B 两个项目，激活 B，在 A 的 `TaskManager` 中加入未完成任务，然后调用：

```python
response = TestClient(web_app).delete(f"/api/projects/{first['id']}")
self.assertEqual(response.status_code, 409)
self.assertTrue((self.tmpdir / "projects" / first["id"]).exists())
```

- [x] **Step 2: 验证旧实现错误删除非当前项目**

Run:

```powershell
py -3.12 -m pytest tests/api/test_api_tasks.py::ApiTasksTests::test_delete_inactive_project_rejects_active_background_tasks -q
```

Expected: FAIL，响应不是 409 或项目目录被删除。

- [x] **Step 3: 按目标项目检查任务**

在删除路由中解析目标目录并检查：

```python
project_dir = (ws_server.BASE_DIR / "projects" / pid).resolve()
if ws_server._task_registry.has_active_tasks(project_dir):
    raise HTTPException(
        409,
        "Cannot delete project while generation tasks are running",
    )
```

目标目录仍必须由项目管理器和 ID 校验共同约束在 `projects/` 下。

- [x] **Step 4: 验证**

Run:

```powershell
py -3.12 -m pytest tests/api/test_api_tasks.py tests/test_project_task_registry.py -q --tb=short
```

Expected: PASS。

- [x] **Step 5: 提交**

```powershell
git add tests/api/test_api_tasks.py web/routes/projects.py
git commit -m "fix: protect every project with active tasks"
```

## Task 6：建立 Electron 安全边界

**Files:**

- Create: `web/frontend/electron/security.ts`
- Create: `web/frontend/electron/window-security.ts`
- Create: `web/frontend/electron/security.test.ts`
- Create: `web/frontend/vitest.electron.config.ts`
- Modify: `web/frontend/electron/main.ts`
- Modify: `web/frontend/electron/ipc/pet-ipc.ts`
- Modify: `web/frontend/electron/windows/pet-window.ts`
- Modify: `web/frontend/electron/windows/bubble-window.ts`
- Modify: `web/frontend/electron/preload.ts`
- Modify: `web/frontend/electron/agents/python-bridge.ts`
- Modify: `web/frontend/src/electron.d.ts`
- Modify: `web/frontend/tsconfig.electron.json`

- [x] **Step 1: 写安全纯函数测试**

测试必须覆盖：

```typescript
expect(isAllowedAppUrl('http://127.0.0.1:8123/workspace', origins)).toBe(true)
expect(isAllowedAppUrl('https://evil.example/', origins)).toBe(false)
const externalHosts = new Set(['docs.example'])
expect(isAllowedExternalUrl('https://docs.example/', externalHosts)).toBe(true)
expect(isAllowedExternalUrl('file:///C:/secret.txt', externalHosts)).toBe(false)
expect(() => parseWindowBounds({ x: Number.NaN, y: 1 })).toThrow()
expect(() => parseRoute('https://evil.example/')).toThrow()
expect(() => parsePetSettingsPatch({ unexpected: true })).toThrow()
```

- [x] **Step 2: 验证测试失败**

Run:

```powershell
npm run test:electron --prefix web/frontend
```

Expected: FAIL，`security.ts` 导出尚不存在。

- [x] **Step 3: 实现安全模块**

模块导出：

```typescript
export function appOrigins(isDev: boolean, apiPort: number): ReadonlySet<string>
export function isAllowedAppUrl(rawUrl: string, origins: ReadonlySet<string>): boolean
export function isAllowedExternalUrl(rawUrl: string, allowedHosts: ReadonlySet<string>): boolean
export function parseWindowBounds(value: unknown): WindowBounds
export function parseMoveDelta(value: unknown): MoveDelta
export function parseRoute(value: unknown): string
export function parsePetSettingsPatch(value: unknown): Partial<PetSettings>
```

ID 只允许 `/^[A-Za-z0-9_-]{1,64}$/`；route 必须以单个 `/` 开头且不得包含协议；坐标必须是有限数值。

- [x] **Step 4: 启用窗口 sandbox 与导航策略**

所有窗口使用：

```typescript
webPreferences: {
  preload: path.join(__dirname, 'preload.js'),
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
}
```

每个窗口注册：

```typescript
window.webContents.on('will-navigate', (event, targetUrl) => {
  if (!isAllowedAppUrl(targetUrl, origins)) event.preventDefault()
})
window.webContents.setWindowOpenHandler(({ url }) => {
  if (isAllowedExternalUrl(url)) void shell.openExternal(url)
  return { action: 'deny' }
})
```

- [x] **Step 5: 校验 IPC sender 和参数**

每个 `ipcMain.handle` 的第一步调用：

```typescript
assertTrustedSender(event, appOrigins(ctx.isDev, ctx.apiPort))
```

章节、路由、设置 patch、窗口 bounds 和 move delta 使用对应 parser。移除 `chapter:run`、`chapter:abort` 及 preload 的 `runChapter()`、`abortChapter()`，因为 renderer 已通过 FastAPI 任务接口运行章节。

- [x] **Step 6: 验证**

Run:

```powershell
npm run test:electron --prefix web/frontend
npm run build:electron --prefix web/frontend
py -3.12 -m pytest tests/test_security_regressions.py -q --tb=short
```

Expected: 全部 PASS。

- [x] **Step 7: 提交**

```powershell
git add web/frontend/electron web/frontend/vitest.electron.config.ts web/frontend/package.json web/frontend/tsconfig.electron.json tests/test_security_regressions.py
git commit -m "security: harden electron renderer boundary"
```

## Task 7：加入 Ruff 与基础静态门禁

**Files:**

- Create: `pyproject.toml`
- Modify: `.github/workflows/novel-agent-smoke.yml`
- Modify: `CONTRIBUTING.md`
- Modify: `.gitignore`
- Create: `assets/demo_projects/demo-factory-novel/workspace/outline.json`
- Create: `assets/demo_projects/demo-factory-novel/workspace/chapters/chapter_001/chapter_final.txt`
- Create: `assets/demo_projects/demo-factory-novel/workspace/chapters/chapter_002/chapter_final.txt`
- Create: `assets/demo_projects/demo-factory-novel/workspace/chapters/chapter_003/chapter_final.txt`

- [x] **Step 1: 运行未配置的静态检查**

Run:

```powershell
py -3.12 -m ruff check novel_agent web tests
```

Expected: FAIL，Ruff 未安装或现有仓库没有可执行基线。

- [x] **Step 2: 建立不掩盖真实错误的渐进配置**

创建：

```toml
[project]
requires-python = ">=3.11,<3.13"

[tool.ruff]
target-version = "py311"
line-length = 100
extend-exclude = ["build", "dist", "dist-desktop", ".worktrees"]

[tool.ruff.lint]
select = ["E9", "F63", "F7", "F82"]
```

初次全规则扫描得到 1,183 条历史告警，其中 668 条是 API 兼容测试的
`import *` 名称、246 条是未使用兼容导出、189 条是导入排序。Phase 0
不盲目删除公共导出，先阻断语法错误、未定义名称和无效控制流；导入卫生在
后续模块拆分时逐层迁移。配置没有加入全局 `ignore`。

- [x] **Step 3: 修复 Ruff 报告的真实错误**

修复了 `web/task_batch.py` 缺失的 `Optional` 导入。全量 pytest 还暴露了
示例项目 `workspace/` 被 `.gitignore` 误伤的问题，因此将示例大纲和三章
正文纳入版本控制，确保干净 worktree 与 CI 可以导入同一套示例书。

- [x] **Step 4: 加入 CI 和贡献文档**

安装并运行：

```yaml
python -m pip install ruff
python -m ruff check novel_agent web tests
```

本地贡献文档使用相同命令。

- [x] **Step 5: 验证**

Run:

```powershell
py -3.12 -m ruff check novel_agent web tests
py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

Actual: Ruff 全绿；pytest 为 752 passed、4 skipped、10 subtests passed。

- [x] **Step 6: 提交**

```powershell
git add pyproject.toml .github/workflows/novel-agent-smoke.yml CONTRIBUTING.md novel_agent web tests
git commit -m "build: add python static quality gate"
```

## Task 8：Phase 0 全量验收

**Files:**

- Modify: `docs/superpowers/plans/2026-07-27-v2-phase-0-foundation.md`

- [ ] **Step 1: 后端全量验证**

Run:

```powershell
py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

Expected: 0 failed。

- [ ] **Step 2: 前端与 Electron 验证**

Run:

```powershell
npm run test:unit --prefix web/frontend
npm run test:electron --prefix web/frontend
npm run build --prefix web/frontend
npm run build:electron --prefix web/frontend
npm run check:bundle --prefix web/frontend
```

Expected: 所有命令 exit 0。

- [ ] **Step 3: 安全、依赖与性能验证**

Run:

```powershell
npm run audit:prod --prefix web/frontend
py -3.12 -m ruff check novel_agent web tests
py -3.12 scripts/perf_api_baseline.py --check
```

Expected: production audit 无 high/critical，Ruff 无错误，API p95 达到现有预算。

- [ ] **Step 4: 干净安装验证**

删除隔离工作区的 `web/frontend/node_modules` 后重新运行：

```powershell
npm ci --prefix web/frontend
npm run test:unit --prefix web/frontend
npm run build --prefix web/frontend
```

Expected: 干净安装、测试和构建均通过。

- [ ] **Step 5: 更新勾选状态并提交**

把本计划已完成步骤改为 `[x]`，记录实际测试数量和审计结果，然后：

```powershell
git add docs/superpowers/plans/2026-07-27-v2-phase-0-foundation.md
git commit -m "docs: record v2 phase 0 verification"
```
