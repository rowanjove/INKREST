> # 小说生产流水线——我与chatgpt的对话

---

# 

可以实现，而且你这个思路基本就是“小说生产流水线”：规划、分章、并行写作、合并、润色、检查。关键不是让一个模型一次憋出 2000 字，而是把任务工程化，控制每段输入输出边界。

能实现。你的方案方向是对的，但要改一个核心思路：

**不要指望模型“严格按 2000 汉字一次性生成”。应该把 2000 字目标拆成可验证、可续写、可回滚的生产单元。**

最稳的小说 AI 流水线应该是这样：

```text
总设定 Agent
  ↓
大纲 Agent
  ↓
分章 Agent
  ↓
分场景 Agent
  ↓
多个写作 Agent 并行写场景
  ↓
字数检查脚本
  ↓
不足则自动补写 / 超出则压缩
  ↓
合并 Agent / 合并脚本
  ↓
一致性检查 Agent
  ↓
风格润色 Agent
  ↓
“去 AI 味” Agent
  ↓
敏感词 / 违禁表达检查 Agent
  ↓
终稿
```

但这里有几个坑必须先说清楚。

---

## 1. 多 Agent 同时写小说，能不能做？

**能。**

但它不是“多个 Agent 自由发挥”，而是要有一个**总控 Orchestrator**，否则一定会乱。

多 Agent 并行写作最容易出的问题是：

1. 人物语气不一致；
2. 时间线冲突；
3. 前后伏笔断裂；
4. 设定被子 Agent 改写；
5. 每个片段都像独立短文，合并后不像一章；
6. 情绪节奏断掉；
7. 重复解释背景；
8. 结尾总爱总结、升华、鸡汤化。

所以每个子 Agent 不能只拿“剧情梗概”，还必须拿到：

```text
1. 世界观设定
2. 人物卡
3. 当前章节目标
4. 当前场景目标
5. 上一场景摘要
6. 下一场景预期
7. 禁止改动项
8. 文风约束
9. 字数目标
10. 输出格式
```

否则它会乱编。

---

## 2. 2000 汉字生成不到位，怎么解决？

这不是单纯提示词问题，而是模型行为问题。

大模型经常不听“写 2000 字”的原因有几个：

### 原因一：模型按 token 估算，不按汉字精确计数

中文里 2000 汉字和 token 不是一一对应。模型并不会真的边写边数汉字。你让它写 2000 字，它大概只是在心里理解成“写长一点”。

所以结果可能是：

```text
要求：2000 汉字
实际：900～1500 汉字
```

这很常见。

### 原因二：单次输出有上限

即使模型有很大的上下文窗口，也不代表它一次能输出很多。很多模型的**单次输出 token 限制**远小于总上下文窗口。

比如一个模型号称 128K 上下文，不等于它能一口气吐出 128K 文本。它可能单次只能输出 4K、8K、16K token。

### 原因三：模型为了“完成任务”会提前收尾

尤其小说任务里，模型有一个很烦人的倾向：  
它喜欢把段落写成“完整小作文”，而不是按字数展开。

你说“写 2000 字”，它可能写 1000 字后觉得剧情已经闭合，于是自然结束。

---

## 3. 最实用的解决办法：不要让它写 2000，改成写 4 个 500

比如你想要一章 2000 汉字，不要这样：

```text
请写一章，约 2000 汉字。
```

而是这样拆：

```text
第 1 场：约 500 汉字
第 2 场：约 500 汉字
第 3 场：约 500 汉字
第 4 场：约 500 汉字
```

甚至更稳一点：

```text
每场目标：450～650 汉字
总目标：1900～2300 汉字
```

这样成功率高很多。

写完以后用脚本统计字数：

```python
import re

def count_chinese_chars(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

text = open("chapter_01.txt", "r", encoding="utf-8").read()
print(count_chinese_chars(text))
```

如果不足，就让模型自动补写：

```text
当前章节目标是 2000～2200 汉字。
现在只有 1430 汉字。
请在不改变剧情走向、不增加新大事件的前提下，补充 500～700 汉字。
补充重点：
1. 人物动作；
2. 场景细节；
3. 内心反应；
4. 对话间的停顿；
5. 环境压迫感。
不要总结，不要解释设定，不要改变结尾。
```

这个比单次硬写 2000 稳得多。

---

## 4. 推荐的 Agent 分工

你这个流程可以做，但建议拆成这些角色。

### A. 总设定 Agent

负责生成或维护小说的“圣经文档”。

包括：

```text
小说类型：
核心卖点：
世界观：
主线矛盾：
人物卡：
势力关系：
时间线：
禁用设定：
文风样例：
敏感边界：
```

这个 Agent 不直接写正文。

它只维护设定。

---

### B. 大纲 Agent

负责全书结构。

输出类似：

```json
{
  "title": "小说名",
  "genre": "都市异能",
  "main_arc": "主角从被追杀到建立自己的秩序",
  "volumes": [
    {
      "volume": 1,
      "goal": "主角觉醒能力并卷入冲突",
      "chapters": [
        {
          "chapter": 1,
          "title": "雨夜来客",
          "goal": "引出主角、异能线索、第一场危机",
          "ending_hook": "门外传来已故父亲的声音"
        }
      ]
    }
  ]
}
```

---

### C. 分章 Agent

把大纲拆成章节。

每章必须包含：

```json
{
  "chapter_id": "001",
  "chapter_title": "雨夜来客",
  "target_chars": 2200,
  "chapter_goal": "主角发现自己被监视，并第一次使用能力",
  "start_state": "主角独自在出租屋，刚失业",
  "end_state": "主角听见门外传来父亲声音",
  "must_include": [
    "出租屋停电",
    "陌生短信",
    "镜子里出现第二个人影"
  ],
  "must_not_include": [
    "不能解释异能原理",
    "不能让主角马上掌控能力",
    "不能出现官方组织"
  ],
  "emotional_curve": "压抑 → 怀疑 → 恐惧 → 爆发 → 悬念"
}
```

---

### D. 分场景 Agent

把一章拆成多个场景。

比如 2200 汉字一章，拆成 4 个场景：

```json
{
  "chapter_id": "001",
  "scenes": [
    {
      "scene_id": "001-1",
      "target_chars": 550,
      "purpose": "建立主角处境和出租屋氛围",
      "entry": "主角回到出租屋",
      "exit": "灯突然灭了",
      "focus": "环境、疲惫、压抑"
    },
    {
      "scene_id": "001-2",
      "target_chars": 550,
      "purpose": "陌生短信出现，制造不安",
      "entry": "手机亮起",
      "exit": "镜子里出现人影",
      "focus": "短信、怀疑、现实感崩坏"
    }
  ]
}
```

---

### E. 写作 Agent

每个写作 Agent 只负责一个场景。

注意：**不要让它自己决定剧情。**

它只能根据场景卡写正文。

提示词可以这样：

```text
你是小说正文写作 Agent。

你只负责写当前场景，不要写前情提要，不要总结，不要跳到下一场景。

【小说文风】
冷峻、克制、具体，有压迫感。
少用抽象词，多写动作、物体、声音、气味、停顿。
不要鸡汤，不要升华，不要“命运”“宿命”“仿佛整个世界”这类空泛表达。

【当前章节目标】
主角发现自己被监视，并第一次使用能力。

【当前场景】
scene_id: 001-2
目标字数：500～650 汉字
场景目的：陌生短信出现，制造不安。
入场状态：出租屋停电，主角站在门口。
出场状态：主角在镜子里看到第二个人影。
必须包含：
- 手机屏幕亮起；
- 短信内容只有一句：“别回头。”；
- 主角先以为是恶作剧；
- 镜子中的人影不是他自己。
禁止包含：
- 不解释异能；
- 不出现警察；
- 不让主角离开出租屋；
- 不要写下一场景。

【输出要求】
只输出正文。
不要标题。
不要说明。
不要 Markdown。
```

这个比“帮我写一章小说”强很多。

---

## 5. 合并用脚本，不要全靠 Agent

合并其实应该分两步。

### 第一步：机械合并

这个用脚本就行：

```python
from pathlib import Path

chapter_dir = Path("chapter_001_scenes")
parts = sorted(chapter_dir.glob("scene_*.txt"))

chapter_text = "\n\n".join(p.read_text(encoding="utf-8").strip() for p in parts)

Path("chapter_001_raw.txt").write_text(chapter_text, encoding="utf-8")
```

### 第二步：合并润色 Agent

机械合并后，再让一个 Agent 做“接缝修复”。

提示词：

```text
你是小说章节接缝修复 Agent。

任务：修复多个场景拼接后的生硬感。

你可以：
1. 调整段落顺序；
2. 添加少量过渡句；
3. 删除重复信息；
4. 统一人物称呼；
5. 统一时态和叙述视角；
6. 让场景之间更自然。

你不可以：
1. 改变剧情；
2. 增加新人物；
3. 删除关键事件；
4. 提前揭示设定；
5. 把文风改成散文腔；
6. 写总结性结尾。

输出完整章节正文。
```

---

## 6. “去 AI 味 Agent”可以做，但不要叫它“去 AI 味”

“去 AI 味”这个需求本质上不是魔法，而是几个具体操作：

### AI 味常见症状

```text
1. 喜欢总结人生道理；
2. 喜欢过度对称的句式；
3. 喜欢“他知道，从这一刻起……”；
4. 喜欢“空气仿佛凝固了”；
5. 喜欢“命运的齿轮开始转动”；
6. 喜欢所有角色说话都很完整、很礼貌；
7. 喜欢解释人物心理，而不是让动作体现心理；
8. 喜欢每章结尾强行悬念；
9. 喜欢用“某种”“仿佛”“似乎”“无法言说”糊弄细节；
10. 喜欢把普通场面写得过度宏大。
```

所以你的“去 AI 味 Agent”应该拆成明确规则。

更好的名字是：

```text
风格降噪 Agent
```

或者：

```text
人类化修稿 Agent
```

提示词可以这样：

```text
你是小说风格降噪编辑。

你的任务不是润色得更华丽，而是去掉机器生成文本的油腻感、空泛感和模板感。

重点处理：
1. 删除总结人生意义的句子；
2. 删除过度解释心理的句子；
3. 删除“仿佛、似乎、某种、命运、齿轮、深处、无法言说”等空泛表达；
4. 把抽象心理改成具体动作；
5. 把过于工整的句式打散；
6. 减少形容词堆叠；
7. 保留粗粝、不完美、有生活质感的表达；
8. 对话要像真人说话，可以有省略、打断、重复和不完整句；
9. 不要把文风改成散文诗；
10. 不要新增剧情。

输出完整修订版。
```

还可以加一个禁词表：

```text
尽量避免：
“命运的齿轮”
“空气仿佛凝固”
“他不知道的是”
“从这一刻起”
“内心深处”
“某种难以言说”
“仿佛整个世界”
“悄然改变”
“再也回不到从前”
```

这些词不是绝对不能用，而是 AI 太爱用了。

---

## 7. 敏感词检查 Agent：应该脚本 + 模型双层

你说的“检查 Agent 确保没有敏感词”，可以做，但不要只靠 Agent。

最稳的是：

```text
第一层：本地敏感词词库硬匹配
第二层：规则检测
第三层：LLM 语义风险检查
第四层：人工抽查高风险章节
```

### 第一层：词库扫描

```python
from pathlib import Path

text = Path("chapter_001_final.txt").read_text(encoding="utf-8")

sensitive_words = [
    "敏感词1",
    "敏感词2",
    "敏感词3"
]

hits = []
for word in sensitive_words:
    if word in text:
        hits.append(word)

if hits:
    print("命中敏感词：")
    for h in hits:
        print(h)
else:
    print("未命中敏感词")
```

### 第二层：上下文风险检查

有些词本身不敏感，但上下文敏感。这个就适合用 Agent。

提示词：

```text
你是小说内容风险审校 Agent。

任务：检查下面文本是否存在平台发布风险。

检查维度：
1. 明确敏感词；
2. 暴力描写是否过度具体；
3. 色情描写是否露骨；
4. 政治风险；
5. 违法犯罪教学；
6. 未成年人相关风险；
7. 极端血腥；
8. 现实人物影射；
9. 平台可能误判的词语；
10. 需要替换或弱化的表达。

输出格式：
{
  "risk_level": "低/中/高",
  "hits": [
    {
      "text": "原文片段",
      "issue": "问题说明",
      "suggestion": "修改建议"
    }
  ],
  "clean_version_needed": true/false
}
```

然后再让另一个 Agent 修改：

```text
根据审校报告修改文本。
要求：
1. 保留剧情；
2. 保留人物关系；
3. 降低发布风险；
4. 不要把文本改得幼稚；
5. 不要删掉关键冲突；
6. 输出完整修订版。
```

---

## 8. 字数控制的最佳实践

你想要 2000 汉字，就不要设死 2000。设区间：

```text
目标：1900～2300 汉字
```

然后由脚本检查。

完整逻辑：

```python
import re
from pathlib import Path

def count_chinese_chars(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

target_min = 1900
target_max = 2300

text = Path("chapter_001.txt").read_text(encoding="utf-8")
count = count_chinese_chars(text)

print("汉字数：", count)

if count < target_min:
    print("不足，需要补写", target_min - count, "字以上")
elif count > target_max:
    print("超出，需要压缩", count - target_max, "字以上")
else:
    print("字数合格")
```

然后自动决定下一步：

```text
if 不足:
    调用补写 Agent
elif 超出:
    调用压缩 Agent
else:
    进入下一步
```

---

## 9. 最推荐的自动化结构

你可以做成这种目录结构：

```text
novel_project/
  config/
    style.md
    banned_phrases.txt
    sensitive_words.txt
    character_cards.md
    world_bible.md

  outlines/
    novel_outline.json
    volume_01_outline.json
    chapter_001_plan.json

  scenes/
    chapter_001/
      scene_001.json
      scene_002.json
      scene_003.json
      scene_004.json

  drafts/
    chapter_001/
      scene_001.txt
      scene_002.txt
      scene_003.txt
      scene_004.txt
      chapter_001_raw.txt
      chapter_001_merged.txt
      chapter_001_style_clean.txt
      chapter_001_final.txt

  reports/
    chapter_001_wordcount.json
    chapter_001_consistency.json
    chapter_001_sensitivity.json
```

这样每一步都有文件落地，出问题可以回滚。

---

## 10. 不建议所有步骤都用 Agent

有些活应该给脚本：

| 任务 | 推荐方式 |
|---|---|
| 字数统计 | 脚本 |
| 文件合并 | 脚本 |
| 敏感词硬匹配 | 脚本 |
| 章节编号 | 脚本 |
| JSON 校验 | 脚本 |
| 去重检测 | 脚本 |
| 设定一致性判断 | Agent |
| 文风润色 | Agent |
| 剧情拆分 | Agent |
| 人物语气检查 | Agent |

一句话：

**确定性任务交给脚本，审美和语义任务交给 Agent。**

---

## 11. 并行写作的真正难点：共享上下文

多 Agent 并行时，每个 Agent 不能看到其他 Agent 现场写的内容。

所以你要给每个场景提供“前后锚点”。

比如：

```json
{
  "previous_scene_summary": "主角回到出租屋，发现楼道灯坏了，门缝里有一张没有署名的纸条。",
  "current_scene_goal": "主角收到陌生短信，并在镜子中看到异常。",
  "next_scene_setup": "下一场景要让主角尝试开门逃离，但门外传来父亲的声音。",
  "continuity_constraints": [
    "主角此时还不知道异能存在",
    "主角没有报警",
    "出租屋仍然停电",
    "窗外正在下雨"
  ]
}
```

这比把整章扔给它强。

---

## 12. 更高级一点：用“状态表”控制剧情

每写完一个场景，让 Agent 输出正文之外，再输出一个状态更新。

例如：

```json
{
  "scene_id": "001-2",
  "new_facts": [
    "主角收到短信：别回头",
    "镜子里出现一个不是主角的人影"
  ],
  "character_state": {
    "主角": {
      "emotion": "恐惧、怀疑",
      "knowledge": "知道有人在监视自己，但不知道是谁",
      "physical_state": "站在出租屋门口，右手拿着手机"
    }
  },
  "open_hooks": [
    "短信发送者是谁",
    "镜子里的人影是什么",
    "为什么对方知道主角会回头"
  ],
  "closed_hooks": []
}
```

然后后续 Agent 只需要读这个状态，不需要读全部原文。

这就是小说工程化的核心。

---

## 13. 推荐实际流程

你可以按这个流程跑一章：

```text
1. 输入小说设定
2. 大纲 Agent 生成章节计划
3. 分场景 Agent 把章节拆成 3～6 个场景
4. 写作 Agent 并行生成每个场景
5. 脚本统计每个场景字数
6. 不足的场景自动补写
7. 超出的场景自动压缩
8. 脚本合并
9. 接缝修复 Agent 统一章节
10. 一致性检查 Agent 检查设定冲突
11. 风格降噪 Agent 去 AI 味
12. 敏感词脚本扫描
13. 风险审校 Agent 做语义检查
14. 输出终稿
```

---

## 14. 但是别过度 Agent 化

你这个想法很容易走向一个坑：

```text
大纲 Agent
分章 Agent
分场景 Agent
写作 Agent
润色 Agent
去 AI 味 Agent
敏感词 Agent
设定 Agent
读者反馈 Agent
市场分析 Agent
标题 Agent
爽点 Agent
节奏 Agent
……
```

最后 Agent 太多，质量反而下降。

第一版建议只保留 6 个：

```text
1. Planner：大纲/分章/分场景
2. Writer：写正文
3. Expander：补字数
4. Merger：接缝修复
5. StyleEditor：风格降噪
6. Auditor：一致性 + 敏感检查
```

够用了。

---

## 15. 一个最小可行版本

你可以先做最简单的：

```text
输入：章节梗概 + 目标字数

Step 1：把章节拆成 4 个场景
Step 2：每个场景写 500～700 汉字
Step 3：统计总字数
Step 4：不足则补写
Step 5：合并
Step 6：去 AI 味
Step 7：敏感词检查
```

不要一开始就上复杂多 Agent 框架。先把“单章稳定产出”打通。

---

## 16. 关键结论

你的设想可行，而且是正确方向。

但要记住：

```text
不要用提示词强迫模型一次写够 2000 字。
要用拆分、并行、统计、补写、合并来保证字数。
```

真正可靠的方案是：

```text
大纲 Agent 定方向
分场景 Agent 拆任务
写作 Agent 并行生产
脚本统计字数
补写 Agent 修长度
合并 Agent 修接缝
风格 Agent 去模板味
审校 Agent 查风险
```

如果你想做成长篇小说生产系统，核心不是“找最强模型”，而是搭一个**可控流水线**。模型只是工人，真正决定质量的是：设定文档、场景卡、状态表、字数校验、回滚机制和审校流程。

---

# you asked

message time: 2026-05-22 02:16:35

所以我是不是需要一些一直在更新的资产文档，确保人物设定不冲突。如何设计能不冗余，能更高效。

---

# chatgpt response

是的，你需要一套**持续更新的资产文档**，但不能搞成一堆臃肿 Markdown。小说多 Agent 写作最容易死在这里：设定越写越多，Agent 每次读一大坨，结果既浪费上下文，又抓不住重点。

正确做法不是“所有设定写进一个超大 Bible”，而是做成**分层资产库 + 状态表 + 摘要索引**。

核心原则：

```text
长期稳定信息：写进资产文档
短期章节状态：写进状态表
每次写作只喂相关切片
每章结束后再回写更新
```

---

# 一、你确实需要哪些资产文档？

建议分成 7 类，不要更多。

```text
novel_assets/
  00_project_brief.md          # 项目总说明
  01_world_bible.md            # 世界观
  02_character_cards.md        # 人物卡
  03_relationships.md          # 人物关系
  04_timeline.md               # 时间线
  05_style_guide.md            # 文风规范
  06_glossary.md               # 专有名词 / 地名 / 组织 / 道具
  07_continuity_state.json     # 当前连续性状态
```

其中最重要的是：

```text
character_cards.md
timeline.md
continuity_state.json
style_guide.md
```

这四个文件决定小说不会崩。

---

# 二、不要把所有设定都写得很长

人物卡最容易冗余。很多人会写成这样：

```text
林澈，男，24岁，身高181，黑发，眼神冷淡，童年不幸，性格孤僻但内心温柔，喜欢咖啡，讨厌下雨……
```

这类信息太散。Agent 看了也不一定用得上。

更好的结构是“硬事实 + 可变状态 + 写作约束”。

例如：

```markdown
# 林澈

## 1. 硬事实
- 性别：男
- 年龄：24
- 身份：失业程序员
- 居住地：城南旧公寓 703
- 核心能力：可以短暂听见别人即将说出口的话
- 能力限制：不能读取记忆；越疲惫越失控

## 2. 核心动机
- 表层目标：活下去，查清父亲死亡原因
- 深层目标：证明自己不是被抛弃的人

## 3. 性格约束
- 不主动倾诉
- 遇到危险先观察，不会立刻逞英雄
- 讨厌被人安排
- 信任建立很慢

## 4. 说话风格
- 句子短
- 很少解释自己
- 生气时更冷静，不会大吼大叫
- 常用反问，不爱正面回答

## 5. 禁止事项
- 不能突然热血演讲
- 不能轻易相信陌生人
- 不能在前 30 章完全掌控能力
- 不能主动向官方组织求助

## 6. 当前状态
- 最新位置：城南旧公寓 703
- 最新情绪：高度戒备
- 已知信息：知道父亲死亡可能不是意外
- 未知信息：不知道镜中人影来自哪里
- 身体状态：右手受伤，睡眠不足
```

这样写，Agent 才知道怎么用。

---

# 三、资产文档要分成“三层”

你真正需要的是三层结构。

## 第一层：不可随便改的核心设定

这部分叫 **Canon / 正史设定**。

例如：

```text
主角年龄
主角能力限制
父亲死亡真相
世界观规则
组织名称
关键人物关系
主线谜底
```

这些东西不能被写作 Agent 随便改。

可以放在：

```text
world_bible.md
character_cards.md
glossary.md
```

---

## 第二层：当前状态

这部分是会持续变化的。

例如：

```text
主角现在在哪
知道了什么
受了什么伤
和谁决裂了
谁还活着
某个伏笔是否已经揭露
某个道具现在在谁手上
```

这些不要塞进长篇设定文档里，应该放进结构化状态文件。

比如：

```json
{
  "current_chapter": 12,
  "characters": {
    "林澈": {
      "location": "城南旧公寓 703",
      "emotion": "戒备、疲惫",
      "physical_state": ["右手割伤", "连续两晚没睡"],
      "known_facts": [
        "父亲死亡不是普通车祸",
        "短信发送者知道他的行动路线"
      ],
      "unknown_facts": [
        "镜中人影的身份",
        "能力真正来源"
      ],
      "relationships": {
        "许知遥": "暂时合作，但不信任",
        "周砚": "怀疑对方隐瞒关键线索"
      }
    }
  },
  "objects": {
    "黑色录音笔": {
      "holder": "林澈",
      "status": "损坏，但芯片还在",
      "last_seen": "第 11 章结尾"
    }
  },
  "open_threads": [
    {
      "id": "T001",
      "thread": "父亲死亡真相",
      "status": "推进中",
      "last_update": "第 10 章发现车祸现场照片被篡改"
    }
  ]
}
```

这个文件是给 Agent 保持连续性的。

---

## 第三层：写作风格与禁区

这部分不管写哪章都要遵守。

放在：

```text
style_guide.md
```

示例：

```markdown
# 文风规范

## 基本文风
- 冷峻、具体、压迫感强
- 少解释，多动作
- 对话不完整，允许停顿和打断
- 不写散文诗
- 不强行升华

## 禁止表达
- 命运的齿轮
- 空气仿佛凝固
- 他不知道的是
- 从这一刻起
- 内心深处
- 某种难以言说
- 再也回不到从前

## 叙事限制
- 不使用全知视角剧透
- 不提前解释谜底
- 不让人物突然说出作者想说的话
- 每章结尾可以有钩子，但不能每章都“惊天反转”
```

这个文件很重要，因为它能压住 AI 味。

---

# 四、最高效的设计：主档案 + 摘要切片

不要每次都把完整资产文档塞给 Agent。

应该这样：

```text
完整资产文档
  ↓
检索相关内容
  ↓
生成本章上下文包
  ↓
喂给写作 Agent
```

也就是说，每一章开始前，先生成一个 **Chapter Context Pack**。

例如：

```markdown
# Chapter 12 Context Pack

## 本章目标
林澈和许知遥进入废弃诊所，发现父亲生前留下的录音。

## 本章必须使用的设定
- 林澈能力只能听见别人即将说出口的话，不能读心。
- 许知遥知道诊所的位置，但没有告诉林澈原因。
- 黑色录音笔目前在林澈手里，但外壳损坏。

## 相关人物状态
### 林澈
- 疲惫，右手有伤
- 对许知遥不完全信任
- 想确认父亲死亡真相

### 许知遥
- 表面冷静
- 实际知道更多内幕
- 不希望林澈听完整段录音

## 本章禁止
- 不能揭示父亲真正死因
- 不能让林澈完全掌控能力
- 不能出现官方组织
- 不能让许知遥彻底坦白

## 上一章结尾
林澈发现录音笔里的第一段声音，是父亲在死前一天留下的。

## 下一章预期
录音内容引出一个新地名：白塔医院。
```

写作 Agent 只需要读这个，不需要读全书设定。

这是效率关键。

---

# 五、资产文档如何更新？

建议每章结束后跑一个 **State Update Agent**。

它不写正文，只负责抽取变化。

提示词：

```text
你是小说连续性状态维护 Agent。

请阅读本章正文，提取需要写入资产库的变化。

只提取事实，不做文学评价。

输出 JSON：
{
  "chapter_id": "",
  "new_facts": [],
  "character_updates": {},
  "relationship_updates": {},
  "object_updates": {},
  "timeline_updates": [],
  "open_threads_added": [],
  "open_threads_updated": [],
  "open_threads_closed": [],
  "contradictions_found": []
}
```

比如它输出：

```json
{
  "chapter_id": "012",
  "new_facts": [
    "白塔医院首次被提及",
    "林澈父亲生前去过废弃诊所"
  ],
  "character_updates": {
    "林澈": {
      "known_facts_add": [
        "父亲生前调查过白塔医院"
      ],
      "physical_state_add": [
        "右手伤口重新裂开"
      ]
    },
    "许知遥": {
      "known_facts_add": [
        "她早就知道废弃诊所位置"
      ],
      "relationship_to_林澈": "信任下降"
    }
  },
  "object_updates": {
    "黑色录音笔": {
      "holder": "林澈",
      "status": "可播放前半段，后半段损坏"
    }
  },
  "timeline_updates": [
    "父亲死亡前一天曾到废弃诊所"
  ],
  "open_threads_added": [
    "白塔医院与父亲死亡的关系"
  ],
  "open_threads_updated": [
    "父亲死亡真相推进"
  ],
  "open_threads_closed": [],
  "contradictions_found": []
}
```

然后由脚本把这些内容合并进 `continuity_state.json`。

---

# 六、避免冗余的关键：不要重复记录同一事实

坏设计：

```text
character_cards.md 里写一遍主角父亲死了
timeline.md 里写一遍主角父亲死了
world_bible.md 里写一遍主角父亲死了
chapter_context.md 里又写一遍
state.json 里又写一遍
```

久了必冲突。

正确做法是：

```text
硬事实只在一个地方有权威版本
其他地方只引用或摘要
```

比如：

```text
父亲死亡真相 → timeline.md / mystery_threads.json
主角对父亲的认知 → character_state
父亲这个人物设定 → character_cards.md
```

不要混在一起。

---

# 七、建议你采用“单一事实源”规则

每类信息只能有一个权威文件：

| 信息类型 | 权威文件 |
|---|---|
| 人物基本设定 | `character_cards.md` |
| 人物当前状态 | `continuity_state.json` |
| 世界规则 | `world_bible.md` |
| 时间线 | `timeline.md` |
| 伏笔与谜团 | `threads.json` |
| 道具归属 | `continuity_state.json` |
| 文风规则 | `style_guide.md` |
| 专有名词 | `glossary.md` |

这样一旦冲突，你知道该信哪个。

---

# 八、建议用 JSON 管状态，用 Markdown 管设定

不要全用 Markdown。

Markdown 适合人读：

```text
人物设定
世界观
文风规范
剧情理念
```

JSON 适合机器处理：

```text
当前状态
道具归属
伏笔状态
章节进度
字数统计
风险报告
```

推荐结构：

```text
assets/
  world_bible.md
  character_cards.md
  relationships.md
  style_guide.md
  glossary.md

state/
  continuity_state.json
  threads.json
  objects.json
  chapter_index.json
  timeline.json
```

---

# 九、人物设定不要频繁改，人物状态才频繁改

这是很多人搞混的地方。

例如：

```text
林澈不信任别人
```

这是人物设定，稳定。

```text
林澈目前开始部分信任许知遥
```

这是人物状态，会变化。

```text
林澈已经知道父亲死前去过白塔医院
```

这是认知状态，会变化。

三者不能混在一起。

建议人物卡分开写：

```markdown
# 林澈

## 固定设定
- 不轻信别人
- 遇事先观察
- 对父亲死亡有执念

## 可变状态
见：continuity_state.json

## 写作约束
- 不写热血演讲
- 不主动暴露脆弱
- 对话短促
```

人物卡不要天天改。  
天天改的是 `continuity_state.json`。

---

# 十、每章写作前应该生成一个“最小上下文包”

流程应该是：

```text
读取：
- 本章计划
- 相关人物卡
- 当前状态
- 相关伏笔
- 文风规则

生成：
- chapter_context_pack.md

写作 Agent 只读：
- chapter_context_pack.md
- 当前 scene_card.json
```

不要让写作 Agent 读全量资产库。

这样最省上下文，也最不容易跑偏。

---

# 十一、可以加一个“资产压缩 Agent”

长篇写到 50 章以后，状态会变得很大。你需要定期压缩。

比如每 10 章跑一次：

```text
资产压缩 Agent：
1. 删除已经失效的临时状态；
2. 合并重复事实；
3. 把已关闭伏笔移到 archive；
4. 保留主线相关内容；
5. 输出更新后的 state 文件。
```

示例：

```json
{
  "active_threads": [
    {
      "id": "T001",
      "name": "父亲死亡真相",
      "status": "active",
      "importance": "main",
      "summary": "林澈已确认父亲死前调查过白塔医院，但不知道调查对象。"
    }
  ],
  "archived_threads": [
    {
      "id": "T004",
      "name": "陌生快递来源",
      "closed_at": "chapter_009",
      "resolution": "快递由周砚伪装寄出。"
    }
  ]
}
```

不要让已结束的小伏笔一直污染上下文。

---

# 十二、建议你的 Agent 流水线这样设计

```text
1. Planner Agent
   负责大纲、章节计划、场景卡

2. Context Builder Agent
   从资产库提取本章相关设定，生成最小上下文包

3. Writer Agent
   根据场景卡写正文

4. Continuity Checker Agent
   检查正文是否违反资产库

5. State Update Agent
   从正文中抽取状态变化

6. Asset Merger Script
   把状态变化写入 JSON

7. Style Editor Agent
   统一风格，去 AI 味

8. Risk Checker Agent
   检查敏感词和平台风险
```

里面最关键的是：

```text
Context Builder Agent
State Update Agent
Continuity Checker Agent
```

这三个决定长篇能不能稳。

---

# 十三、一个非常实用的文件设计

你可以直接用这个结构：

```text
novel/
  README.md

  assets/
    project_brief.md
    world_bible.md
    character_cards/
      lin_che.md
      xu_zhiyao.md
      zhou_yan.md
    relationships.md
    style_guide.md
    glossary.md

  state/
    continuity_state.json
    timeline.json
    threads.json
    objects.json
    character_state.json

  plans/
    volume_01_plan.md
    chapter_001_plan.json
    chapter_002_plan.json

  contexts/
    chapter_001_context.md
    chapter_002_context.md

  scenes/
    chapter_001/
      scene_001.json
      scene_002.json
      scene_003.json

  drafts/
    chapter_001/
      scene_001.txt
      scene_002.txt
      scene_003.txt
      raw.md
      merged.md
      final.md

  reports/
    chapter_001_continuity_report.json
    chapter_001_state_update.json
    chapter_001_risk_report.json

  archive/
    closed_threads.json
    old_states/
```

这个结构不花哨，但够稳。

---

# 十四、最重要的检查：冲突检测

每章写完后，必须问 Continuity Checker：

```text
你是小说连续性检查 Agent。

请检查正文是否违反以下资产库设定。

检查类型：
1. 人物性格冲突；
2. 人物已知信息冲突；
3. 人物位置冲突；
4. 时间线冲突；
5. 道具归属冲突；
6. 能力规则冲突；
7. 伏笔提前揭露；
8. 称呼错误；
9. 世界观规则错误；
10. 本章禁止事项违规。

输出 JSON：
{
  "pass": true/false,
  "issues": [
    {
      "type": "",
      "severity": "low/medium/high",
      "text": "原文问题片段",
      "why": "为什么冲突",
      "fix": "建议修改"
    }
  ]
}
```

这个比写完后人工翻设定强太多。

---

# 十五、简单结论

你需要资产文档，但不要做成一坨巨型设定集。

最优设计是：

```text
Markdown 存稳定设定
JSON 存动态状态
每章生成最小上下文包
写完后抽取状态更新
定期压缩资产
所有事实只保留一个权威来源
```

真正高效的结构是：

```text
资产库 ≠ 全量喂给模型
资产库 → 检索/筛选 → 本章上下文包 → 场景写作
```

如果一句话概括：

**小说长篇多 Agent 系统的核心不是多 Agent，而是“资产状态管理”。**

没有资产库，多 Agent 会乱编。  
资产库太大，多 Agent 会失焦。  
最好的方案是：**小上下文写作，大资产后台维护。**

---

# you asked

message time: 2026-05-22 02:18:12

那需不需要向量化，查询高效

---

# chatgpt response

需要，但**不要一上来就全量向量化**。

小说资产管理里，向量检索有用，但它不是核心数据库。最稳的方案是：

```text
结构化 JSON / SQLite 做事实源
向量库做语义召回
关键词 / 标签做精确过滤
最后由 Context Builder 组装上下文
```

一句话：

**向量库适合“找相关内容”，不适合“判断事实真伪”。**

---

# 1. 哪些东西需要向量化？

适合向量化的是这些：

```text
历史章节正文
章节摘要
场景摘要
伏笔描述
人物过往行为
对话风格样例
世界观长文档
风格样例
设定说明
```

比如你要写第 37 章，想知道：

```text
主角以前什么时候见过这个戒指？
许知遥之前有没有说过类似的话？
白塔医院相关线索在哪些章出现过？
男二和主角上次冲突发生在哪？
```

这些适合向量检索。

---

# 2. 哪些东西不要只靠向量化？

这些必须结构化存储：

```text
人物当前状态
人物是否死亡
道具当前归属
时间线顺序
伏笔是否关闭
人物已知信息
人物关系状态
能力规则
章节编号
敏感词表
禁用设定
```

比如：

```json
{
  "character": "林澈",
  "alive": true,
  "location": "白塔医院地下二层",
  "knows": ["父亲死前调查过白塔医院"],
  "injuries": ["右手伤口未愈合"],
  "trust": {
    "许知遥": "低",
    "周砚": "敌对"
  }
}
```

这种东西不能靠向量库。  
因为向量检索可能漏召回、召回旧状态、召回相似但错误的段落。

---

# 3. 最推荐架构：三层检索

不要只有向量库。应该是：

```text
第一层：结构化状态库
  - SQLite / JSON
  - 查当前事实、人物状态、道具归属

第二层：关键词 / 标签检索
  - 章节编号、人物名、地名、伏笔 ID
  - 查精确出现位置

第三层：向量检索
  - 查语义相关历史内容
  - 找相似情节、对话、氛围、伏笔
```

写作前生成上下文时：

```text
Context Builder:
1. 从结构化状态库拿硬事实
2. 用关键词查相关章节
3. 用向量查语义相关片段
4. 去重、压缩、排序
5. 生成本章上下文包
```

---

# 4. 最小可用方案

你先不用搞复杂的分布式向量库。

直接用：

```text
SQLite + sqlite-vec
```

或者：

```text
LanceDB
```

就够了。

考虑你本来就在折腾 OpenClaw / 本地 agent / SQLite-vec，最适合你的其实是：

```text
SQLite 存结构化状态
sqlite-vec 存 embedding
同一个项目一个 .sqlite 文件
```

示例结构：

```text
novel_memory.sqlite
  characters
  character_state
  objects
  threads
  timeline
  chapters
  scenes
  embeddings
```

这样比一堆散乱 Markdown 稳。

---

# 5. 推荐数据库表设计

可以这样设计。

## `characters`

存人物固定设定。

```sql
CREATE TABLE characters (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT,
  fixed_profile TEXT,
  speech_style TEXT,
  constraints TEXT
);
```

## `character_state`

存人物当前状态。

```sql
CREATE TABLE character_state (
  character_id TEXT PRIMARY KEY,
  location TEXT,
  emotion TEXT,
  physical_state TEXT,
  known_facts TEXT,
  relationship_state TEXT,
  updated_chapter INTEGER
);
```

## `objects`

存道具归属。

```sql
CREATE TABLE objects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  holder TEXT,
  status TEXT,
  last_seen_chapter INTEGER
);
```

## `threads`

存伏笔和谜团。

```sql
CREATE TABLE threads (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT,
  importance TEXT,
  summary TEXT,
  first_seen_chapter INTEGER,
  last_updated_chapter INTEGER,
  resolution TEXT
);
```

## `chapters`

存章节摘要。

```sql
CREATE TABLE chapters (
  id INTEGER PRIMARY KEY,
  title TEXT,
  summary TEXT,
  word_count INTEGER,
  timeline_position TEXT
);
```

## `scenes`

存场景摘要。

```sql
CREATE TABLE scenes (
  id TEXT PRIMARY KEY,
  chapter_id INTEGER,
  scene_order INTEGER,
  summary TEXT,
  involved_characters TEXT,
  involved_objects TEXT,
  open_threads TEXT,
  text_path TEXT
);
```

---

# 6. 向量化粒度怎么选？

不要把整章直接向量化。太粗。

也不要每句话都向量化。太碎。

最合适的是：

```text
场景级摘要 + 关键片段
```

推荐粒度：

```text
1 个 embedding chunk = 300～800 汉字
```

对于小说系统，最好向量化这几类内容：

```text
scene_summary
scene_full_text_chunk
character_profile
character_speech_samples
thread_summary
world_rule
style_example
```

你可以给每个 chunk 加 metadata：

```json
{
  "chunk_id": "chapter_012_scene_003_summary",
  "type": "scene_summary",
  "chapter": 12,
  "scene": 3,
  "characters": ["林澈", "许知遥"],
  "objects": ["黑色录音笔"],
  "threads": ["T001_父亲死亡真相", "T008_白塔医院"],
  "text": "林澈和许知遥进入废弃诊所，发现父亲留下的录音..."
}
```

查询时先过滤：

```text
角色 = 林澈
伏笔 = 白塔医院
章节 < 当前章节
```

再做向量相似度。

这叫：

```text
metadata filter + vector search
```

比纯向量检索强很多。

---

# 7. 为什么不能只用向量检索？

因为向量检索有几个硬伤。

## 第一，旧信息可能被召回

比如第 5 章：

```text
许知遥不信任林澈。
```

第 18 章：

```text
许知遥开始信任林澈。
```

你在第 30 章查询“许知遥和林澈关系”，向量库可能把第 5 章召回来。

这就会误导 Agent。

所以当前关系必须看结构化状态：

```json
{
  "许知遥_to_林澈": "有限信任，但仍隐瞒白塔医院相关信息"
}
```

## 第二，向量检索不保证完整

你问：

```text
黑色录音笔现在在谁手里？
```

向量库可能没召回最新那章。

但结构化库可以直接查：

```sql
SELECT holder FROM objects WHERE name = '黑色录音笔';
```

## 第三，向量检索不适合做否定判断

比如：

```text
主角有没有向官方组织求助过？
```

向量库没搜到，不代表没有。

这种要靠 timeline / state / event log。

---

# 8. 更好的设计：事件日志 Event Log

长篇小说最应该有一个事件表。

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  chapter_id INTEGER,
  scene_id TEXT,
  event_type TEXT,
  characters TEXT,
  objects TEXT,
  location TEXT,
  summary TEXT,
  consequences TEXT
);
```

例如：

```json
{
  "id": "E012_003",
  "chapter_id": 12,
  "scene_id": "012-003",
  "event_type": "discovery",
  "characters": ["林澈", "许知遥"],
  "objects": ["黑色录音笔"],
  "location": "废弃诊所",
  "summary": "林澈播放录音笔，听到父亲提到白塔医院。",
  "consequences": "林澈知道父亲死前调查过白塔医院。"
}
```

这个非常重要。

之后你查：

```text
白塔医院第一次出现在哪？
谁知道白塔医院？
录音笔经历过哪些事件？
许知遥什么时候开始隐瞒？
```

都可以直接查 events。

---

# 9. 最理想的小说记忆系统

可以这样：

```text
Canonical DB
  ├─ characters
  ├─ character_state
  ├─ objects
  ├─ threads
  ├─ timeline
  ├─ events
  └─ world_rules

Vector Index
  ├─ scene summaries
  ├─ chapter summaries
  ├─ selected prose chunks
  ├─ dialogue samples
  ├─ world descriptions
  └─ style examples

Files
  ├─ full chapter text
  ├─ scene drafts
  ├─ reports
  └─ archived states
```

查询时：

```text
事实问题 → Canonical DB
风格/相似/历史语境 → Vector Index
全文引用/检查 → Files
```

---

# 10. 上下文包生成逻辑

每一章开写前，自动生成：

```text
chapter_037_context.md
```

来源：

```text
1. 本章计划
2. 当前人物状态
3. 当前伏笔状态
4. 当前道具状态
5. 上一章摘要
6. 相关历史事件
7. 向量召回的相似片段
8. 本章禁止事项
9. 文风规则摘要
```

示例：

```markdown
# Chapter 37 Context Pack

## 本章目标
林澈进入白塔医院地下二层，第一次发现父亲当年实验记录。

## 当前硬事实
- 林澈右手伤口尚未恢复。
- 林澈已经知道父亲死前调查过白塔医院。
- 许知遥知道地下二层存在，但没有告诉林澈。
- 黑色录音笔目前在林澈身上，后半段损坏。

## 相关历史事件
- 第 12 章：父亲录音首次提到白塔医院。
- 第 19 章：许知遥阻止林澈接近医院旧档案室。
- 第 24 章：周砚提到“地下二层不存在于建筑图纸”。

## 相关伏笔
- T001 父亲死亡真相：推进中。
- T008 白塔医院：核心谜团，不能在本章完全揭示。
- T014 许知遥隐瞒的原因：可以暗示，不能摊牌。

## 相关文风样例
- 使用冷静、压迫、具体的场景描写。
- 不要宏大抒情。
- 医院场景重点写声音、气味、灯光、空间压迫。

## 本章禁止
- 不要解释能力来源。
- 不要让许知遥完全坦白。
- 不要出现官方组织。
- 不要关闭父亲死亡真相主线。
```

这个上下文包才是喂给写作 Agent 的东西。

---

# 11. 向量化用在哪些查询最值？

非常值的场景：

## 查询历史伏笔

```text
找出和“白塔医院地下二层”语义相关的历史片段。
```

## 查询人物说话风格

```text
找出许知遥过去 5 段重要对话，作为说话风格样例。
```

## 查询相似场景

```text
找出之前写过的医院、地下室、雨夜、追逐场景，避免重复。
```

## 查询情绪递进

```text
找出主角上次情绪崩溃前后的片段，保持心理连续。
```

## 查询设定说明

```text
找出和“能力失控”相关的世界观规则。
```

---

# 12. 查询流程可以这样写

用户/Agent 提出需求：

```text
我要写第 37 章，涉及林澈、许知遥、白塔医院、黑色录音笔。
```

系统执行：

```text
1. SQL 查当前状态：
   - 林澈状态
   - 许知遥状态
   - 黑色录音笔归属
   - 白塔医院伏笔状态

2. SQL 查事件：
   - WHERE characters 包含 林澈/许知遥
   - WHERE objects 包含 黑色录音笔
   - WHERE summary 包含 白塔医院

3. 向量查：
   - query: “白塔医院 地下二层 父亲录音 许知遥隐瞒”
   - filter: chapter < 37
   - top_k: 8

4. 去重和排序：
   - 最近章节优先
   - 核心伏笔优先
   - 高相似度优先
   - 已关闭伏笔降权

5. 生成 Context Pack
```

---

# 13. 向量库选型

对你这种个人小说生产系统：

## 最推荐

```text
SQLite + sqlite-vec
```

优点：

```text
轻量
本地
方便备份
和结构化表放一起
适合 OpenClaw / 本地 Agent
```

## 次推荐

```text
LanceDB
```

优点：

```text
本地向量库体验好
适合文档类检索
比 Chroma 稳一点
```

## 不太建议第一版用

```text
Milvus
Qdrant
Weaviate
Elasticsearch
```

不是不好，而是太重。  
你现在做小说资产管理，没必要一上来搞生产级向量服务。

---

# 14. Embedding 模型怎么选？

中文小说可以用这些思路：

```text
1. 中文/多语言 embedding 模型
2. 支持长文本
3. 成本低
4. 本地或 API 都可以
```

如果你本地跑，优先：

```text
bge-m3
bge-large-zh
jina-embeddings-v3
multilingual-e5
```

如果你用 API，选稳定便宜的 embedding 模型就行。

对小说资产来说，embedding 不是越强越好。  
因为你还有 metadata 和 SQL 兜底。

---

# 15. Chunk 设计比模型更重要

向量检索效果差，通常不是 embedding 模型太差，而是 chunk 做错了。

不要这样：

```text
整章直接 embedding
```

也不要这样：

```text
每 100 字切一段
```

推荐：

```text
场景摘要：一条
场景正文：每 500～800 汉字切一条
人物对话样例：按对话片段切
伏笔：每个伏笔一条
世界规则：每条规则一条
```

每条都带 metadata。

示例：

```json
{
  "id": "C012_S03_chunk_02",
  "type": "prose_chunk",
  "chapter": 12,
  "scene": 3,
  "characters": ["林澈", "许知遥"],
  "location": "废弃诊所",
  "threads": ["T001", "T008"],
  "importance": "high",
  "text": "林澈把录音笔放在桌上……"
}
```

---

# 16. 检索结果还要重排

不要直接把 top_k 全塞给模型。

应该重排：

```text
score = 
  向量相似度
  + 人物匹配加权
  + 伏笔匹配加权
  + 最近章节加权
  + 重要性加权
  - 已关闭伏笔降权
  - 重复内容降权
```

简单点也可以：

```python
final_score = vector_score

if character_matched:
    final_score += 0.15

if thread_matched:
    final_score += 0.2

if importance == "high":
    final_score += 0.1

if status == "closed":
    final_score -= 0.2
```

---

# 17. 你真正需要的是“混合检索”

结论很明确：

```text
只用关键词：漏掉语义相关内容
只用向量：容易召回旧事实和错事实
SQL + keyword + vector：最稳
```

也就是：

```text
Hybrid Retrieval
```

对于小说系统，混合检索比单纯 RAG 更重要。

---

# 18. 实际推荐方案

你可以这样落地：

```text
第一版：
- Markdown 写资产
- JSON 写状态
- Python 脚本生成 Context Pack
- 暂时不用向量

第二版：
- SQLite 管状态
- 章节摘要入库
- scene summary 做向量化

第三版：
- 正文 chunk 向量化
- 对话样例向量化
- 伏笔/世界观向量化
- Context Builder 自动混合检索

第四版：
- 每章结束自动更新状态
- 自动冲突检测
- 自动资产压缩
```

不要第一天就做成复杂 RAG。先跑通流程。

---

# 19. 我的建议

以你的需求，最终应该做向量化。

但第一阶段不要依赖它。

最合理路线：

```text
阶段 1：JSON / SQLite 状态库
阶段 2：章节摘要和场景摘要入库
阶段 3：对摘要做向量化
阶段 4：正文片段和对话样例再向量化
阶段 5：做混合检索生成上下文包
```

最后形态应该是：

```text
权威事实：SQLite / JSON
历史语境：Vector DB
原始正文：Markdown / txt 文件
查询入口：Context Builder Agent
```

最关键一句：

**向量化是“召回器”，不是“记忆本体”。真正的记忆本体应该是结构化状态库。**

---

# you asked

message time: 2026-05-22 02:19:18

结构化一定要json吗，能不能html，ai读直观，人看也直观

---

# chatgpt response

可以用 HTML，但**不建议把 HTML 当唯一结构化数据源**。

更准确地说：

```text
HTML 适合做人机共读界面
JSON / SQLite 适合做机器权威数据
Markdown 适合做人类设定文档
```

你的想法有道理：HTML 对人看很直观，AI 也能读。但问题是，**HTML 不是很适合作为“权威状态库”**，除非你设计得非常规整。

---

# 1. HTML 能不能给 AI 读？

能，而且读得不错。

比如这个 HTML：

```html
<section id="character-lin-che" data-type="character">
  <h2>林澈</h2>

  <table>
    <tr><th>年龄</th><td>24</td></tr>
    <tr><th>身份</th><td>失业程序员</td></tr>
    <tr><th>当前位置</th><td>城南旧公寓 703</td></tr>
    <tr><th>当前状态</th><td>疲惫，右手受伤，高度戒备</td></tr>
  </table>

  <h3>固定设定</h3>
  <ul>
    <li>不轻信别人</li>
    <li>遇到危险先观察</li>
    <li>讨厌被人安排</li>
  </ul>

  <h3>禁止事项</h3>
  <ul>
    <li>不能突然热血演讲</li>
    <li>不能轻易相信陌生人</li>
    <li>不能在前 30 章完全掌控能力</li>
  </ul>
</section>
```

AI 读这个完全没问题，甚至比乱七八糟的 Markdown 更清楚。

但它的问题在于：**程序不好稳定改。**

---

# 2. 为什么不建议只用 HTML？

因为小说资产系统不只是“读”，还要频繁做这些事：

```text
查询人物当前状态
更新人物已知信息
修改道具归属
关闭某个伏笔
检查时间线冲突
统计人物出现次数
按章节筛选事件
生成上下文包
自动合并状态更新
```

这些操作用 JSON / SQLite 很自然。

但用 HTML 就变成：

```text
解析 DOM
找到对应 section
找到 table 里的某个 td
修改文本
防止破坏格式
保存回 HTML
再校验结构没坏
```

不是不能做，而是麻烦，且更容易出错。

尤其你要做自动化 Agent，HTML 作为权威源会有几个问题：

| 问题 | 解释 |
|---|---|
| 更新麻烦 | Agent 或脚本要精准改 DOM |
| 容易混入展示内容 | 样式、注释、说明文字会污染数据 |
| 不适合复杂查询 | 比如“谁知道白塔医院？” |
| 不适合状态合并 | 多 Agent 同时更新时容易冲突 |
| 不适合版本 diff | HTML diff 比 JSON/SQLite 难看 |
| 不适合严格校验 | JSON Schema / SQL 约束更强 |

所以结论不是“HTML 不行”，而是：

**HTML 适合作为展示层，不适合作为唯一事实源。**

---

# 3. 最好的方案：数据和展示分离

我建议你用这种结构：

```text
权威数据：SQLite / JSON
展示界面：HTML 自动生成
AI 输入：Markdown / XML / 简化 HTML 上下文包
```

也就是：

```text
SQLite / JSON
   ↓ 自动渲染
HTML 资产看板
   ↓ 摘要提取
Context Pack
   ↓
写作 Agent
```

这样你既能人看直观，又能机器稳定维护。

---

# 4. 你可以把 HTML 当“资产看板”

比如生成一个：

```text
novel_dashboard.html
```

里面展示：

```text
人物表
当前状态
道具归属
伏笔状态
时间线
章节列表
风险报告
字数统计
```

人打开浏览器就能看。

但真正数据来源仍然是：

```text
novel_state.sqlite
```

或者：

```text
state/*.json
```

这样最好。

---

# 5. 如果你强烈想用 HTML，也要用“语义化 HTML”

不要写成纯视觉网页：

```html
<div class="card">
  <div class="title">林澈</div>
  <div>他现在很累，拿着录音笔。</div>
</div>
```

这对人好看，但对机器不够稳。

应该写成带 `id`、`data-*`、表格、列表的结构：

```html
<article id="char-lin-che" data-entity="character" data-name="林澈">
  <h2>林澈</h2>

  <section data-field="fixed-profile">
    <h3>固定设定</h3>
    <dl>
      <dt>年龄</dt>
      <dd data-key="age">24</dd>

      <dt>身份</dt>
      <dd data-key="role">失业程序员</dd>

      <dt>核心动机</dt>
      <dd data-key="motivation">查清父亲死亡原因</dd>
    </dl>
  </section>

  <section data-field="current-state">
    <h3>当前状态</h3>
    <dl>
      <dt>位置</dt>
      <dd data-key="location">城南旧公寓 703</dd>

      <dt>情绪</dt>
      <dd data-key="emotion">高度戒备，疲惫</dd>

      <dt>身体状态</dt>
      <dd data-key="physical_state">右手受伤，睡眠不足</dd>
    </dl>
  </section>

  <section data-field="known-facts">
    <h3>已知信息</h3>
    <ul>
      <li data-fact-id="K001">父亲死亡可能不是意外</li>
      <li data-fact-id="K002">黑色录音笔与白塔医院有关</li>
    </ul>
  </section>
</article>
```

这种 HTML 才适合作为 AI 可读资产。

---

# 6. 更适合 AI 读的其实是 XML 风格

如果你的目标是“AI 读起来直观”，那 XML/HTML-like 格式比 JSON 更舒服。

比如：

```xml
<character id="lin_che" name="林澈">
  <fixed_profile>
    <age>24</age>
    <role>失业程序员</role>
    <core_motivation>查清父亲死亡原因</core_motivation>
  </fixed_profile>

  <personality_constraints>
    <item>不轻信别人</item>
    <item>遇到危险先观察</item>
    <item>讨厌被人安排</item>
  </personality_constraints>

  <current_state chapter="12">
    <location>城南旧公寓 703</location>
    <emotion>高度戒备，疲惫</emotion>
    <physical_state>右手受伤，睡眠不足</physical_state>
    <known_fact>父亲死亡可能不是意外</known_fact>
  </current_state>

  <writing_rules>
    <rule>对话短促</rule>
    <rule>不能突然热血演讲</rule>
    <rule>不能轻易相信陌生人</rule>
  </writing_rules>
</character>
```

这个对 AI 非常友好。

但是对程序查询来说，还是不如 JSON/SQLite。

---

# 7. JSON 的优势不是“好读”，而是“好控制”

JSON 看着确实不如 HTML 直观：

```json
{
  "id": "lin_che",
  "name": "林澈",
  "age": 24,
  "role": "失业程序员",
  "location": "城南旧公寓 703",
  "emotion": ["高度戒备", "疲惫"]
}
```

但它强在：

```text
容易校验
容易更新
容易 diff
容易被脚本解析
容易转成 HTML
容易转成 Markdown
容易转成上下文包
```

你要做自动化流水线，JSON/SQLite 更像“数据库”，HTML 更像“仪表盘”。

---

# 8. 我的推荐：三种格式各司其职

最实用的组合是：

```text
SQLite / JSON：权威数据
Markdown：人工维护的长设定
HTML：可视化资产看板
XML/Markdown：喂给 Agent 的上下文包
```

具体可以这样：

```text
novel/
  data/
    novel.sqlite
    state.json

  assets/
    world_bible.md
    style_guide.md
    character_notes.md

  dashboard/
    index.html

  contexts/
    chapter_012_context.xml
    chapter_012_context.md
```

---

# 9. 一个非常稳的工作流

```text
1. 你人工改 Markdown 设定
2. Agent/脚本抽取成 JSON/SQLite
3. 每章写完后 Agent 输出 state_update.json
4. 脚本合并进 SQLite/JSON
5. 自动生成 HTML 看板
6. 自动生成本章 Context Pack
7. 写作 Agent 只读 Context Pack
```

这样不会乱。

---

# 10. HTML 可以用于哪些资产？

适合 HTML 的：

```text
人物卡展示
人物关系图
时间线浏览
章节列表
伏笔状态看板
道具归属表
字数统计
风险报告
写作进度
```

不适合只用 HTML 存的：

```text
当前事实源
道具归属源
人物状态源
伏笔状态源
事件日志源
时间线源
敏感词库
```

---

# 11. 如果只做个人轻量系统，可以怎么选？

如果你不想上数据库，第一版可以这样：

```text
assets/
  characters.html
  world.html
  timeline.html
  style.html

state/
  continuity_state.json
  threads.json
  objects.json
```

也就是说：

```text
人物设定可以 HTML
世界观可以 HTML
文风说明可以 HTML
动态状态最好 JSON
```

这个折中很好。

---

# 12. 更好的折中：YAML

你可能会喜欢 YAML，因为它比 JSON 好读：

```yaml
id: lin_che
name: 林澈
age: 24
role: 失业程序员

fixed_profile:
  motivation: 查清父亲死亡原因
  personality:
    - 不轻信别人
    - 遇到危险先观察
    - 讨厌被人安排

current_state:
  chapter: 12
  location: 城南旧公寓 703
  emotion:
    - 高度戒备
    - 疲惫
  physical_state:
    - 右手受伤
    - 睡眠不足

writing_rules:
  - 对话短促
  - 不能突然热血演讲
  - 不能轻易相信陌生人
```

YAML 的优势：

```text
人看舒服
AI 读得懂
脚本也能解析
比 HTML 更适合数据
比 JSON 更适合手写
```

如果你想“人看直观 + AI 读直观 + 还能自动化”，我反而建议你考虑：

```text
YAML 做轻量结构化资产
HTML 做展示
SQLite 做后期升级
```

---

# 13. 最终建议

你的想法可以落地，但我建议这样分：

```text
固定设定：Markdown / YAML / HTML 都可以
动态状态：JSON / YAML / SQLite 更好
展示看板：HTML 最好
喂给 Agent：XML / Markdown 最好
```

如果你现在要做第一版，我建议：

```text
assets/
  character_cards.yaml
  world_bible.md
  style_guide.md

state/
  continuity_state.yaml
  threads.yaml
  objects.yaml
  events.yaml

dashboard/
  index.html  # 自动生成，不手写

contexts/
  chapter_001_context.md
```

最关键的原则：

**不要把“人看的页面”和“机器写入的事实源”混成一个文件。**

HTML 可以让人和 AI 看得舒服，但权威状态最好还是用 YAML/JSON/SQLite。  
你可以把 HTML 做成自动生成的资产仪表盘，这样既直观，又不牺牲自动化稳定性。