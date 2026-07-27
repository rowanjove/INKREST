# 栖墨 (INKREST) 小说生成 Agent — 代码审查与改进建议报告

**审查日期**: 2026-06-17
**项目版本**: 1.0.0
**技术栈**: Python (FastAPI) + Vue 3 (TypeScript) + Electron + SQLite

---

## 一、项目概述

栖墨 (INKREST) 是一个 AI 驱动的长篇智能写作系统，采用多 Agent 协作架构，通过编排器 (Orchestrator) 协调多个专业 Agent 完成小说章节的规划、生成、审计、润色等全流程。项目包含：

- **Python 后端**: FastAPI Web 服务 + CLI 工具 + 多 Agent 管道
- **Vue 3 前端**: SPA + Electron 桌面应用封装
- **数据层**: SQLite (主存储) + 向量存储 (语义检索) + 文件系统

---

## 二、架构设计评价

### 2.1 优势

| 方面 | 评价 |
|------|------|
| **模块化设计** | 项目结构清晰，`novel_agent/` 按职责分层 (agents/, services/, state/, quality/, control/, phases/) |
| **多 Agent 架构** | 采用专业分工的 Agent 模式 (ChiefEditor, ManagingEditor, Writer, Auditor 等)，职责明确 |
| **管道式执行** | ChapterPipelineRunner 实现了规划 → 生成 → 审计 → 后处理的标准化流程 |
| **检查点机制** | 支持断点续写，chapter checkpoint 可恢复已完成的阶段 |
| **插件系统** | 支持自定义 Pipeline 阶段和 Hooks，扩展性良好 |
| **多项目支持** | 通过 `projects.json` 管理多本书籍，配置分层 (global + project scoped) |
| **角色分级模型路由** | `daily` vs `reasoning` 模型分级，支持 fallback 模型 |
| **质量门禁** | unified_gate 实现质量拦截，支持自动/人工审批 |

### 2.2 架构风险

| 风险 | 严重程度 | 说明 |
|------|---------|------|
| **循环依赖** | 中 | `agents/base.py` 导入 `web.security`，`web/` 导入 `novel_agent/`，存在层间循环依赖 |
| **全局状态** | 中 | `web/context.py` 使用模块级全局变量管理活跃项目，不利于并发测试 |
| **ORM 缺失** | 低 | 纯 SQL 操作，维护成本高但可控 |
| **WAL 模式单点写入** | 中 | SQLiteWriteQueue 虽保证单线程写入，但高并发下可能成为瓶颈 |

---

## 三、代码质量分析

### 3.1 评分概览

| 维度 | 评分 (1-10) | 说明 |
|------|------------|------|
| 代码结构 | 8 | 目录清晰，职责分离良好 |
| 类型安全 | 6 | Python 类型注解覆盖较好，但存在 `Any` 过度使用；前端 TypeScript 类型严格 |
| 错误处理 | 7 | 自定义异常体系完善，但部分地方使用裸 `except Exception` |
| 测试覆盖 | 5 | 仅有少量单元测试 (`tests/`)，核心业务缺乏测试 |
| 文档注释 | 6 | 关键模块有 docstring，但复杂逻辑缺乏注释 |
| 代码重复 | 5 | 多处存在明显的代码重复 (见下文) |
| 配置管理 | 7 | YAML + JSON 配置，支持环境变量替换 |

### 3.2 具体问题清单

#### 🔴 高优先级问题

**P1-1: `OpenAILLM` 同步/异步代码重复严重**

文件: `novel_agent/agents/base.py`

`generate()` 和 `agenerate()` 方法几乎完全重复（约 100 行重复逻辑）。HTTP 请求构造、错误处理、日志记录完全相同。

```python
# 建议：将核心请求逻辑提取为独立方法
def _do_generate(self, role: str, prompt: str, is_async: bool = False) -> str:
    # 统一构造请求、发送、处理响应
    ...
```

**P1-2: `StaticLLM.generate()` 过于臃肿 (180+ 行)**

一个方法包含了 15+ 个角色的硬编码返回逻辑，违反了单一职责原则。

```python
# 建议：按角色拆分为独立方法或使用注册表模式
_STATIC_RESPONSES: Dict[str, Callable[[str], str]] = {
    "stitch_editor": _mock_stitch_editor,
    "style_editor": _mock_style_editor,
    "state_extractor": _mock_state_extractor,
    ...
}
```

**P1-3: 裸 `except Exception` 过多**

多处使用裸异常捕获，可能吞掉真正的错误：

- `cli.py:61-64` — `run_chapter_cmd`
- `cli.py:118-121` — `run_arc_cmd`
- `novel_agent/dashboard.py:151` — `json.loads` 异常吞掉
- `web/app.py:52-58` — 全局异常处理器掩盖了调试信息

**P1-4: `dashboard.py` 使用字符串拼接 HTML，存在 XSS 风险**

虽然使用了 `html.escape()`，但整个 HTML 在 Python 中拼接维护困难。建议：
- 使用 Jinja2 模板
- 或改为前端渲染（API 返回 JSON 数据）

#### 🟡 中优先级问题

**P2-1: `orchestrator.py` 过大 (400+ 行)**

`NovelOrchestrator` 类包含：单章管道、多章批处理、弧处理、检查点、hooks、成本追踪等。建议进一步拆分：

```
novel_agent/orchestrator/
  __init__.py        # 统一导出
  core.py            # NovelOrchestrator 核心
  batch.py           # 批处理逻辑 (已从 orchestrator_batch.py 合并)
  checkpoint.py      # 检查点管理 (已从 orchestrator_checkpoint.py 合并)
  hooks.py           # Hook 分发 (已从 orchestrator_hooks.py 合并)
```

**P2-2: `pipeline.py` 的 `PipelineConfig` 过于复杂**

`from_config()` 方法长达 100+ 行，包含模型解析、回退逻辑、插件初始化等。建议拆分为多个工厂方法。

**P2-3: `web/server.py` 模块替换 hack**

```python
class _ServerShim(types.ModuleType):
    ...
sys.modules[__name__] = _shim
```

这种模块替换技巧虽然为了兼容，但增加了调试难度，且 `__getattr__` 在 IDE 中无法正确推断类型。

**P2-4: 配置 schema 缺乏验证**

`pipeline.yaml` 没有 Pydantic 模型验证，错误的配置可能在运行时才发现。

**P2-5: `cli.py` 的 `_normalize_argv` hack**

```python
if any(arg.startswith("--chapter-id") or arg == "--goal" for arg in argv):
    return ["run-chapter"] + argv
```

这种参数推断过于脆弱，可能导致意外的命令解析。

#### 🟢 低优先级问题

**P3-1: 大量 `Any` 类型使用**

虽然 Python 的类型系统本来就灵活，但核心模块（如 `PipelinePhase`, `ChapterContext`）中过多使用 `Any` 降低了类型安全性。

**P3-2: `mypy`/`ruff` 等静态检查工具似乎未配置**

未发现 `pyproject.toml` 或 `setup.cfg`，缺乏：
- 代码格式化 (black/ruff)
- 类型检查 (mypy/pyright)
- lint 规则

**P3-3: 前端 `App.vue` 过于庞大 (1000+ 行)**

包含：布局、导航、状态检查、路由逻辑、健康轮询、引导向导等。建议拆分为：
- `AppLayout.vue`
- `EngineStatusPanel.vue`
- `NavigationSidebar.vue`

**P3-4: 前端 `localStorage` 直接访问**

```typescript
localStorage.setItem('setup_wizard_completed', 'true')
```

多处直接访问 `localStorage`，建议封装为类型安全的 storage service。

---

## 四、安全审查

### 4.1 已实施的安全措施 ✅

- **访问令牌**: `web/security.py` 实现了基于环境变量的访问控制
- **URL 验证**: `_assert_safe_model_base_url()` 限制出站 LLM 请求
- **路径遍历防护**: `serve_spa` 中的 `relative_to` 检查
- **敏感信息脱敏**: `_mask_config_secrets()` 隐藏 API Key
- **SQL 注入防护**: 使用参数化查询（未发现格式化字符串拼接 SQL）

### 4.2 安全风险 ⚠️

**S1: `exec`/`eval` 相关代码**

`main.py` 的 Python Interpreter Stub 在 `-c` 模式下禁用了 exec，但 `-m` 模式仍然允许执行任意模块。在打包构建中，建议进一步限制。

**S2: 文件系统操作缺乏沙箱**

```python
# cli.py
root_dir = Path(getattr(args, "root_dir", None) or getattr(args, "root", None) or ".")
```

`root_dir` 可由用户指定，如果应用以特权运行，可能导致任意文件读写。

**S3: 插件系统安全性**

```python
# web/app.py: mount_plugin_web_extensions
plugin_router = ext.get_router()
app.include_router(plugin_router, ...)
```

插件路由被直接挂载到主应用，没有沙箱隔离。恶意插件可以：
- 注册任意路由
- 访问全局 `app` 对象
- 读写文件系统

建议：
- 插件签名验证
- 插件权限声明（文件访问、网络访问等）
- 插件运行时隔离

---

## 五、性能分析

### 5.1 潜在性能问题

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| SQLite 单线程写入队列 | `sqlite_schema.py:SQLiteWriteQueue` | 高并发写入延迟 | 考虑读写分离或批量写入 |
| 向量索引重建频率 | `pipeline.py:hnsw_rebuild_every=50` | 每50章重建一次，可能卡顿 | 改为后台异步重建 |
| 大文件 JSON 加载 | `dashboard.py` | 项目大时内存占用高 | 流式加载或分页 |
| 前端全量状态刷新 | `App.vue:loadEngineStatus()` | 频繁全量请求 | 增量更新 + 缓存 |

### 5.2 LLM 调用优化

- ✅ 已实现：指数退避重试
- ✅ 已实现：Fallback 模型
- ⚠️ 缺失：请求去重（相同 prompt 可能重复调用）
- ⚠️ 缺失：并发限制（`max_workers` 仅控制线程池，未限制 LLM 并发）

---

## 六、改进建议

### 6.1 代码结构改进

```
建议的目录重构：

novel_agent/
  core/                    # 核心领域模型
    models.py              # ChapterResult, ChapterContext 等 dataclass
    exceptions.py          # 异常层次结构

  llm/                     # LLM 客户端层
    client.py              # LLMClient Protocol
    openai_client.py       # OpenAILLM
    static_client.py       # StaticLLM
    fallback.py            # FallbackLLM
    registry.py            # create_llm_registry

  agents/                  # Agent 层 (保持不变)

  pipeline/                # 管道编排
    config.py              # PipelineConfig
    runner.py              # ChapterPipelineRunner
    phases/                # 各阶段实现

  state/                   # 数据层 (保持不变)

  web/                     # 与 web 层交互的适配器
    bridge.py              # 隔离 web 依赖
```

### 6.2 引入代码质量工具

创建 `pyproject.toml`：

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

### 6.3 增加测试覆盖

优先测试的核心模块：

1. `novel_agent/agents/base.py` — LLM 客户端的 mock/fallback 逻辑
2. `novel_agent/pipeline.py` — 配置解析、环境变量替换
3. `novel_agent/state/` — 数据库操作、schema 迁移
4. `novel_agent/quality/` — 质量检测规则
5. `web/security.py` — 访问控制、令牌验证

### 6.4 配置 Schema 验证

使用 Pydantic 定义配置模型：

```python
from pydantic import BaseModel, Field

class LLMConfig(BaseModel):
    provider: str = "static"
    base_url: str | None = None
    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 4096
    temperature: float = 0.7

class PipelineConfigModel(BaseModel):
    runtime: RuntimeConfig
    chapter: ChapterConfig
    llm: LLMConfig
    embedding: EmbeddingConfig
```

### 6.5 前端改进

| 改进项 | 说明 |
|--------|------|
| 组件拆分 | `App.vue` 拆分为 < 200 行的组件 |
| API 层封装 | 统一错误处理、重试、token 刷新 |
| 状态管理 | 考虑按 domain 拆分 Pinia store |
| 单元测试 | 补充 composables 和 utils 的测试 |

---

## 七、具体修复建议

### 修复 1: 消除 OpenAILLM 的代码重复

```python
# novel_agent/agents/base.py

@dataclass
class OpenAILLM:
    # ... fields ...

    def _build_request(self, role: str, prompt: str) -> tuple[str, dict, dict]:
        """Build (url, headers, payload) for chat completions."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"你是{role}。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        return url, headers, payload

    def _handle_response(self, resp: httpx.Response, role: str, t0: float) -> str:
        """Parse response, validate, log, return content."""
        data = resp.json()
        if "choices" not in data or not data["choices"]:
            raise LLMResponseError("Invalid response structure: missing 'choices'")
        result = data["choices"][0].get("message", {}).get("content", "").strip()
        if not result:
            raise LLMResponseError("Empty response content")
        # ... logging ...
        return result

    def generate(self, role: str, prompt: str) -> str:
        url, headers, payload = self._build_request(role, prompt)
        # ... simplified retry loop using _handle_response ...

    async def agenerate(self, role: str, prompt: str) -> str:
        url, headers, payload = self._build_request(role, prompt)
        # ... simplified async retry loop ...
```

### 修复 2: 添加配置验证

```python
# novel_agent/config_schema.py
from pydantic import BaseModel, validator

class PipelineConfigValidator:
    @staticmethod
    def validate(settings: dict) -> "PipelineConfigModel":
        try:
            return PipelineConfigModel(**settings)
        except ValidationError as e:
            raise FatalPipelineError(f"Invalid configuration: {e}")
```

### 修复 3: 改进错误处理

```python
# 替换裸 except Exception

# 之前
try:
    result = orchestrator.run_chapter(...)
except Exception as exc:
    emit_error(...)

# 之后
try:
    result = orchestrator.run_chapter(...)
except FatalPipelineError:
    raise  # 致命的，直接抛出
except RecoverablePipelineError as exc:
    emit_error(...)
    # 记录但允许重试
except AgentError as exc:
    emit_error(...)
    sys.exit(1)
except Exception as exc:
    logger.exception("Unexpected error in run_chapter")
    emit_error(...)
    sys.exit(1)
```

### 修复 4: 插件安全加固

```python
# web/plugin_security.py
from dataclasses import dataclass

@dataclass
class PluginManifest:
    name: str
    version: str
    permissions: list[str]  # "file.read", "file.write", "network", etc.
    signature: str | None = None

def verify_plugin_signature(plugin_path: Path, manifest: PluginManifest) -> bool:
    """Verify plugin signature if signing is enabled."""
    ...

def check_plugin_permission(manifest: PluginManifest, action: str) -> bool:
    """Check if plugin has permission for action."""
    return action in manifest.permissions
```

---

## 八、总结

栖墨项目整体架构设计合理，模块化程度高，多 Agent 协作模式适合小说生成这类复杂任务。核心优势在于：

1. **完善的管道编排** — 检查点、阶段化、插件扩展
2. **灵活的配置系统** — 多项目、分层配置、环境变量
3. **质量保障体系** — 审计、连续性检查、风格检测

主要改进方向：

1. **消除代码重复** — OpenAILLM 同步/异步、StaticLLM 角色分发
2. **增强类型安全** — 引入 Pydantic 配置验证、减少 `Any`
3. **提升测试覆盖** — 核心模块至少达到 70% 覆盖
4. **加固安全性** — 插件沙箱、路径验证
5. **性能优化** — 向量索引异步重建、SQLite 批量写入

---

*报告生成时间: 2026-06-17*
*审查范围: novel_agent/, web/, cli.py, main.py, orchestrator.py, 前端核心组件*
