# 长篇基准

这些命令只使用合成 SQLite 项目，默认不调用模型，也不写入真实 `projects/`。

## 命令

```powershell
py -3.12 scripts/benchmark_longform_state.py --chapters 5000 --output logs/bench-state.json
py -3.12 scripts/benchmark_longform_export.py --chapters 5000 --format txt --output logs/bench-export.json
py -3.12 scripts/benchmark_longform_state.py --chapters 5000 --repeat 5 --output logs/bench-state-5000.json
py -3.12 scripts/benchmark_longform_export.py --chapters 5000 --repeat 5 --format txt --output logs/bench-export-5000.json
py -3.12 -m pytest tests/test_longform_benchmark_contract.py -q
```

`--chapters` 支持 `100|500|1000|3000|5000`。`--workdir` 可指定临时项目目录。

## 口径

- `state`：目录分页、最大章节、事件、开放线程、人物状态、发布摘要、备份清单。
- `export`：TXT/Markdown 流式导出。DOCX/EPUB/PDF 不与纯文本共享阈值。
- 结果 JSON 必须符合 `baseline.schema.json`。
- 结果包含每次样本、P50/P95、峰值 tracemalloc/RSS 和 commit SHA；`--repeat` 范围为 1–100。
- 阈值必须记录本机配置，不能写成跨机器绝对承诺。
