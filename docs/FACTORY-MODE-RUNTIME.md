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

- `yaml_mirror_enabled`（默认 `true`）：关闭后 SQLite 为唯一真相源，不再写 `state/*.yaml`
- `vector_readiness`：`auto` | `block` | `warn` | `ignore` — 覆盖长篇向量 stub 时的阻断/警告策略

## 验证

- 行为差异：`pytest tests/test_factory_mode_policy.py -q`
- Dashboard 聚合：`pytest tests/api/test_factory_dashboard.py -q`
- 开书清单 / continue 门禁：`pytest tests/api/test_api_novel_readiness.py -q`