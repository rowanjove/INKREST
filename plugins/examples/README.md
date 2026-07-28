# 官方示例插件

复制到仓库根目录 `plugins/` 后即可在 **设置 → 插件管理** 启用。

## 示例列表

| 文件 | 类型 | 作用 |
|------|------|------|
| `hello_guard.py` | quality_guard | 演示质量门禁钩子，可拦截低分章节 |
| `txt_export_hook.py` | exporter | 演示导出钩子，可追加自定义 txt 导出 |

## 启用步骤

1. 复制 `plugins/examples/hello_guard.py` → `plugins/hello_guard.py`
2. 重启栖墨后台，或在前端插件页点「重新加载」
3. 在插件管理中找到 **Hello Guard**，打开启用开关
4. 运行一章生成，在章节详情查看门禁报告是否出现插件痕迹

## 类型对照

完整类型、权限和打包方式见 `docs/plugins/PLUGIN_AUTHOR.md`。常见类型：

- `pipeline_hook` — 流水线阶段前后
- `quality_guard` — 统一门禁
- `exporter` — 导出格式扩展
- `event_listener` — 任务完成等事件

## 注意

- 示例默认**不**自动启用，避免污染正式项目
- 修改示例后需重新加载插件；沙箱模式见流水线高级设置
