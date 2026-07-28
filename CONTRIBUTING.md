# 贡献与本地验证

## 提交前检查

按改动范围选择命令（PowerShell，仓库根目录）：

### 只改前端（`web/frontend/`）

```powershell
cd web/frontend
npm run test:unit
npm run audit:dead-code
npm run build
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q
```

### E2E（需本地后台）

```powershell
cd web/frontend
$env:E2E_RUN="1"
npm run test:e2e
```

### 只改后端（`novel_agent/`、`web/` Python）

```powershell
python -m ruff check novel_agent web tests
python -m pytest tests/ --ignore=tests/smoke -q
```

### 推送 / 开 PR 前（推荐全量）

```powershell
cd web/frontend
npm run test:unit
npm run audit:dead-code
npm run test:electron
npm run build
npm run check:bundle
cd ../..
python -m ruff check novel_agent web tests
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
python -m pytest tests/test_full_chain_chaos.py tests/api/test_novel_smoke_chain.py -q --tb=short
python scripts/perf_api_baseline.py --check
```

环境变量 `NOVEL_AGENT_DISABLE_LOCAL_TOKEN=1` 与 CI smoke 一致，本地跑 API 测试时可设置。

## 首次运行

1. 复制 `.env.example` 为 `.env`（可选，API Key 也可写在项目 `config/`）。
2. 复制 `config/pipeline.yaml.example` 为 `config/pipeline.yaml`，填入模型与 Key。
3. `pip install -r requirements.txt`
4. `python main.py serve` 或 `start.bat`（桌面端用 `npm run electron:pack` 产物）

## Git 约定

- **不要** `git add .`：`.gitignore` 已排除 `workspace/`、`data/`、`state/`、构建产物与密钥。
- 每个功能块尽量原子 commit，便于回滚。
- 敏感文件：`config/pipeline.yaml`、`config/models.json`、`.env` 永不入库。

## Electron

桌面壳唯一源码位于 `web/frontend/electron/`；测试和打包不得读取本地忽略副本。

## 发布清单（portable / Electron）

1. 确认 `pytest tests/ --ignore=tests/smoke`、`npm run test:unit`、`npm run build`、`npm run check:bundle` 全绿
2. 对齐版本号：`python scripts/sync_version.py`（以根目录 `VERSION` 为准，同步 `package.json` 与 `web/app.py`）
3. 发布前校验：`python scripts/validate_release.py`
4. 更新发版说明
5. 更新 `CHANGELOG`（如有）与用户可见文案
6. 桌面端：`cd web/frontend && npm run electron:pack`（或全量 `npm run electron:build`）
7. 交付路径：`web/frontend/dist-desktop/win-unpacked/栖墨.exe`（勿混用未 sync 的旧 portable）
8. 可选：`python scripts/verify_bundle_manifest.py <产物目录>`
9. 打包后冒烟：`npm run smoke:electron:packaged`，验证发布页、SQLite 正文、
   五格式入口、真实导出与测试项目自清理

## 长跑与混沌测试（可选）

手动验证连写稳定性：

```powershell
python scripts/chaos_long_run.py --help
```

仅在本地有可用 LLM 时运行；勿纳入默认 PR 门禁。

## 文档

- 架构、目录和数据真源：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 插件开发：[docs/plugins/PLUGIN_AUTHOR.md](docs/plugins/PLUGIN_AUTHOR.md)
- Agent 集成：[docs/AGENT-INTEGRATION.md](docs/AGENT-INTEGRATION.md)
- 数据重置：[docs/V2-DATA-RESET.md](docs/V2-DATA-RESET.md)
