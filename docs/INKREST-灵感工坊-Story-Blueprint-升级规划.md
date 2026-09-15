# INKREST「灵感工坊 / 网文套路设计器」升级规划

> 项目：INKREST / 栖墨  
> 规划主题：将现有 `presets/` 与网文套路设计能力升级为结构化、可编译、可验证、可演化的 Story Blueprint 系统  
> 适用范围：开书策划、灵感设计、套路组合、世界观生成、人物设计、节奏设计、伏笔规划、AI 写作流水线、质量审校  
> 文档性质：产品规划 + 技术架构 + 数据模型 + 开发路线图  
> 状态：建议稿

---

# 1. 背景与目标

INKREST 当前已经具备较完整的长篇小说生产能力，包括：

- 大纲与卷纲；
- 人物、关系、世界设定；
- 时间线与事件；
- 伏笔与运行时状态；
- 多 Agent 辅助写作；
- 章节生产流水线；
- 长篇记忆与上下文召回；
- 连续性检查；
- 质量门禁；
- 正文修订历史；
- 多格式导出；
- 本地优先与项目级 SQLite 数据真源。

与此同时，项目中已经存在 `presets/` 体系，并包含：

- `channels/`
- `cool_points/`
- 多种男频 / 女频成品套路目录；
- JSON 元数据；
- Markdown 写作指南。

现有「网文套路设计器（灵感工坊）」参考方案提出了：

```text
频道
+
题材
+
机制
+
爽点
↓
生成 writing_guide.md
↓
进入小说生产流水线
```

这个方向是成立的，但如果仅实现为“四类卡片选择 + Markdown 拼接”，会低估 INKREST 现有架构能力。

INKREST 更适合把这一模块建设成：

> **Story Blueprint Compiler —— 故事蓝图编译器**

即：

```text
灵感 / 套路组件 / 用户约束
            ↓
       蓝图解析器
            ↓
依赖 / 冲突 / 参数 / 差异化分析
            ↓
      Story Blueprint
            ↓
人物 / 世界 / 节奏 / 伏笔 / 大纲 / Prompt / 审校规则
            ↓
       INKREST Pipeline
```

最终目标不是“帮助用户选择套路”，而是：

> **把零散灵感编译成一套可以被整个小说生产系统执行、检查和持续维护的结构化故事契约。**

---

# 2. 核心升级原则

整个灵感工坊建议遵循以下原则。

## 2.1 不再以 Markdown 为唯一真源

`writing_guide.md` 应继续保留，但只作为：

- 人类可读版本；
- LLM 上下文版本；
- 导出版本。

真正的数据真源应该是结构化 Blueprint。

建议：

```text
SQLite / JSON Blueprint
        ↓
派生
        ├── writing_guide.md
        ├── outline_contract.json
        ├── pacing_plan.json
        ├── world_constraints.json
        ├── character_constraints.json
        ├── foreshadow_plan.json
        └── review_rules.json
```

---

## 2.2 不建立平行系统

灵感工坊不能重新维护一套：

- 人物；
- 世界；
- 关系；
- 时间线；
- 伏笔。

而应该直接与现有 Planning Workspace、SQLite narrative state、Outline、Pipeline 对接。

---

## 2.3 从“标签选择”升级为“规则系统”

套路组件不只是：

```text
系统流
重生
幕后流
打脸
```

而应该拥有：

- 参数；
- 前置条件；
- 互斥条件；
- 推荐组合；
- 风险；
- 适用频道；
- 适用题材；
- 情绪功能；
- 节奏功能；
- 生成规则；
- 审校规则。

---

## 2.4 所有蓝图必须可验证

Blueprint 不应该只是“建议”。

系统需要知道：

```text
什么必须成立
什么不能发生
什么应该多久出现一次
什么需要在哪一卷回收
什么变化会影响哪些章节
```

最终做到：

> 从 Prompt Engineering 升级为 Narrative Constraint Engineering。

---

# 3. 产品定位

建议将“灵感工坊”正式定位为：

> **INKREST 的小说立项与故事工程设计中心。**

它负责从：

```text
一句灵感
```

逐步生成：

```text
Story DNA
↓
Story Blueprint
↓
项目级故事契约
↓
大纲
↓
卷纲
↓
章纲
↓
正文
```

它是整个生产流水线最上游的一层。

---

# 4. Story DNA：从四维升级为十维

原始参考方案包含四个维度：

1. 频道；
2. 题材；
3. 机制；
4. 爽点。

建议升级为十维 Story DNA。

| 层级 | 维度 | 作用 | 示例 |
|---|---|---|---|
| 1 | 受众 / 频道 | 决定读者期待 | 男频、女频、轻小说、通用 |
| 2 | 题材壳 | 决定世界表现 | 玄幻、都市、历史、科幻、悬疑 |
| 3 | 世界结构 | 决定社会运行方式 | 宗门、帝国、公司社会、末世聚落 |
| 4 | 主角原型 | 决定角色起点 | 底层逆袭、天才跌落、小人物、反派重生 |
| 5 | 核心欲望 | 决定角色驱动力 | 变强、复仇、守护、自由、求真 |
| 6 | 核心机制 | 决定推进引擎 | 系统、回档、模拟器、马甲、空间 |
| 7 | 核心矛盾 | 决定故事对抗 | 阶层、资源、身份、文明、人性 |
| 8 | 情绪引擎 | 决定阅读快感 | 打脸、揭秘、成长、救赎、经营 |
| 9 | 叙事结构 | 决定组织方式 | 升级流、单元剧、无限流、群像、双线 |
| 10 | 文风与节奏 | 决定表达 | 轻松、黑暗、克制、热血、快节奏 |

示例：

```yaml
channel: male

genre:
  primary: xianxia
  secondary:
    - survival
    - mystery

protagonist:
  archetype: fallen_genius
  desire: regain_control
  morality: pragmatic

world:
  structure: sect_feudalism
  scarcity: spiritual_resources

mechanisms:
  - simulator
  - identity_disguise

emotional_engines:
  - reversal
  - discovery
  - power_growth

narrative:
  structure: progressive_escalation
  pacing: fast
  viewpoint: limited_third_person
```

---

# 5. Story Blueprint Compiler

这是整个升级的核心。

## 5.1 输入

Blueprint Compiler 接收：

```text
用户灵感
+
Trope Atom
+
Recipe
+
用户参数
+
AI 补全
+
项目已有设定
```

---

## 5.2 编译流程

```text
Input
  ↓
Normalize
  ↓
Dependency Resolve
  ↓
Conflict Detection
  ↓
Parameter Completion
  ↓
Narrative Inference
  ↓
Uniqueness Analysis
  ↓
Constraint Generation
  ↓
Blueprint
```

---

## 5.3 编译产物

Blueprint 不应该只生成一个文件。

建议生成：

```text
story_blueprint.json
writing_guide.md
outline_contract.json
world_constraints.json
character_constraints.json
pacing_plan.json
foreshadow_plan.json
reader_promises.json
review_rules.json
```

其中：

### story_blueprint.json

唯一结构化总蓝图。

### writing_guide.md

给作者和 LLM 阅读。

### outline_contract.json

约束 Outline Agent。

### world_constraints.json

约束世界设定和连续性检查。

### character_constraints.json

约束人物弧线和 OOC 检测。

### pacing_plan.json

提供爽点、高潮和低谷节奏。

### foreshadow_plan.json

规划伏笔生命周期。

### reader_promises.json

定义阅读期待。

### review_rules.json

直接提供给 Review Agent。

---

# 6. Atom / Recipe / Blueprint 三层模型

建议正式确立三层概念。

---

## 6.1 Atom

最小故事原子。

例如：

```text
系统
重生
马甲
经营
幕后流
打脸
追妻火葬场
规则怪谈
```

Atom 不能直接等于一段 Markdown。

应该至少拥有：

```json
{
  "id": "rebirth",
  "name": "重生",
  "type": "mechanism",
  "tags": ["信息差", "历史修正"],
  "channels": ["male", "female", "general"],
  "requires": [],
  "recommended_with": [
    "revenge",
    "knowledge_advantage"
  ],
  "conflicts_with": [
    "total_amnesia"
  ]
}
```

---

## 6.2 Recipe

Recipe 是成熟套路组合。

例如：

```text
都市神豪
苟道修仙
年代创业
追妻火葬场
幕后流修仙
规则怪谈
高武学院
```

Recipe 本质是：

```text
多个 Atom
+
预设参数
+
结构规则
+
节奏模板
```

---

## 6.3 Blueprint

Blueprint 是作品最终版本。

```text
Recipe
+
用户修改
+
自定义 Atom
+
AI 推导
+
项目参数
=
Blueprint
```

Blueprint 属于项目。

Atom 和 Recipe 属于公共资源库。

---

# 7. Trope Graph：套路关系图

当前“多选卡片”模式存在严重问题：

用户无法判断组合之间是否合理。

例如：

```text
无敌流
+
绝境求生
+
硬核生存
```

理论上可以组合，但存在叙事张力冲突。

因此建议建立 Trope Graph。

---

## 7.1 关系类型

至少支持：

```text
requires
recommended_with
conflicts_with
weak_conflict
enhances
replaces
derived_from
```

---

## 7.2 示例

```text
重生
├── 强协同 → 信息差
├── 强协同 → 复仇
├── 中协同 → 商战
├── 中协同 → 改变遗憾
└── 冲突 → 完全失忆
```

---

## 7.3 自动推荐

用户加入：

```text
重生
```

系统推荐：

```text
信息差      92%
复仇        89%
蝴蝶效应    85%
商业竞争    72%
```

这样灵感工坊从组件仓库升级为：

> Narrative Recommendation Engine。

---

# 8. 套路冲突检测器

建议建立专门的：

```text
Blueprint Validator
```

判断：

- 硬冲突；
- 软冲突；
- 节奏冲突；
- 世界观冲突；
- 主角定位冲突；
- 情绪结构冲突。

例如：

```text
无敌流
+
绝境求生
```

系统不应该简单禁止。

应该返回：

```text
风险：高

原因：
“主角绝对无敌”会显著削弱生存威胁。

可调整：
1. 危险从主角本人转移到队友；
2. 威胁改为时间限制；
3. 威胁改为身份暴露；
4. 威胁改为信息未知；
5. 威胁改为社会后果；
6. 让力量无法解决核心问题。
```

这比简单的：

```text
组合不兼容
```

更有价值。

---

# 9. 参数化套路系统

这是灵感工坊从“标签工具”升级为“故事设计工具”的关键。

---

## 9.1 系统流参数

```yaml
system:
  consciousness: false
  visibility: protagonist_only
  reward_source: causal_exchange
  mandatory_tasks: false
  penalty: none
  growth_curve: diminishing
  can_lie: false
  origin_reveal:
    stage: late_story
```

UI 可以展示：

```text
系统是否有意识？
系统是否能对话？
系统谁能看到？
奖励从哪里来？
是否强制任务？
失败有无惩罚？
成长速度如何？
系统能否欺骗主角？
最终是否解释系统来源？
```

---

## 9.2 重生参数

```text
重生到哪个时间点？
保留多少记忆？
记忆是否绝对可靠？
原时间线是否存在？
能否改变历史？
蝴蝶效应等级？
是否存在其他重生者？
```

---

## 9.3 无限流参数

```text
副本类型
副本入口
副本失败代价
现实世界是否继续运行
副本是否重复
玩家是否可互杀
能力能否带回现实
最终副本是否存在
```

所有主要机制都应该拥有自己的 schema。

---

# 10. 灵感孵化模式：Snowflake 式渐进创作

灵感工坊不应该只有“卡片模式”。

建议加入：

> **灵感孵化模式**

从一句话逐层推导。

```text
一句脑洞
↓
故事种子
↓
一句话卖点
↓
核心幻想
↓
核心冲突
↓
300 字简介
↓
主角
↓
世界
↓
故事主线
↓
卷级结构
↓
Blueprint
```

例如输入：

```text
一个现代 AI 运维员带着机房穿越古代。
```

系统可以生成多个方向：

```text
A 工业革命
B 种田经营
C 技术官僚
D 军事争霸
E 文明演化
```

用户选择：

```text
B + D
```

再继续推导。

---

# 11. 灵感变异器

加入一个非常适合“灵感工坊”的能力：

> Story Mutator

用户已有：

```text
玄幻
+
废柴
+
系统
+
打脸
```

点击：

```text
变异
```

生成：

### 保守变异

```text
玄幻 + 废柴 + 模拟器 + 逆袭
```

### 中等变异

```text
玄幻 + 被废宗主 + 宗门模拟器 + 幕后经营
```

### 激进变异

```text
末法修仙 + 无法修炼的主角 + AI 推演修仙文明 + 文明升级
```

---

## 11.1 锁定机制

支持：

```text
🔒 题材
🔒 主角
🔓 机制
🔓 爽点
```

用户决定哪些维度保持不变。

---

# 12. 差异化检测系统

套路设计器最大的风险是：

> 最终生成的作品高度模板化。

因此建议增加：

> Novel Uniqueness Engine

输出：

```text
常见度        82%
差异度        41%
卖点辨识度    53%
套路拥挤度    86%
```

---

## 12.1 分析维度

分析：

- 题材组合常见程度；
- 主角原型常见度；
- 金手指常见度；
- 情绪引擎重复度；
- 核心卖点独特性；
- 世界结构独特性；
- 叙事结构独特性。

---

## 12.2 差异化建议

例如：

```text
都市
+
神豪系统
+
打脸
+
直播
```

系统提示：

```text
组合高度常见。
```

提供：

### 职业差异化

```text
神豪 + 文物修复
```

### 机制反转

```text
奖励不是消费，而是解决现实问题
```

### 主角反转

```text
主角不是年轻人，而是破产企业家
```

### 叙事反转

```text
升级流 → 单元剧
```

---

# 13. USP：核心卖点系统

所有 Blueprint 必须拥有：

```text
Unique Selling Proposition
```

示例：

```yaml
hook:
  one_sentence: >
    一个只能看到别人死亡倒计时的殡仪馆化妆师，
    发现自己的倒计时永远停在七天。

core_fantasy:
  - 掌控命运
  - 破解死亡

novelty:
  - 死亡倒计时
  - 殡仪行业

reader_promise:
  - 每10章推进一次重大死亡真相
```

后续 Outline Agent 必须持续围绕 USP 工作。

防止：

```text
开头很有特色
↓
100章以后变成普通升级流
```

---

# 14. Reader Promise：读者承诺系统

建议增加：

```text
Reader Promise
```

定义：

> 读者为什么继续阅读，以及多久应该兑现一次。

示例：

```yaml
reader_promises:
  - id: cultivation_progress
    type: progression
    expected_interval: 8-15

  - id: identity_reveal
    type: mystery
    payoff_stage: volume_3

  - id: face_slap
    type: emotional_payoff
    expected_interval: 3-6
```

Quality Gate 可以检查：

```text
最近 19 章没有明显实力成长
超过 Blueprint 约定的 8-15 章
```

或者：

```text
“师父身份”悬念已经 27 章没有推进
可能出现悬念失温
```

---

# 15. 爽点预算与节奏曲线

当前“选择爽点”应该升级为：

> Pacing Planner

---

## 15.1 节奏曲线

每卷定义：

```yaml
volume_1:
  emotional_curve:
    opening_hook: 8
    buildup: 4
    first_payoff: 7
    midpoint: 6
    climax: 10
    ending_hook: 8
```

---

## 15.2 爽点排期

例如：

```text
第3章     小爽
第7章     反转
第12章    中爽
第18章    压抑
第23章    大反转
第29章    卷高潮
第30章    新钩子
```

---

## 15.3 节奏质量门禁

系统自动识别：

```text
连续 16 章情绪强度低于 4
```

或者：

```text
连续 5 次高潮类型相同
```

提示：

```text
可能出现爽点同质化。
```

---

# 16. 规划派 / 探索派 / 混合派

建议新增三种故事运行模式。

---

## 16.1 规划模式

```text
Blueprint
↓
总纲
↓
卷纲
↓
章纲
↓
正文
```

适合：

- 长篇网文；
- 商业连载；
- 强主线。

---

## 16.2 探索模式

```text
Blueprint
↓
当前局面
↓
生成多个合理发展
↓
作者选择
↓
更新世界状态
↓
下一故事节点
```

适合：

- 强角色驱动；
- 群像；
- 悬疑；
- 互动创作。

---

## 16.3 混合模式

推荐作为默认高级模式：

```text
卷级目标固定
+
章节级允许涌现
```

即：

> 知道这一卷去哪，但允许过程自然生长。

---

# 17. 世界模板系统

套路不能只生成文字。

应该生成：

> Entity Schema

例如修仙世界：

```text
人物
宗门
境界
功法
法宝
丹药
灵兽
秘境
城池
王朝
```

科幻世界：

```text
人物
星球
文明
公司
舰船
科技
AI
殖民地
政治实体
```

悬疑：

```text
人物
案件
证据
嫌疑人
地点
时间点
动机
证词
秘密
```

这些实体可以直接进入现有 Planning Workspace。

---

# 18. 世界规则可验证化

世界设定不能只是描述。

每条重要规则建议结构化为：

```yaml
rule:
  name: 筑基

  condition:
    - 炼气九层
    - 筑基丹

  effect:
    lifespan: +100
    spiritual_power: x3

  limitations:
    - 失败概率20%
    - 经脉损伤

  forbidden:
    - 炼气三层直接筑基

  consequences:
    violation:
      - 经脉崩毁
```

于是 Review Agent 可以准确判断：

```text
第56章
主角炼气六层直接突破筑基
```

返回：

```text
世界规则违规
```

而不是让模型凭印象判断。

---

# 19. 人物弧线设计器

人物不应该只有 Profile。

建议增加：

```text
Character Arc
```

结构：

```text
初始状态
↓
错误认知
↓
欲望
↓
冲突
↓
第一次改变
↓
重大失败
↓
认知崩塌
↓
最终选择
↓
终局状态
```

示例：

```yaml
character_arc:
  character: 江炘

  start:
    belief: 技术可以解决所有问题

  want:
    survive

  need:
    learn_to_lead_people

  midpoint:
    belief_crisis: true

  climax:
    choice: sacrifice_control

  end:
    belief: 技术只是工具，秩序来自人
```

这样 OOC 检测可以判断：

```text
当前行为是否符合角色当前阶段。
```

---

# 20. 伏笔设计器

伏笔应该从立项阶段开始规划。

建议建立完整生命周期：

```text
Seed
↓
Reminder
↓
Escalation
↓
Misdirection
↓
Payoff
```

示例：

```yaml
foreshadow:
  id: master_disappearance
  mystery: 师父为何失踪
  seed: chapter_3

  reminders:
    - chapter_16
    - chapter_31

  escalation:
    chapter: 48

  payoff:
    chapter: 78
```

与现有运行时伏笔状态结合后，可以检查：

```text
尚未埋设
已埋设
已提醒
已升级
等待回收
已回收
逾期
```

---

# 21. Blueprint 版本系统

长篇创作中 Blueprint 必然会变化。

因此禁止：

```text
直接覆盖旧 Blueprint
```

应该采用：

```text
Blueprint v1
↓
Blueprint v2
↓
Blueprint v3
```

---

## 21.1 Blueprint Diff

例如：

```diff
relationship_mode:
- none
+ slow_burn

romance_weight:
- 0
+ 0.25
```

---

## 21.2 影响提示

```text
受影响：

人物设定       3项
卷纲           2卷
伏笔           6项
未来章节       41章
已完成正文     12章
```

默认：

```text
不自动改写已完成正文。
```

---

# 22. 蓝图影响分析

这是 INKREST 可以形成差异化优势的重要能力。

例如用户修改：

```text
穿越者
→
重生者
```

系统自动分析：

```text
世界设定
无影响

第一卷
7个剧情节点依赖“现代知识”

人物
主角背景需要修改

伏笔
3条身份来源伏笔失效

已完成章节
第1、4、8章存在设定冲突
```

这本质上是：

> 小说领域 Dependency Graph + Impact Analysis。

---

# 23. 拆书 → Trope Pack

未来建议加入：

> Story Pattern Extraction

用户输入：

- 小说文本；
- 若干章节；
- 自己旧作品；
- 大纲；
- 剧情摘要。

系统分析：

```text
题材
主角原型
成长模型
剧情循环
爽点
钩子
冲突
节奏
人物结构
世界结构
```

然后生成：

```text
Custom Trope Pack
```

注意应定位为：

> 结构与机制抽象

而不是复制原作品文本。

---

# 24. 自定义套路包

建议未来支持：

```text
Trope Pack
```

结构：

```text
manifest.json
atoms/
recipes/
schemas/
guides/
validators/
```

用户可：

```text
导入
导出
复制
修改
版本管理
```

后续还可以形成：

```text
社区套路市场
```

但建议放到 P3 以后。

---

# 25. 灵感工坊 UI 重构

灵感工坊不建议只做“两栏卡片”。

最终建议至少包含五种视图。

---

## 25.1 灵感模式

```text
一句灵感
↓
AI 发散
↓
选择方向
↓
继续推导
```

---

## 25.2 积木模式

```text
组件库
│
├── 频道
├── 题材
├── 主角
├── 世界
├── 机制
├── 情绪
└── 结构

        ↓

Blueprint 工作台
```

---

## 25.3 图谱模式

使用 Vue Flow。

```text
           重生
          /    \
      信息差    复仇
       |         |
      商战      逆袭
```

展示：

- 推荐；
- 依赖；
- 冲突；
- 替代；
- 派生。

---

## 25.4 节奏模式

展示：

```text
卷
章节
高潮
低谷
爽点
伏笔
回收
Reader Promise
```

---

## 25.5 蓝图模式

查看完整：

```text
Story DNA
人物
世界
机制
情绪
节奏
伏笔
Reader Promise
USP
红线
质量规则
```

---

# 26. 建议页面布局

桌面端可以采用：

```text
┌──────────────────────────────────────────────────────────┐
│ 灵感工坊                                                 │
│ [灵感] [积木] [图谱] [节奏] [蓝图]                     │
├───────────────┬─────────────────────────────┬────────────┤
│ 元件库        │ Blueprint 工作区            │ 诊断面板   │
│               │                             │            │
│ 搜索          │ 频道                        │ 冲突       │
│ 分类          │ 题材                        │ 推荐       │
│ 推荐          │ 主角                        │ 风险       │
│ 收藏          │ 机制                        │ 差异度     │
│               │ 爽点                        │ 完整度     │
│               │ 世界                        │            │
├───────────────┴─────────────────────────────┴────────────┤
│ Blueprint Preview / Writing Guide                        │
└──────────────────────────────────────────────────────────┘
```

---

# 27. Blueprint 完整度评分

建议加入：

```text
Blueprint Health
```

示例：

```text
立项完整度       86%
机制完整度       92%
世界一致性       78%
人物驱动力       85%
节奏设计         74%
差异化           61%
伏笔规划         55%
```

并明确指出缺失项：

```text
缺少：
- 主要反派目标；
- 第一卷终点；
- 主角失败代价；
- 世界资源稀缺规则；
- 长线悬念。
```

---

# 28. AI Copilot

灵感工坊内部建议增加一个专属：

> Story Architect Agent

职责不是写正文，而是：

```text
分析蓝图
发现漏洞
推荐组合
发现套路冲突
补足故事逻辑
提出差异化方向
调整节奏
补充世界规则
```

它不应该自动修改 Blueprint。

默认：

```text
建议
→
用户接受
→
变更 Blueprint
```

---

# 29. 与现有 Pipeline 对接

完整链路建议：

```text
                    用户灵感
                       │
                       ▼
              Inspiration Agent
                       │
                       ▼
                 Trope Atom
                       │
                       ▼
             Blueprint Resolver
                       │
             ┌─────────┼─────────┐
             │         │         │
          依赖       冲突       参数
             │         │         │
             └─────────┼─────────┘
                       ▼
                STORY BLUEPRINT
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
   世界模型          人物模型          节奏模型
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                  Outline Agent
                       ▼
                     卷纲
                       ▼
                     章纲
                       ▼
                  Draft Agent
                       ▼
                 Review Agent
                       ▼
                  Quality Gate
```

---

# 30. Quality Gate 接入 Blueprint

新增：

```text
Blueprint Compliance Check
```

检查：

### 世界

```text
是否违反世界规则
```

### 人物

```text
是否 OOC
```

### 主线

```text
是否偏离核心目标
```

### 节奏

```text
是否超过 Reader Promise 最大间隔
```

### 伏笔

```text
是否逾期
```

### USP

```text
核心卖点是否长期消失
```

### 机制

```text
金手指是否出现能力膨胀
```

---

# 31. 推荐数据结构

建议新增：

```text
novel_agent/domain/blueprint/
```

例如：

```text
blueprint.py
trope.py
recipe.py
constraints.py
pacing.py
reader_promise.py
character_arc.py
foreshadow.py
```

---

## 31.1 StoryBlueprint

示例：

```python
class StoryBlueprint(BaseModel):
    schema_version: int
    id: str
    revision: int

    channel: ChannelSpec
    genres: GenreSpec
    protagonist: ProtagonistSpec
    world: WorldSpec

    mechanisms: list[MechanismSpec]
    emotional_engines: list[EmotionSpec]

    narrative: NarrativeSpec

    usp: USP
    reader_promises: list[ReaderPromise]

    pacing: PacingPlan
    character_arcs: list[CharacterArc]
    foreshadows: list[ForeshadowPlan]

    constraints: BlueprintConstraints
```

---

# 32. SQLite 建议

如果继续遵守 INKREST V2 数据真源原则，建议最终写入 SQLite。

可以考虑：

```text
story_blueprints
story_blueprint_revisions
trope_atoms
trope_relations
project_trope_bindings
reader_promises
pacing_nodes
planned_foreshadows
character_arcs
blueprint_constraints
```

---

# 33. Blueprint 与 Preset 的边界

仓库内：

```text
presets/
```

继续作为：

> 内置可版本化资源。

项目运行时 Blueprint：

```text
SQLite
```

作为：

> 项目真实状态。

不要反过来让：

```text
presets/
```

成为项目状态数据库。

---

# 34. 后端建议

新增：

```text
novel_agent/services/blueprint/
```

包括：

```text
blueprint_service.py
compiler.py
validator.py
recommendation.py
impact_analysis.py
mutation.py
```

---

# 35. API 建议

```http
GET /api/blueprint/components
GET /api/blueprint/components/{id}

GET /api/blueprint/recipes
GET /api/blueprint/recipes/{id}

GET /api/blueprint/current

POST /api/blueprint/compile
POST /api/blueprint/validate
POST /api/blueprint/recommend
POST /api/blueprint/mutate

POST /api/blueprint/apply
POST /api/blueprint/revisions

GET /api/blueprint/diff
POST /api/blueprint/impact-analysis
```

---

# 36. 前端建议

建议：

```text
web/frontend/src/features/blueprint/
```

包括：

```text
components/
  TropeCard.vue
  TropeLibrary.vue
  BlueprintSlot.vue
  BlueprintGraph.vue
  BlueprintDiagnostics.vue
  BlueprintPreview.vue

views/
  InspirationView.vue
  BuilderView.vue
  GraphView.vue
  PacingView.vue
  BlueprintView.vue

stores/
  blueprint.ts

composables/
  useBlueprintCompiler.ts
  useTropeGraph.ts
  useBlueprintValidation.ts
```

---

# 37. 不建议的实现方式

以下方案不建议作为最终架构。

---

## 37.1 所有规则直接字符串拼接

问题：

- 无法验证；
- 无法 Diff；
- 无法影响分析；
- 无法审校；
- 无法结构化修改。

---

## 37.2 Blueprint 只存在 Markdown

问题：

无法成为系统真源。

---

## 37.3 用户任意组合套路

没有依赖和冲突图谱会产生大量：

```text
逻辑上自相矛盾的蓝图。
```

---

## 37.4 所有套路都写死在代码里

应该：

```text
数据驱动
```

不是：

```text
if trope == ...
```

---

## 37.5 页面加载自动调用模型

继续保持 INKREST 当前原则：

```text
普通浏览不消耗模型额度。
```

AI：

```text
推荐
变异
分析
编译补全
```

都应由用户显式触发。

---

# 38. 开发阶段规划

建议分四期。

---

# Phase 0：Blueprint 基础设施

目标：

> 先建立正确架构。

实现：

- StoryBlueprint 数据模型；
- Atom / Recipe / Blueprint；
- 现有 Preset 兼容读取；
- Blueprint Compiler；
- Blueprint Validator；
- Blueprint SQLite 存储；
- Blueprint Revision；
- Blueprint → writing_guide；
- Blueprint → Outline Context；
- Blueprint → Review Rules。

优先级：

> P0 / 必须完成。

---

## Phase 0 验收标准

必须做到：

```text
选择套路
↓
生成 Blueprint
↓
保存项目
↓
生成 writing guide
↓
Outline Agent 可以读取
↓
Review Agent 可以读取
```

并且：

```text
重启后 Blueprint 不丢失。
```

---

# Phase 1：故事工程能力

目标：

> 从模板拼装升级为可验证故事设计。

实现：

- 参数化套路；
- Trope Graph；
- 依赖检测；
- 冲突检测；
- USP；
- Reader Promise；
- 世界规则；
- 人物弧；
- 伏笔计划；
- 爽点预算；
- 节奏曲线。

---

## Phase 1 验收标准

例如：

```text
无敌流 + 绝境求生
```

系统能够：

```text
发现冲突
解释冲突
给出解决方案
```

并且：

```text
Reader Promise
```

可以被章节质量检查实际使用。

---

# Phase 2：智能灵感

目标：

> 让灵感工坊真正拥有“工坊感”。

实现：

- Snowflake 灵感孵化；
- AI 套路推荐；
- 灵感变异器；
- 差异化检测；
- Blueprint Health；
- 图谱模式；
- 节奏视图；
- Story Architect Agent。

---

## Phase 2 验收标准

用户只输入：

```text
一个 AI 运维员带着机房穿越古代
```

系统能逐步产生：

```text
多个故事方向
↓
用户选择
↓
Story DNA
↓
Blueprint
```

---

# Phase 3：高级生态

目标：

> 建立长期壁垒。

实现：

- Blueprint Diff；
- Impact Analysis；
- 拆书；
- Trope Pack；
- 自定义套路市场；
- 导入 / 导出；
- 社区模板；
- Blueprint 分享。

---

# 39. 优先级总表

| 功能 | 优先级 |
|---|---:|
| Story Blueprint | ★★★★★ |
| Atom / Recipe / Blueprint | ★★★★★ |
| Compiler | ★★★★★ |
| Pipeline 注入 | ★★★★★ |
| Validator | ★★★★★ |
| Trope Graph | ★★★★★ |
| 参数化套路 | ★★★★★ |
| Reader Promise | ★★★★★ |
| 节奏曲线 | ★★★★★ |
| 世界规则验证 | ★★★★★ |
| Blueprint Revision | ★★★★★ |
| Impact Analysis | ★★★★★ |
| 人物弧 | ★★★★☆ |
| 伏笔规划 | ★★★★☆ |
| Snowflake | ★★★★☆ |
| AI 推荐 | ★★★★☆ |
| 变异器 | ★★★★☆ |
| 差异化检测 | ★★★★☆ |
| 拆书 | ★★★★☆ |
| Trope Pack | ★★★★☆ |
| 社区市场 | ★★★☆☆ |

---

# 40. 预期最终体验

用户进入灵感工坊。

输入：

```text
普通大学生穿越修仙世界，
但他完全没有灵根。
```

系统先推荐：

```text
方向 A
凡人流 + 科学修仙

方向 B
无灵根 + 模拟器

方向 C
无法修炼 + 宗门经营

方向 D
科技文明 vs 修仙文明
```

用户选择：

```text
D
```

继续得到：

```text
主角：理性技术型
核心欲望：生存 → 改变文明
机制：知识体系 + 工业化
冲突：技术秩序 vs 修仙资源垄断
爽点：技术碾压 / 体系突破 / 文明升级
结构：文明成长流
```

系统检查：

```text
套路兼容度    94%
差异化        82%
主线清晰度    88%
机制完整度    61%
```

提示：

```text
缺少：
能源来源
技术扩散路径
修仙势力反制方式
工业升级限制
```

用户补全。

生成：

```text
Story Blueprint v1
```

自动派生：

```text
世界规则
人物弧
Reader Promise
节奏计划
伏笔计划
Outline Contract
Review Rules
Writing Guide
```

最后：

```text
[生成总纲]
```

进入 INKREST 原有生产流水线。

---

# 41. 最终产品形态

完成上述升级后：

```text
灵感工坊
```

不再只是：

> 网文套路选择器。

而是：

> **INKREST Story Engineering Workspace**

其核心价值是：

```text
灵感
→
结构化
→
可执行
→
可验证
→
可演化
```

最终形成：

```text
Story Blueprint
        ↓
World
Character
Outline
Pacing
Foreshadow
Draft
Review
Memory
```

所有模块共同遵守同一套故事契约。

---

# 42. 最终建议

本次升级最重要的不是 UI。

优先级应该是：

```text
Story Blueprint
>
Compiler
>
Validator
>
Pipeline Integration
>
Trope Graph
>
参数化
>
Reader Promise
>
Pacing
>
AI 灵感能力
>
视觉表现
```

不要先把大量时间投入：

```text
拖拽动画
卡片特效
渐变
复杂过渡
```

真正决定 INKREST 是否形成差异化的，是：

> **故事设计是否从 Prompt 模板，升级成可编译、可验证、可追踪、可迭代的 Story Blueprint。**

如果这一层完成，INKREST 会从：

```text
AI 小说生成工具
```

进一步升级为：

> **长篇小说工程化生产系统。**

---

# 43. 推荐实施顺序

建议 Codex / 开发团队严格按以下顺序推进：

```text
1. StoryBlueprint Domain Model
2. Atom / Recipe Domain Model
3. Preset Adapter
4. Blueprint Compiler
5. Blueprint Validator
6. SQLite Repository
7. Blueprint API
8. Blueprint Store
9. Builder UI
10. Pipeline Context Injection
11. Review Integration
12. Trope Graph
13. Parameter Schema
14. Reader Promise
15. Pacing Planner
16. Foreshadow Planner
17. Character Arc
18. Mutation / Recommendation
19. Blueprint Diff
20. Impact Analysis
```

其中前 11 项完成后，即可形成：

> **灵感工坊 V1 正式可用版本。**

后续能力再逐步叠加。

---

# 44. 参考项目与思路来源

本规划综合参考：

- INKREST / 栖墨当前项目结构与现有 `presets/`、Planning Workspace、Pipeline、SQLite 数据真源设计；
- 《网文套路设计器（灵感工坊）功能设计与实现参考》；
- Manuskript 的 Snowflake 渐进式故事设计思路；
- Fantasia Archive 的世界实体与模板化世界观管理方式；
- StoryDaemon 的探索式 / 涌现式剧情理念；
- 部分 AI 小说项目中的角色状态、伏笔台账、节奏控制、质量门禁思路。

参考仓库：

```text
https://github.com/rowanjove/INKREST
https://github.com/olivierkes/manuskript
https://github.com/vishiri/fantasia-archive
https://github.com/EdwardAThomson/StoryDaemon
```

---

# 45. 一句话总结

> **把 INKREST 的“灵感工坊”从套路卡片拼装器，升级成全项目共用的 Story Blueprint Compiler，让故事从立项开始就是结构化、可执行、可检查、可版本化、可持续演化的。**
