# DramaForge：国内短剧全自动剧本生成系统

**设计文档 v1.0**　｜　面向国内竖屏短剧市场（番茄/红果·快手·抖音等平台）

---

## 目录

1. [项目定位与核心目标](#一项目定位与核心目标)
2. [市场与平台规范研究](#二市场与平台规范研究)
3. [系统架构总览](#三系统架构总览)
4. [五大 Agent 角色矩阵](#四五大-agent-角色矩阵)
5. [生成流水线（12步）](#五生成流水线12步)
6. [状态数据库设计](#六状态数据库设计)
7. [合规审查引擎](#七合规审查引擎)
8. [题材热度与爆款引擎](#八题材热度与爆款引擎)
9. [桌面应用 UI 设计](#九桌面应用-ui-设计)
10. [输出格式规范](#十输出格式规范)
11. [技术选型](#十一技术选型)
12. [数据库完整表结构](#十二数据库完整表结构)
13. [Agent Prompt 模板](#十三agent-prompt-模板)
14. [MVP 开发计划](#十四mvp-开发计划)
15. [商业变现路径](#十五商业变现路径)

---

## 一、项目定位与核心目标

### 1.1 产品定位

DramaForge 是一款运行于 Windows 10/11 的桌面端短剧剧本生成工具。它不是通用写作助手，而是一个**深度绑定国内短剧市场工业标准**的全自动 AI 生产力工具，核心目标只有一个：

> **帮助用户批量生成符合平台投稿要求、可过初审的国内竖屏短剧剧本，实现从"选题"到"可投稿文档"的全流程自动化。**

### 1.2 用户画像

| 用户类型 | 描述 | 核心需求 |
|:---|:---|:---|
| **个人编剧** | 有写作经验、了解短剧市场，但产量不足 | 提速、保持节奏感 |
| **工作室经营者** | 运营小型剧本工作室，需批量出稿 | 批量生产、格式规范 |
| **跨界转型者** | 小说作者、自媒体人想切入短剧赛道 | 降低入门门槛 |
| **投资测试者** | 想测试多个题材是否有市场潜力 | 快速原型验证 |

### 1.3 与竞品的核心差异

| 功能 | 通用 AI 写作工具 | DramaForge |
|:---|:---|:---|
| 格式规范 | 通用文本，无剧本格式 | 内置国内短剧标准格式 |
| 合规意识 | 无 | 广电红线硬扫描 + 自动修正 |
| 节奏控制 | 依赖提示词质量 | 内置"冲突-升级-反转-钩子"节奏引擎 |
| 题材引导 | 无 | 内置题材热度库 + 平台偏好匹配 |
| 可拍性评估 | 无 | 场景/演员数量自动评分 |
| 投稿材料 | 无 | 一键生成完整投稿包（Word 文档） |

---

## 二、市场与平台规范研究

### 2.1 国内短剧行业 2025-2026 标准

根据《微短剧创作生产及内容审核技术规范》（T/CEAP 1—2025）及广电总局最新管理规定：

**剧本结构要求：**
- 单集时长：1-2 分钟，对应剧本字数 **550-800 字/集**
- 总集数：60-100 集
- 整体结构：六幕式（起 → 困 → 反 → 升 → 爽 → 合）
- 每集公式：**冲突 → 升级 → 反转 → 留钩**
- 情绪密度：每 3 分钟一个爽点/泪点/笑点，每集结尾必留悬念

**黄金节奏法则：**
- 开篇 3 秒必须抛出钩子
- 30 秒内建立核心冲突
- 每集结尾必须有反转或悬念

### 2.2 主流平台投稿规则

| 平台 | 初审集数 | 完本集数 | 保底稿费 | 主收题材 |
|:---|:---|:---|:---|:---|
| 番茄/红果 | 前 30 集 | 80-100 集 | 5 万起 | 全题材，女频强势 |
| 七猫 | 10 集（一卡） | 自定 | 1.5-10 万 | 优先改编七猫 IP |
| 快手短剧 | 前 10 集 | 60-80 集 | 协商 | 下沉市场、现实题材 |
| 抖音/红果 | 10 集 | 60-100 集 | 分账为主 | 全题材，爆款逻辑 |

### 2.3 2026 年热门题材矩阵

```
政策扶持（平台优先推）     市场刚需（付费率高）      新兴赛道（竞争少）
────────────────        ────────────────        ────────────────
非遗文化                 清醒大女主              AI/科技题材
乡村振兴                 复仇打脸                电竞/游戏
红色主旋律               甜宠虐恋                跨文化/留学
文旅融合                 家庭伦理                职场成长
现实成长                 赘婿/战神（男频）         悬疑推理
```

### 2.4 合规红线（一票否决项）

> 以下内容触发直接毙稿，系统必须在生成前后双重扫描：

- 政治敏感：危害国家统一、美化历史错误、歪曲重大事件
- 价值观红线：拜金炫富、恋爱脑、美化犯罪、替身文学
- 尺度禁区：血腥暴力、性暗示、未成年人不当内容
- 职业禁区：司法/军警题材中的程序违法、私自刑讯
- 格式红线：标题封面低俗、哗众取宠

---

## 三、系统架构总览

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户输入层（UI）                        │
│  题材选择 / 人物设定 / 爽点类型 / 集数 / 特殊要求           │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                   ScriptOrchestrator                     │
│          （主控调度器 · 管理12步流水线状态）                │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
 ① 总策划    ② 分集    ③ 写手     ④ 合规     ⑤ 格式化
  Agent      规划      Agent     审查        输出
             Agent              Agent       Agent
   │
   ▼
┌──────────────────────────────┐
│        SQLite 状态数据库       │
│  项目表/人物表/集纲表/道具表    │
│  场景表/合规报告表/输出记录表   │
└──────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                     输出层                               │
│  ① 完整剧本 .docx　② 投稿包（大纲+前10集）　③ 合规报告    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 数据流向

```
用户配置
    │
    ├──► 题材热度引擎 ──► 题材评分报告（反馈给用户确认）
    │
    └──► Orchestrator
              │
              ├──[Step 1-2]── 总策划 Agent ──► 六幕大纲 + 人物档案 (JSON)
              │
              ├──[Step 3-4]── 分集规划 Agent ──► 集纲列表 (JSON × N集)
              │
              ├──[Step 5-6]── 剧本写手 Agent ──► 单集剧本草稿 (× 并行N集)
              │                    │
              │              [读 SQLite 状态]
              │
              ├──[Step 7]──── 合规审查 Agent ──► 风险评分 + 修正建议
              │                    │
              │              [高风险 → 回写写手重生成]
              │
              ├──[Step 8]──── 格式化输出 Agent ──► 标准中文剧本格式
              │
              ├──[Step 9]──── 状态同步 ──► 更新 SQLite（道具/情绪/场景）
              │
              └──[Step 10-12]─ 投稿包组装 ──► Word 文档导出
```

---

## 四、五大 Agent 角色矩阵

### 4.1 Agent 职责概览

```
Agent               职责一句话                      输入              输出
────────────────    ──────────────────────         ────────          ────────
① 总策划 Agent      六幕大纲 + 人物档案              用户配置          结构化 JSON
② 分集规划 Agent    逐集集纲（冲突/钩子/场景）        大纲 + 人物档案   集纲列表 JSON
③ 剧本写手 Agent    单集剧本正文（中文剧本格式）       集纲 + 状态上下文  550-800字剧本文本
④ 合规审查 Agent    广电红线扫描 + 评分 + 自动修正    剧本文本          合规报告 + 修正稿
⑤ 格式化输出 Agent  组装可投稿文档                   所有集剧本         Word 文档包
```

### 4.2 ① 总策划 Agent（Chief Planner）

**职责：** 这是整个项目的"创意总监"。接收用户输入，结合题材热度数据，生成完整的故事架构、六幕结构分布、主要人物档案。

**核心产出（JSON 格式）：**

```json
{
  "project": {
    "title": "项目标题",
    "genre": "题材类型",
    "platform_target": "目标平台",
    "total_episodes": 80,
    "logline": "一句话故事概述（不超过50字）",
    "hook": "开篇钩子描述"
  },
  "six_act_structure": {
    "act_1_qi": { "episodes": "1-10", "core_event": "", "emotion_peak": "" },
    "act_2_kun": { "episodes": "11-25", "core_event": "", "emotion_peak": "" },
    "act_3_fan": { "episodes": "26-40", "core_event": "", "emotion_peak": "" },
    "act_4_sheng": { "episodes": "41-55", "core_event": "", "emotion_peak": "" },
    "act_5_shuang": { "episodes": "56-70", "core_event": "", "emotion_peak": "" },
    "act_6_he": { "episodes": "71-80", "core_event": "", "emotion_peak": "" }
  },
  "characters": [
    {
      "id": "char_001",
      "name": "角色名",
      "role": "主角/配角/反派",
      "core_motivation": "核心动机",
      "fatal_flaw": "性格弱点",
      "speech_style": "台词特征（如：说话简短、爱用反问、带方言词）",
      "arc": "角色成长弧线"
    }
  ],
  "paid_hooks": [
    { "episode": 10, "hook_type": "身份反转", "description": "" },
    { "episode": 30, "hook_type": "关系破裂", "description": "" }
  ]
}
```

**设计重点：**
- 强制要求每 10 集设置一个"付费钩子"（逆袭/揭秘/身份反转）
- 六幕结构比例锁定，不允许 Agent 自由发挥偏移
- 人物档案中的 `speech_style` 字段会被传递给写手 Agent，强制保持台词一致性

### 4.3 ② 分集规划 Agent（Episode Planner）

**职责：** 将六幕大纲拆解为逐集的集纲卡片。每张集纲卡是写手 Agent 的"施工图"，不允许含糊。

**核心产出（每集一个 JSON）：**

```json
{
  "episode_id": 5,
  "act": "act_1_qi",
  "episode_title": "第5集参考标题",
  "opening_hook": "开篇3秒抓手描述",
  "core_conflict": "本集核心冲突",
  "escalation": "冲突如何升级",
  "reversal": "反转点描述",
  "ending_hook": "结尾悬念/钩子",
  "emotion_type": "爽/虐/甜/笑",
  "scenes": [
    {
      "scene_no": 1,
      "location": "地点描述",
      "time": "日/夜",
      "environment": "内景/外景",
      "characters": ["角色A", "角色B"],
      "scene_purpose": "本场戏推进了什么",
      "estimated_cost": "低/中/高"
    }
  ],
  "props_involved": ["关键道具1", "关键道具2"],
  "character_states_entry": { "角色A": "情绪/状态" },
  "character_states_exit": { "角色A": "情绪/状态" },
  "word_count_target": 700
}
```

**设计重点：**
- `estimated_cost` 字段：低（3景以内、5人以内、无特效）、中、高
- 超过"高"的场景自动触发警告，提示用户是否接受
- `ending_hook` 字段不允许为空，强制填写

### 4.4 ③ 剧本写手 Agent（Script Writer）

**职责：** 这是系统的核心生产力模块。根据集纲卡和角色档案，生成符合国内短剧格式标准的单集剧本正文。

**输入上下文包（Context Pack）：**

```
1. 本集集纲（JSON）
2. 相关角色档案（name / speech_style / current_state）
3. 前集关键事件摘要（从 SQLite 读取）
4. 当前道具状态（从 SQLite 读取）
5. 格式规范说明（硬编码在 System Prompt）
```

**国内短剧标准格式规范（写手必须遵守）：**

```
场景头格式：
【内景·咖啡厅·白天】

动作描写：
简洁精炼，第三人称，无心理描写。
错误：他内心很纠结，想起了往事。
正确：他攥紧了外套，视线停在窗外，一言不发。

对白格式：
角色名（情绪/动作备注，可选）
台词内容

示例：
林晓（逼近一步）
你以为你还有选择吗？

段落间空一行。每场戏结尾标注"——"换场。
```

**写手 Agent 的限制规则（硬编码进 Prompt）：**

- 单集字数：550-800 字，超出截断，不足补充
- 禁止心理独白（"他想到了…" "她心里清楚…" 一律替换为动作）
- 每集结尾最后一行必须是悬念或反转（对应集纲的 `ending_hook`）
- 台词必须符合角色的 `speech_style`
- 场景数量不超过集纲规定值

### 4.5 ④ 合规审查 Agent（Compliance Auditor）

**职责：** 所有剧本生成后的强制过滤层。分两阶段工作：

**阶段一：硬规则扫描（不走 LLM，本地正则）**

```python
# 敏感词库硬匹配（部分示例）
HARD_BLOCK_KEYWORDS = [
    # 政治类（直接毙稿）
    "分裂", "台独", "藏独",
    # 价值观类
    "私刑", "非法拘禁", "以暴制暴并且逍遥法外",
    # 尺度类
    "露骨", "裸体", "色情",
]

SOFT_WARN_KEYWORDS = [
    # 需要 LLM 判断上下文的
    "复仇", "绑架", "黑金", "洗钱",
]
```

**阶段二：LLM 语义审查**

针对软警告词和整体价值观进行语义级别的评估，输出：

```json
{
  "episode_id": 5,
  "hard_violations": [],
  "soft_warnings": [
    {
      "line": "第23行",
      "content": "原文片段",
      "reason": "涉及私刑场景，需调整法律后果描写",
      "suggestion": "建议修改方向"
    }
  ],
  "overall_risk_level": "低/中/高",
  "platform_pass_probability": 0.85,
  "auto_fix": "修正后的对应段落文本"
}
```

**风险处理机制：**
- `低`：直接通过，记录日志
- `中`：高亮标注，提示用户手动确认
- `高`：自动将问题描述打包回写手 Agent，触发定向重写（最多重试 3 次）

### 4.6 ⑤ 格式化输出 Agent（Formatter）

**职责：** 将通过合规审查的所有集剧本组装为可直接投稿的文档结构。

**产出物清单：**

1. **完整剧本 .docx**
   - 封面页：剧名、总集数、题材、联系方式
   - 人物表：所有角色简介
   - 正文：按集编排，每集有分隔标题

2. **投稿包 .docx**（初审用）
   - 作品信息表（平台要求格式）
   - 故事简介（200字以内）
   - 六幕大纲（1500字以内）
   - 前10集完整剧本正文

3. **合规报告 .pdf**
   - 各集风险评分
   - 平台过审概率预估
   - 具体修改建议

---

## 五、生成流水线（12步）

```
Step 01  题材评估
         输入用户题材需求 → 查询题材热度库 → 生成题材评分报告
         → 用户确认（可调整题材方向）

Step 02  概念设计
         总策划 Agent → 六幕大纲 + 人物档案
         → 写入 projects / characters 表
         → 展示给用户预览，支持调整

Step 03  集纲排布
         分集规划 Agent → 生成全部集纲（并行生成，每10集一批）
         → 写入 episodes 表
         → 展示集纲看板，用户可拖拽调整顺序

Step 04  可拍性评估
         扫描所有集纲中的场景数量、演员数量、特效需求
         → 生成可拍性评分报告
         → 高成本场景高亮提示

Step 05  单集剧本生成（并行 × 5集）
         写手 Agent × 5（并行）
         读取 SQLite：前集事件摘要 + 道具状态 + 角色情绪
         输出单集剧本草稿

Step 06  节奏校验
         自动检测每集：
         - 字数是否在 550-800 范围内
         - 结尾是否有悬念/反转（检查结尾20%内容）
         - 是否有心理独白（关键词匹配）
         不达标集自动补充生成

Step 07  合规审查（强制关卡）
         硬词扫描 → LLM 语义审查 → 风险评分
         高风险 → 定向重写（回到 Step 05）
         中风险 → 高亮标注，等待用户决策

Step 08  人工审阅门（可选）
         用户可在此步骤逐集审阅、编辑、标注
         支持：通过 / 驳回重写 / 手动编辑
         可跳过（全自动模式）

Step 09  状态同步
         将每集结束时的状态写入 SQLite：
         - 各角色情绪状态
         - 道具当前持有者
         - 关键事件摘要（供后续集召回）

Step 10  集纲摘要生成
         为每集生成100字以内摘要（供后续上下文压缩使用）
         写入 episode_summaries 表

Step 11  投稿包组装
         格式化输出 Agent
         → 完整剧本 .docx
         → 投稿包 .docx（大纲+前10集）
         → 合规报告 .pdf

Step 12  导出与归档
         文件保存到本地
         项目状态更新为"已完成"
         生成项目统计报告（总字数/耗时/Token消耗/费用估算）
```

---

## 六、状态数据库设计

使用 SQLite，一个项目对应一个 `.db` 文件，可随时中断恢复。

### 6.1 数据库表总览

```
projects          项目主表
characters        人物档案表
episodes          集纲表
episode_scripts   集剧本正文表
episode_summaries 集摘要表（用于上下文压缩）
scenes            场景目录表
props             道具流转表
character_states  角色状态变化表
compliance_logs   合规检查记录表
generation_logs   生成日志表
```

### 6.2 核心表结构

#### `projects` 项目主表

```sql
CREATE TABLE projects (
    id              TEXT PRIMARY KEY,        -- 项目 UUID
    title           TEXT NOT NULL,           -- 剧本名称
    genre           TEXT NOT NULL,           -- 题材类型
    sub_genre       TEXT,                    -- 子题材（如：都市甜宠+逆袭）
    platform_target TEXT,                    -- 目标投稿平台
    total_episodes  INTEGER DEFAULT 80,      -- 总集数
    episode_length  INTEGER DEFAULT 700,     -- 目标每集字数
    logline         TEXT,                    -- 一句话简介
    six_act_json    TEXT,                    -- 六幕结构 JSON
    status          TEXT DEFAULT 'init',     -- init/planning/writing/reviewing/done
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

#### `characters` 人物档案表

```sql
CREATE TABLE characters (
    id              TEXT PRIMARY KEY,
    project_id      TEXT REFERENCES projects(id),
    name            TEXT NOT NULL,
    role_type       TEXT,                    -- 主角/配角/反派/工具人
    core_motivation TEXT,                    -- 核心动机
    fatal_flaw      TEXT,                    -- 性格弱点
    speech_style    TEXT,                    -- 台词特征（关键！传给写手）
    character_arc   TEXT,                    -- 角色成长弧线
    appearance      TEXT,                    -- 外貌描述
    current_emotion TEXT DEFAULT '平静',     -- 当前情绪状态（随剧情更新）
    current_location TEXT,                   -- 当前所在场景
    is_alive        INTEGER DEFAULT 1        -- 是否存活
);
```

#### `episodes` 集纲表

```sql
CREATE TABLE episodes (
    id              INTEGER PRIMARY KEY,
    project_id      TEXT REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,        -- 集数
    act_stage       TEXT,                    -- 所属幕次（act_1_qi 等）
    opening_hook    TEXT,                    -- 开篇钩子
    core_conflict   TEXT,                    -- 核心冲突
    escalation      TEXT,                    -- 冲突升级
    reversal        TEXT,                    -- 反转点
    ending_hook     TEXT NOT NULL,           -- 结尾钩子（不允许为空）
    emotion_type    TEXT,                    -- 爽/虐/甜/笑
    scenes_json     TEXT,                    -- 场景列表 JSON
    props_involved  TEXT,                    -- 涉及道具（JSON 数组）
    word_target     INTEGER DEFAULT 700,
    status          TEXT DEFAULT 'planned',  -- planned/writing/done/rejected
    generation_attempts INTEGER DEFAULT 0
);
```

#### `episode_scripts` 集剧本正文表

```sql
CREATE TABLE episode_scripts (
    id              TEXT PRIMARY KEY,
    project_id      TEXT REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,
    content         TEXT NOT NULL,           -- 剧本正文全文
    word_count      INTEGER,                 -- 实际字数
    version         INTEGER DEFAULT 1,       -- 重写版本号
    compliance_risk TEXT DEFAULT 'low',      -- low/medium/high
    is_approved     INTEGER DEFAULT 0,       -- 用户审批标记
    created_at      TEXT DEFAULT (datetime('now'))
);
```

#### `props` 道具流转表

```sql
CREATE TABLE props (
    id              TEXT PRIMARY KEY,        -- 道具标识（如 gun_001）
    project_id      TEXT REFERENCES projects(id),
    name            TEXT NOT NULL,           -- 道具名称
    description     TEXT,                    -- 道具描述
    current_holder  TEXT,                    -- 当前持有角色（或"场景容器"）
    current_state   TEXT,                    -- 当前状态（如：已上膛/损坏/信封未拆）
    last_episode    INTEGER,                 -- 最后出现集数
    importance      TEXT DEFAULT 'normal'    -- normal/key（关键道具重点追踪）
);
```

#### `character_states` 角色状态变化表

```sql
CREATE TABLE character_states (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT REFERENCES projects(id),
    character_id    TEXT REFERENCES characters(id),
    episode_no      INTEGER,
    emotion         TEXT,                    -- 情绪状态
    physical_state  TEXT,                    -- 生理状态（伤势/衣着变化）
    location        TEXT,                    -- 所在场景
    key_event       TEXT,                    -- 本集发生的关键事件摘要
    recorded_at     TEXT DEFAULT (datetime('now'))
);
```

#### `compliance_logs` 合规检查记录表

```sql
CREATE TABLE compliance_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT REFERENCES projects(id),
    episode_no      INTEGER,
    risk_level      TEXT,                    -- low/medium/high
    hard_violations TEXT,                    -- JSON：硬违规列表
    soft_warnings   TEXT,                    -- JSON：软警告列表
    pass_probability REAL,                   -- 过审概率 0-1
    auto_fixed      INTEGER DEFAULT 0,       -- 是否自动修复
    checked_at      TEXT DEFAULT (datetime('now'))
);
```

---

## 七、合规审查引擎

### 7.1 架构设计

合规审查分为**两层**，严格按顺序执行：

```
                输入：剧本文本
                     │
              ┌──────▼──────┐
              │  第一层      │
              │ 本地硬规则   │──► 命中 → 立即返回高风险，不进 LLM
              │ 正则匹配     │
              └──────┬──────┘
                     │ 未命中
              ┌──────▼──────┐
              │  第二层      │
              │  LLM 语义   │──► 输出风险评分 + 修改建议
              │  审查        │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │  综合评分    │──► low/medium/high
              │  输出报告    │
              └─────────────┘
```

### 7.2 敏感词库分级

```python
# 硬违规词（命中即返回 high risk，不进 LLM 审查）
HARD_BLOCK = {
    "政治类": ["台独", "分裂国家", "藏独", "港独", "天安门事件"],
    "尺度类": ["色情", "强奸", "露骨性描写", "裸体"],
    "极端类": ["恐怖主义", "极端组织", "炸弹制作"],
}

# 软警告词（命中后进入 LLM 语义判断）
SOFT_WARN = {
    "价值观类": [
        "私刑", "以暴制暴", "恋爱脑", "有钱就是爹",
        "炫富", "拜金", "不劳而获"
    ],
    "法律类": [
        "无证据定罪", "私自拘禁", "程序违法",
        "刑讯逼供", "非法集资成功"
    ],
    "尺度类": [
        "血腥", "暴力美学", "嗜血", "肢解"
    ],
    "历史类": [
        "戏说历史", "歪曲事实", "美化侵略"
    ]
}
```

### 7.3 LLM 审查 Prompt 模板

```
System:
你是中国网络微短剧内容合规审查专家，熟悉广电总局《微短剧创作生产及内容审核技术规范》（T/CEAP 1—2025）及最新管理规定。

你的任务是对以下剧本片段进行合规审查，重点检查：
1. 价值观导向：是否美化犯罪、宣扬拜金、鼓励极端行为
2. 内容尺度：是否含有不当暴力、性暗示、低俗内容
3. 法律常识：是否存在明显的法律错误（如私刑描写、非法行为美化）
4. 结局导向：反派/不良行为是否最终得到应有惩戒

输出 JSON 格式，字段如下：
- risk_level: "low" / "medium" / "high"
- issues: 问题列表（每项含 line/content/reason/suggestion）
- pass_probability: 0.0-1.0（预估平台过审概率）
- auto_fix_suggestion: 主要问题的修改建议文本

User:
以下是第{N}集剧本内容：
{script_content}

请进行合规审查。
```

---

## 八、题材热度与爆款引擎

### 8.1 题材数据库结构

题材热度数据以 JSON 文件存储于本地，定期手动更新（或接入爬虫自动更新）：

```json
{
  "update_date": "2026-05",
  "genres": [
    {
      "name": "清醒大女主",
      "heat_score": 95,
      "competition": "高",
      "platforms": ["番茄", "抖音", "快手"],
      "typical_elements": ["职场逆袭", "渣男打脸", "闺蜜背叛"],
      "avoid_elements": ["恋爱脑", "过度依赖男主"],
      "reference_works": ["《XX》","《YY》"],
      "trend": "稳定",
      "note": "2026年顶流题材，竞争激烈，需微创新"
    },
    {
      "name": "非遗文化",
      "heat_score": 72,
      "competition": "低",
      "platforms": ["番茄", "抖音", "优酷"],
      "typical_elements": ["传承故事", "技艺展示", "师徒情"],
      "avoid_elements": [],
      "trend": "上升",
      "note": "政策扶持，平台推流优先，竞争少，新赛道"
    }
  ]
}
```

### 8.2 用户题材选择界面逻辑

```
用户输入/选择题材
        │
        ▼
查询题材数据库
        │
        ▼
生成"题材评估卡"展示：
┌────────────────────────────────┐
│  题材：清醒大女主               │
│  热度：★★★★★ (95/100)          │
│  竞争：高（推荐微创新）          │
│  平台：番茄/抖音/快手            │
│  趋势：稳定                     │
│                                │
│  推荐融合元素：                  │
│  + 加入"非遗"元素 → 政策加分     │
│  + 融合"职场成长" → 变现点更多   │
│                                │
│  规避风险：                     │
│  ⚠ 避免"恋爱脑"情节              │
│  ⚠ 结局需价值观正向收束          │
└────────────────────────────────┘
        │
        ▼
用户确认题材方向 → 进入 Step 02
```

### 8.3 爆款节奏模板库

内置各题材类型的节奏模板，分集规划 Agent 优先调用：

```json
{
  "template_name": "复仇打脸标准模板",
  "genre": "复仇/打脸",
  "rhythm_pattern": {
    "ep_1_5": "受辱/失败，建立同情共鸣",
    "ep_6_10": "身份/能力初次暗示（第一个付费钩子）",
    "ep_11_20": "开始反击，小胜利积累",
    "ep_21_30": "关系危机，背叛出现（第二个付费钩子）",
    "ep_31_45": "逆袭加速，打脸密集",
    "ep_46_60": "高潮对决，身份完全揭露",
    "ep_61_75": "最终胜利，各方收束",
    "ep_76_80": "结局：正向价值观落地"
  },
  "must_have_elements": [
    "至少3次打脸场景（分布在第15/35/65集附近）",
    "1次身份大反转",
    "2次关系破裂与修复",
    "最终反派得到法律/道德惩处"
  ]
}
```

---

## 九、桌面应用 UI 设计

### 9.1 技术框架

- **桌面框架**：Tauri 2.x（Rust 后端 + WebView 前端）
- **前端**：React 18 + TypeScript
- **UI 组件**：Tailwind CSS（自定义主题）
- **本地服务**：Python FastAPI（通过 Tauri sidecar 启动）
- **AI 调用**：由 Python 层统一管理，前端通过 HTTP 调用

### 9.2 主界面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  标题栏：DramaForge  [项目：《无名之辈》]  ●●○ 当前：写稿中（45%）  │
├───────────┬──────────────────────────────┬─────────────────────┤
│           │                              │                     │
│  左侧栏   │      中央主编辑区             │     右侧信息面板      │
│  (200px)  │      (弹性宽度)              │     (280px)         │
│           │                              │                     │
│ ◎ 项目    │  ┌──集纲看板 / 剧本编辑──┐    │  人物状态            │
│ ◎ 题材    │  │                      │    │  道具追踪            │
│ ◎ 人物    │  │   [集数卡片看板]       │    │  合规报告            │
│ ◎ 集纲    │  │   [单集剧本编辑器]     │    │  生成日志            │
│ ◎ 导出    │  │   [全文预览]          │    │                     │
│           │  └──────────────────────┘    │                     │
│           │                              │                     │
└───────────┴──────────────────────────────┴─────────────────────┘
│  底部状态栏：Token消耗: 12,450  费用: ¥0.38  当前步骤: Step 5/12   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 集数看板（核心视图）

以卡片形式展示所有集的状态，支持拖拽调序：

```
┌──────┬──────┬──────┬──────┬──────┐
│ E01  │ E02  │ E03  │ E04  │ E05  │
│ ✓已完成│ ✓已完成│ ⚠合规  │ ✍写作中│ ○未开始│
│[预览]│[预览]│[审阅]│ 70%  │      │
└──────┴──────┴──────┴──────┴──────┘
  • 绿色边框：已完成+已审批
  • 橙色边框：合规风险待处理
  • 蓝色边框：生成中
  • 灰色：未开始
```

### 9.4 单集剧本编辑器

左右双栏设计：
- 左侧：可编辑的剧本文本区域（支持中文剧本格式语法高亮）
- 右侧：集纲信息（提醒当前集的冲突/反转/钩子要求）
- 底部工具栏：字数统计 / 合规重检 / 重新生成 / 通过

### 9.5 可拍性评分面板

在集纲生成后展示，帮助用户了解拍摄成本：

```
第 12 集 可拍性评估
─────────────────────────────────
场景数量：   ██░░░░ 2个   ✓ 优秀
演员数量：   ███░░░ 4人   ✓ 良好
特效需求：   ░░░░░░ 无    ✓ 优秀
外景比例：   ██░░░░ 1处   ✓ 良好
整体评分：   ★★★★☆ 低成本

预估单集拍摄成本：偏低（适合中小成本制作）
```

### 9.6 道具流转追踪面板

以时序列表展示关键道具的状态变化（不做复杂的桑基图，MVP 阶段用简洁列表）：

```
道具：神秘信封 #001
─────────────────────────────────
E01  → 出现  持有者：张秘书  状态：未拆封
E05  → 转移  持有者：男主    状态：未拆封
E08  → 状态变更  男主拆封，发现内容，信封销毁
E09  → 内容传递  男主告知女主
（信封道具归档，内容线索作为"信息道具"继续追踪）
```

---

## 十、输出格式规范

### 10.1 国内短剧标准剧本格式

**注意：国内短剧不用 Fountain 格式，用中文剧本行业惯例格式。**

```
【内景·医院走廊·白天】

护士推着病历车匆匆走过，走廊另一头，林晓靠在墙上，
死死盯着手机屏幕上那条信息——"你父亲的手术费还差
三十万，请尽快处理。"

她缓缓放下手机，深吸一口气。

陈总（西装笔挺，走近）
林晓，你来了。

林晓（抬头，神情平静到令人不安）
陈总，我想谈谈合同的事。

陈总（停顿，目光游移）
……什么合同？

林晓（轻轻笑了）
五年前，你让我签的那份。

陈总的笑容僵在脸上。

——
```

**格式规则总结：**
- 场景头：`【内景/外景·地点·时间】`
- 动作描写：第三人称，无心理描写，顶格写
- 角色名：加粗显示（Word 文档中），对话前独占一行
- 情绪/动作备注：括号内，轻描淡写
- 段落间空一行
- 换场符：`——` 单独一行

### 10.2 Word 文档结构

**完整剧本 .docx 结构：**

```
封面
├─ 剧名（大字居中）
├─ 总集数 / 每集时长
├─ 题材分类
├─ 版本号 / 日期
└─ 联系方式

人物表（第2页）
├─ 主要人物：姓名 + 一句话人设
└─ 次要人物列表

六幕大纲（第3页）
└─ 各幕核心事件描述

正文（第4页起）
├─ 第1集
│   ├─ 集标题（可选）
│   └─ 剧本正文
├─ 第2集
└─ ……（按集编排，每集之间分页符）
```

**投稿包 .docx 结构（初审专用）：**

```
作品信息表
├─ 剧名
├─ 题材：都市情感（微创新：…）
├─ 总集数：80集  每集时长：2分钟
├─ 版权状态：原创 / 改编自…
├─ 参考作品：《XX》《YY》
└─ 联系方式

作者简介（200字）

一句话简介

故事大纲（800-1500字）
├─ 主要人物
├─ 核心冲突
└─ 六幕结构简述

前10集剧本正文
└─ 完整格式
```

---

## 十一、技术选型

### 11.1 技术栈总览

| 层级 | 技术选型 | 选型理由 |
|:---|:---|:---|
| 桌面框架 | Tauri 2.x | 轻量、Rust 安全、你有经验 |
| 前端 | React 18 + TypeScript | 组件化成熟，生态好 |
| CSS | Tailwind CSS | 快速开发，定制性强 |
| 本地后端 | Python 3.11 + FastAPI | AI 调用生态最丰富 |
| 进程管理 | Tauri Sidecar | 让 Python 作为子进程运行 |
| 数据库 | SQLite（via SQLAlchemy） | 轻量、单文件、断点续传 |
| AI 调用 | Anthropic Python SDK | Claude 中文语感最好 |
| 文档生成 | python-docx | 生成 Word 文档 |
| 合规扫描 | 本地正则 + LLM | 分层处理，省钱高效 |

### 11.2 项目目录结构

```
DramaForge/
├── src-tauri/              # Tauri/Rust 主进程
│   ├── src/
│   │   ├── main.rs
│   │   └── sidecar.rs      # Python sidecar 管理
│   └── tauri.conf.json
│
├── src/                    # React 前端
│   ├── components/
│   │   ├── EpisodeBoard/   # 集数看板
│   │   ├── ScriptEditor/   # 剧本编辑器
│   │   ├── CompliancePanel/# 合规面板
│   │   ├── PropTracker/    # 道具追踪
│   │   └── ExportPanel/    # 导出面板
│   ├── pages/
│   │   ├── NewProject.tsx
│   │   ├── Dashboard.tsx
│   │   └── Settings.tsx
│   └── store/              # Zustand 全局状态
│
├── backend/                # Python FastAPI 后端
│   ├── main.py             # FastAPI 入口
│   ├── orchestrator.py     # 主调度器
│   ├── agents/
│   │   ├── chief_planner.py
│   │   ├── episode_planner.py
│   │   ├── script_writer.py
│   │   ├── compliance_auditor.py
│   │   └── formatter.py
│   ├── database/
│   │   ├── models.py       # SQLAlchemy 模型
│   │   └── crud.py         # 数据库操作
│   ├── compliance/
│   │   ├── keyword_scanner.py
│   │   └── keyword_lists.py
│   ├── genre_engine/
│   │   ├── genre_db.json   # 题材热度数据
│   │   └── templates.json  # 节奏模板库
│   └── exporter/
│       └── docx_builder.py # Word 文档生成
│
└── docs/                   # 设计文档
    └── shortdrama_agent_design.md
```

### 11.3 API 接口设计（后端）

```
POST /api/project/create          创建新项目
POST /api/project/{id}/start      启动生成流水线
GET  /api/project/{id}/status     获取生成进度

GET  /api/genre/evaluate          题材评估
GET  /api/genre/list              题材列表

POST /api/episode/{id}/regenerate 重新生成指定集
POST /api/episode/{id}/approve    审批通过
POST /api/episode/{id}/reject     驳回重写

GET  /api/compliance/{ep_id}      获取合规报告
POST /api/compliance/{ep_id}/fix  触发自动修复

POST /api/export/full             导出完整剧本
POST /api/export/submission       导出投稿包
POST /api/export/report           导出合规报告

GET  /api/props/{project_id}      获取道具流转
GET  /api/characters/{project_id} 获取角色状态列表
```

---

## 十二、数据库完整表结构

```sql
-- 项目主表
CREATE TABLE projects (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    genre           TEXT NOT NULL,
    sub_genre       TEXT,
    platform_target TEXT,
    total_episodes  INTEGER DEFAULT 80,
    episode_length  INTEGER DEFAULT 700,
    logline         TEXT,
    six_act_json    TEXT,
    characters_json TEXT,
    status          TEXT DEFAULT 'init',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 人物档案表
CREATE TABLE characters (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    name            TEXT NOT NULL,
    role_type       TEXT CHECK(role_type IN ('主角','配角','反派','工具人')),
    core_motivation TEXT,
    fatal_flaw      TEXT,
    speech_style    TEXT,
    character_arc   TEXT,
    appearance      TEXT,
    current_emotion TEXT DEFAULT '平静',
    current_location TEXT,
    is_alive        INTEGER DEFAULT 1
);

-- 集纲表
CREATE TABLE episodes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,
    act_stage       TEXT,
    opening_hook    TEXT,
    core_conflict   TEXT,
    escalation      TEXT,
    reversal        TEXT,
    ending_hook     TEXT NOT NULL,
    emotion_type    TEXT CHECK(emotion_type IN ('爽','虐','甜','笑','悬')),
    scenes_json     TEXT,
    props_involved  TEXT,
    word_target     INTEGER DEFAULT 700,
    filmability_score TEXT DEFAULT '低',
    status          TEXT DEFAULT 'planned',
    generation_attempts INTEGER DEFAULT 0,
    UNIQUE(project_id, episode_no)
);

-- 集剧本正文表
CREATE TABLE episode_scripts (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,
    content         TEXT NOT NULL,
    word_count      INTEGER,
    version         INTEGER DEFAULT 1,
    compliance_risk TEXT DEFAULT 'low',
    is_approved     INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 集摘要表（用于上下文压缩）
CREATE TABLE episode_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,
    summary         TEXT NOT NULL,
    key_events      TEXT,
    UNIQUE(project_id, episode_no)
);

-- 场景目录表
CREATE TABLE scenes (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,
    scene_no        INTEGER NOT NULL,
    location        TEXT,
    time_of_day     TEXT CHECK(time_of_day IN ('白天','夜晚','傍晚','清晨')),
    environment     TEXT CHECK(environment IN ('内景','外景')),
    characters_present TEXT,
    scene_purpose   TEXT,
    estimated_cost  TEXT CHECK(estimated_cost IN ('低','中','高'))
);

-- 道具流转表
CREATE TABLE props (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    name            TEXT NOT NULL,
    description     TEXT,
    current_holder  TEXT,
    current_state   TEXT,
    last_episode    INTEGER,
    importance      TEXT DEFAULT 'normal' CHECK(importance IN ('normal','key'))
);

-- 角色状态变化表
CREATE TABLE character_states (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    character_id    TEXT NOT NULL REFERENCES characters(id),
    episode_no      INTEGER NOT NULL,
    emotion         TEXT,
    physical_state  TEXT,
    location        TEXT,
    key_event       TEXT,
    recorded_at     TEXT DEFAULT (datetime('now'))
);

-- 合规检查记录表
CREATE TABLE compliance_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    episode_no      INTEGER NOT NULL,
    risk_level      TEXT CHECK(risk_level IN ('low','medium','high')),
    hard_violations TEXT,
    soft_warnings   TEXT,
    pass_probability REAL,
    auto_fixed      INTEGER DEFAULT 0,
    checked_at      TEXT DEFAULT (datetime('now'))
);

-- 生成日志表
CREATE TABLE generation_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    episode_no      INTEGER,
    step            INTEGER,
    step_name       TEXT,
    model_used      TEXT,
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    duration_ms     INTEGER,
    status          TEXT,
    error_msg       TEXT,
    logged_at       TEXT DEFAULT (datetime('now'))
);
```

---

## 十三、Agent Prompt 模板

### 13.1 总策划 Agent System Prompt

```
你是专业的国内竖屏短剧总策划，精通番茄短剧、快手短剧、抖音短剧的市场规律和创作标准。

## 你的工作原则

1. 结构优先：所有故事必须严格遵循六幕式结构（起-困-反-升-爽-合）
2. 爽点密度：每10集必须设置至少1个重大情绪高点或付费钩子
3. 价值观正向：故事结局必须体现正向价值观，反派必须得到应有惩处
4. 可拍性思维：场景设计优先选择室内、固定场景，降低制作成本

## 国内短剧禁区（绝对不写）

- 美化犯罪行为、为违法行为开脱
- 宣扬恋爱脑、拜金主义、不劳而获
- 替身文学、强制爱情、无底线复仇
- 涉及政治敏感、历史虚无、民族问题

## 输出格式要求

严格按照指定 JSON 格式输出，不要添加任何额外文字。
字段不允许为空，特别是 ending_hook 和 paid_hooks。

## 人物设定要求

- 每个主要人物必须有鲜明的 speech_style（台词特征）
- 主角需有明确的 fatal_flaw（性格弱点），否则成长弧无法成立
- 反派需有合理动机，不能只是"坏人"
```

### 13.2 剧本写手 Agent System Prompt

```
你是专业的国内竖屏短剧编剧，擅长写节奏紧凑、情绪密集的短剧剧本。

## 国内短剧剧本格式标准

场景头格式：
【内景·地点·时间】或【外景·地点·时间】
时间选项：白天/夜晚/傍晚/清晨

动作描写规则：
- 第三人称，客观描述，简洁精炼
- 绝对禁止心理独白（他想到了…/她明白了…/内心深处…）
- 所有内心活动必须转化为外部动作、表情、道具交互

对白格式：
角色名（情绪/动作备注，简短）
台词（口语化，短句为主，有力量感）

换场：——（单独一行）

## 写作铁律

1. 字数严格控制在 550-800 字之间
2. 每集结尾最后必须是悬念或反转（对应集纲的 ending_hook）
3. 角色台词必须符合其 speech_style 特征
4. 禁止拖沓，每句台词、每个动作都要推进剧情
5. 开头必须有钩子（对应集纲的 opening_hook）

## 当前集的集纲约束

请严格依据输入的集纲卡片写作，不要添加集纲中没有的人物或情节。
```

### 13.3 分集规划 Agent System Prompt

```
你是专业的国内短剧分集规划师，负责将六幕大纲拆解为逐集的集纲卡片。

## 节奏密度要求

- 每集严格遵循"冲突→升级→反转→留钩"四段式结构
- ending_hook 字段不允许为空，必须明确说明悬念或反转内容
- 每5集左右安排一次情绪峰值（爽/虐/甜/笑/悬）的变化
- 每10集必须有一个"付费钩子"（重大身份/关系/信息反转）

## 场景设计约束

- 单集场景数：建议不超过3个
- 场景 estimated_cost 评估标准：
  - 低：3景以内、5人以内、室内为主、无特效
  - 中：有1处外景，或人数6-10人
  - 高：大外景/群演/特效/动作戏

## 输出要求

严格按照 JSON 格式输出，episode_no 从1开始连续编号，
ending_hook 必须具体描述（不能只写"留有悬念"这种空话）。
```

---

## 十四、MVP 开发计划

### Phase 1：核心功能（目标：6-8周）

**Week 1-2：项目基础**
- [ ] Tauri + React + Python FastAPI 框架搭建
- [ ] SQLite 数据库初始化，所有表结构创建
- [ ] 新建项目流程（题材选择 → 基础配置）
- [ ] 题材热度数据库（手动维护 JSON，20个题材）

**Week 3-4：生成核心**

- [ ] 总策划 Agent（Prompt 调优 + JSON 输出验证）
- [ ] 分集规划 Agent（Prompt 调优 + 批量生成）
- [ ] 剧本写手 Agent（单集生成 + 格式校验）
- [ ] SQLite 状态读写（道具/角色状态同步）

**Week 5-6：合规与输出**
- [ ] 合规硬词扫描（本地正则）
- [ ] 合规 LLM 语义审查
- [ ] python-docx 文档生成（完整剧本 + 投稿包）
- [ ] 集数看板 UI（React）

**Week 7-8：完善与测试**
- [ ] 节奏校验（字数/结尾检测）
- [ ] 可拍性评分面板
- [ ] 道具流转追踪列表
- [ ] 端到端测试（生成一部完整80集剧本）

### Phase 2：商业功能（目标：Phase 1 后 4 周）

- [ ] 题材热度爬虫（自动更新）
- [ ] 多项目管理（项目列表/切换/删除）
- [ ] 并行生成优化（同时写手 × 5集）
- [ ] 用户设置（API Key管理/模型选择/费用预算）
- [ ] 导出格式优化（Word 文档精排版）

### Phase 3：高级功能（待定）

- [ ] 节奏模板市场（用户分享自定义模板）
- [ ] 爆款分析（接入平台分账榜数据）
- [ ] 语音朗读预览（验证台词流畅度）
- [ ] 协作模式（多人同时审稿）
