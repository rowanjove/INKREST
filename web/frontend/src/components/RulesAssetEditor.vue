<script setup lang="ts">
import { ref, watch } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'save': []
}>()

type RuleItem = {
  content: string
  description: string
}

type RulesData = {
  commonWords: RuleItem[]
  commonSentences: RuleItem[]
  forbiddenWords: RuleItem[]
  forbiddenSentences: RuleItem[]
  writingTechniques: string
  referenceAuthors: string[]
}

const activeTab = ref('forbidden_words')
const rulesData = ref<RulesData>({
  commonWords: [],
  commonSentences: [],
  forbiddenWords: [],
  forbiddenSentences: [],
  writingTechniques: '',
  referenceAuthors: []
})

// Parser for rules.yaml
const parseRules = (content: string): RulesData => {
  const result: RulesData = {
    commonWords: [],
    commonSentences: [],
    forbiddenWords: [],
    forbiddenSentences: [],
    writingTechniques: '',
    referenceAuthors: []
  }

  const lines = content.split(/\r?\n/)
  let currentKey: 'commonWords' | 'commonSentences' | 'forbiddenWords' | 'forbiddenSentences' | 'writingTechniques' | 'referenceAuthors' | null = null
  let currentItem: RuleItem | null = null
  let isBlockString = false
  let blockStringLines: string[] = []

  for (let line of lines) {
    const trimmed = line.trim()
    
    if (isBlockString) {
      if (line.length > 0 && !line.startsWith(' ') && line.includes(':')) {
        isBlockString = false
        if (currentKey) {
          result[currentKey] = blockStringLines.join('\n') as any
        }
        blockStringLines = []
      } else {
        const contentLine = line.startsWith('  ') ? line.substring(2) : line.trim()
        blockStringLines.push(contentLine)
        continue
      }
    }

    if (trimmed.startsWith('commonWords:')) {
      currentKey = 'commonWords'
      if (trimmed.endsWith('[]')) {
        result.commonWords = []
        currentKey = null
      }
    } else if (trimmed.startsWith('commonSentences:')) {
      currentKey = 'commonSentences'
      if (trimmed.endsWith('[]')) {
        result.commonSentences = []
        currentKey = null
      }
    } else if (trimmed.startsWith('forbiddenWords:')) {
      currentKey = 'forbiddenWords'
      if (trimmed.endsWith('[]')) {
        result.forbiddenWords = []
        currentKey = null
      }
    } else if (trimmed.startsWith('forbiddenSentences:')) {
      currentKey = 'forbiddenSentences'
      if (trimmed.endsWith('[]')) {
        result.forbiddenSentences = []
        currentKey = null
      }
    } else if (trimmed.startsWith('referenceAuthors:')) {
      currentKey = 'referenceAuthors'
      if (trimmed.endsWith('[]')) {
        result.referenceAuthors = []
        currentKey = null
      }
    } else if (trimmed.startsWith('writingTechniques:')) {
      currentKey = 'writingTechniques'
      if (trimmed.endsWith('|')) {
        isBlockString = true
        blockStringLines = []
      }
    } else if (currentKey && ['commonWords', 'commonSentences', 'forbiddenWords', 'forbiddenSentences'].includes(currentKey)) {
      if (trimmed.startsWith('- content:')) {
        if (currentItem) {
          ;(result[currentKey] as RuleItem[]).push(currentItem)
        }
        currentItem = {
          content: trimmed.substring('- content:'.length).trim(),
          description: ''
        }
      } else if (trimmed.startsWith('content:')) {
        if (currentItem) {
          ;(result[currentKey] as RuleItem[]).push(currentItem)
        }
        currentItem = {
          content: trimmed.substring('content:'.length).trim(),
          description: ''
        }
      } else if (trimmed.startsWith('description:')) {
        if (currentItem) {
          currentItem.description = trimmed.substring('description:'.length).trim()
        }
      } else if (trimmed.startsWith('- ')) {
        if (currentItem) {
          ;(result[currentKey] as RuleItem[]).push(currentItem)
          currentItem = null
        }
        const val = trimmed.substring(2).trim()
        ;(result[currentKey] as RuleItem[]).push({ content: val, description: '' })
      }
    } else if (currentKey === 'referenceAuthors') {
      if (trimmed.startsWith('- ')) {
        result.referenceAuthors.push(trimmed.substring(2).trim())
      }
    }
  }

  if (currentItem && currentKey && ['commonWords', 'commonSentences', 'forbiddenWords', 'forbiddenSentences'].includes(currentKey)) {
    ;(result[currentKey] as RuleItem[]).push(currentItem)
  }

  if (isBlockString && currentKey === 'writingTechniques') {
    result.writingTechniques = blockStringLines.join('\n')
  }

  return result
}

// Serializer to YAML
const serializeRules = (data: RulesData): string => {
  const lines: string[] = []

  const writeList = (key: 'commonWords' | 'commonSentences' | 'forbiddenWords' | 'forbiddenSentences') => {
    const list = data[key]
    if (!list || !list.length) {
      lines.push(`${key}: []`)
    } else {
      lines.push(`${key}:`)
      for (const item of list) {
        lines.push(`  - content: ${item.content}`)
        lines.push(`    description: ${item.description || ''}`)
      }
    }
  }

  writeList('commonWords')
  writeList('commonSentences')
  writeList('forbiddenWords')
  writeList('forbiddenSentences')

  if (data.writingTechniques) {
    lines.push('writingTechniques: |')
    const techLines = data.writingTechniques.split('\n')
    for (const line of techLines) {
      lines.push(`  ${line}`)
    }
  } else {
    lines.push('writingTechniques: ""')
  }

  if (data.referenceAuthors && data.referenceAuthors.length) {
    lines.push('referenceAuthors:')
    for (const author of data.referenceAuthors) {
      lines.push(`  - ${author}`)
    }
  } else {
    lines.push('referenceAuthors: []')
  }

  return lines.join('\n').trim() + '\n'
}

const syncToText = () => {
  const yaml = serializeRules(rulesData.value)
  emit('update:modelValue', yaml)
}

watch(() => props.modelValue, (newVal) => {
  // Prevent parsing cycle if content matches serialized value
  const curYaml = serializeRules(rulesData.value)
  if (newVal !== curYaml) {
    rulesData.value = parseRules(newVal)
  }
}, { immediate: true })

type DraftKey =
  | 'forbidden_words'
  | 'forbidden_sentences'
  | 'common_words'
  | 'common_sentences'
  | 'authors'

const drafts = ref<Record<DraftKey, { content: string; desc: string }>>({
  forbidden_words: { content: '', desc: '' },
  forbidden_sentences: { content: '', desc: '' },
  common_words: { content: '', desc: '' },
  common_sentences: { content: '', desc: '' },
  authors: { content: '', desc: '' },
})

const draftFor = (key: DraftKey) => drafts.value[key]

const clearDraft = (key: DraftKey) => {
  drafts.value[key] = { content: '', desc: '' }
}

const addItem = (key: 'commonWords' | 'commonSentences' | 'forbiddenWords' | 'forbiddenSentences', draftKey: DraftKey) => {
  const d = draftFor(draftKey)
  if (!d.content.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  rulesData.value[key].push({
    content: d.content.trim(),
    description: d.desc.trim(),
  })
  clearDraft(draftKey)
  syncToText()
  ElMessage.success('已添加')
}

const removeItem = (key: 'commonWords' | 'commonSentences' | 'forbiddenWords' | 'forbiddenSentences', index: number) => {
  rulesData.value[key].splice(index, 1)
  syncToText()
}

const addAuthor = () => {
  const name = draftFor('authors').content.trim()
  if (!name) return
  if (rulesData.value.referenceAuthors.includes(name)) {
    ElMessage.warning('该对标已存在')
    return
  }
  rulesData.value.referenceAuthors.push(name)
  clearDraft('authors')
  syncToText()
}

const removeAuthor = (index: number) => {
  rulesData.value.referenceAuthors.splice(index, 1)
  syncToText()
}
</script>

<template>
  <div class="rules-workspace">
    <el-tabs v-model="activeTab" class="rules-tabs">
      <el-tab-pane label="禁用词" name="forbidden_words">
        <div class="tab-content">
          <p class="pane-tip">写入提示词，引导模型避免 AI 腔套话；与敏感词库硬扫描互补。</p>
          <div class="inline-add-form">
            <el-input v-model="drafts.forbidden_words.content" placeholder="禁用词，如：命运的齿轮" class="input-content" />
            <el-input v-model="drafts.forbidden_words.desc" placeholder="原因或替代写法（可选）" class="input-desc" />
            <el-button type="primary" :icon="Plus" @click="addItem('forbiddenWords', 'forbidden_words')">添加</el-button>
          </div>

          <div class="rules-grid" v-if="rulesData.forbiddenWords.length">
            <div v-for="(item, idx) in rulesData.forbiddenWords" :key="idx" class="rule-card danger">
              <div class="card-main">
                <span class="rule-content">{{ item.content }}</span>
                <p class="rule-desc">{{ item.description || '无具体说明' }}</p>
              </div>
              <el-button class="delete-btn" type="danger" link :icon="Delete" @click="removeItem('forbiddenWords', idx)" />
            </div>
          </div>
          <el-empty v-else description="暂无禁用词，在上方添加" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="禁用句式" name="forbidden_sentences">
        <div class="tab-content">
          <p class="pane-tip">整句模板、剧透式旁白等，比单词更易破坏沉浸感。</p>
          <div class="inline-add-form">
            <el-input v-model="drafts.forbidden_sentences.content" placeholder="禁用句式，如：他不知道的是" class="input-content" />
            <el-input v-model="drafts.forbidden_sentences.desc" placeholder="说明原因（可选）" class="input-desc" />
            <el-button type="primary" :icon="Plus" @click="addItem('forbiddenSentences', 'forbidden_sentences')">添加</el-button>
          </div>

          <div class="rules-grid" v-if="rulesData.forbiddenSentences.length">
            <div v-for="(item, idx) in rulesData.forbiddenSentences" :key="idx" class="rule-card danger">
              <div class="card-main">
                <span class="rule-content">{{ item.content }}</span>
                <p class="rule-desc">{{ item.description || '无具体说明' }}</p>
              </div>
              <el-button class="delete-btn" type="danger" link :icon="Delete" @click="removeItem('forbiddenSentences', idx)" />
            </div>
          </div>
          <el-empty v-else description="暂无禁用句式，在上方添加" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="常用表达" name="common_expressions">
        <div class="tab-content group-panes">
          <p class="pane-tip full-width">鼓励使用的词汇/句式；可标注使用场景，避免模型过度重复同一表达。</p>
          <div class="pane-column">
            <h3>常用词汇</h3>
            <div class="inline-add-form mini">
              <el-input v-model="drafts.common_words.content" placeholder="常用词" />
              <el-button type="primary" :icon="Plus" @click="addItem('commonWords', 'common_words')">添加</el-button>
            </div>
            <div class="rules-list" v-if="rulesData.commonWords.length">
              <div v-for="(item, idx) in rulesData.commonWords" :key="idx" class="rule-list-item">
                <span>{{ item.content }}</span>
                <el-button type="danger" link :icon="Delete" @click="removeItem('commonWords', idx)" />
              </div>
            </div>
            <el-empty v-else :image-size="60" description="暂无数据" />
          </div>

          <div class="pane-column">
            <h3>常用句式</h3>
            <div class="inline-add-form mini">
              <el-input v-model="drafts.common_sentences.content" placeholder="常用句式" />
              <el-button type="primary" :icon="Plus" @click="addItem('commonSentences', 'common_sentences')">添加</el-button>
            </div>
            <div class="rules-list" v-if="rulesData.commonSentences.length">
              <div v-for="(item, idx) in rulesData.commonSentences" :key="idx" class="rule-list-item">
                <span>{{ item.content }}</span>
                <el-button type="danger" link :icon="Delete" @click="removeItem('commonSentences', idx)" />
              </div>
            </div>
            <el-empty v-else :image-size="60" description="暂无数据" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="写作手法" name="techniques">
        <div class="tab-content flex-column">
          <p class="pane-tip">每条一行，会写入「写作手法」提示段落；保存后下一章生效。</p>
          <el-input
            v-model="rulesData.writingTechniques"
            type="textarea"
            :rows="12"
            class="techniques-textarea"
            placeholder="- 用具体动作、物体、声音、气味、停顿推动画面。"
            @input="syncToText"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="对标作者" name="authors">
        <div class="tab-content flex-column">
          <p class="pane-tip">
            填写作者或作品名（如「金庸」「诡秘之主」）。会进入写作提示词，用于借鉴叙事节奏与类型语感，不会照抄剧情。
          </p>
          <div class="inline-add-form">
            <el-input
              v-model="drafts.authors.content"
              placeholder="作者或作品名"
              @keyup.enter="addAuthor"
            />
            <el-button type="primary" :icon="Plus" @click="addAuthor">添加对标</el-button>
          </div>

          <div class="authors-tags">
            <el-tag
              v-for="(author, idx) in rulesData.referenceAuthors"
              :key="idx"
              closable
              type="info"
              effect="light"
              class="author-tag"
              @close="removeAuthor(idx)"
            >
              {{ author }}
            </el-tag>
            <div v-if="!rulesData.referenceAuthors.length" class="empty-hint">暂无对标，添加后保存写作规范即可生效</div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.rules-workspace {
  background: var(--color-bg-surface);
  padding: 16px;
  min-height: 500px;
}

.rules-tabs :deep(.el-tabs__item) {
  font-weight: 700;
  font-size: 14px;
}

.tab-content {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pane-tip {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.pane-tip.full-width {
  grid-column: 1 / -1;
  width: 100%;
}

.inline-add-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  background: var(--color-bg-surface-muted);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.inline-add-form :deep(.el-input) {
  flex: 1;
  min-width: 120px;
}

.inline-add-form.mini {
  padding: 8px;
}

.input-content {
  flex: 2;
}

.input-desc {
  flex: 3;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.rule-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  transition: all 0.25s ease;
}

.rule-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.rule-card.danger {
  border-left: 4px solid var(--color-danger);
}

.card-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.rule-content {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.rule-desc {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.delete-btn {
  margin-left: 10px;
}

.group-panes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.pane-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pane-column h3 {
  margin: 0;
  font-size: 15px;
  color: var(--color-text);
  border-bottom: 2px solid var(--color-bg-hover);
  padding-bottom: 8px;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-bg-hover);
  border-radius: 6px;
  font-size: 14px;
  color: var(--color-text-strong);
}

.flex-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pane-header-tip {
  font-size: 13px;
  color: var(--color-text-muted);
}

.techniques-textarea :deep(.el-textarea__inner) {
  font-family: "Cascadia Mono", Consolas, Monaco, monospace;
  font-size: 14px;
  line-height: 1.6;
  padding: 14px;
}

.authors-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 16px;
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-bg-hover);
  border-radius: 8px;
  min-height: 80px;
  align-content: flex-start;
}

.author-tag {
  font-size: 13px;
  padding: 6px 10px;
  height: auto;
}

.empty-hint {
  color: var(--color-text-subtle);
  font-size: 13px;
  display: flex;
  align-items: center;
  width: 100%;
  height: 50px;
  justify-content: center;
}
</style>
