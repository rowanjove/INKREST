# Factory 模式 ↔ 运行时映射

> 单一来源：`novel_agent/control/factory_policy.py`（行为）+ `web/factory_modes.json`（文案）  
> 仅当 `config/project_meta.json` **显式写入** `factory_mode` 时生效；未设置则保持旧版默认流水线。

| 模式 ID | 中文名 | 门禁 | 自动改写 | 审校档 | 向量长篇 | 续跑熔断 |
|---------|--------|------|----------|--------|----------|----------|
| `newbie_auto` | 新手全自动 | `block_on_fail` | 开 | 默认 | 按体量 | 默认 |
| `author_copilot` | 作者协作 | `report_only` | 关 | standard | 按体量 | 默认 |
| `platform_review` | 平台过审 | `block_on_fail` | 开 | premium | 按体量 | 默认 |
| `longform_stable` | 长篇稳定 | `block_on_fail` | 开 | premium | **stub 时阻断 continue** | 默认 |
| `studio` | 工作室生产 | `block_on_fail` | 开 | 默认 | 按体量 | 批次失败 3 次熔断 |

## 相关配置

`config/pipeline.yaml` → `runtime`：

- `yaml_mirror_mode`：`write`（默认）| `read_only` | `off` — 控制 `state/*.yaml` 双写；`read_only` 时 SQLite 为唯一写入源，仍可读旧 YAML 并做漂移检查
- `yaml_mirror_enabled`（遗留布尔）：`true`→`write`，`false`→`off`；未设置 `yaml_mirror_mode` 时生效
- `vector_readiness`：`auto` | `block` | `warn` | `ignore` — 覆盖长篇向量 stub 时的阻断/警告策略

### YAML 只读导出

`read_only` 或需要一次性对齐磁盘时，调用 `POST /api/database/export-yaml-mirror`，从 SQLite 导出 `events/objects/foreshadows/hooks` 到 `state/*.yaml`（不恢复实时双写）。

## 验证

- 行为差异：`pytest tests/test_factory_mode_policy.py -q`
- Dashboard 聚合：`pytest tests/api/test_factory_dashboard.py -q`
- 开书清单 / continue 门禁：`pytest tests/api/test_api_novel_readiness.py -q`