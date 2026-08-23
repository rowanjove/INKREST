# 栖墨质量中心使用说明

质量中心是本地证据层，不会自动生成候选、调用模型或把“AI 检测器通过率”当作质量 KPI。默认策略仍是单候选、report-only、人工确认。

## 1. 校准与本地基线

在项目中明确选择 20–30 个真实章节作为 golden samples 后，通过质量中心的“保存基线”和“运行校准”生成：

- `workspace/reports/golden_chapters.json`：样本正文、来源标签和 sha256。
- `workspace/reports/quality_calibration.json`：golden 检查、L0/L1/L2 分层、mutation 命中/漏报和反馈统计。
- `workspace/reports/quality_baseline.json`：按章节的事实冲突、知识边界、表达复读、返工、接受率、手改比例、误报率和候选成本。

样本数少于 20、mutation 未达到 80% 或执行有错误时，状态保持 `uncalibrated`，不会自动阻断写作。

质量指标支持按章节和时间窗读取或导出：

```text
GET /api/quality/metrics?chapter_id=001&since=2026-08-01T00:00:00+08:00&until=2026-08-31T23:59:59+08:00
GET /api/quality/metrics/export?format=csv&chapter_id=001
```

## 2. 声线实验室

实验室只显示显式选择的 profile 来源摘要、sha256、章节偏离趋势和版本列表。冻结后，恢复旧 profile 会返回 `VOICE_PROFILE_FROZEN`；先解除冻结或在受控脚本中显式传 `force`。误报、有效偏离和人工备注都写入本地 JSONL，便于复盘而不改变正文。

## 3. 审校中心与候选集

审校中心把证据分为：

- **L0**：格式、长度、CONTENT_LOCK 和门禁证据；
- **L1**：表达、声线、复读、事件一致性与来源 span；
- **L2**：人工审校、盲选反馈和候选偏好。

候选集仍必须由调用方显式提交，最多 3 个候选并受成本/TTL 限制。质量中心可以：

1. 查看候选正文、L0 校验、CONTENT_LOCK 摘要和反馈排名；
2. 通过浏览器确认后采纳候选，正文一定创建新的 revision/hash；
3. 回滚候选集时间线快照。该操作不修改正文；
4. 查看原文 span、source ref、audit issue 和 render contract 证据。

候选集 API 不会把候选集回滚误当正文回滚；正文回滚仍走 Manuscript revision API。

## 4. 默认开关与失败边界

- 候选模式默认 `manual_only`；没有显式候选时保持旧的单候选流程。
- 表达复读、声线偏离和人工偏好均为诊断/报告层，不单独阻断章节。
- L0 格式、来源锁和正文 revision/hash 冲突采用 fail-closed；审校报告读取、指标文件缺失和声线反馈写入采用 fail-open 并显示错误状态。
- 所有样本、事件和反馈默认只写项目 `workspace/` 与 `assets/`，不上传第三方。

## 5. 验收命令

```powershell
py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short
cd web/frontend
npm run test:unit
npm run build
npm run check:bundle
```
