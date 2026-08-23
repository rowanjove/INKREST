# 中文长篇评测与长跑验收

评测使用 `benchmarks/longform/retrieval-cases.jsonl` 和
`novel_agent.evaluation` 中的自建最小样本，不复制外部作品正文。每条一致性
样本记录分类、变体、章节、预期标签和 `expected_evidence`；报告必须保留证据
定位，不能只输出一个通过率。

离线检索消融：

```powershell
py -3.12 scripts/evaluate_retrieval.py --cases benchmarks/longform/retrieval-cases.jsonl --output logs/retrieval.json --csv logs/retrieval.csv
```

真实模型 20/50/100 章长跑必须显式启动，并固定模型、prompt/embedding/config
摘要、seed、temperature 和预算。先生成计划清单：

```powershell
py -3.12 scripts/run_longform_acceptance.py --chapters 20 --output logs/longform-plan.json
```

仅在人工复核预算后使用 `--start --budget <数量>` 生成“已明确授权”的运行清单；
该命令仍不会调用模型。真实执行必须再加一层独立确认，并且必须指向已有项目根目录：

```powershell
py -3.12 scripts/run_longform_acceptance.py --chapters 20 `
  --root "$env:NOVEL_AGENT_ROOT\projects\<project_id>" `
  --output logs/longform-20.json --start --execute --budget 20
```

执行器只消费 `workspace/arc_*.json` 中已有的章节队列，不替用户生成大纲；启动前会检查
配置和队列数量。`--execute` 是唯一会实例化 `PipelineConfig`/`NovelOrchestrator` 的路径，
必须与 `--start`、正数 `--budget` 一起提供。每章完成后原子写回 manifest，记录章节结果、
重试、持久化成本/Token、每 10 章的脱敏质量趋势和待人工抽检点；进程中断或预算耗尽时
状态为 `cancelled`/`paused`，可用同一清单续跑；续跑会先用 SQLite 已落库成本与清单基线
对账，避免进程恰好在扣费后中断而低报预算。运行时会从实际解析出的 PipelineConfig、
prompt manifest、embedding 配置和 models/pipeline 文件生成摘要；显式传入的 model、
prompt/embedding/config、temperature 与实际值不一致时拒绝启动。OpenAI client 会把
seed 写入请求 payload；其他 provider 至少固定本进程随机种子并在 manifest 标注绑定能力。
续跑会校验 model、prompt/embedding/config 摘要、seed、temperature 和预算不可变，不能借
续跑偷偷换模型或扩大预算。

当前 runner 只记录 adjacent-only/hybrid 两种检索模式，尚未自动执行二者的对照实验；
manifest 会标记 `retrieval_comparison_status=not_run`，不能把它当作检索消融结果。

原始正文和模型日志默认留在项目本地，manifest 只写聚合指标、章节 ID 和脱敏错误。
提交到仓库的报告只允许脱敏聚合指标和少量证据摘录；真实长跑仍需人工审阅质量趋势，
不能只报告最好一次运行。
