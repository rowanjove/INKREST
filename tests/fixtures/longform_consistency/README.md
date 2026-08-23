# 中文长篇一致性 fixtures

这里的样本是版权安全的最小中文句子，仅用于回归测试。每条记录都包含
`expected_evidence`，评测必须同时保留证据定位，不能只输出 PASS/FAIL。

完整矩阵可由 `novel_agent.evaluation.fixtures.build_consistency_fixtures()`
在测试或本地报告中生成；默认覆盖人物、事实、时间情节、世界规则和声线表达
的正常、单点突变、跨章突变与反例。

`core.jsonl` 提供可直接加载的版权安全冒烟样本；完整矩阵仍由生成器提供，
避免把测试夹具重复维护成第二套真相源。
