# INKREST · 栖墨 — Long-form fiction writing workspace

[简体中文](README.md) | [English](README.en.md)

INKREST is a local-first workspace for writing novels. It brings outlines, chapter editing, multi-agent writing assistance, continuity checks, and multi-format export into one project. Authors can write manually or run single-chapter and batch generation, then inspect quality reports, revision history, and task logs.

[Download Windows v2.0.2](https://github.com/rowanjove/INKREST/releases/tag/v2.0.2) · [Changelog](CHANGELOG.md) · [Issues](https://github.com/rowanjove/INKREST/issues)

Manuscripts and project state are stored locally. **Remote model calls send the selected context to your configured provider and may incur charges.** Local-first storage does not imply offline model inference.

![INKREST project overview and production status](docs/images/readme-overview.png)

## Install and get started

Windows users can download the `Setup.2.0.2.exe` installer or `2.0.2.exe` portable application from the Release.

Create a project, configure a model service, then choose manual editing or assisted generation. Before a live model task, review the endpoint, model, credentials, and cost settings. Browsing ordinary pages does not automatically invoke writing models; generation, rewriting, review, and batch jobs are explicitly initiated by the user.

The source setup below is for developers, not a prerequisite for using a Windows release.

## Workspaces and generation

| Workspace | Purpose |
| --- | --- |
| Planning | Outlines, volume plans, character relationships, world settings, timelines, and reference material |
| Manuscript editing | Rich text, autosave, revision history, context inspection, and on-demand rewriting |
| Chapter production | Planning, scene writing, assembly, style editing, review, and state updates |
| Quality checks | Continuity, length, sensitive terms, and repetitive or formulaic language |
| Long-form memory | SQLite project state, chapter summaries, checkpoints, and optional vector retrieval |
| Export | TXT, Markdown, DOCX, EPUB 3, and PDF |
| Extensions | Project isolation, backups, plugin permissions, and project-scoped operations |

Chapter pipelines organize writing, editing, and checks, with batch production, checkpoint recovery, retries, and pauses after repeated failures. Project SQLite is the source of truth for manuscripts and tasks; compatibility files and chapter artifacts should not overwrite newer database records.

![INKREST manuscript editor](docs/images/readme-writer.png)

## Style and continuity

Configure style, prohibited phrases, and writing constraints before generation. Style editing, local rules, and model review then identify issues for targeted repair or manual revision. These checks assist editing; they do not guarantee literary quality, factual accuracy, or acceptance by third-party AI detectors.

Long-form tasks can retrieve characters, settings, events, foreshadowing, and historical passages. Vector retrieval is optional and requires compatible models and ready indexes. When a quality gate blocks a task, inspect the report before repairing, rerunning, or continuing.

Available modes include beginner automation, author collaboration, platform review, long-form stability, and studio workflows. They adjust generation and review policies rather than replacing the author's final judgment.

## Shanshan assistant

Shanshan resides in the Electron desktop app. It reads project, task, and log state to explain pauses and provide navigation, model connectivity checks, chapter retries, repair, and gate reruns. Its conversation model can be configured separately.

Model calls and manuscript changes require user initiation and applicable confirmation. The assistant should not independently change outlines, delete projects, or bypass confirmation to resume a whole-book run.

![INKREST project library](docs/images/readme-library.png)

Screenshots use bundled demo projects, not private manuscripts or credentials.

## Run from source

Requires Python **3.11 or 3.12** and Node.js **>=22.12.0**. Desktop packaging targets Windows 10/11.

In Windows PowerShell:

```powershell
git clone https://github.com/rowanjove/INKREST.git
cd INKREST
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item config/pipeline.yaml.example config/pipeline.yaml
cd web/frontend
npm ci
npm run build
cd ../..
./.venv/Scripts/python.exe main.py serve --no-browser
```

Open `http://127.0.0.1:8000`. Source setup requires building the frontend first; the backend serves files from `web/frontend/dist`. Rebuild after frontend changes or use the development workflow.

Configure models locally in `config/pipeline.yaml` or `config/models.json` as needed. Both files and `.env` are ignored by Git; do not force-add them. Do not commit the `.venv/` environment either; you can exclude it locally through `.git/info/exclude`.

### CLI example without model charges

From the repository root, use the static-model dry run:

```powershell
./.venv/Scripts/python.exe main.py run-chapter --chapter-id 001 --goal "主角雨夜回到出租屋，并遭遇第一次异常。" --dry-run
```

The sample goal describes a protagonist returning home on a rainy night and encountering an anomaly. A dry run may still create local artifacts; it is not a read-only operation. Chapter artifacts are stored in the active project's `workspace/chapters/`.

### Windows desktop packaging

The packaging script probes Python 3.12/3.11 environments. Install runtime and build dependencies for it:

```powershell
py -3.12 -m pip install -r requirements.txt -r requirements-build.txt
cd web/frontend
npm run electron:build
```

Artifacts are written to `web/frontend/dist-desktop/`. For a directory build, run `npm run build:backend` followed by `npm run electron:pack`; its executable is `win-unpacked/栖墨.exe`. See [contribution and verification notes](CONTRIBUTING.md) for acceptance checks.

## Verification

Backend, from the repository root:

```powershell
./.venv/Scripts/python.exe -m pip install pytest pytest-asyncio
./.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/smoke -q --tb=short
```

Frontend:

```powershell
cd web/frontend
npm run test:unit
npm run test:electron
npm run build
npm run check:bundle
```

`check:bundle` uses `python` from PATH; ensure it points to a compatible environment. The contribution guide covers additional lint, performance, E2E, and packaged smoke checks. Live model tests may incur charges and should not run without confirmation.

## Data, credentials, and plugins

- `projects/`, `workspace/`, `data/`, `state/`, `logs/`, and `backups/` are excluded from commits by default.
- The service listens on `127.0.0.1` by default. Remote binding requires explicit opt-in and an access token.
- Project backups and V2 resets use confirmation phrases containing the project ID; a verifiable backup precedes a reset.
- API, log, and backup flows isolate or redact credentials. Still inspect diagnostics before sharing them.
- Plugin permissions require authorization tied to a manifest hash; installation does not imply trust or unrestricted access.

## Technology and documentation

The backend uses Python, FastAPI, Pydantic, and SQLite. The frontend uses Vue 3, TypeScript, Pinia, Vite, Element Plus, and Tiptap. Desktop packaging uses Electron and PyInstaller. Tests use pytest, Vitest, and Playwright.

[Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Plugin authors](docs/plugins/PLUGIN_AUTHOR.md) · [Agent integration](docs/AGENT-INTEGRATION.md) · [Backup and reset](docs/V2-DATA-RESET.md) · [Remote deployment security](docs/remote-deployment-security.md)

The interface and supporting guides are primarily Chinese; an English README does not imply full interface localization.

## License

Licensed under [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for copyright and attribution.
