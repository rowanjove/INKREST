# 贡献与本地验证

## 提交前检查

按改动范围选择命令（PowerShell，仓库根目录）：

### 只改前端（`web/frontend/`）

```powershell
cd web/frontend
npm run build
cd ../..
python -m pytest tests/test_workspace_ui_contract.py -q
```

### 只改后端（`novel_agent/`、`web/` Python）

```powershell
python -m pytest tests/ --ignore=tests/smoke -q
```

### 推送 / 开 PR 前（推荐全量）

```powershell
cd web/frontend; npm run build; cd ../..
python -m pytest tests/ --ignore=tests/smoke -q --tb=short
python -m pytest tests/test_full_chain_chaos.py tests/api/test_novel_smoke_chain.py -q --tb=short
```

环境变量 `NOVEL_AGENT_DISABLE_LOCAL_TOKEN=1` 与 CI smoke 一致，本地跑 API 测试时可设置。

## 首次运行

1. 复制 `.env.example` 为 `.env`（可选，API Key 也可写在项目 `config/`）。
2. 复制 `config/pipeline.yaml.example` 为 `config/pipeline.yaml`，填入模型与 Key。
3. `pip install -r requirements.txt`
4. `python main.py` 或 `start.bat`

## Git 约定

- **不要** `git add .`：`.gitignore` 已排除 `workspace/`、`data/`、`state/`、构建产物与密钥。
- 每个功能块尽量原子 commit，便于回滚。
- 敏感文件：`config/pipeline.yaml`、`config/models.json`、`.env` 永不入库。

## Electron

桌面壳源码以 `web/frontend/electron` 为准。若曾改 `electron_version/`，请用：

```powershell
.\scripts\sync_electron_canonical.ps1
```

## 长跑与混沌测试（可选）

手动验证连写稳定性：

```powershell
python scripts/chaos_long_run.py --help
```

仅在本地有可用 LLM 时运行；勿纳入默认 PR 门禁。

## 文档

- 产品双车道：[docs/PLAN-全书链路与人机协同.md](docs/PLAN-全书链路与人机协同.md)
- 工程路线图：[docs/IMPROVEMENT-ROADMAP-2026Q2.md](docs/IMPROVEMENT-ROADMAP-2026Q2.md)