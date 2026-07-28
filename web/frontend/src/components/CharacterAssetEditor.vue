<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Plus, Delete, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getState } from '../api'

const props = defineProps<{
  modelValue: string
  showSource?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'save': []
}>()

type CharacterCard = {
  id: string
  name: string
  gender: string
  role: string
  core_motivation: string
  location?: string
  emotion?: string
  physical_state?: string
  personality_constraints: string[]
  speech_style: string[]
  must_not: string[]
}

const characterCards = ref<CharacterCard[]>([])
const activeCharacterId = ref('')

const activeCharacter = computed(() => 
  characterCards.value.find((c) => c.id === activeCharacterId.value) || characterCards.value[0]
)

// Parse YAML format into character items
const parseCharacterCards = (content: string) => {
  const cards: CharacterCard[] = []
  let current: CharacterCard | null = null
  let section: 'personality_constraints' | 'speech_style' | 'must_not' | '' = ''

  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (trimmed.startsWith('- id:')) {
      current = {
        id: trimmed.replace('- id:', '').trim() || `character_${cards.length + 1}`,
        name: '',
        gender: '',
        role: '',
        core_motivation: '',
        location: '',
        emotion: '',
        physical_state: '',
        personality_constraints: [],
        speech_style: [],
        must_not: [],
      }
      cards.push(current)
      section = ''
      continue
    }
    if (!current) continue
    if (trimmed.startsWith('name:')) {
      current.name = trimmed.replace('name:', '').trim()
    } else if (trimmed.startsWith('role:')) {
      current.role = trimmed.replace('role:', '').trim()
    } else if (trimmed.startsWith('gender:')) {
      current.gender = trimmed.replace('gender:', '').trim()
    } else if (trimmed.startsWith('core_motivation:')) {
      current.core_motivation = trimmed.replace('core_motivation:', '').trim()
    } else if (trimmed.startsWith('location:')) {
      current.location = trimmed.replace('location:', '').trim()
    } else if (trimmed.startsWith('emotion:')) {
      current.emotion = trimmed.replace('emotion:', '').trim()
    } else if (trimmed.startsWith('physical_state:')) {
      current.physical_state = trimmed.replace('physical_state:', '').trim()
    } else if (trimmed.startsWith('status:')) {
      // 兼容可能以 status 字段存储的情况
      current.physical_state = trimmed.replace('status:', '').trim()
    } else if (trimmed.startsWith('personality_constraints:')) {
      section = 'personality_constraints'
    } else if (trimmed.startsWith('speech_style:')) {
      section = 'speech_style'
    } else if (trimmed.startsWith('must_not:')) {
      section = 'must_not'
    } else if (trimmed.startsWith('- ') && section) {
      current[section].push(trimmed.replace('- ', '').trim())
    }
  }

  characterCards.value = (cards.length ? cards : [{
    id: 'protagonist',
    name: '主角',
    gender: '未指定',
    role: '待填写',
    core_motivation: '待填写',
    location: '未知',
    emotion: '平静',
    physical_state: '健康',
    personality_constraints: ['遇到危险先观察', '不轻易相信陌生人'],
    speech_style: ['短句', '少解释'],
    must_not: ['不能突然热血演讲'],
  }]).map((c) => ({ ...c, gender: c.gender || '未指定' }))
  if (!activeCharacterId.value || !characterCards.value.some(c => c.id === activeCharacterId.value)) {
    activeCharacterId.value = characterCards.value[0]?.id || ''
  }
}

// Serialize characters to YAML
const serializeCharacterCards = (): string => {
  const lines = ['characters:']
  for (const card of characterCards.value) {
    lines.push(`  - id: ${card.id || 'character'}`)
    lines.push(`    name: ${card.name || '未命名角色'}`)
    lines.push('    fixed_profile:')
    lines.push(`      role: ${card.role || '待填写'}`)
    lines.push(`      gender: ${card.gender || '未指定'}`)
    lines.push(`      core_motivation: ${card.core_motivation || '待填写'}`)
    lines.push('    current_state:')
    lines.push(`      location: ${card.location || '未知'}`)
    lines.push(`      emotion: ${card.emotion || '平静'}`)
    lines.push(`      physical_state: ${card.physical_state || '健康'}`)
    lines.push('    personality_constraints:')
    const constraints = card.personality_constraints.length ? card.personality_constraints : ['待填写']
    for (const item of constraints) lines.push(`      - ${item}`)
    lines.push('    speech_style:')
    const speech = card.speech_style.length ? card.speech_style : ['待填写']
    for (const item of speech) lines.push(`      - ${item}`)
    lines.push('    must_not:')
    const mustNot = card.must_not.length ? card.must_not : ['待填写']
    for (const item of mustNot) lines.push(`      - ${item}`)
    lines.push('')
  }
  return lines.join('\n').trim() + '\n'
}

const syncToText = () => {
  emit('update:modelValue', serializeCharacterCards())
}

watch(() => props.modelValue, (newVal) => {
  const curYaml = serializeCharacterCards()
  if (newVal !== curYaml) {
    parseCharacterCards(newVal)
  }
}, { immediate: true })

const updateCharacterId = (card: CharacterCard, val: string) => {
  const oldId = card.id
  const cleanId = val.trim()
  if (!cleanId) return
  card.id = cleanId
  if (activeCharacterId.value === oldId) {
    activeCharacterId.value = cleanId
  }
  syncToText()
}

const addCharacter = () => {
  const next = characterCards.value.length + 1
  const card: CharacterCard = {
    id: `character_${next}`,
    name: `新角色${next}`,
    gender: '未指定',
    role: '待填写',
    core_motivation: '待填写',
    location: '未知',
    emotion: '平静',
    physical_state: '健康',
    personality_constraints: [],
    speech_style: [],
    must_not: [],
  }
  characterCards.value.push(card)
  activeCharacterId.value = card.id
  syncToText()
}

const removeCharacter = (id: string) => {
  if (characterCards.value.length <= 1) {
    ElMessage.warning('至少保留一个角色')
    return
  }
  characterCards.value = characterCards.value.filter((item) => item.id !== id)
  if (activeCharacterId.value === id) {
    activeCharacterId.value = characterCards.value[0]?.id || ''
  }
  syncToText()
}

const syncFromPlotState = async () => {
  try {
    const { data } = await getState()
    const dbCharacters = data.characters || {}
    let updatedCount = 0
    let addedCount = 0

    // 检测当前资产中是否含有未修改过的初始占位“主角”
    const hasPlaceholder = characterCards.value.some(
      c => c.id === 'protagonist' && c.name === '主角' && c.role === '待填写'
    )

    for (const [id, state] of Object.entries(dbCharacters)) {
      const dbChar = state as any
      // 根据 ID 匹配，或者根据名字匹配
      const existing = characterCards.value.find(c => c.id === id || c.name === dbChar.name)
      
      if (existing) {
        if (dbChar.gender) existing.gender = dbChar.gender
        existing.location = dbChar.location || existing.location || '未知'
        existing.emotion = dbChar.emotion || existing.emotion || '平静'
        existing.physical_state = dbChar.physical_state || dbChar.status || existing.physical_state || '健康'
        updatedCount++
      } else {
        characterCards.value.push({
          id: id,
          name: dbChar.name || id,
          gender: dbChar.gender || '未指定',
          role: dbChar.role || '新出场角色',
          core_motivation: dbChar.core_motivation || '待填写',
          location: dbChar.location || '未知',
          emotion: dbChar.emotion || '平静',
          physical_state: dbChar.physical_state || dbChar.status || '健康',
          personality_constraints: [],
          speech_style: [],
          must_not: []
        })
        addedCount++
      }
    }

    // 如果从剧情中成功同步到了任何角色，并且之前含有占位主角，则自动清理占位主角
    if (hasPlaceholder && Object.keys(dbCharacters).length > 0) {
      characterCards.value = characterCards.value.filter(
        c => !(c.id === 'protagonist' && c.name === '主角' && c.role === '待填写')
      )
      // 如果删除的占位主角是当前选中的，切换至第一个新同步的角色
      if (activeCharacterId.value === 'protagonist') {
        activeCharacterId.value = characterCards.value[0]?.id || ''
      }
    }

    if (updatedCount > 0 || addedCount > 0) {
      syncToText()
      ElMessage.success(`同步成功：已更新 ${updatedCount} 个角色状态，新增了 ${addedCount} 个剧情人物。`)
    } else {
      ElMessage.info('剧情中人物状态与当前资产一致，无需更新。')
    }
  } catch (err: any) {
    ElMessage.error(err.message || '从剧情状态同步失败，请确保生成过章节。')
  }
}

// Tag input handlers
const tagInputs = ref({
  personality_constraints: '',
  speech_style: '',
  must_not: ''
})

const handleAddTag = (card: CharacterCard, field: 'personality_constraints' | 'speech_style' | 'must_not') => {
  const val = tagInputs.value[field].trim()
  if (!val) return
  if (card[field].includes(val)) {
    ElMessage.warning('该标签已存在')
    return
  }
  card[field].push(val)
  tagInputs.value[field] = ''
  syncToText()
}

const handleRemoveTag = (card: CharacterCard, field: 'personality_constraints' | 'speech_style' | 'must_not', idx: number) => {
  card[field].splice(idx, 1)
  syncToText()
}

</script>

<template>
  <div class="character-workspace" :class="{ 'no-preview': !showSource }">
    <aside class="character-list">
      <div class="character-list-head">
        <strong>角色列表</strong>
        <div class="head-actions">
          <el-button size="small" :icon="Refresh" title="从剧情状态同步" circle @click="syncFromPlotState" />
          <el-button size="small" type="primary" :icon="Plus" title="新增角色" circle @click="addCharacter" />
        </div>
      </div>
      <div class="list-rows">
        <button
          v-for="card in characterCards"
          :key="card.id"
          class="character-row"
          :class="{ active: activeCharacterId === card.id }"
          @click="activeCharacterId = card.id"
        >
          <div class="char-avatar-badge">{{ card.name ? card.name.substring(0, 1) : '?' }}</div>
          <div class="char-meta">
            <span class="char-name">{{ card.name || card.id }}</span>
            <small class="char-role">{{ card.role || '待填写' }}</small>
          </div>
        </button>
      </div>
    </aside>

    <main class="character-editor-pane" v-if="activeCharacter">
      <div class="character-editor-head">
        <div>
          <span class="subtitle">角色设定卡</span>
          <h3>{{ activeCharacter.name || '未命名角色' }}</h3>
        </div>
        <div class="head-btn-group">
          <el-button text type="danger" :icon="Delete" @click="removeCharacter(activeCharacter.id)">删除</el-button>
        </div>
      </div>

      <div class="character-form">
        <div class="form-row split">
          <label class="form-field">
            <span>角色标识 (ID)</span>
            <el-input :model-value="activeCharacter.id" @input="updateCharacterId(activeCharacter, $event)" placeholder="例如: protagonist" />
          </label>
          <label class="form-field">
            <span>角色姓名</span>
            <el-input v-model="activeCharacter.name" @input="syncToText" placeholder="例如: 萧炎" />
          </label>
        </div>

        <div class="form-row split">
          <label class="form-field">
            <span>性别</span>
            <el-select
              v-model="activeCharacter.gender"
              placeholder="选择性别"
              style="width: 100%"
              @change="syncToText"
            >
              <el-option label="男" value="男" />
              <el-option label="女" value="女" />
              <el-option label="其他 / 未指定" value="未指定" />
            </el-select>
          </label>
          <label class="form-field">
            <span>定位 (Role)</span>
            <el-input v-model="activeCharacter.role" @input="syncToText" placeholder="主角 / 配角 / 幕后黑手" />
          </label>
          <label class="form-field">
            <span>核心动机</span>
            <el-input v-model="activeCharacter.core_motivation" @input="syncToText" placeholder="核心驱动力，如：洗刷家族耻辱" />
          </label>
        </div>

        <div class="form-row split">
          <label class="form-field">
            <span>当前位置 (Location)</span>
            <el-input v-model="activeCharacter.location" @input="syncToText" placeholder="未知（从剧情同步）" />
          </label>
          <label class="form-field">
            <span>当前情绪 (Emotion)</span>
            <el-input v-model="activeCharacter.emotion" @input="syncToText" placeholder="平静（从剧情同步）" />
          </label>
          <label class="form-field">
            <span>身体/能力状态</span>
            <el-input v-model="activeCharacter.physical_state" @input="syncToText" placeholder="健康（从剧情同步）" />
          </label>
        </div>

        <!-- Personality Constraints Tag Editor -->
        <div class="form-row full">
          <div class="form-field">
            <span>性格约束</span>
            <div class="tags-editor-box">
              <el-tag
                v-for="(tag, idx) in activeCharacter.personality_constraints"
                :key="idx"
                closable
                class="edit-tag"
                @close="handleRemoveTag(activeCharacter, 'personality_constraints', idx)"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-model="tagInputs.personality_constraints"
                placeholder="+ 添加性格特征 (回车确认)"
                size="small"
                class="new-tag-input"
                @keyup.enter="handleAddTag(activeCharacter, 'personality_constraints')"
                @blur="handleAddTag(activeCharacter, 'personality_constraints')"
              />
            </div>
          </div>
        </div>

        <!-- Speech Style Tag Editor -->
        <div class="form-row full">
          <div class="form-field">
            <span>说话风格</span>
            <div class="tags-editor-box">
              <el-tag
                v-for="(tag, idx) in activeCharacter.speech_style"
                :key="idx"
                closable
                class="edit-tag"
                @close="handleRemoveTag(activeCharacter, 'speech_style', idx)"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-model="tagInputs.speech_style"
                placeholder="+ 添加说话特征 (回车确认)"
                size="small"
                class="new-tag-input"
                @keyup.enter="handleAddTag(activeCharacter, 'speech_style')"
                @blur="handleAddTag(activeCharacter, 'speech_style')"
              />
            </div>
          </div>
        </div>

        <!-- Must Not Tag Editor -->
        <div class="form-row full">
          <div class="form-field">
            <span>禁止事项</span>
            <div class="tags-editor-box">
              <el-tag
                v-for="(tag, idx) in activeCharacter.must_not"
                :key="idx"
                closable
                type="danger"
                class="edit-tag"
                @close="handleRemoveTag(activeCharacter, 'must_not', idx)"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-model="tagInputs.must_not"
                placeholder="+ 添加禁止事项 (回车确认)"
                size="small"
                class="new-tag-input"
                @keyup.enter="handleAddTag(activeCharacter, 'must_not')"
                @blur="handleAddTag(activeCharacter, 'must_not')"
              />
            </div>
          </div>
        </div>
      </div>
    </main>

    <aside class="yaml-preview-pane" v-if="showSource">
      <div class="pane-header">YAML 数据实时预览</div>
      <pre class="yaml-code"><code>{{ modelValue }}</code></pre>
    </aside>
  </div>
</template>

<style scoped>
.character-workspace {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr) 240px;
  background: #fbfcfe;
  min-height: 500px;
  height: 100%;
  transition: grid-template-columns 0.3s ease;
}

.character-workspace.no-preview {
  grid-template-columns: 190px minmax(0, 1fr);
}

.head-btn-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.character-list {
  border-right: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
}

.character-list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.head-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.character-list-head strong {
  font-size: 14px;
  color: var(--color-text);
}

.list-rows {
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.character-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  width: 100%;
  transition: all 0.2s ease;
}

.character-row:hover {
  background: var(--color-bg-hover);
}

.character-row.active {
  background: var(--color-border);
  border-color: var(--color-border);
}

.char-avatar-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #c66f4f, var(--color-warning));
  color: var(--color-bg-surface);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 14px;
}

.char-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.char-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.char-role {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.character-editor-pane {
  padding: 24px;
  background: var(--color-bg-surface);
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.character-editor-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid var(--color-bg-hover);
  padding-bottom: 14px;
}

.subtitle {
  font-size: 12px;
  font-weight: 800;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

.character-editor-head h3 {
  margin: 4px 0 0;
  font-size: 22px;
  color: var(--color-text-strong);
}

.character-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 16px;
}

.form-row.full {
  grid-template-columns: 1fr;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field span {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-muted);
}

.tags-editor-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-surface-muted);
  min-height: 50px;
  align-items: center;
}

.edit-tag {
  font-size: 12px;
  padding: 4px 8px;
  height: auto;
}

.new-tag-input {
  width: 150px !important;
}

.new-tag-input :deep(.el-input__inner) {
  height: 24px;
  font-size: 11px;
}

.yaml-preview-pane {
  border-left: 1px solid var(--color-border-subtle);
  background: var(--color-text-strong);
  color: var(--color-text-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.yaml-preview-pane .pane-header {
  padding: 12px 16px;
  background: var(--color-text-strong);
  color: var(--color-border);
  font-size: 12px;
  font-weight: 700;
  border-bottom: 1px solid var(--color-text-strong);
}

.yaml-code {
  margin: 0;
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  font-family: "Cascadia Mono", Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
