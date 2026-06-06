# 🔌 小说生成 Agent 插件开发规范

本文档旨在为开发者提供小说生成 Agent 的插件开发规范。通过本插件系统，您无需修改核心代码即可无缝扩展系统的功能，包括自定义 LLM 接入、特定格式导出、新增流水线步骤、加入质量检测规则等。

---

## 一、 插件架构与发现机制

系统支持以下三种插件发现与装载方式，优先级从高到低依次为：

1. **本地开发目录 (`plugins/`)**：最高优先级，适合开发调试。
2. **PIP 包注入 (`entry_points`)**：通过 Python 的 `importlib.metadata` 动态加载。
3. **YAML 显式配置 (`config/plugins.yaml`)**：指定 Python 模块导入路径。

### 1. 插件目录结构规范

插件可以以**单文件模式**或**文件夹包模式**存放在项目根目录的 `plugins/` 文件夹下。

#### 1.1 单文件插件（最简模式）
适合简单的逻辑扩展（如单个质量检查项）。
```text
plugins/
  ├── my_custom_guard.py    # 插件入口，内部定义 PLUGIN_CLASS
```

#### 1.2 文件夹包插件（复杂模式）
适合带有前后台路由或有第三方依赖的插件。
```text
plugins/
  └── my_complex_plugin/
      ├── __init__.py       # 必须定义 PLUGIN_CLASS 指向插件类
      ├── router.py         # 插件特有的 API 路由 (FastAPI)
      └── helpers.py        # 内部辅助函数
```

---

## 二、 插件元数据与声明配置

每个插件类都必须继承自 `PluginBase`，并实现 `get_meta` 方法。元数据决定了插件的展示名称、类型、依赖以及在前端动态渲染的**配置表单（JSON Schema）**。

### 元数据字段说明 (`PluginMeta`)

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `name` | `str` | **插件唯一标识符**（必须全局唯一，如 `docx-exporter`）。 |
| `version` | `str` | 插件版本（如 `0.1.0`）。 |
| `display_name` | `str` | 前端界面展示的友好名称。 |
| `description` | `str` | 简短描述插件的作用。 |
| `author` | `str` | 作者名称。 |
| `icon` | `str` | 标识图标或 emoji（如 `document` 或 🧩）。 |
| `plugin_type` | `PluginType` | 插件类型枚举（共 15 种）。 |
| `requires` | `List[str]` | 依赖的其他插件 `name` 列表，加载时会检查依赖状态。 |
| `min_core_version`| `str` | 所需的最低内核版本。 |
| `config_schema` | `dict` | **配置项 JSON Schema**。提供后，前端会自动生成配置对话框表单。 |

### 示例：插件元数据定义

```python
from novel_agent.plugins import PluginBase, PluginMeta, PluginType

class MyPlugin(PluginBase):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="wechat-notifier",
            display_name="微信通知插件",
            version="0.1.0",
            description="在章节生成或小说全部完成后，自动发送企业微信机器人通知。",
            author="Ryan",
            plugin_type=PluginType.EVENT_LISTENER,
            config_schema={
                "type": "object",
                "properties": {
                    "webhook_url": {
                        "type": "string",
                        "title": "Webhook 地址",
                        "description": "企业微信群机器人的 Webhook URL"
                    },
                    "notify_events": {
                        "type": "array",
                        "title": "订阅事件",
                        "description": "选择需要接收通知的事件",
                        "items": {
                            "type": "string",
                            "enum": ["chapter.completed", "novel.completed"]
                        },
                        "default": ["chapter.completed"]
                    }
                },
                "required": ["webhook_url"]
            }
        )
```

---

## 三、 15 种插件接口规范与开发示例

### 1. `pipeline_hook` — 流水线钩子
**用途**：在流水线的关键节点（大纲生成前后、章节规划前后、风格编辑前后、审核拦截、完成事件等）插入自定义控制逻辑。

```python
from novel_agent.plugins import PipelineHookPlugin, PluginMeta, PluginType

class OutlinePolishHook(PipelineHookPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="outline-polish-hook",
            display_name="大纲前置润色",
            plugin_type=PluginType.PIPELINE_HOOK
        )

    def before_outline(self, theme: str, genre: str, **kwargs) -> dict:
        # 在生成大纲前，强行注入一些风格限定参数到 kwargs 中
        kwargs["style_preference"] = "硬核科幻"
        return kwargs

    def after_outline(self, outline: dict) -> dict:
        # 大纲生成后，对其结构进行调整或修饰
        outline["macro_outline"] = [item for item in outline.get("macro_outline", [])]
        return outline

PLUGIN_CLASS = OutlinePolishHook
```

### 2. `quality_guard` — 质量守卫
**用途**：为生成的章节文本添加质量规则检测（例如敏感词、方言检查、段落排版一致性等）。

```python
from novel_agent.plugins import QualityGuardPlugin, PluginMeta, PluginType

class CharacterConsistencyGuard(QualityGuardPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="char-consistency-guard",
            display_name="角色一致性检测",
            plugin_type=PluginType.QUALITY_GUARD
        )

    def check(self, text: str, context: dict) -> dict:
        # 执行检测逻辑
        issues = []
        score = 100
        # 比如检测文中是否有错别字或称呼混淆
        if "主角小明" in text and "明哥" in text:
            issues.append("检测到同一场景中对主角混合使用了'小明'和'明哥'，请确认称呼一致性")
            score = 80
        
        return {
            "pass": len(issues) == 0,
            "score": score,
            "details": issues
        }

PLUGIN_CLASS = CharacterConsistencyGuard
```

### 3. `exporter` — 文件导出器
**用途**：支持将生成的小说导出为内置（txt/epub/pdf）之外的新格式（如 docx, markdown 等）。

```python
from pathlib import Path
from typing import List, Optional
from novel_agent.plugins import ExporterPlugin, PluginMeta, PluginType

class DocxExporter(ExporterPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="docx",
            display_name="Word 文档导出 (.docx)",
            plugin_type=PluginType.EXPORTER
        )

    def get_format(self) -> str:
        return "docx"

    def export(self, root_dir: Path, output_path: Path, chapter_ids: Optional[List[str]] = None, title: str = "", **kwargs) -> Path:
        # 使用 python-docx 或其他库导出文件
        # 执行完后返回文件路径
        output_path.write_text(f"# {title}\n(Word Export Placeholder)", encoding="utf-8")
        return output_path

PLUGIN_CLASS = DocxExporter
```

### 4. `llm_provider` — LLM 服务提供商
**用途**：对接第三方大模型服务（如 Anthropic, Gemini, DeepSeek, Ollama 等）。

```python
from novel_agent.plugins import LLMProviderPlugin, PluginMeta, PluginType

class CustomLLMClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate(self, role: str, prompt: str) -> str:
        return f"【Custom LLM】关于 {role} 的回复"

    async def agenerate(self, role: str, prompt: str) -> str:
        return self.generate(role, prompt)

class DeepSeekProvider(LLMProviderPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="deepseek-provider",
            display_name="DeepSeek 模型服务",
            plugin_type=PluginType.LLM_PROVIDER
        )

    def get_provider_name(self) -> str:
        return "deepseek"

    def create_client(self, config: dict):
        return CustomLLMClient(api_key=config.get("api_key"))

PLUGIN_CLASS = DeepSeekProvider
```

### 5. `agent_override` — Agent 角色替换
**用途**：替换默认的 Agent 提示词解析器或处理逻辑（内置的 12 个 Agent 都可以被无缝顶替）。

```python
from novel_agent.plugins import AgentOverridePlugin, PluginMeta, PluginType

class CustomWriterAgent:
    def __init__(self, llm):
        self.llm = llm

    def run(self, prompt: str) -> str:
        # 自定义小说写手的生成逻辑
        return "武侠风的小说章节内容..."

class WuxiaWriterOverride(AgentOverridePlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="wuxia-writer-override",
            display_name="武侠风写手 Agent",
            plugin_type=PluginType.AGENT_OVERRIDE
        )

    def get_target_role(self) -> str:
        return "writer"  # 替换系统默认的 writer

    def create_agent(self, llm, prompts):
        return CustomWriterAgent(llm)

PLUGIN_CLASS = WuxiaWriterOverride
```

### 6. `pipeline_phase` — 流水线全新阶段
**用途**：在生成、审核、状态提取这三个基本步骤之间或之后，插入自定义的全新执行阶段（例如“自动配图阶段”）。

```python
from novel_agent.plugins import PipelinePhasePlugin, PluginMeta, PluginType

class AutoIllustrationPhase(PipelinePhasePlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="illustration-phase",
            display_name="AI 配图阶段",
            plugin_type=PluginType.PIPELINE_PHASE
        )

    def get_insert_after(self) -> str:
        return "post_audit"  # 插入在审批通过之后

    def execute(self, ctx):
        # 针对章节的文字，自动生成图画描述并调用绘图 API
        # 并写入 ctx 中
        ctx.warnings.append("自动配图成功，已保存至 assets")
        return ctx

PLUGIN_CLASS = AutoIllustrationPhase
```

### 7. `event_listener` — 事件监听器
**用途**：实现旁路通知、数据监控和日志追踪。

```python
from novel_agent.plugins import EventListenerPlugin, PluginMeta, PluginType

class DingTalkNotifier(EventListenerPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="dingtalk-notifier",
            display_name="钉钉通知",
            plugin_type=PluginType.EVENT_LISTENER
        )

    def get_subscriptions(self) -> list:
        return ["chapter.completed", "novel.completed"]

    def on_event(self, event) -> None:
        print(f"【通知发送】事件 {event.name} 触发，数据：{event.data}")

PLUGIN_CLASS = DingTalkNotifier
```

### 8. `web_extension` — Web UI 与 API 扩展
**用途**：插件除了扩展后台逻辑，还可以为 FastAPI Web 服务动态提供自定义路由。

```python
from fastapi import APIRouter
from novel_agent.plugins import WebExtensionPlugin, PluginMeta, PluginType

router = APIRouter(prefix="/api/my-plugin", tags=["my-plugin"])

@router.get("/hello")
def hello():
    return {"message": "Hello from Plugin!"}

class CustomWebExt(WebExtensionPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="custom-web-ext",
            display_name="自定义 Web 扩展",
            plugin_type=PluginType.WEB_EXTENSION
        )

    def get_router(self) -> APIRouter:
        return router

PLUGIN_CLASS = CustomWebExt
```

---

## 四、 插件开发最佳实践

为了保证插件的健壮性以及系统内核的安全，请开发者遵守以下原则：

1. **不可变数据结构优先**：在钩子（Pipeline Hooks）处理上下文数据时，优先返回修改后的副本或就地安全修改，避免删除核心关键字段引发崩溃。
2. **零内核依赖修改**：严禁在插件包中直接修改系统的 `novel_agent` 核心代码，所有扩展点应该通过 SDK 的声明接口挂载。
3. **隔离防崩溃保护**：在插件运行生命周期（如 `check`、`export`、`on_event`）中，内核均会采用 `try-except` 包裹。插件内部也必须处理好边界数据校验，避免因外部 API 超时或网络异常导致生成流程中断。
4. **清理释放机制**：在 `on_deactivate` 回调函数中，必须彻底注销与清理插件申请的资源（如关闭本地端口监听、释放大对象内存、注销事件总线等）。
