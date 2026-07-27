# 栖墨插件作者指南

## 包结构

ZIP 根目录（或唯一顶层文件夹）须包含：

- `inkrest.plugin.json` — 清单（id、version、plugin_type、entry 等）
- `plugin.py` 或 `__init__.py` — 实现类，导出 `PLUGIN_CLASS`

可选：`bundles`（包内 zip 安装时解压到 `data/<名>/`）、`extract`（自定义解压规则）。

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

- `project_read` — 读取正文、设定、状态与项目配置
- `project_write` — 修改项目内容或配置
- `model_access` — 参与模型路由、提示词或生成流水线
- `network_access` — 连接第三方网络服务
- `file_export` — 创建导出文件
- `web_routes` — 注册本地 Web/API 路由
- `command_execution` — 注册可执行命令

应用会按 `plugin_type` 补齐最低权限，并为所有本地插件增加
`local_code`。省略 `capabilities` 时进入兼容推导模式；旧式单 `.py`
插件无法预判边界，会显示为 `legacy_full_access` 高风险。权限确认用于
产品边界与审计，不是操作系统沙箱。

## 配置

在清单中声明 `config_schema`（JSON Schema）；用户在 **配置** 弹窗中编辑，写入 `config/plugins.yaml` 的 `registry.<id>.config`。

## 开发打包

```powershell
.\scripts\package-plugin.ps1 -PluginDir .\templates\plugin-starter
```

模板目录：`templates/plugin-starter/`。
