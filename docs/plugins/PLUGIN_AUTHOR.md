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

1. 应用内 **插件 → 载入插件** 上传 `.zip`
2. 安装后默认 **未信任、未启用**
3. 在卡片上打开开关 → 确认信任后才会 import 本地代码

## 配置

在清单中声明 `config_schema`（JSON Schema）；用户在 **配置** 弹窗中编辑，写入 `config/plugins.yaml` 的 `registry.<id>.config`。

## 开发打包

```powershell
.\scripts\package-plugin.ps1 -PluginDir .\templates\plugin-starter
```

模板目录：`templates/plugin-starter/`。