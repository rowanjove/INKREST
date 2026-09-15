# INKREST · 栖墨

<p align="center">
  <strong>A Local-First, Multi-Agent Long-Form Fiction Writing & Industrial Production Workspace</strong>
</p>

<p align="center">
  <a href="https://github.com/rowanjove/INKREST/releases/tag/v2.1.0"><img src="https://img.shields.io/badge/Release-v2.1.0-blue.svg?style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-green.svg?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Frontend-Vue%203.5%20%7C%20Electron-4FC08D.svg?style=flat-square&logo=vuedotjs&logoColor=white" alt="Frontend">
  <img src="https://img.shields.io/badge/Tests-1450%2B%20Passed-brightgreen.svg?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/Architecture-Local--First-orange.svg?style=flat-square" alt="Architecture">
</p>

<p align="center">
  <a href="README.md">简体中文</a> | <a href="README.en.md">English</a>
</p>

---

**INKREST** is not a superficial "type a single prompt, get a block of prose" AI chatbot. It unites **concept planning, Story Blueprint compilation, advanced manuscript editing, Human Writing Engine (HWE), multi-agent continuous production pipelines, persistent narrative memory & vector retrieval, de-AI prose constraints, panoramic quality gates, Plugin Platform 2.0, and multi-format publication** into an observable, pausable, and human-in-the-loop industrial creation workflow.

> **Core Principle**: AI empowers storytelling and pipeline throughput; the author always maintains editorial authority and final veto power.

---

## 📸 Interface Gallery

### 1. Production Dashboard & Overview
Comprehensive real-time view of book completion, active pipelines, background tasks, gate health, and word count velocity.
![Dashboard & Overview](docs/images/readme-overview.png)

### 2. Inspiration Workshop & Story Blueprint
From raw creative spark to three-act conflict engines, volume breakdown, and chapter goal decomposition.
![Inspiration Workshop & Story Blueprint](docs/images/readme-blueprint.png)

### 3. Manuscript Workspace
Integrated Tiptap rich-text editor, chapter navigation tree, live character count, inline AI rewriting, expansion, and protected manual text selections.
![Manuscript Workspace](docs/images/readme-writer.png)

### 4. Multi-Agent Production Center
Continuous long-form writing pipelines, parallel scene rendering, checkpoint recovery, circuit-breaker fault protection, and real-time LLM telemetry.
![Production Center](docs/images/readme-production.png)

### 5. Panoramic Quality Center
Multi-layer automated audit gates: plot continuity validation, forbidden word check, conflict contradiction detection, and targeted auto-repair.
![Quality Center](docs/images/readme-quality.png)

### 6. Plugin Platform 2.0 & SDK
Isolated IPC process sandbox with fine-grained capability broker, supporting foreshadowing inspectors, mystery deduction, and community extensions.
![Plugin Platform 2.0](docs/images/readme-plugins.png)

### 7. Publishing & Export Center
Authoritative source verification, print-ready preview, and one-click export to TXT, Markdown, DOCX, EPUB 3, and high-fidelity PDF.
![Publishing Center](docs/images/readme-publishing.png)

### 8. Project Library
Manage multiple novels locally with seamless switching, global settings, zero-leak local encryption, and instant backup/restore.
![Project Library](docs/images/readme-library.png)

---

## ⚡ Core Highlights

### 1. Multi-Agent Industrial Assembly Line
A chapter is produced through specialized, coordinated agent stages rather than a single black-box LLM call:
```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Story Blueprint │ ──> │ Chapter Breakdown│ ──> │ Parallel Scene Gen  │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                                                            │
┌─────────────────┐     ┌──────────────────┐     ┌──────────▼──────────┐
│ SQLite Authority│ <── │ Quality Auditing │ <── │ Assembly & Prose Pol│
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```
- **Tiered Model Routing**: Assign specialized models for creative outlining (e.g. Claude 3.5 / DeepSeek-R1), prose writing (DeepSeek-V3 / GPT-4o), and rapid rule checking.
- **Narrative Continuity**: Unified SQLite persistence for character states, fact ledgers, and checkpoints.
- **Hybrid Retrieval**: Combine exact full-text search with vector recall (ChromaDB / SQLite-VSS) across hundreds of chapters.

### 2. Real Prose Polish & De-AI Constraints
Reducing formulaic machine prose requires continuous constraint across the pipeline:
- **Pre-generation Constraints**: Inject style standards, rhythm guidance, and forbidden cliché terms.
- **Prose Editing**: Eliminate repetitive rhetorical transitions and mechanical summaries.
- **Human Writing Engine (HWE)**: Protect hand-crafted prose spans against accidental AI overwriting.
- **Targeted Repair**: Automatically re-draft problematic paragraphs without discarding the whole chapter.

### 3. Local-First & Zero-Leak Privacy
- All manuscripts, outlines, revisions, and logs reside **strictly on your local machine**.
- First-class support for fully offline local models (**Ollama, vLLM, LM Studio**)—zero API costs, zero data exposure.
- Cryptographically verified project backup and restore.

### 4. Shanshan: In-App Editorial Assistant
- Desktop-resident companion in Electron capable of monitoring active production tasks.
- Explains pipeline pause reasons in human-friendly terms and offers quick actions for retries, diagnostics, and repairs.

---

## 🚀 Quick Start

### Option 1: Windows Desktop Package (Recommended)
Download the latest binaries from [Releases](https://github.com/rowanjove/INKREST/releases/tag/v2.1.0):
- **Installer**: `Setup.2.1.0.exe` (automatic desktop shortcuts and background updates)
- **Portable**: `2.1.0.exe` (run directly without installation)

### Option 2: Run from Source

**Prerequisites**:
- Python **3.11 or 3.12**
- Node.js **>= 22.12.0**

```powershell
# 1. Clone repository
git clone https://github.com/rowanjove/INKREST.git
cd INKREST

# 2. Setup Python virtual environment
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3. Copy pipeline configuration template
Copy-Item config/pipeline.yaml.example config/pipeline.yaml

# 4. Build frontend assets
cd web/frontend
npm ci
npm run build
cd ../..

# 5. Launch local server
python main.py serve --no-browser
```
Access the application at `http://127.0.0.1:8000`.

### Desktop Packaging

Pack the application into a local Windows desktop binary:

```powershell
cd web/frontend
npm run build:backend
npm run electron:pack
```

The unpacked binary is located at `win-unpacked/栖墨.exe`. Full installers can be generated using `npm run electron:build`.

---

## 🛠️ Model Configuration

Navigate to **Settings -> Models** or configure `config/pipeline.yaml`:

```yaml
# OpenAI-compatible API or cloud provider
llm:
  provider: "openai_compatible"
  base_url: "https://api.deepseek.com/v1"
  api_key: "sk-your-api-key"
  model: "deepseek-chat"

# Fully offline setup (e.g. Ollama, no API key needed)
# base_url: "http://127.0.0.1:11434/v1"
# model: "qwen2.5:14b"
```

> [!NOTE]
> `config/pipeline.yaml`, `config/models.json`, and `.env` are in `.gitignore`. Your credentials will never be committed.

---

## 🧪 Testing & Verification

INKREST maintains an extensive automated test suite with 1,450+ unit and integration tests:

```powershell
# Backend test suite
py -3.12 -m pytest tests/ --ignore=tests/smoke -q --tb=short

# Frontend unit tests
cd web/frontend
npm run test:unit

# Frontend bundle budget check
npm run check:bundle
```

---

## 📄 License

Distributed under the [Apache License 2.0](LICENSE).
See [NOTICE](NOTICE) for third-party acknowledgments.
