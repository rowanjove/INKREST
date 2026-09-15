# 官方示例插件

复制到项目的 `plugins/` 后，可在 **扩展中心** 扫描、核对权限并分别完成信任与启用。

## 示例列表

| 文件 | 类型 | 作用 |
|------|------|------|
| `hello_guard.py` | quality_guard | 演示质量门禁钩子，可拦截低分章节 |
| `txt_export_hook.py` | exporter | 演示导出钩子，可追加自定义 txt 导出 |

## 启用步骤

1. 复制 `plugins/examples/hello_guard.py` → `plugins/hello_guard.py`
2. 在扩展中心点「重新扫描」
3. 找到 **Hello Guard**，先核对内容摘要和本地代码权限，再建立信任
4. 单独打开启用开关
5. 明确开始一章生产后，在章节详情查看门禁报告是否出现插件痕迹

## 类型对照

完整类型、权限和打包方式见 `docs/plugins/PLUGIN_AUTHOR.md`。常见类型：

- `pipeline_hook` — 流水线阶段前后
- `quality_guard` — 统一门禁
- `exporter` — 导出格式扩展
- `event_listener` — 任务完成等事件

## 注意

- 示例默认**不**自动启用，避免污染正式项目
- 当前示例是兼容用的单文件本地插件，会按本地代码权限处理；启用前务必核对来源、摘要和权限
- 修改示例后需重新扫描插件；沙箱模式见流水线高级设置
