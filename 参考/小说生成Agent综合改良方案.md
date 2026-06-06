# 小说生成 Agent 综合改良方案

> 本方案基于对 7 个开源 AI 写作项目的逆向分析，结合小说生成 Agent 的当前架构，提炼出可落地的改进方向。
> 每项改进标注了来源项目、优先级和预估工作量。

---

## 目录

- [第一部分：质量门禁体系（确定性检测层）](#第一部分质量门禁体系确定性检测层)
- [第二部分：剧情债务管理系统](#第二部分剧情债务管理系统)
- [第三部分：上下文工程优化](#第三部分上下文工程优化)
- [第四部分：去 AI 味与文风控制](#第四部分去-ai-味与文风控制)
- [第五部分：容错与稳定性](#第五部分容错与稳定性)
- [第六部分：状态管理增强](#第六部分状态管理增强)
- [第七部分：数据库 Schema 扩展](#第七部分数据库-schema-扩展)
- [第八部分：实施路线图](#第八部分实施路线图)

---

## 第一部分：质量门禁体系（确定性检测层）

### 核心问题

当前质量检查链路是 `AuditorAgent（LLM）→ audit_schema（JSON 校验）→ 敏感词扫描`。LLM 说"风险低"就直接通过，没有确定性验证。LLM 可以被"骗"，regex 不会。

### 1.1 防灌水门禁（Padding Guard）

**来源**：novel-pipeline-write-engine 的 `padding_guard.py` + inkos 的段落排版漂移检测

新增 `novel_agent/quality/padding_guard.py`，实现 6 种检测模式，加权打分（0-100）：

| 模式 | 检测逻辑 | 权重 | 上限 |
|------|---------|------|------|
| **重复解释** | 相邻 3 句的 2-4 字词集合交集 > 3 词 | 5 分/次 | 25 分 |
| **空洞内心戏** | 含心理动词的句子前后均无物理动作动词 | 3 分/次 | 20 分 |
| **对话回音** | 连续对话对的关键词重合度 > 5 | 4 分/次 | 15 分 |
| **低增量段落** | 段落不含动作/对话/感知/转折/变化标记，超 5 段后每段 +2 | 2 分/段 | 25 分 |
| **尾部总结** | 最后 400 字含"总之/总而言之/他知道…了"等总结信号 | 15 分 | 15 分 |
| **段落过长**（新增） | 单段超过 150 字（网文排版规范） | 2 分/段 | 10 分 |

**判定**：0-20 通过 → 21-40 警告 → 41-60 需审查 → 61+ 拦截

**关键正则**：
```python
# 重复解释检测用的分词器（滑动窗口，不依赖 jieba）
def extract_ngrams(text: str, n_range=(2, 4)) -> set:
    chars = re.findall(r'[一-鿿]', text)
    result = set()
    for n in range(n_range[0], n_range[1] + 1):
        for i in range(len(chars) - n + 1):
            result.add(''.join(chars[i:i+n]))
    return result

# 空洞内心戏
INNER_MONOLOGUE = re.compile(r'(他|她|我)(知道|明白|意识到|觉得|感觉|想起|想到|感到|认为)')
ACTION_VERBS = re.compile(r'(走|跑|拿|放|看|站|坐|蹲|劈|搬|推|拉|拔|握|抱|挡|闪|跃|冲|踢|打|击)')

# 尾部总结
TAIL_SUMMARY = re.compile(r'(总之|总而言之|总的来说|从此以后|他知道.*了|她明白.*了|他知道.*了|她终于.*了)')
```

### 1.2 反 AI 腔门禁（Anti-AI Style Gate）

**来源**：novel-pipeline-write-engine 的 10 条 regex + inkos 的 AI tell detection + 天命系统的 12 子模块 humanize 规则

新增 `novel_agent/quality/anti_ai_style.py`，检测 15 种中文 AI 写作特征（比之前方案扩展到 15 条）：

| 序号 | 模式 | 正则 | 来源 |
|------|------|------|------|
| 1 | 不是A而是B | `不是.{1,10}而是.{1,10}` | pipeline |
| 2 | 那一刻明白 | `那一刻.{0,5}(终于\|猛然\|突然)?明白` | pipeline |
| 3 | 从未想过 | `(她\|他\|我)从未想过` | pipeline |
| 4 | 他意识到 | `(他\|她\|我)意识到` | pipeline |
| 5 | 这意味着 | `这意味着` | pipeline |
| 6 | 像一座/一尊 | `像一(座\|尊\|个).{1,8}(一样\|般\|似的)` | pipeline |
| 7 | 沉默了几秒 | `沉默了.{1,3}秒` | pipeline |
| 8 | 是她的救赎 | `是(她\|他\|我)的救赎` | pipeline |
| 9 | 硬科学引用 | `(公式\|方程\|热力学\|量子\|熵\|牛顿)` | pipeline |
| 10 | 学术论文腔 | `通过.{2,15}实现了\|基于.{2,15}进行了` | pipeline |
| 11 | 翻译腔 | `进行了一次.{1,6}\|被.{1,10}所震惊\|在.*方面` | 天命 |
| 12 | 过度修饰 | `(美丽动人\|犹如.*般\|宛如.*一样).{0,20}(美丽动人\|犹如.*般\|宛如.*一样)` | 天命 |
| 13 | 机械过渡 | `(随着.*的流逝\|不可否认的是\|值得一提的是)` | inkos |
| 14 | 成串四字成语 | `[一-鿿]{4}，[一-鿿]{4}，[一-鿿]{4}，[一-鿿]{4}` | 天命 |
| 15 | 总结腔开头 | `^(总之\|总而言之\|综上所述\|不难看出)` | inkos |

**判定**：0 处 perfect → 1-2 处 pass → 3+ 处 fail（拦截）

**配置化**：将 15 条模式放到 `assets/anti_ai_patterns.yaml`，支持增删改，不硬编码。

```yaml
patterns:
  - id: "not_a_but_b"
    name: "不是A而是B"
    regex: "不是.{1,10}而是.{1,10}"
    severity: "medium"
    source: "pipeline"
  - id: "that_moment_realize"
    name: "那一刻明白"
    regex: "那一刻.{0,5}(终于|猛然|突然)?明白"
    severity: "high"
    source: "pipeline"
  # ... 共 15 条
```

### 1.3 场景增量验证（Scene Delta Guard）

**来源**：novel-pipeline-write-engine 的 `scene_delta_guard.py`

新增 `novel_agent/quality/scene_delta.py`，按场景分段后检查 7 个增量维度：

| 维度 | 关键词 | 说明 |
|------|--------|------|
| plot | 发现\|揭露\|得知\|出现\|发生\|遭遇\|获得\|失去 | 新事件/发现 |
| character_state | 决定\|改变\|选择\|放弃\|接受\|觉醒\|突破 | 角色决策/变化 |
| relationship | 信任\|怀疑\|背叛\|结盟\|爱上\|仇恨\|和解\|反目 | 关系变化 |
| conflict | 战斗\|对峙\|威胁\|追杀\|逃离\|对抗\|击败\|受伤 | 冲突升级 |
| worldbuilding | 规则\|法则\|禁制\|秘境\|势力\|宝物\|功法 | 世界观扩展 |
| reader_promise | 承诺\|发誓\|约定\|复仇\|报恩\|欠下 | 爽点铺垫 |
| next_hook | 然而\|但是\|忽然\|突然\|没想到\|谁知\|岂料 | 悬念设置 |

**场景分割正则**：
```python
SCENE_BOUNDARY = re.compile(
    r'(?:'
    r'第[一二三四五六七八九十百千]+[天日夜]|次日|黎明|黄昏|入夜|天亮|天黑'  # 时间
    r'|来到|进入|走出|回到|飞往|离开|到达|传送'  # 地点
    r'|\*\*\*|---'  # 显式分隔
    r')'
)
```

**判定**：单场景至少激活 2 维度 → 有效；整章有效场景 >= 3（短章 >= 1）

### 1.4 连续性 Hooks 提取器（Continuity Hooks Extractor）

**来源**：novel-pipeline-write-engine 的 `continuity_evidence_guard.py` 的正则 + AI_NovelGenerator 的前文摘要机制

新增 `novel_agent/quality/hooks_extractor.py`，从上章结尾提取结构化 hooks：

```python
HOOKS = {
    "unfinished_actions": re.compile(r'(正要|准备|打算|决定|即将|就要|刚想|刚准备|开始|试图).{0,15}(?:[。！？\n]|$)'),
    "perceptions": re.compile(r'(发现|察觉|注意|看出|感觉到|意识到|听到|闻到|看到).{0,20}(?:了|到|出)'),
    "injuries": re.compile(r'(受伤|流血|伤口|疼痛|晕|昏迷|中毒|发热|发冷|虚弱|透支|内伤|经脉)'),
    "suspense_endings": re.compile(r'(?:\.{3,}|……|[？?])\s*$'),
    "location_changes": re.compile(r'(来到|进入|走出|到达|飞往|传送至|回到).{0,15}(?:[。！？\n]|$)'),
}
```

**集成方式**：在 ContinuityCheckerAgent 之前调用，将提取的 hooks 作为结构化上下文注入 prompt：
```
上章结尾检测到以下待承接要素：
- 未完成动作：[正要拔剑, 准备离开]
- 感知发现：[发现洞口有异光]
- 伤势状态：[左臂受伤]
请检查本章开头是否合理承接了以上要素，逐项给出判断。
```

### 1.5 硬声明来源追溯（Canon Evidence Guard）

**来源**：novel-pipeline-write-engine 的 `canon_evidence_guard.py` + NovelForge 的实体类型校验

新增 `novel_agent/quality/canon_evidence.py`，提取正文中 12 类"硬声明"并绑定来源：

```
硬声明类型：character_identity, character_realm, relationship, faction,
            cultivation_method, world_rule, timeline, major_item,
            plot_payoff, reader_promise_payoff, injury_state, location_state
```

**来源绑定优先级链**：
1. task_card.allowed_new_canon / must_include
2. 前章结尾 400 字关键词匹配
3. 前章 chapter_brief.json
4. 已知世界观设定（worldbuilding 表）
5. 软细节分类（伤势/地点状态给 soft_pass）
6. 以上均无 → unsupported_hallucination

**判定**：evidence_coverage >= 0.95 且 hard_claims_without_source == 0

### 1.6 门禁集成到流水线

在 `orchestrator.py` 的 Step 10（Auditor）之后、Step 11（敏感词扫描）之前插入：

```python
# Step 10.5: 确定性质量门禁层
from novel_agent.quality.padding_guard import check_padding
from novel_agent.quality.anti_ai_style import check_anti_ai_style
from novel_agent.quality.scene_delta import check_scene_delta
from novel_agent.quality.canon_evidence import check_canon_evidence

gate_results = {}

# 1.5.1 防灌水
padding_result = check_padding(final_text)
gate_results["padding"] = padding_result
if padding_result["level"] == "fail":
    audit.setdefault("issues", []).append({
        "type": "padding_excessive", "severity": "high",
        "detail": f"水文评分 {padding_result['score']}/100",
        "issues": padding_result["details"]
    })

# 1.5.2 反 AI 腔
ai_style_result = check_anti_ai_style(final_text)
gate_results["anti_ai_style"] = ai_style_result
if ai_style_result["status"] == "fail":
    audit.setdefault("issues", []).append({
        "type": "ai_style_detected", "severity": "medium",
        "detail": f"检测到 {ai_style_result['count']} 处 AI 腔特征",
        "patterns": ai_style_result["matched_patterns"]
    })

# 1.5.3 场景增量
scene_delta_result = check_scene_delta(final_text)
gate_results["scene_delta"] = scene_delta_result
if not scene_delta_result["passed"]:
    audit.setdefault("issues", []).append({
        "type": "low_scene_delta", "severity": "medium",
        "detail": f"有效场景 {scene_delta_result['effective_count']}，低增量场景过多"
    })

# 1.5.4 硬声明追溯（需要 task_card 和已知设定）
canon_result = check_canon_evidence(
    final_text,
    task_card=plan,
    known_facts=continuity_state,
    prev_chapter_tail=prev_chapter_tail,
)
gate_results["canon_evidence"] = canon_result
if canon_result["coverage"] < 0.95:
    audit.setdefault("issues", []).append({
        "type": "unsupported_claims", "severity": "high",
        "detail": f"硬声明覆盖率 {canon_result['coverage']:.0%}，{canon_result['unsupported_count']} 条无来源"
    })

# 保存门禁报告
_write_json(reports_dir / "gate_results.json", gate_results)

# 如果门禁发现高严重度问题，升级审计风险等级
high_gate_issues = [i for i in audit.get("issues", []) if i.get("severity") == "high"]
if high_gate_issues and audit.get("risk_level") != "高":
    audit["risk_level"] = "高"
    logger.warning("Gate checks elevated risk_level to 高 due to %d high-severity issues", len(high_gate_issues))
```

---

## 第二部分：剧情债务管理系统

### 核心问题

当前系统只追踪伏笔（foreshadows）和钩子（hooks），但缺少三个关键维度：读者承诺的回收窗口管理、秘密信息差控制、截止期约束。

### 2.1 Reader Promises 表（读者承诺）

**来源**：novel-pipeline-write-engine 的 `reader_promises` 表

在 `sqlite_store.py` 新增表：

```sql
CREATE TABLE IF NOT EXISTS reader_promises (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    introduced_chapter TEXT,
    expected_payoff_range TEXT,     -- JSON: [5, 12]
    actual_payoff_chapter TEXT,
    reader_emotion TEXT,            -- 期待/悬念/爽感/愤怒/同情/恐惧
    status TEXT DEFAULT 'open',     -- open / delayed / paid / abandoned
    priority INTEGER DEFAULT 3,     -- 1-5，5 最高
    payload TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

**集成点**：
- StateExtractorAgent 输出 schema 增加 `reader_promises` 字段
- ChapterPlannerAgent prompt 增加回收窗口检查逻辑
- 前端 ChapterDetail.vue 增加"读者承诺"面板

### 2.2 Secrets 表（秘密控制）

**来源**：天命系统的 SecretReveal 机制

```sql
CREATE TABLE IF NOT EXISTS secrets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    holder_character TEXT,           -- 知道秘密的角色
    hidden_from TEXT,               -- 不应知道秘密的角色（JSON 数组）
    introduced_chapter TEXT,
    reveal_after_chapter TEXT,       -- 最早可揭露的章节号
    max_keep_chapters INTEGER,       -- 最多保密章数
    actual_reveal_chapter TEXT,
    status TEXT DEFAULT 'hidden',    -- hidden / partially_revealed / fully_revealed / leaked
    leak_severity TEXT,              -- low / medium / high / critical（泄露后果）
    payload TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Prompt 集成**：在 writer 的 context_pack 中注入当前活跃的秘密约束：
```
## 信息差约束（严禁违反）
- 秘密「林家灭门真凶是宗主」：持有者=林轩，隐藏对象=全宗门，最早揭露章节=第15章
  → 本章中任何角色的台词和心理活动都不得透露此秘密
```

### 2.3 Pledges 表（誓言/截止期约束）

**来源**：天命系统的 Deadline/Pledge 机制

```sql
CREATE TABLE IF NOT EXISTS pledges (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    character_id TEXT,               -- 立誓角色
    introduced_chapter TEXT,
    deadline_chapter TEXT,           -- 截止章节号
    pledge_type TEXT,                -- revenge / promise / oath / debt / quest
    status TEXT DEFAULT 'active',    -- active / fulfilled / broken / delayed
    fulfilled_chapter TEXT,
    escalation_on_breach TEXT,       -- 违约后果描述
    payload TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**自动报警**：当 `current_chapter >= deadline_chapter` 且 `status == 'active'` 时，自动注入警告到 planner prompt：
```
## 剧情债务警告
- 「三天后报仇」（第5章立誓）已到截止期限，本章必须推进或给出合理延期理由
```

### 2.4 StateExtractorAgent 改造

在 `state_extractor.py` 的输出 schema 中增加三个新字段：

```python
# 原有输出
{
    "events": [...],
    "characters": {...},
    "objects": [...],
    "threads": [...],
    "foreshadows": [...],
    "hooks": [...],
    # 新增
    "reader_promises": [...],
    "secrets": [...],
    "pledges": [...]
}
```

---

## 第三部分：上下文工程优化

### 核心问题

当前 ContextBuilder 的上下文组装策略较粗，缺少防重复机制和前瞻规划。

### 3.1 前文防重复的"章节距离过滤"

**来源**：AI_NovelGenerator 的时间距离打压规则 + 302_novel_writing 的 1300 字滑窗

改造 `vector_store.py` 的检索逻辑，在召回后增加距离过滤：

```python
def search_with_distance_filter(
    self, query: str, current_chapter: int, limit: int = 5
) -> List[Dict]:
    results = self.search(query, limit=limit * 3)  # 多召回一些用于过滤
    filtered = []
    for r in results:
        recall_chapter = int(r["metadata"].get("chapter", "0"))
        delta = current_chapter - recall_chapter

        if delta <= 0:
            continue  # 未来章节，跳过
        elif delta <= 3:
            continue  # 最近 3 章，强制丢弃（读者刚看过）
        elif delta <= 5:
            r["rewrite_tag"] = "[REWRITE_40%]"  # 标记需改写
            filtered.append(r)
        else:
            r["rewrite_tag"] = "[OK]"  # 正常采纳
            filtered.append(r)

    return filtered[:limit]
```

**ContextBuilder 集成**：在组装 context_pack 时，对带 `[REWRITE_40%]` 标记的片段，在 prompt 中明确要求 LLM 改写引用而非照搬。

### 3.2 前一片段滑窗注入

**来源**：302_novel_writing 的 `slice(-1300)` 策略

在 ContextBuilder 中，除了向量检索，还应固定注入上一章的最后 1300 字作为"前一片段"：

```python
def _get_previous_clip(self, chapter_id: str, clip_chars: int = 1300) -> str:
    """截取上一章最后 N 个字符作为滑窗上下文"""
    prev_chapters = self.store.get_chapters()
    if not prev_chapters:
        return ""
    # 找到上一章
    current_idx = next(
        (i for i, c in enumerate(prev_chapters) if c["id"] == chapter_id), -1
    )
    if current_idx <= 0:
        return ""
    prev = prev_chapters[current_idx - 1]
    prev_path = Path(prev["final_path"])
    if not prev_path.exists():
        return ""
    text = prev_path.read_text(encoding="utf-8").strip()
    return text[-clip_chars:] if len(text) > clip_chars else text
```

### 3.3 下一章前瞻规划（Teaser）

**来源**：302_novel_writing 的 `generateFragmentedPlot` + AI_NovelGenerator 的"提要过渡"

在每章生成完成后，自动调用 LLM 预测下一章的 3-4 个剧情要点：

```python
def _generate_next_chapter_teaser(self, chapter_text: str, chapter_summary: str) -> Dict:
    """当前章完成后，自动规划下一章要点"""
    prompt = f"""
    基于以下刚完成的章节，为下一章规划 3-4 个剧情要点。
    要求：每个要点 1-2 句话，要能自然承接本章结尾，并埋下悬念。

    本章正文（最后 800 字）：{chapter_text[-800:]}
    本章总结：{chapter_summary}

    输出 JSON：
    {{"teaser_points": ["要点1", "要点2", "要点3"], "hook_direction": "下一章的悬念方向"}}
    """
    return self.llm.generate("chapter_planner", prompt)
```

**集成点**：在 orchestrator 的 Step 8（Chapter Summary）之后执行，结果写入 `chapter_brief.json` 的 `next_chapter_teaser` 字段。ChapterPlannerAgent 在规划下一章时自动读取。

### 3.4 导入长文的自适应锚点压缩

**来源**：inkos 的 `buildImportFoundationSource`

当用户导入已有小说进行续写时，数十万字会超出上下文窗口。新增压缩器：

```python
def compress_imported_novel(
    chapters: List[Dict],
    edge_count: int = 4,    # 保留首尾各 N 章
    anchor_count: int = 8,  # 中段均匀抽样 N 章
) -> str:
    """
    将导入小说压缩为"导入资料包"：
    1. 保留开篇 edge_count 章全文
    2. 保留续写点前 edge_count 章全文
    3. 中段均匀抽样 anchor_count 章，只保留标题+首尾摘要
    4. 保留完整精简目录
    """
    total = len(chapters)
    if total <= edge_count * 2:
        return "\n\n".join(c["content"] for c in chapters)

    result_parts = []

    # 开篇保留
    for c in chapters[:edge_count]:
        result_parts.append(f"【{c['name']}】\n{c['content']}")

    # 中段锚点
    mid_chapters = chapters[edge_count:-edge_count]
    step = max(1, len(mid_chapters) // anchor_count)
    for i in range(0, len(mid_chapters), step):
        c = mid_chapters[i]
        head = c["content"][:200]
        tail = c["content"][-200:]
        result_parts.append(f"【{c['name']}】（摘要）\n开头：{head}...\n结尾：...{tail}")

    # 续写点前保留
    for c in chapters[-edge_count:]:
        result_parts.append(f"【{c['name']}】\n{c['content']}")

    # 精简目录
    toc = "\n".join(f"  {i+1}. {c['name']}" for i, c in enumerate(chapters))
    result_parts.insert(0, f"## 全书目录\n{toc}\n")

    return "\n\n---\n\n".join(result_parts)
```

---

## 第四部分：去 AI 味与文风控制

### 4.1 风格指纹提取

**来源**：inkos 的 StyleProfile + 天命系统的 N-gram 频率评分

新增 `novel_agent/quality/style_fingerprint.py`，从参考文本中提取量化风格指标：

```python
def extract_style_fingerprint(text: str) -> Dict:
    """分析文本的风格统计特征"""
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    return {
        "avg_sentence_length": sum(len(s) for s in sentences) / max(len(sentences), 1),
        "short_sentence_ratio": sum(1 for s in sentences if len(s) <= 15) / max(len(sentences), 1),
        "dialogue_ratio": len(re.findall(r'"[^"]{1,}"', text)) / max(len(sentences), 1),
        "exclamation_ratio": text.count("！") / max(len(text), 1),
        "ellipsis_ratio": text.count("……") / max(len(text), 1),
        "paragraph_avg_length": _avg_paragraph_length(text),
        "action_verb_density": len(ACTION_VERBS.findall(text)) / max(len(text), 1),
    }
```

**Writer prompt 集成**：将风格指纹转化为定量约束：
```
## 风格约束（基于参考文本分析）
- 平均句长：15-25 字（当前参考：22 字）
- 短句比例：>= 30%
- 对话比例：20-40%
- 感叹号密度：<= 0.5%
- 段落平均长度：<= 150 字
```

### 4.2 排版规范检测

**来源**：inkos 的 `detectParagraphLengthDrift`

新增 `novel_agent/quality/format_checker.py`：

```python
def check_format(text: str) -> Dict:
    """检查网文排版规范"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    issues = []

    for i, para in enumerate(paragraphs):
        # 单段过长（网文忌讳大段排版）
        if len(para) > 150:
            issues.append({"type": "paragraph_too_long", "para_index": i, "length": len(para)})

        # 段首缩进检查
        if para and para[0] != "　" and para[0] != " ":
            # 非对话段应该有缩进
            if not para.startswith('"') and not para.startswith('"'):
                issues.append({"type": "missing_indent", "para_index": i})

    return {
        "total_paragraphs": len(paragraphs),
        "issues": issues,
        "passed": len(issues) <= 3,
    }
```

### 4.3 Thinking 标签过滤

**来源**：天命系统的 Thinking 过程提取中间件

在 `base.py` 的 OpenAILLM 中增加后处理：

```python
def _strip_thinking(self, text: str) -> str:
    """剥离推理模型的思维链标签，只保留纯净正文"""
    # DeepSeek-R1 / OpenAI o1 等推理模型的思维链标签
    patterns = [
        r'<think>.*?</think>',
        r'<thought>.*?</thought>',
        r'<reasoning>.*?</reasoning>',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    return text.strip()
```

---

## 第五部分：容错与稳定性

### 5.1 七层 AI 中间件管道

**来源**：天命系统的 7 层中间件 + inkos 的 Dispatcher

改造 `pipeline.py` 的 LLM 客户端，增加中间件链：

```python
class LLMWithMiddleware:
    def __init__(self, base_client, config):
        self.client = base_client
        self.config = config
        self.middleware = [
            ErrorNormalizer(),       # 1. 统一报错格式
            KeyRotator(config),      # 2. API Key 轮换
            RetryWithFallback(config),  # 3. 重试 + 模型降级
            ThinkingExtractor(),     # 4. 思维链剥离
            ResponseParser(),        # 5. 结构化抽取
            TokenCounter(),          # 6. Token 统计
            LatencyTracer(),         # 7. 链路追踪
        ]

    def generate(self, role: str, prompt: str) -> str:
        request = {"role": role, "prompt": prompt}

        # 前置中间件
        for mw in self.middleware:
            request = mw.before(request)

        # 调用
        response = self.client.generate(request["role"], request["prompt"])

        # 后置中间件
        for mw in self.middleware:
            response = mw.after(response)

        return response["text"]
```

### 5.2 原子化文件写入

**来源**：AI_NovelGenerator 的 `_write_text_atomic`

当前 `_write_json` 直接覆写，断电可能损坏。改为 temp + rename：

```python
@staticmethod
def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)  # 原子替换
```

### 5.3 迭代预算保护

**来源**：novel-pipeline-write-engine 的 `agent_iteration_budget.md`

新增 `novel_agent/budget.py`：

```python
class BudgetTracker:
    MODES = {
        (0.5, 1.0): "normal",      # 全流程
        (0.3, 0.5): "shrink",      # 跳过 dashboard + vector_index
        (0.15, 0.3): "wrap_up",    # 只做 state_update
        (0.08, 0.15): "freeze",    # 保存 checkpoint 停止
        (0.0, 0.08): "readonly",   # 只输出状态
    }

    def __init__(self, estimated_total: int):
        self.total = estimated_total
        self.used = 0

    def record(self, tokens: int):
        self.used += tokens

    @property
    def ratio(self) -> float:
        return max(0, 1.0 - self.used / self.total)

    @property
    def mode(self) -> str:
        for (lo, hi), mode in self.MODES.items():
            if lo < self.ratio <= hi:
                return mode
        return "readonly"

    def should_skip(self, step: str) -> bool:
        skip_map = {
            "shrink": ["dashboard", "vector_index"],
            "wrap_up": ["dashboard", "vector_index", "style_editor", "chapter_summary"],
            "freeze": ["all"],
            "readonly": ["all"],
        }
        steps = skip_map.get(self.mode, [])
        return step in steps or "all" in steps
```

### 5.4 WAL 预写日志

**来源**：天命系统的 WAL 机制

当前 checkpoint 是 3 个阶段粒度。改为步骤级 WAL：

```python
class ChapterWAL:
    def __init__(self, chapter_dir: Path):
        self.wal_path = chapter_dir / "wal.json"
        self.entries = self._load()

    def _load(self) -> List[Dict]:
        if self.wal_path.exists():
            return json.loads(self.wal_path.read_text(encoding="utf-8"))
        return []

    def log(self, step: str, status: str, data: Any = None):
        entry = {
            "step": step,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "data_summary": str(data)[:200] if data else None,
        }
        self.entries.append(entry)
        self.wal_path.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def last_completed_step(self) -> Optional[str]:
        completed = [e for e in self.entries if e["status"] == "done"]
        return completed[-1]["step"] if completed else None
```

---

## 第六部分：状态管理增强

### 6.1 版本不可变快照

**来源**：novel-pipeline-write-engine 的 `chapter_versions` 表

```sql
CREATE TABLE IF NOT EXISTS chapter_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id TEXT NOT NULL,
    version_no INTEGER NOT NULL,
    title TEXT,
    content TEXT,
    word_count INTEGER,
    status TEXT DEFAULT 'draft',
    change_reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**保留策略**：最近 5 个版本保留全文，更早版本只保留摘要 + diff 摘要，避免存储膨胀。

### 6.2 Reducer 模式状态机

**来源**：inkos 的 `state-reducer.ts`

当前 `StateManager.apply_update()` 是全量合并。改为增量 delta 模式：

```python
class StateReducer:
    """将章节事件合并至全局状态，类似 Redux reducer"""

    def reduce(self, current_state: Dict, delta: Dict) -> Dict:
        new_state = {**current_state}

        # 字符状态：合并更新
        for char_id, changes in delta.get("characters", {}).items():
            if char_id in new_state.get("characters", {}):
                new_state["characters"][char_id] = {
                    **new_state["characters"][char_id],
                    **changes,
                }
            else:
                new_state.setdefault("characters", {})[char_id] = changes

        # 线程状态：状态机跃迁
        for thread in delta.get("threads", []):
            existing = next(
                (t for t in new_state.get("threads", []) if t["id"] == thread["id"]),
                None,
            )
            if existing:
                # 只允许合法跃迁：open → progressing → closed
                valid_transitions = {
                    "open": ["progressing", "closed"],
                    "progressing": ["closed"],
                    "closed": [],
                }
                if thread.get("status") in valid_transitions.get(existing["status"], []):
                    existing.update(thread)
            else:
                new_state.setdefault("threads", []).append(thread)

        # 伏笔/钩子：标记状态变化
        for foreshadow in delta.get("foreshadows", []):
            existing = next(
                (f for f in new_state.get("foreshadows", []) if f["id"] == foreshadow["id"]),
                None,
            )
            if existing:
                existing.update(foreshadow)
            else:
                new_state.setdefault("foreshadows", []).append(foreshadow)

        return new_state
```

### 6.3 里程碑压缩器

**来源**：天命系统的 Milestone Compressor

当事件数超过阈值时，自动将久远事件压缩为里程碑：

```python
def compress_to_milestones(events: List[Dict], keep_recent: int = 30) -> List[Dict]:
    """
    保留最近 keep_recent 条事件全文，
    更早的事件按卷/弧线压缩为里程碑摘要。
    """
    if len(events) <= keep_recent:
        return events

    recent = events[-keep_recent:]
    old = events[:-keep_recent]

    # 按 chapter_id 分组
    from itertools import groupby
    milestones = []
    for chapter_id, group in groupby(old, key=lambda e: e.get("chapter_id", "")):
        group_list = list(group)
        milestones.append({
            "id": f"milestone_{chapter_id}",
            "type": "milestone",
            "chapter_id": chapter_id,
            "summary": f"第{chapter_id}章：{len(group_list)}个事件（已压缩）",
            "key_events": [e["summary"] for e in group_list[:3]],  # 只保留前 3 个关键事件
        })

    return milestones + recent
```

---

## 第七部分：数据库 Schema 扩展

汇总所有新增表，统一在 `sqlite_store.py` 的 `_init_schema()` 中添加：

```sql
-- 读者承诺
CREATE TABLE IF NOT EXISTS reader_promises (...);

-- 秘密控制
CREATE TABLE IF NOT EXISTS secrets (...);

-- 誓言/截止期
CREATE TABLE IF NOT EXISTS pledges (...);

-- 版本快照
CREATE TABLE IF NOT EXISTS chapter_versions (...);
```

**FTS5 扩展**（可选，参考 novel-pipeline-write-engine）：

```sql
-- 如果 SQLite 支持 FTS5，增加全文索引
CREATE VIRTUAL TABLE IF NOT EXISTS novel_character_fts USING fts5(
    name, alias, identity, personality, tags
);

CREATE VIRTUAL TABLE IF NOT EXISTS novel_world_fts USING fts5(
    title, content, tags
);
```

---

## 第八部分：实施路线图

### Phase 1（3-4 天）：确定性质量门禁

| 任务 | 文件 | 工作量 |
|------|------|--------|
| padding_guard | `novel_agent/quality/padding_guard.py` | 1 天 |
| anti_ai_style（含配置化） | `novel_agent/quality/anti_ai_style.py` + `assets/anti_ai_patterns.yaml` | 0.5 天 |
| hooks_extractor | `novel_agent/quality/hooks_extractor.py` | 0.5 天 |
| scene_delta | `novel_agent/quality/scene_delta.py` | 0.5 天 |
| canon_evidence | `novel_agent/quality/canon_evidence.py` | 1 天 |
| 流水线集成 + 测试 | `orchestrator.py` + `tests/` | 0.5 天 |

### Phase 2（2-3 天）：剧情债务管理

| 任务 | 文件 | 工作量 |
|------|------|--------|
| reader_promises 表 | `sqlite_store.py` | 0.5 天 |
| secrets 表 | `sqlite_store.py` | 0.5 天 |
| pledges 表 | `sqlite_store.py` | 0.5 天 |
| StateExtractorAgent 改造 | `agents/state_extractor.py` + prompt | 0.5 天 |
| ChapterPlannerAgent 集成 | `agents/chapter_planner.py` + prompt | 0.5 天 |
| 前端面板 | `ChapterDetail.vue` | 0.5 天 |

### Phase 3（2 天）：上下文工程优化

| 任务 | 文件 | 工作量 |
|------|------|--------|
| 章节距离过滤 | `state/vector_store.py` | 0.5 天 |
| 前一片段滑窗 | `agents/context_builder.py` | 0.5 天 |
| 下一章前瞻规划 | `orchestrator.py` | 0.5 天 |
| 导入锚点压缩 | `novel_agent/importer.py`（新建） | 0.5 天 |

### Phase 4（2 天）：去 AI 味与文风

| 任务 | 文件 | 工作量 |
|------|------|--------|
| 风格指纹提取 | `novel_agent/quality/style_fingerprint.py` | 0.5 天 |
| 排版规范检测 | `novel_agent/quality/format_checker.py` | 0.5 天 |
| Thinking 标签过滤 | `novel_agent/agents/base.py` | 0.5 天 |
| Writer prompt 集成 | `prompts/writer.md` | 0.5 天 |

### Phase 5（2-3 天）：容错与稳定性

| 任务 | 文件 | 工作量 |
|------|------|--------|
| 七层中间件管道 | `novel_agent/llm_middleware.py`（新建） | 1.5 天 |
| 原子化文件写入 | `orchestrator.py` | 0.5 天 |
| 迭代预算保护 | `novel_agent/budget.py`（新建） | 0.5 天 |
| WAL 预写日志 | `orchestrator.py` | 0.5 天 |

### Phase 6（1-2 天）：状态管理增强

| 任务 | 文件 | 工作量 |
|------|------|--------|
| chapter_versions 表 | `sqlite_store.py` | 0.5 天 |
| StateReducer | `novel_agent/state/reducer.py`（新建） | 0.5 天 |
| 里程碑压缩器 | `novel_agent/state/compressor.py`（新建） | 0.5 天 |

---

## 附录：各改进项来源追溯

| 改进项 | novel-pipeline | 302_writing | AI-Writer | AI_NovelGen | NovelForge | inkos | 天命 |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| padding_guard | ★ | | | | | ◐ | |
| anti_ai_style | ★ | | | | | ★ | ★ |
| scene_delta | ★ | | | | | | |
| hooks_extractor | ★ | | | ◐ | | | |
| canon_evidence | ★ | | | | ◐ | | |
| reader_promises | ★ | | | | | | |
| secrets | | | | | | | ★ |
| pledges | | | | | | | ★ |
| 章节距离过滤 | | | | ★ | | | |
| 前一片段滑窗 | | ★ | | | | | |
| 下一章前瞻 | | ★ | | ★ | | | |
| 导入锚点压缩 | | | | | | ★ | |
| 风格指纹 | | | | | | ★ | |
| 排版检测 | | | | | | ★ | |
| Thinking 过滤 | | | | | | | ★ |
| 七层中间件 | | | | | | | ★ |
| 原子化写入 | | | | ★ | | | |
| 预算保护 | ★ | | | | | | |
| WAL 日志 | | | | | | | ★ |
| 版本快照 | ★ | | | | | | |
| Reducer 状态机 | | | | | | ★ | |
| 里程碑压缩 | | | | | | | ★ |
| 辩论机制 | | | | | ★ | | |
| 实体类型校验 | | | | | ★ | | |

> ★ = 主要来源，◐ = 部分参考
