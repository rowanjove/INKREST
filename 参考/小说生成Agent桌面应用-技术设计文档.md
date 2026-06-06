# 小说生成 Agent 桌面应用 — 技术设计文档

> 版本：v1.0
> 日期：2026-05-22
> 作者：Ryan

---

## 一、项目概述

### 1.1 项目背景

当前"小说生成 Agent"是一个 Python + FastAPI + Vue 3 的 Web 应用，通过 PyInstaller 打包为 exe。存在以下问题：

- 用户需要 Python 环境（非打包模式下）
- 打包后 exe 体积大（~33MB），启动慢
- 浏览器窗口容易被误关，缺乏原生桌面体验
- 无法深度集成系统能力（托盘通知、文件关联、自动更新）
- 前后端分离部署，通信效率有优化空间

### 1.2 目标

将项目重构为 **Electron 桌面应用**，参考 ToonFlow 的技术架构，实现：

- 原生桌面体验（窗口管理、托盘、通知）
- 前后端同进程通信，降低延迟
- 统一数据目录，方便备份迁移
- 支持自动更新
- 保留现有 Agent 流水线的核心能力

### 1.3 参考项目

| 项目 | 参考内容 |
|------|----------|
| ToonFlow | Electron + Vue 3 架构、SQLite 本地存储、Express 内嵌服务、Vercel AI SDK 多模型路由 |
| 当前小说生成 Agent | Agent 流水线、YAML 状态管理、Web UI |

---

## 二、技术选型

### 2.1 技术栈对比

| 层级 | 当前方案 | 新方案 | 变更说明 |
|------|----------|--------|----------|
| 桌面壳 | PyInstaller | **Electron 35+** | 原生窗口、托盘、自动更新 |
| 前端框架 | Vue 3 + Element Plus | **Vue 3 + Element Plus** | 保持不变 |
| 前端构建 | Vite | **Vite** | 保持不变 |
| 状态管理 | 无 | **Pinia** | 全局状态管理 |
| 后端服务 | FastAPI + Uvicorn | **Express 5 + Socket.IO** | Node.js 原生，进程内通信 |
| 数据库 | YAML/JSON + SQLite | **SQLite (better-sqlite3 + knex)** | 结构化存储，查询更高效 |
| AI 调用 | httpx + OpenAI 兼容 API | **Vercel AI SDK (@ai-sdk/*)** | 统一多 provider 接口 |
| 实时通信 | WebSocket (FastAPI) | **Socket.IO** | 更可靠的实时推送 |
| 打包分发 | PyInstaller | **electron-builder** | 跨平台打包、自动更新 |

### 2.2 关键依赖

```json
{
  "dependencies": {
    "electron": "^35.0.0",
    "vue": "^3.5.0",
    "vue-router": "^4.6.0",
    "pinia": "^2.3.0",
    "element-plus": "^2.14.0",
    "express": "^5.2.0",
    "socket.io": "^4.8.0",
    "better-sqlite3": "^12.8.0",
    "knex": "^3.2.0",
    "ai": "^6.0.0",
    "@ai-sdk/openai": "^3.0.0",
    "@ai-sdk/anthropic": "^3.0.0",
    "@ai-sdk/google": "^3.0.0",
    "@ai-sdk/deepseek": "^2.0.0",
    "zod": "^4.3.0",
    "yaml": "^2.7.0",
    "sharp": "^0.34.0",
    "graphlib": "^2.1.8"
  },
  "devDependencies": {
    "electron-builder": "^26.0.0",
    "vite": "^8.0.0",
    "typescript": "^5.8.0",
    "vue-tsc": "^3.2.0",
    "@vitejs/plugin-vue": "^6.0.0"
  }
}
```

### 2.3 为什么不用 TDesign

ToonFlow 用了 TDesign，但本项目当前已用 Element Plus。迁移 UI 组件库成本高且收益不大，保持 Element Plus 不变。Pinia 状态管理是本次新增的关键改进。

---

## 三、架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   Electron 主进程                     │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Express     │  │  Agent      │  │  窗口管理    │  │
│  │  API Server  │  │  Orchestrator│  │  托盘/通知   │  │
│  │  (端口内通)  │  │  (Python桥接)│  │  自动更新    │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  │
│         │                │                           │
│  ┌──────┴──────┐  ┌──────┴──────┐                    │
│  │  SQLite     │  │  AI SDK     │                    │
│  │  数据层     │  │  模型调用    │                    │
│  └─────────────┘  └─────────────┘                    │
│                                                     │
└───────────────────────┬─────────────────────────────┘
                        │ IPC / Socket.IO
┌───────────────────────┴─────────────────────────────┐
│                   渲染进程 (Vue 3)                    │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Dashboard │ │ 章节管理  │ │ 状态查看  │ │ 资产编辑│  │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ 配置管理  │ │ 实时日志  │ │ 写作编辑器│            │
│  └──────────┘ └──────────┘ └──────────┘            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.2 进程模型

| 进程 | 职责 | 技术 |
|------|------|------|
| 主进程 (Main) | 窗口管理、Express 服务、SQLite 操作、Agent 调度、系统集成 | Node.js + Electron |
| 渲染进程 (Renderer) | UI 展示、用户交互 | Vue 3 + Element Plus |
| Agent 工作进程 | 执行 Python Agent 流水线 | Python 子进程 |

### 3.3 通信方式

```
渲染进程 ←→ 主进程：Electron IPC（invoke/handle）
渲染进程 ←→ Express：HTTP API + Socket.IO（实时进度）
主进程 ←→ Agent：Python 子进程（stdin/stdout JSON 协议）
主进程 ←→ AI API：Vercel AI SDK（HTTP 调用）
```

---

## 四、目录结构

```
novel-agent-desktop/
├── electron/                    # Electron 主进程
│   ├── main.ts                  # 入口，窗口管理
│   ├── preload.ts               # 预加载脚本（IPC 桥接）
│   ├── server/                  # Express 服务
│   │   ├── app.ts               # Express 应用
│   │   ├── routes/
│   │   │   ├── chapters.ts      # 章节 API
│   │   │   ├── state.ts         # 状态 API
│   │   │   ├── assets.ts        # 资产 API
│   │   │   ├── config.ts        # 配置 API
│   │   │   └── dashboard.ts     # 看板 API
│   │   └── websocket.ts         # Socket.IO 服务
│   ├── database/                # SQLite 数据层
│   │   ├── connection.ts        # Knex 连接
│   │   ├── migrations/          # 数据库迁移
│   │   └── repositories/        # 数据访问层
│   │       ├── chapter.repo.ts
│   │       ├── character.repo.ts
│   │       ├── event.repo.ts
│   │       └── timeline.repo.ts
│   ├── agents/                  # Agent 调度层
│   │   ├── orchestrator.ts      # 流水线编排
│   │   ├── python-bridge.ts     # Python 子进程桥接
│   │   └── llm-client.ts        # Vercel AI SDK 封装
│   ├── updater/                 # 自动更新
│   │   └── auto-updater.ts
│   └── tray/                    # 系统托盘
│       └── tray-manager.ts
│
├── src/                         # Vue 渲染进程
│   ├── App.vue
│   ├── main.ts
│   ├── router/
│   │   └── index.ts
│   ├── stores/                  # Pinia 状态管理
│   │   ├── chapters.ts
│   │   ├── state.ts
│   │   ├── config.ts
│   │   └── tasks.ts
│   ├── views/
│   │   ├── Dashboard.vue
│   │   ├── ChapterList.vue
│   │   ├── ChapterDetail.vue
│   │   ├── NovelState.vue
│   │   ├── AssetEditor.vue
│   │   ├── ConfigEditor.vue
│   │   └── TaskMonitor.vue
│   ├── components/
│   │   ├── ChapterRunner.vue
│   │   ├── CharacterCard.vue
│   │   ├── TimelineGraph.vue
│   │   ├── EventLog.vue
│   │   ├── LogStream.vue        # 实时日志流
│   │   └── RichEditor.vue       # 富文本/Markdown 编辑器
│   ├── api/                     # HTTP 客户端
│   │   └── index.ts
│   └── assets/
│       └── styles/
│
├── python/                      # Python Agent 核心（保留）
│   ├── novel_agent/
│   │   ├── agents/
│   │   ├── pipeline.py
│   │   ├── orchestrator.py
│   │   └── state/
│   ├── prompts/
│   └── requirements.txt
│
├── config/                      # 配置文件
│   └── pipeline.yaml
│
├── data/                        # 运行时数据（userData 目录）
│   ├── novel.sqlite
│   ├── state/
│   ├── assets/
│   ├── workspace/
│   └── logs/
│
├── electron-builder.yml         # 打包配置
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

---

## 五、核心模块设计

### 5.1 Electron 主进程

```typescript
// electron/main.ts
import { app, BrowserWindow, ipcMain, Tray } from 'electron';
import { createServer } from './server/app';
import { initDatabase } from './database/connection';
import { createTray } from './tray/tray-manager';
import { initAutoUpdater } from './updater/auto-updater';

let mainWindow: BrowserWindow;
let expressServer: any;

app.whenReady().then(async () => {
  // 1. 初始化数据库
  await initDatabase();

  // 2. 启动 Express 服务（仅内部通信）
  expressServer = await createServer();

  // 3. 创建主窗口
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 4. 系统托盘
  createTray(mainWindow);

  // 5. 自动更新
  initAutoUpdater(mainWindow);

  // 6. 注册 IPC 处理器
  registerIpcHandlers(mainWindow);
});
```

### 5.2 Python 桥接层

保留现有 Python Agent 逻辑，通过子进程通信：

```typescript
// electron/agents/python-bridge.ts
import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';

export class PythonBridge extends EventEmitter {
  private process: ChildProcess | null = null;

  async runChapter(chapterId: string, goal: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.process = spawn('python', [
        '-m',
        'novel_agent.orchestrator',
        'run-chapter',
        '--chapter-id', chapterId,
        '--goal', goal,
        '--json-output',  // 新增：JSON 输出模式
      ], {
        cwd: this.pythonDir,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      });

      this.process.stdout?.on('data', (data) => {
        const lines = data.toString().split('\n').filter(Boolean);
        for (const line of lines) {
          try {
            const msg = JSON.parse(line);
            this.emit('progress', msg);
          } catch {
            this.emit('log', line);
          }
        }
      });

      this.process.on('close', (code) => {
        code === 0 ? resolve() : reject(new Error(`Exit code: ${code}`));
      });
    });
  }

  abort(): void {
    this.process?.kill('SIGTERM');
  }
}
```

Python 端需要新增 `--json-output` 模式，每完成一个步骤输出一行 JSON：

```python
# novel_agent/orchestrator.py 新增
import json
import sys

def emit_progress(step: str, status: str, data: dict = None):
    """输出 JSON 进度到 stdout，供 Electron 主进程读取。"""
    msg = {"step": step, "status": status, "data": data or {}}
    print(json.dumps(msg, ensure_ascii=False), flush=True)

# 在每个 Agent 步骤前后调用：
emit_progress("planner", "running")
result = planner.run(...)
emit_progress("planner", "done", {"scenes": len(result.scenes)})
```

### 5.3 Vercel AI SDK 集成

替代现有的 httpx 直接调用，获得更好的流式输出和多 provider 支持：

```typescript
// electron/agents/llm-client.ts
import { generateText, streamText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createDeepSeek } from '@ai-sdk/deepseek';

export interface LLMConfig {
  provider: string;
  apiKey: string;
  baseUrl?: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
}

export class LLMClient {
  private provider: any;

  constructor(config: LLMConfig) {
    switch (config.provider) {
      case 'openai':
        this.provider = createOpenAI({
          apiKey: config.apiKey,
          baseURL: config.baseUrl,
        });
        break;
      case 'anthropic':
        this.provider = createAnthropic({ apiKey: config.apiKey });
        break;
      case 'deepseek':
        this.provider = createDeepSeek({ apiKey: config.apiKey });
        break;
      // ... 其他 provider
    }
  }

  async generate(prompt: string, system?: string): Promise<string> {
    const { text } = await generateText({
      model: this.provider(this.config.model),
      system,
      prompt,
      maxTokens: this.config.maxTokens ?? 4096,
      temperature: this.config.temperature ?? 0.7,
    });
    return text;
  }

  stream(prompt: string, system?: string) {
    return streamText({
      model: this.provider(this.config.model),
      system,
      prompt,
      maxTokens: this.config.maxTokens ?? 4096,
    });
  }
}

// 多模型路由：不同 Agent 使用不同模型
export class LLMRegistry {
  private clients: Map<string, LLMClient> = new Map();
  private defaultClient: LLMClient;

  constructor(defaultConfig: LLMConfig, overrides?: Record<string, LLMConfig>) {
    this.defaultClient = new LLMClient(defaultConfig);
    if (overrides) {
      for (const [role, config] of Object.entries(overrides)) {
        this.clients.set(role, new LLMClient(config));
      }
    }
  }

  getClient(role: string): LLMClient {
    return this.clients.get(role) || this.defaultClient;
  }
}
```

### 5.4 SQLite 数据层

替代 YAML/JSON 文件，提供结构化查询：

```typescript
// electron/database/connection.ts
import knex from 'knex';
import { app } from 'electron';
import path from 'path';

const DB_PATH = path.join(app.getPath('userData'), 'data', 'novel.sqlite');

export const db = knex({
  client: 'better-sqlite3',
  connection: { filename: DB_PATH },
  useNullAsDefault: true,
});

export async function initDatabase() {
  // 人物表
  if (!(await db.schema.hasTable('characters'))) {
    await db.schema.createTable('characters', (t) => {
      t.string('id').primary();
      t.string('name').notNullable();
      t.string('role');
      t.text('fixed_profile');
      t.text('speech_style');
      t.text('constraints');
    });
  }

  // 人物状态表
  if (!(await db.schema.hasTable('character_state'))) {
    await db.schema.createTable('character_state', (t) => {
      t.string('character_id').primary().references('characters.id');
      t.string('location');
      t.string('emotion');
      t.text('physical_state');
      t.json('known_facts');
      t.json('relationship_state');
      t.integer('updated_chapter');
    });
  }

  // 章节表
  if (!(await db.schema.hasTable('chapters'))) {
    await db.schema.createTable('chapters', (t) => {
      t.string('id').primary();
      t.string('title');
      t.text('summary');
      t.integer('word_count');
      t.string('risk_level');
      t.text('plan_json');
      t.text('final_text');
      t.text('chapter_summary');
      t.timestamps(true, true);
    });
  }

  // 事件表
  if (!(await db.schema.hasTable('events'))) {
    await db.schema.createTable('events', (t) => {
      t.string('id').primary();
      t.integer('chapter_id');
      t.string('scene_id');
      t.string('event_type');
      t.json('characters');
      t.json('objects');
      t.string('location');
      t.text('summary');
      t.text('consequences');
      t.timestamps(true, true);
    });
  }

  // 时间线节点表
  if (!(await db.schema.hasTable('timeline_nodes'))) {
    await db.schema.createTable('timeline_nodes', (t) => {
      t.string('id').primary();
      t.string('label');
      t.integer('chapter_id');
      t.text('description');
      t.timestamps(true, true);
    });
  }

  // 时间线边表
  if (!(await db.schema.hasTable('timeline_edges'))) {
    await db.schema.createTable('timeline_edges', (t) => {
      t.string('id').primary();
      t.string('from_node').references('timeline_nodes.id');
      t.string('to_node').references('timeline_nodes.id');
      t.string('relation');
    });
  }

  // 伏笔表
  if (!(await db.schema.hasTable('foreshadows'))) {
    await db.schema.createTable('foreshadows', (t) => {
      t.string('id').primary();
      t.text('content');
      t.integer('planted_chapter');
      t.integer('resolved_chapter');
      t.string('status'); // 'open' | 'resolved' | 'abandoned'
      t.timestamps(true, true);
    });
  }

  // 钩子表
  if (!(await db.schema.hasTable('hooks'))) {
    await db.schema.createTable('hooks', (t) => {
      t.string('id').primary();
      t.text('content');
      t.integer('chapter_id');
      t.string('type'); // 'opening' | 'cliffhanger' | 'transition'
      t.timestamps(true, true);
    });
  }

  // 道具表
  if (!(await db.schema.hasTable('objects'))) {
    await db.schema.createTable('objects', (t) => {
      t.string('id').primary();
      t.string('name').notNullable();
      t.string('holder');
      t.text('status');
      t.integer('last_seen_chapter');
      t.timestamps(true, true);
    });
  }
}
```

### 5.5 Pinia 状态管理

```typescript
// src/stores/chapters.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useChaptersStore = defineStore('chapters', () => {
  const chapters = ref<ChapterSummary[]>([]);
  const currentChapter = ref<ChapterDetail | null>(null);
  const loading = ref(false);

  const sortedChapters = computed(() =>
    [...chapters.value].sort((a, b) => a.chapter_id.localeCompare(b.chapter_id))
  );

  async function fetchChapters() {
    loading.value = true;
    try {
      const { data } = await axios.get('/api/chapters');
      chapters.value = data;
    } finally {
      loading.value = false;
    }
  }

  async function fetchChapter(id: string) {
    const { data } = await axios.get(`/api/chapters/${id}`);
    currentChapter.value = data;
  }

  async function runChapter(chapterId: string, goal: string) {
    const { data } = await axios.post('/api/chapters/run', {
      chapter_id: chapterId,
      goal,
    });
    return data.task_id;
  }

  return {
    chapters,
    currentChapter,
    loading,
    sortedChapters,
    fetchChapters,
    fetchChapter,
    runChapter,
  };
});
```

### 5.6 Socket.IO 实时进度

```typescript
// src/stores/tasks.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { io, Socket } from 'socket.io-client';

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<TaskStatus[]>([]);
  const logs = ref<LogEntry[]>([]);
  let socket: Socket | null = null;

  function connect() {
    socket = io('http://localhost:3000');

    socket.on('task:progress', (data) => {
      const idx = tasks.value.findIndex(t => t.task_id === data.task_id);
      if (idx >= 0) {
        tasks.value[idx] = { ...tasks.value[idx], ...data };
      } else {
        tasks.value.push(data);
      }
    });

    socket.on('task:log', (data) => {
      logs.value.push({
        timestamp: Date.now(),
        step: data.step,
        message: data.message,
        level: data.level || 'info',
      });
      // 保留最近 500 条
      if (logs.value.length > 500) {
        logs.value = logs.value.slice(-500);
      }
    });

    socket.on('task:complete', (data) => {
      const idx = tasks.value.findIndex(t => t.task_id === data.task_id);
      if (idx >= 0) {
        tasks.value[idx].status = 'completed';
      }
    });
  }

  function disconnect() {
    socket?.disconnect();
  }

  return { tasks, logs, connect, disconnect };
});
```

---

## 六、Agent 流水线迁移策略

### 6.1 迁移原则

| 原则 | 说明 |
|------|------|
| **保留 Python 核心** | Agent 逻辑不重写，通过子进程桥接 |
| **渐进式迁移** | 先跑通主流程，再逐步优化 |
| **统一数据层** | YAML 状态迁移到 SQLite |
| **流式输出** | Agent 进度实时推送到前端 |

### 6.2 迁移阶段

#### 阶段一：最小可行（2-3 周）

```
目标：Electron 壳 + 现有功能完整运行

工作内容：
├── 搭建 Electron + Vue 3 项目骨架
├── 实现 Python 子进程桥接
├── Express 内嵌服务（代理 Python API）
├── 迁移现有 Vue 页面到 Electron 渲染进程
├── SQLite 基础表结构
└── 基本窗口管理和托盘
```

#### 阶段二：体验升级（2-3 周）

```
目标：原生桌面体验 + 实时反馈

工作内容：
├── Pinia 全局状态管理
├── Socket.IO 实时进度推送
├── Agent 日志流式展示
├── 写作编辑器（Monaco Editor 或 CodeMirror）
├── 人物关系图可视化（D3.js / vis-network）
├── 时间线可视化
└── 系统通知（章节完成提醒）
```

#### 阶段三：深度集成（3-4 周）

```
目标：Node.js 原生能力 + 性能优化

工作内容：
├── 部分 Agent 用 Node.js 重写（字数统计、合并、敏感词检查）
├── Vercel AI SDK 替代 Python httpx 调用
├── SQLite 全面替代 YAML/JSON
├── 数据库迁移脚本（YAML → SQLite）
├── 向量检索集成（sqlite-vec 或 LanceDB）
└── 自动更新机制（electron-updater）
```

#### 阶段四：高级功能（持续迭代）

```
目标：智能化 + 生态完善

工作内容：
├── 本地 Embedding 模型（HuggingFace Transformers）
├── 混合检索（SQL + 向量）
├── 多小说项目管理
├── 导出功能（EPUB、PDF、TXT）
├── 插件系统（自定义 Agent）
└── 协作模式（局域网共享）
```

### 6.3 Python → Node.js 渐进迁移清单

| Agent | 优先级 | 迁移难度 | 说明 |
|-------|--------|----------|------|
| 字数统计脚本 | 高 | 低 | 纯计算，直接用 JS 重写 |
| 文件合并脚本 | 高 | 低 | 纯 IO，直接用 JS 重写 |
| 敏感词硬匹配 | 高 | 低 | 正则匹配，直接用 JS 重写 |
| Context Builder | 中 | 中 | 读取资产 + 组装上下文 |
| Planner | 低 | 高 | JSON 输出解析，需保留提示词 |
| Writer | 低 | 高 | 核心写作逻辑，建议保留 Python |
| Auditor | 低 | 高 | 状态更新逻辑复杂 |
| Style Editor | 低 | 高 | 文风处理，建议保留 Python |
| Stitch Editor | 低 | 中 | 接缝修复 |
| Continuity Checker | 低 | 高 | 一致性检查逻辑复杂 |

---

## 七、数据迁移方案

### 7.1 迁移范围

```
当前数据位置：
├── state/*.yaml          → SQLite tables
├── data/novel.sqlite     → userData/data/novel.sqlite（保留）
├── assets/*.yaml         → userData/assets/（保留）
├── assets/*.md           → userData/assets/（保留）
├── config/pipeline.yaml  → userData/config/（保留）
├── workspace/chapters/   → userData/workspace/（保留）
└── prompts/*.md          → 打包到应用内
```

### 7.2 YAML → SQLite 迁移脚本

```typescript
// electron/database/migrate-from-yaml.ts
import yaml from 'yaml';
import fs from 'fs';
import path from 'path';
import { db } from './connection';

export async function migrateFromYaml(stateDir: string) {
  // 迁移人物
  const contFile = path.join(stateDir, 'continuity_state.yaml');
  if (fs.existsSync(contFile)) {
    const cont = yaml.parse(fs.readFileSync(contFile, 'utf-8'));
    for (const [name, data] of Object.entries(cont.characters || {})) {
      await db('characters').insert({
        id: name,
        name,
        role: data.role || '',
        fixed_profile: JSON.stringify(data.fixed_profile || {}),
        speech_style: data.speech_style || '',
        constraints: JSON.stringify(data.constraints || []),
      }).onConflict('id').merge();
    }
  }

  // 迁移事件
  const eventsFile = path.join(stateDir, 'events.yaml');
  if (fs.existsSync(eventsFile)) {
    const events = yaml.parse(fs.readFileSync(eventsFile, 'utf-8'));
    for (const event of events.events || []) {
      await db('events').insert({
        id: event.id || `evt_${Date.now()}`,
        chapter_id: event.chapter_id,
        scene_id: event.scene_id,
        event_type: event.type,
        characters: JSON.stringify(event.characters || []),
        objects: JSON.stringify(event.objects || []),
        location: event.location,
        summary: event.summary,
        consequences: event.consequences,
      }).onConflict('id').ignore();
    }
  }

  // 迁移伏笔、钩子、道具类似...
}
```

---

## 八、UI 页面设计

### 8.1 页面清单

| 页面 | 路由 | 功能 |
|------|------|------|
| Dashboard | `/` | 总览看板：字数统计、进度、最近章节 |
| 章节列表 | `/chapters` | 所有章节、运行新章节 |
| 章节详情 | `/chapters/:id` | 章节正文、计划、报告、状态更新 |
| 小说状态 | `/state` | 人物、伏笔、钩子、道具、事件历史 |
| 时间线 | `/timeline` | 可视化时间线图 |
| 资产编辑 | `/assets` | 编辑人物卡、世界观、文风指南 |
| 配置管理 | `/config` | LLM 配置、多模型路由 |
| 任务监控 | `/tasks` | 实时任务进度、Agent 日志流 |

### 8.2 关键页面布局

```
┌─────────────────────────────────────────────────┐
│  [Logo] Novel Agent    [任务监控] [设置]    [─][□][×] │
├──────────┬──────────────────────────────────────┤
│          │                                      │
│  仪表盘   │  章节列表                              │
│  章节管理  │  ┌──────────────────────────────────┐│
│  小说状态  │  │ 001 | 雨夜来客 | 2100字 | 低风险  ││
│  时间线   │  │ 002 | 暗流涌动 | 1950字 | 低风险  ││
│  资产编辑  │  │ 003 | 白塔医院 | 2300字 | 中风险  ││
│  配置管理  │  │ ...                              ││
│  任务监控  │  └──────────────────────────────────┘│
│          │                                      │
│          │  [+ 运行新章节]                        │
│          │                                      │
│          │  实时日志                              │
│          │  ┌──────────────────────────────────┐│
│          │  │ [14:32:01] Planner: 生成场景卡...  ││
│          │  │ [14:32:15] Writer: 写作场景 001-1 ││
│          │  │ [14:32:45] Writer: 写作场景 001-2 ││
│          │  │ [14:33:12] Auditor: 审校中...      ││
│          │  └──────────────────────────────────┘│
└──────────┴──────────────────────────────────────┘
```

---

## 九、打包与分发

### 9.1 electron-builder 配置

```yaml
# electron-builder.yml
appId: com.novelagent.desktop
productName: NovelAgent
directories:
  output: dist-electron
files:
  - dist/**/*
  - electron/**/*
  - python/**/*
  - prompts/**/*
  - package.json
extraResources:
  - from: python/
    to: python/
  - from: prompts/
    to: prompts/
  - from: config/
    to: config/
win:
  target:
    - nsis
  icon: build/icon.ico
nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
  createDesktopShortcut: true
  createStartMenuShortcut: true
mac:
  target:
    - dmg
  icon: build/icon.icns
linux:
  target:
    - AppImage
  icon: build/icon.png
```

### 9.2 Python 运行时打包

由于保留了 Python Agent，需要在打包时包含 Python 运行时：

```
方案 A（推荐）：嵌入式 Python
├── 下载 Python embeddable package（~15MB）
├── 打包到 resources/python-runtime/
├── 安装依赖到 resources/python-runtime/Lib/site-packages/
└── 应用启动时设置 PYTHONPATH

方案 B：要求用户安装 Python
├── 应用启动时检测 Python 环境
├── 提示用户安装 Python 3.10+
└── 自动 pip install -r requirements.txt
```

### 9.3 预期产物大小

| 组件 | 大小 |
|------|------|
| Electron 运行时 | ~60MB |
| Vue 前端打包 | ~5MB |
| Node.js 依赖 | ~20MB |
| Python 嵌入式运行时 | ~15MB |
| Python 依赖 | ~30MB |
| Prompts + Config | ~1MB |
| **总计** | **~130MB** |

对比当前 PyInstaller 的 ~33MB，体积增大但功能和体验显著提升。可通过 electron-builder 的 asar 压缩减少 ~20%。

---

## 十、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| Python 子进程通信不稳定 | 中 | 高 | JSON 协议 + 超时重试 + 进程健康检查 |
| SQLite 并发写入冲突 | 低 | 中 | WAL 模式 + 单写多读 |
| Electron 包体积过大 | 高 | 低 | asar 压缩 + 按需加载 |
| Python 运行时版本兼容 | 中 | 高 | 嵌入式 Python + 锁定版本 |
| AI API 调用失败 | 中 | 中 | 重试机制 + 本地缓存 + 降级策略 |
| 跨平台兼容性 | 低 | 中 | CI/CD 多平台构建 + 自动测试 |

---

## 十一、开发环境搭建

### 11.1 前置要求

```
Node.js >= 20.0.0
Python >= 3.10
pnpm >= 9.0.0（推荐）或 npm >= 10.0.0
Git
```

### 11.2 快速开始

```bash
# 1. 创建项目
pnpm create electron-vue novel-agent-desktop
cd novel-agent-desktop

# 2. 安装依赖
pnpm install

# 3. 复制 Python Agent 核心
cp -r /path/to/小说生成agent/novel_agent ./python/novel_agent
cp -r /path/to/小说生成agent/prompts ./python/prompts
cp /path/to/小说生成agent/requirements.txt ./python/

# 4. 安装 Python 依赖
cd python && pip install -r requirements.txt && cd ..

# 5. 开发模式
pnpm dev

# 6. 构建
pnpm build

# 7. 打包
pnpm electron:build
```

### 11.3 开发脚本

```json
{
  "scripts": {
    "dev": "concurrently \"pnpm dev:renderer\" \"pnpm dev:main\"",
    "dev:renderer": "vite",
    "dev:main": "tsc -p tsconfig.electron.json && electron .",
    "build": "vue-tsc -b && vite build",
    "build:electron": "tsc -p tsconfig.electron.json",
    "electron:build": "pnpm build && pnpm build:electron && electron-builder",
    "test": "vitest",
    "lint": "eslint src electron --ext .ts,.vue"
  }
}
```

---

## 十二、里程碑时间线

```
Week 1-2:  项目骨架搭建
           ├── Electron + Vue 3 项目初始化
           ├── Express 内嵌服务
           ├── Python 子进程桥接（基础）
           └── SQLite 表结构设计

Week 3-4:  核心功能迁移
           ├── 章节运行流程（Planner → Writer → Auditor）
           ├── 章节列表 / 详情页面
           ├── 状态查看页面
           └── 实时日志流

Week 5-6:  体验优化
           ├── Pinia 状态管理
           ├── Socket.IO 实时进度
           ├── 资产编辑页面
           ├── 配置管理页面
           └── 系统托盘 + 通知

Week 7-8:  数据迁移 + 打包
           ├── YAML → SQLite 迁移脚本
           ├── electron-builder 打包
           ├── Python 运行时嵌入
           ├── 自动更新
           └── 基本测试

Week 9+:   持续迭代
           ├── Node.js 重写部分 Agent
           ├── Vercel AI SDK 集成
           ├── 向量检索
           └── 高级功能
```

---

## 附录 A：与 ToonFlow 的技术对照

| 特性 | ToonFlow | 本项目 | 差异说明 |
|------|----------|--------|----------|
| Electron 版本 | 未知 | 35+ | 使用最新稳定版 |
| 前端框架 | Vue 3.5.30 | Vue 3.5+ | 一致 |
| UI 组件库 | TDesign | Element Plus | 不迁移，保持现有 |
| 状态管理 | Pinia | Pinia | 一致 |
| 后端框架 | Express 5 | Express 5 | 一致 |
| 实时通信 | Socket.IO | Socket.IO | 一致 |
| 数据库 | better-sqlite3 + knex | better-sqlite3 + knex | 一致 |
| AI SDK | Vercel AI SDK | Vercel AI SDK | 一致 |
| 编辑器 | Monaco Editor | 待定（Monaco/CodeMirror） | 视需求选择 |
| Python Agent | 无 | 有（子进程桥接） | 本项目特有 |
| 打包工具 | electron-builder | electron-builder | 一致 |

## 附录 B：配置文件兼容

现有 `config/pipeline.yaml` 格式保持不变：

```yaml
# 多模型路由配置（兼容现有格式）
llm:
  default:
    provider: openai
    base_url: https://api.siliconflow.cn/v1
    api_key: sk-xxx
    model: deepseek-ai/DeepSeek-V3
  overrides:
    writer:
      model: Pro/deepseek-ai/DeepSeek-R1
    planner:
      model: Pro/deepseek-ai/DeepSeek-R1

chapter:
  default_target_chars: [1200, 2200]
  default_scene_target_chars: [400, 800]

runtime:
  max_workers: 4
  retry_attempts: 1
  interactive: false
```

Node.js 端读取此配置并映射到 Vercel AI SDK 的 provider 配置。

## 附录 C：IPC 接口清单

| 通道 | 方向 | 说明 |
|------|------|------|
| `app:getUserDataPath` | Renderer → Main | 获取 userData 路径 |
| `chapter:run` | Renderer → Main | 运行章节生成 |
| `chapter:abort` | Renderer → Main | 中止当前任务 |
| `chapter:progress` | Main → Renderer | 章节生成进度 |
| `agent:log` | Main → Renderer | Agent 日志输出 |
| `db:query` | Renderer → Main | 数据库查询（受限） |
| `config:get` | Renderer → Main | 获取配置 |
| `config:set` | Renderer → Main | 更新配置 |
| `window:minimizeToTray` | Renderer → Main | 最小化到托盘 |
| `updater:checkForUpdates` | Renderer → Main | 检查更新 |
| `updater:downloadUpdate` | Renderer → Main | 下载更新 |

---

*文档结束*
