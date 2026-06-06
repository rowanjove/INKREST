# 小说生成 Agent — 深度改进文档

> 基于 CAN (Novel Pipeline - Write Engine) 深度逆向分析报告及 6 大 AI 写作项目横向对比，针对当前「小说生成 Agent」系统提出的系统性改进方案。

---

## 一、现状差距分析

### 1.1 核心能力对比

| 维度 | 当前项目 | CAN (逆向参考) | 差距评级 |
|------|----------|---------------|---------|
| 质量门禁 | 软性审计（Auditor 输出 risk_level） | 8 步物理硬门禁，任一不过则阻断入库 | ⚠️ 严重 |
| 连续性保证 | 连贯性检查 Agent（LLM 判断） | 正则+关键词的物理证据核验 | ⚠️ 严重 |
| 防水文机制 | 无 | padding_guard + scene_delta_guard 双层 | ⚠️ 严重 |
| 幻觉拦截 | 无 | canon_evidence_guard + hallucination_guard | ⚠️ 严重 |
| 执行审计 | 无 | execution_receipt.json 防伪收据 | ⚠️ 严重 |
| 剧情债务管理 | foreshadows 表（被动记录） | pledges/secrets 主动约束注入 Prompt | ❌ 缺失 |
| 向量检索防重复 | 余弦相似度召回（无时间打压） | 章节距离打压算法 | ❌ 缺失 |
| 模型 Fallback | FallbackLLM（链式尝试） | 7 层中间件管道（含 Thinking 剥离） | 🔶 部分 |
| 状态版本快照 | YAML 快照 | chapter_versions 只增不删版本表 | 🔶 部分 |

### 1.2 当前项目核心痛点

基于逆向报告对照分析，当前系统存在三类根本性问题：

**问题一：质量保证依赖 LLM 自审，无物理兜底**
Auditor Agent 的审计结论本身是 LLM 生成的，当主模型性能不稳定时，审计结论同样不可靠。CAN 系统用正则脚本对正文做静态扫描，与 LLM 无关，不可绕过。

**问题二：上下文承接缺乏可验证的物理证据**
现有 ContinuityCheckerAgent 依赖模型理解，无法核验"本章开头是否真实引用了上章的 Hook 关键词"。CAN 系统对此有精确的字符级匹配算法。

**问题三：向量检索存在复读风险**
当前 vector_store 没有对近期章节做距离惩罚，可能导致模型频繁检索并复述最近 1-3 章内容，造成读者感知重复。

---

## 二、改进方案

### 改进一：构建物理质量门禁层（Priority: P0）

#### 背景

CAN 的核心创新不在 Agent 设计，而在于**把质量标准从 Prompt 指令转移到代码逻辑**。每个门禁都是一段独立的 Python 脚本，任何一项不过都阻断章节入库。

#### 改进目标

在 `novel_agent/` 下新增 `guards/` 子包，实现 5 个静态质量守卫，并集成进现有 orchestrator 的 Step 10（审计）之后。

#### 具体实现

**① 连续性证据守卫 `guards/continuity_evidence_guard.py`**

```python
import re

# 从上章结尾 400 字提取 Hook 关键词
HOOK_PATTERNS = [
    r'(正要|准备|打算|决定|即将|就要|刚想).{0,15}(?:[。！？\n]|$)',
    r'(发现|察觉|注意|看出|感觉到|意识到).{0,20}(?:了|到|出)',
    r'(受伤|流血|伤口|疼痛|昏迷|中毒|发热|虚弱)',
]

STATE_PATTERNS = {
    'injuries': r'(受伤|流血|伤势|昏迷|中毒)',
    'items':    r'(持有|拿着|手中|怀里|背着)',
    'tasks':    r'(必须|一定要|不能放弃|找到|完成)',
    'emotions': r'(愤怒|恐惧|绝望|喜悦|悲伤)',
}

def check(prev_tail: str, curr_head: str) -> dict:
    """
    prev_tail: 上章末尾 400 字
    curr_head: 本章开头 600 字
    Returns: {'pass': bool, 'score': float, 'missing_hooks': list, 'forgotten_states': list}
    """
    hooks = []
    for pat in HOOK_PATTERNS:
        for m in re.finditer(pat, prev_tail):
            # 提取 2-4 字关键词
            kw = re.findall(r'[\u4e00-\u9fff]{2,4}', m.group())
            hooks.extend(kw)
    
    missing = [kw for kw in hooks if kw not in curr_head]
    
    forgotten = []
    for state, pat in STATE_PATTERNS.items():
        if re.search(pat, prev_tail) and not re.search(pat, curr_head):
            forgotten.append(state)
    
    hook_score = 1.0 if not missing else max(0, 1 - len(missing) / max(len(hooks), 1))
    state_score = 1.0 - len(forgotten) / len(STATE_PATTERNS)
    total = hook_score * 0.5 + state_score * 0.3 + 0.2  # conflict_score 默认 1.0
    
    return {
        'pass': len(missing) == 0 and len(forgotten) == 0 and total >= 0.8,
        'score': round(total, 3),
        'missing_hooks': missing,
        'forgotten_states': forgotten,
    }
```

**② 防水文守卫 `guards/padding_guard.py`**

检测四类水文特征，每项超阈值记 1 分，总分 > 2 则阻断：

```python
def check_padding(text: str) -> dict:
    score = 0
    issues = []
    
    # 检测①：连续三段同义（相邻句子词集交集 > 3）
    sentences = re.split(r'[。！？\n]', text)
    for i in range(len(sentences) - 2):
        s1 = set(re.findall(r'[\u4e00-\u9fff]{2,4}', sentences[i]))
        s2 = set(re.findall(r'[\u4e00-\u9fff]{2,4}', sentences[i+1]))
        s3 = set(re.findall(r'[\u4e00-\u9fff]{2,4}', sentences[i+2]))
        if len(s1 & s2) > 3 and len(s2 & s3) > 3:
            score += 1
            issues.append(f'连续同义句: {sentences[i][:20]}...')
            break
    
    # 检测②：空泛心理独白（无前后动作）
    psych_pattern = r'他(知道|明白|意识到|觉得|感觉|想起|想到).{0,30}[。]'
    action_pattern = r'(蹲|站|走|跑|拿|放|劈|搬|跳|挥|刺|射)'
    for m in re.finditer(psych_pattern, text):
        ctx = text[max(0, m.start()-30):m.end()+30]
        if not re.search(action_pattern, ctx):
            score += 1
            issues.append('空泛心理独白')
            break
    
    # 检测③：对话复读
    dialogs = re.findall(r'[""「」].{15,80}[""」]', text)
    for i in range(len(dialogs) - 1):
        d1 = set(re.findall(r'[\u4e00-\u9fff]{2,4}', dialogs[i]))
        d2 = set(re.findall(r'[\u4e00-\u9fff]{2,4}', dialogs[i+1]))
        if len(d1 & d2) > 5:
            score += 1
            issues.append('对话复读')
            break
    
    # 检测④：AI 腔特征词
    ai_phrases = ['不是.*而是', '那一刻.*终于明白', '总而言之', '换句话说',
                  '值得注意的是', '毫无疑问', '不得不说', '不禁让人']
    ai_hits = sum(1 for p in ai_phrases if re.search(p, text))
    if ai_hits > 2:
        score += 1
        issues.append(f'AI腔词汇 {ai_hits} 处')
    
    return {'pass': score <= 2, 'padding_score': score, 'issues': issues}
```

**③ 场景推进度守卫 `guards/scene_delta_guard.py`**

将章节按时间/地点词分割为场景，每个场景检查 7 个推进维度：

```python
SCENE_SPLIT_PATTERN = r'(?:(?:翌日|次日|片刻|须臾|不久).{0,8}[，,]|(?:走进|来到|抵达|进入).{0,15}[，,。])'

DELTA_DIMS = {
    'plot':         r'(突破|击败|发现|决定|逃脱|被捕|揭露)',
    'char_state':   r'(受伤|痊愈|晋级|突破|死亡|觉醒)',
    'relationship': r'(结盟|决裂|相爱|背叛|误会|和解)',
    'conflict':     r'(战斗|争执|对峙|追杀|逃跑|对抗)',
    'world':        r'(秘密|禁区|传说|历史|法则|设定)',
    'promise':      r'(承诺|发誓|许下|赌注|约定)',
    'hook':         r'(突然|不料|竟然|怎么可能|震惊|难以置信)',
}

def check_scene_delta(text: str, short_chapter=False) -> dict:
    scenes = re.split(SCENE_SPLIT_PATTERN, text)
    scenes = [s for s in scenes if len(s.strip()) > 100]
    
    valid, low = 0, 0
    for scene in scenes:
        active = sum(1 for dim, pat in DELTA_DIMS.items() if re.search(pat, scene))
        if active >= 2:
            valid += 1
        else:
            low += 1
    
    min_valid = 1 if short_chapter else 3
    return {
        'pass': valid >= min_valid and low <= 1,
        'valid_scenes': valid,
        'low_delta_scenes': low,
    }
```

**④ 设定幻觉守卫 `guards/canon_evidence_guard.py`**

```python
# 硬声明模式（境界突变/新势力/新法宝等）
HARD_CLAIM_PATTERNS = {
    'realm_change': r'(突破|晋升|踏入|进阶).{0,10}(境界|层次|级别|阶段)',
    'new_faction':  r'(?:一个|某个).{0,5}(?:门派|势力|组织|家族).{0,10}(?:出现|诞生|崛起)',
    'new_item':     r'(得到|获得|发现).{0,10}(法宝|神器|秘籍|功法)',
    'betrayal':     r'(背叛|投靠|倒戈|出卖).{0,15}(?:了|道|地)',
}

def check_canon(text: str, task_card: dict, prev_brief: str) -> dict:
    hard_claims = []
    for claim_type, pat in HARD_CLAIM_PATTERNS.items():
        for m in re.finditer(pat, text):
            hard_claims.append({'type': claim_type, 'text': m.group()})
    
    # 检查每个硬声明是否有来源依据
    allowed = task_card.get('allowed_new_canon', []) + [prev_brief]
    unsupported = []
    for claim in hard_claims:
        has_evidence = any(
            any(kw in src for kw in re.findall(r'[\u4e00-\u9fff]{2,4}', claim['text']))
            for src in allowed
        )
        if not has_evidence:
            unsupported.append(claim)
    
    total = len(hard_claims)
    coverage = 1.0 - len(unsupported) / max(total, 1)
    
    return {
        'pass': coverage >= 0.95 and len(unsupported) == 0,
        'evidence_coverage': round(coverage, 3),
        'unsupported_hallucinations': unsupported,
        'total_hard_claims': total,
    }
```

#### 集成方式

在 `novel_agent/orchestrator.py` 的 Step 10（审计）之后、Step 11（敏感词扫描）之前，新增 Step 10.5：

```python
# Step 10.5: 物理质量门禁
from novel_agent.guards import (
    continuity_evidence_guard,
    padding_guard,
    scene_delta_guard,
    canon_evidence_guard,
)

guard_results = {
    'continuity': continuity_evidence_guard.check(prev_tail, curr_head),
    'padding':    padding_guard.check_padding(final_text),
    'scene':      scene_delta_guard.check_scene_delta(final_text),
    'canon':      canon_evidence_guard.check_canon(final_text, task_card, prev_brief),
}

failed_guards = [k for k, v in guard_results.items() if not v['pass']]
if failed_guards:
    # 注入详细反馈进重写循环
    rewrite_feedback = format_guard_feedback(guard_results, failed_guards)
    # 触发已有的 auto-rewrite 逻辑（Step 10 审计高风险重写）
    raise GuardFailedException(failed_guards, rewrite_feedback)
```

---

### 改进二：剧情债务管理器（Priority: P1）

#### 背景

当前 `foreshadows` 表是被动记录（记录伏笔的存在）。天命系统和 inkos 的核心创新是**主动约束**：把"第 X 章前不能曝光秘密 Z"、"Y 角色必须在 N 章内兑现承诺"变成 Prompt 内的动态禁令与催促。

#### 数据表设计

在 `state/sqlite_store.py` 增加两张表：

```sql
-- 角色/剧情承诺（必须兑现）
CREATE TABLE IF NOT EXISTS pledges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id    TEXT NOT NULL,
    description TEXT NOT NULL,        -- "主角报仇杀死反派X"
    deadline_ch INTEGER NOT NULL,     -- 最迟兑现章节号
    created_ch  INTEGER NOT NULL,     -- 建立章节号
    status      TEXT DEFAULT 'open',  -- open / fulfilled / abandoned
    fulfil_ch   INTEGER,              -- 实际兑现章节
    urgency     TEXT DEFAULT 'normal' -- low / normal / high / critical
);

-- 信息差管控（秘密不能提前泄露）
CREATE TABLE IF NOT EXISTS secrets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id    TEXT NOT NULL,
    description TEXT NOT NULL,        -- "主角真实身份是皇族后裔"
    forbidden_until_ch INTEGER NOT NULL, -- 解禁章节号
    created_ch  INTEGER NOT NULL,
    revealed_ch INTEGER,              -- NULL=未揭露
    status      TEXT DEFAULT 'sealed' -- sealed / revealed / voided
);
```

#### Prompt 注入逻辑

在 `agents/context_builder.py` 的上下文组装阶段，追加以下模块：

```python
def build_narrative_debt_block(current_chapter: int, novel_id: str, db) -> str:
    """生成剧情债务约束块，注入到 Writer Prompt"""
    
    # 查询即将到期的承诺（deadline 在当前章 ±3 章内）
    urgent_pledges = db.execute("""
        SELECT description, deadline_ch FROM pledges
        WHERE novel_id=? AND status='open' AND deadline_ch BETWEEN ? AND ?
    """, (novel_id, current_chapter - 1, current_chapter + 3)).fetchall()
    
    # 查询当前章节仍需保密的秘密
    sealed_secrets = db.execute("""
        SELECT description FROM secrets
        WHERE novel_id=? AND status='sealed' AND forbidden_until_ch > ?
    """, (novel_id, current_chapter)).fetchall()
    
    block = "\n## 剧情债务约束（必须遵守）\n"
    
    if sealed_secrets:
        block += "\n### ⛔ 信息禁令（以下秘密本章绝对不可揭露）\n"
        for s in sealed_secrets:
            block += f"- {s['description']}\n"
    
    if urgent_pledges:
        block += "\n### ⏰ 即将到期的承诺（需要在本章或下章推进）\n"
        for p in urgent_pledges:
            urgency = "【本章必须推进】" if p['deadline_ch'] <= current_chapter else "【即将到期】"
            block += f"- {urgency} {p['description']}（截止第{p['deadline_ch']}章）\n"
    
    return block
```

#### 自动识别与更新

在 Auditor Agent 的输出 schema 中新增 `narrative_debt_updates` 字段：

```json
{
  "risk_level": "低",
  "issues": [],
  "state_update": {},
  "narrative_debt_updates": {
    "pledges_fulfilled": ["pledge_id_1"],
    "secrets_revealed": ["secret_id_2"],
    "new_pledges": [
      {"description": "主角承诺三章内救出师父", "deadline_ch": 25}
    ]
  }
}
```

---

### 改进三：向量检索时间距离打压（Priority: P1）

#### 背景

当前 `context_builder.py` 直接按余弦相似度召回历史片段，没有对距离当前章节过近的内容做惩罚。读者刚读过的内容再被 LLM 检索并复述，会造成强烈的重复感。

#### 改进实现

修改 `state/vector_store.py` 的检索逻辑：

```python
def retrieve_with_distance_penalty(
    self,
    query: str,
    current_chapter: int,
    top_k: int = 5,
) -> list[dict]:
    """
    带章节距离打压的向量检索。
    距离 ≤ 3 章：直接丢弃（读者刚读过）
    距离 3-5 章：打标 REQUIRE_REWRITE_40%（需要改写引用）
    距离 > 5 章 或 来源为设定 Wiki：正常采纳
    """
    raw_results = self.retrieve(query, top_k=top_k * 3)  # 多召回以备过滤
    
    filtered = []
    for chunk in raw_results:
        chunk_chapter = chunk.get('chapter_id', 0)
        delta = current_chapter - chunk_chapter
        
        if chunk.get('source_type') == 'wiki':
            # 设定 Wiki 永远优先采纳
            chunk['rewrite_hint'] = None
            filtered.append(chunk)
        elif delta <= 3:
            # 丢弃：太近，读者刚读过
            continue
        elif 3 < delta <= 5:
            # 保留但打标，要求 Writer 改写引用方式
            chunk['rewrite_hint'] = 'REQUIRE_REWRITE_40%'
            filtered.append(chunk)
        else:
            chunk['rewrite_hint'] = None
            filtered.append(chunk)
        
        if len(filtered) >= top_k:
            break
    
    return filtered
```

并在 `ContextBuilderAgent` 组装时，将 `rewrite_hint` 注入 Prompt：

```python
for chunk in retrieved:
    if chunk.get('rewrite_hint') == 'REQUIRE_REWRITE_40%':
        context += f"\n[注意：以下内容来自近期章节，引用时须改写措辞，不可原文复述]\n"
    context += chunk['content'] + "\n"
```

---

### 改进四：7 层 LLM 中间件管道（Priority: P2）

#### 背景

当前 `FallbackLLM` 只做了链式重试，缺少 Thinking 链剥离（推理模型如 DeepSeek-R1 输出会包含 `<think>` 标签污染正文）、API Key 轮换和详细的调用追踪。

#### 中间件架构

重构 `agents/base.py` 的 `OpenAILLM`，包装 7 层过滤器：

```python
class RobustLLMClient:
    """7 层中间件 LLM 客户端"""
    
    def __init__(self, config: dict):
        self.config = config
        self.key_pool = config.get('api_keys', [config.get('api_key')])
        self.key_index = 0
    
    async def generate(self, role: str, prompt: str) -> LLMResult:
        # Layer 1: API Key 轮换
        api_key = self._rotate_key()
        
        try:
            raw = await self._call_api(api_key, prompt)
        except RateLimitError:
            # Layer 2: 限频自动切换 Key
            api_key = self._rotate_key(force=True)
            raw = await self._call_api(api_key, prompt)
        except Exception as e:
            # Layer 3: 模型降级
            raw = await self._fallback_call(prompt, str(e))
        
        # Layer 4: Thinking 链剥离（推理模型）
        thinking, content = self._extract_thinking(raw)
        
        # Layer 5: 结构解析（JSON 修复）
        parsed = self._parse_structured(content)
        
        # Layer 6: Token 统计与成本追踪
        self._log_usage(role, raw.usage, thinking)
        
        # Layer 7: 内容完整性校验
        self._validate_output(content, role)
        
        return LLMResult(content=content, thinking=thinking, usage=raw.usage)
    
    def _extract_thinking(self, raw) -> tuple[str, str]:
        """剥离 <think>...</think> 推理链，归档供调试"""
        content = raw.choices[0].message.content or ''
        think_pattern = r'<think>(.*?)</think>'
        thinking = re.findall(think_pattern, content, re.DOTALL)
        clean_content = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
        return '\n'.join(thinking), clean_content
    
    def _rotate_key(self, force=False) -> str:
        if force:
            self.key_index = (self.key_index + 1) % len(self.key_pool)
        return self.key_pool[self.key_index]
```

#### 配置支持

在 `config/pipeline.yaml` 新增多 Key 配置：

```yaml
llm:
  default:
    provider: openai
    model: deepseek-chat
    api_keys:               # 多 Key 轮换
      - sk-key1
      - sk-key2
    fallback_chain:         # 降级链
      - model: gpt-4o-mini
        api_key: sk-openai
  overrides:
    writer:
      model: deepseek-r1    # 推理模型，自动剥离 <think>
      thinking_archive: true
```

---

### 改进五：chapter_versions 版本快照升级（Priority: P2）

#### 背景

当前 YAML 快照只保存状态，不保存章节文本的历史版本。当审计高风险触发重写时，原始版本丢失，无法回滚对比。

#### 数据表设计

在 `state/sqlite_store.py` 新增版本表：

```sql
CREATE TABLE IF NOT EXISTS chapter_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id        TEXT NOT NULL,
    chapter_id      INTEGER NOT NULL,
    version         INTEGER NOT NULL,      -- 自增，v1/v2/vN
    content         TEXT NOT NULL,
    word_count      INTEGER,
    guard_results   TEXT,                  -- JSON，本版本的门禁结果
    change_reason   TEXT,                  -- 'initial' / 'rewrite_audit_high' / 'manual'
    is_current      INTEGER DEFAULT 0,     -- 1 = 当前正式版
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(novel_id, chapter_id, version)
);
```

**写入逻辑**：每次 Step 7（写入最终文本）都触发一次版本存档，`is_current` 只有最新版为 1，历史版本保留但标为 0，永不删除。

---

### 改进六：段落排版规范化（Priority: P3）

#### 背景

inkos 逆向报告指出，网文对段落排版有特殊要求：单段不宜超过 150 字，否则在手机阅读时视觉压迫感强。当前系统无此检测。

#### 实现方式

在 `guards/padding_guard.py` 增加段落排版检查：

```python
def check_paragraph_layout(text: str) -> dict:
    """检测段落长度分布，网文单段建议 ≤ 150 字"""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    long_paras = [p for p in paragraphs if len(p) > 150]
    ratio = len(long_paras) / max(len(paragraphs), 1)
    
    return {
        'pass': ratio < 0.3,  # 超长段落不超过 30%
        'long_paragraph_ratio': round(ratio, 3),
        'long_paragraph_count': len(long_paras),
        'suggestion': '建议将超长段落在自然停顿处拆分，提升手机端阅读体验',
    }
```

---

## 三、实施优先级与路线图

### Phase 1（1-2 周）：物理门禁层

实现改进一的四个守卫脚本，集成进 orchestrator，但以**警告模式**（不阻断，只记录）先运行一周，观察各门禁的误报率，再切换为**阻断模式**。

**验收标准：**
- 各守卫在已生成的 11 章上跑通，输出可读的 JSON 报告
- 与 rewrite 循环正确对接，失败时 rewrite_feedback 包含守卫详情
- 前端章节详情页新增「守卫报告」Tab

### Phase 2（3-4 周）：剧情债务管理器

实现 `pledges` 和 `secrets` 数据表，完成 ContextBuilder 注入，并在前端素材页增加管理 UI。

**验收标准：**
- 可在 UI 中手动添加/完成承诺和秘密
- Auditor 能自动识别兑现事件并更新状态
- Writer Prompt 中能看到债务约束块

### Phase 3（5-6 周）：检索优化与中间件

实现向量检索距离打压（改进三）和 7 层中间件管道（改进四）。

**验收标准：**
- 检索结果中近 3 章内容被正确过滤
- DeepSeek-R1 的 `<think>` 标签不出现在正文
- 多 Key 配置在 pipeline.yaml 可用

### Phase 4（7-8 周）：版本管理与排版

实现 `chapter_versions` 表（改进五）和段落排版检查（改进六），前端提供版本历史查看。

---

## 四、快速收益项（本周可做）

不依赖架构改动，可立即实施的微改进：

**① 给 Planner 的输出 JSON 新增 `prev_tail_hooks` 字段**
要求 Planner 明确列出上章结尾的 Hook 关键词，并强制 Writer 在开头 200 字内引用至少 2 个。这是物理守卫实现前的 Prompt 层临时替代。

**② 在 StyleEditor 的 Prompt 中增加 AI 腔黑名单**
将以下词组加入禁止使用列表：「不是A而是B」「那一刻他终于明白」「总而言之」「值得注意的是」「毫无疑问」「不禁让人」「令人印象深刻」「不得不说」。

**③ 向量检索结果加章节号标注**
在返回给 ContextBuilder 的检索片段前，加注章节号：`[第X章] ...`，帮助 Writer 隐式感知信息的远近，减少复读。

**④ Auditor 输出 schema 新增 `narrative_hooks` 字段**
要求 Auditor 明确记录本章结尾留下了哪些 Hook（未完成动作、悬念、伤势等），供下一章 Planner 直接引用。

---

## 五、关键参考数据

来自 CAN 逆向分析的门禁判定阈值，可作为当前项目门禁的初始校准值：

| 门禁项 | CAN 阈值 | 建议初始值（较宽松，避免误报） |
|--------|---------|--------------------------|
| 连续性得分 | ≥ 0.80 | ≥ 0.65 |
| 遗忘状态数 | = 0 | ≤ 1 |
| 缺失 Hook 数 | = 0 | ≤ 1 |
| 设定覆盖率 | ≥ 0.95 | ≥ 0.85 |
| 水文评分 | ≤ 60 / 级别不为 fail | ≤ 3 分（本文档定义的 0-4 分制） |
| 最小有效场景数 | ≥ 3（短章 ≥ 1） | ≥ 2（短章 ≥ 1） |
| AI 腔词汇处数 | ≤ 2 | ≤ 4 |

---

*文档生成于 2026-05-24，基于 CAN（Novel Pipeline - Write Engine）深度逆向报告及 6 大 AI 写作项目横向对比研究。*
