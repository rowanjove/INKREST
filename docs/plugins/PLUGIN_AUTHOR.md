# 栖墨插件作者指南

插件在当前 Python 进程中运行，不是操作系统沙箱。只安装可信来源的插件，
并尽量申请完成工作所需的最小权限。

## 包结构

ZIP 根目录（或唯一顶层文件夹）须包含：

- `inkrest.plugin.json` — 清单（id、version、plugin_type、entry 等）
- `plugin.py` 或 `__init__.py` — 实现类，导出 `PLUGIN_CLASS`

可选：`bundles`（包内 zip 安装时解压到 `data/<名>/`）、`extract`（自定义解压规则）。

最小清单示例：

```json
{
  "id": "example-quality-guard",
  "name": "示例质量检查",
  "version": "0.1.0",
  "plugin_type": "quality_guard",
  "entry": "plugin:PLUGIN_CLASS",
  "capabilities": ["project_read"]
}
```

## entry 写法

- `plugin:PLUGIN_CLASS` — 从 `plugin.py` 或包 `__init__.py` 加载
- `package:子模块路径:类名` — 从子包加载

## 安装与启用

1. 应用内 **扩展中心 → 载入插件** 上传 `.zip`
2. 安装后默认 **未信任、未启用**
3. 用户先核对来源、SHA-256 内容摘要与有效权限，再单独建立信任
4. 建立信任后仍保持禁用；用户显式启用时才会 import 本地代码
5. 包内容或权限发生变化会使旧信任自动失效

## 权限清单

`capabilities` 只接受下列值，未知、重复或非字符串值会使安装失败：

- `project_read` — 读取当前活动作品的正文、设定、状态与项目配置
- `project_write` — 修改当前活动作品的内容或配置
- `project_catalog_read` — 读取书库作品元数据目录（ID、标题、修改时间），低风险
- `all_projects_read` — 跨项目读取所有作品正文与敏感设定（高风险）
- `all_projects_write` — 跨项目批量修改所有作品（极高风险）
- `ui_embed` — 挂载受控的 UI 交互视图到宿主界面
- `model_access` — 参与模型路由、提示词或生成流水线
- `network_access` — 连接第三方网络服务
- `file_export` — 创建导出文件
- `web_routes` — 注册本地 Web/API 路由
- `command_execution` — 注册可执行命令

应用会按 `plugin_type` 补齐最低权限，并为所有本地插件增加
`local_code`。省略 `capabilities` 时进入兼容推导模式；旧式单 `.py`
插件无法预判边界，会显示为 `legacy_full_access` 高风险。权限确认用于
产品边界与审计，不是操作系统沙箱。

受信任并启用后，插件与宿主同进程运行，可以读取进程环境变量和本机配置
（含 `config/models.json` 中的 API Key）。`project_read` 等权限不能阻止这一点。
流水线 hook 若走子进程，会剥离 `TOKEN` / `KEY` / `SECRET` 类环境变量，并仅保留
PATH、TEMP、SystemRoot 等启动所需项；无法 pickle 的第三方 hook 不会回退到
宿主进程内执行。这仍不是操作系统隔离，不要安装不可信插件。

## 双区域侧栏贡献点规范 (`contributes.navigation`)

在 `inkrest.plugin.json` 中声明 `contributes.navigation`，可将插件视图挂载到客户端侧栏：

```json
{
  "contributes": {
    "navigation": [
      {
        "id": "radar-view",
        "title": "伏笔雷达",
        "surface": "project_sidebar",
        "view": "radar-panel",
        "icon": "radar",
        "order": 100,
        "requires": ["project_read"]
      }
    ]
  }
}
```

### 挂载区域限制 (`surface`)
- `library_sidebar`：**书库级侧栏**。适用于全局模板库、统计、预设市场等，严禁依赖当前作品上下文。
- `project_sidebar`：**作品级侧栏**。适用于单书伏笔追踪、人物拓扑图等创作辅助工具。
- ⚠️ **严格禁止 `both`**：如果一个插件需要同时在两个区域提供功能，必须声明两条独立的 entry。
- 单个区域最多声明 2 个导航入口，避免过度挤占导航空间。

### 视图沙箱与受控 RPC 协议
插件 UI 运行在安全的 Sandboxed iframe 中，通过 `window.parent.postMessage` 与宿主进行受控通信：
1. **初始化**：宿主发送 `inkrest:init`（携带当前会话 ID、主题配色 Token、当前作品 ID、上下文版本号）。
2. **生命周期与切书**：当用户切换作品或离开时，宿主发送 `inkrest:dispose`（2 秒强制超时熔断）。插件应监听并及时响应 `inkrest:disposed`。
3. **受控 RPC 请求**：插件发送 `inkrest:rpc_request`，宿主服务端根据会话授权的安全子集校验后执行，并返回 `inkrest:rpc_response`：
   - `host.ping` — 握手心跳（无需特殊权限）
   - `catalog.listProjects` — 读取书库作品列表（需要 `project_catalog_read`）
   - `project.getInfo` — 读取当前作品摘要（需要 `project_read`）
   - `project.getChapters` — 读取章节目录与字数（需要 `project_read`）
   - `project.getCharacters` — 读取人物设定列表（需要 `project_read`）
   - `project.getOutline` — 读取大纲与世界观（需要 `project_read`）

### 推荐模版仓库
- 书库工具模板：`templates/plugin-starters/library-tool/`
- 作品辅助模板：`templates/plugin-starters/project-tool/`
- 双区域复合套件模板：`templates/plugin-starters/dual-region/`

## 插件类型

`plugin_type` 支持以下 15 种类型：

| 类型 | 用途 |
| --- | --- |
| `pipeline_hook` | 在流水线节点前后执行钩子 |
| `quality_guard` | 检查正文质量并返回问题 |
| `exporter` | 增加导出格式 |
| `llm_provider` | 接入模型服务 |
| `agent_override` | 替换特定 Agent 实现 |
| `pipeline_phase` | 增加流水线阶段 |
| `vector_store` | 接入向量存储 |
| `embedding_provider` | 提供向量嵌入 |
| `approval_strategy` | 自定义人工确认策略 |
| `rules_extension` | 扩展质量或业务规则 |
| `prompt_enhancer` | 修改或补充提示词 |
| `event_listener` | 监听完成、失败等事件 |
| `web_extension` | 注册本地 Web/API 路由 |
| `command` | 注册可执行命令 |
| `sensitive_scanner` | 扩展敏感内容检查 |

实现类应继承 `novel_agent.plugins` 中相应的基础类，并在模块级导出
`PLUGIN_CLASS`。基础接口、参数和返回值以 `novel_agent/plugins/base.py`
中的定义为准，避免复制内部实现。

示例：

```python
from novel_agent.plugins import PluginMeta, PluginType, QualityGuardPlugin


class ExampleGuard(QualityGuardPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="example-quality-guard",
            display_name="示例质量检查",
            version="0.1.0",
            description="检查示例规则。",
            author="example",
            plugin_type=PluginType.QUALITY_GUARD,
        )

    def check(self, text: str, context: dict) -> dict:
        issues = []
        return {"pass": not issues, "score": 100, "details": issues}


PLUGIN_CLASS = ExampleGuard
```

## 配置

在清单中声明 `config_schema`（JSON Schema）；用户在 **配置** 弹窗中编辑，写入 `config/plugins.yaml` 的 `registry.<id>.config`。

## 开发打包

```powershell
.\scripts\package-plugin.ps1 -PluginDir .\templates\plugin-starter
```

最小模板：`templates/plugin-starter/`。带侧栏视图的模板见上文「推荐模版仓库」。

打包前建议检查：

1. ZIP 中不包含 `.env`、密钥、日志、数据库、缓存或测试账号。
2. 清单只声明实际使用的权限，版本号与实现一致。
3. 插件在缺少配置、网络超时和重复启停时能安全失败。
4. `on_deactivate` 会关闭连接、线程、文件句柄和事件订阅。
5. 安装后核对应用显示的 SHA-256 摘要和权限，再建立信任。
