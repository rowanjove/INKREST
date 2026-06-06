<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ChatDotRound, Check, Edit, MagicStick } from '@element-plus/icons-vue'
import { novelChatIntro, novelChatStep } from '../api'
import PresetSelector from './PresetSelector.vue'
import type { Composition } from '../types/preset'
import { AI_SCALE_OPTIONS, longFormScaleHint, targetChaptersInputMax } from '../constants/scaleOptions'

const emit = defineEmits<{
  (e: 'complete', data: {
    name: string
    description: string
    genre: string
    context: Record<string, unknown>
  }): void
}>()

defineProps<{ modelLabel?: string }>()

interface ChatMessage {
  role: 'ai' | 'user'
  content: string
}

const baseLabels = ['创意种子', '读者期待', '主角引擎', '冲突舞台', '连载发动机', '定稿建档']
const deepLabels = ['角色关系网', '成长变化', '分卷骨架', '关键转折']
const messages = ref<ChatMessage[]>([])
const userInput = ref('')
const currentStep = ref(1)
const context = ref<Record<string, any>>({})
const loading = ref(false)
const suggestions = ref<string[]>([])
const editableCard = ref<Record<string, any> | null>(null)
const chatContainer = ref<HTMLElement | null>(null)
const composition = ref<Composition | null>(null)
const selectedScale = ref('long')
const scaleConfig = ref({ target_chapters: 200, target_chars: [2000, 3000] as [number, number] })
const scaleOptions = AI_SCALE_OPTIONS
/** 默认完整引导；开启后定稿时直接建档，跳过深度规划 7–10 步 */
const skipDeepPlanning = ref(false)
const chaptersMax = computed(() => targetChaptersInputMax(selectedScale.value))
const scaleHint = computed(() => longFormScaleHint(selectedScale.value))

const isDeepPlanning = computed(() => currentStep.value >= 7)
const labels = computed(() => isDeepPlanning.value ? deepLabels : baseLabels)
const visibleStepIndex = computed(() => isDeepPlanning.value ? currentStep.value - 7 : currentStep.value - 1)
const progressWidth = computed(() => {
  const denominator = Math.max(labels.value.length - 1, 1)
  return `${Math.min(visibleStepIndex.value / denominator, 1) * 100}%`
})
const showFinalize = computed(() => currentStep.value === 6 && Boolean(editableCard.value))

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}

onMounted(async () => {
  try {
    const { data } = await novelChatIntro(1)
    messages.value.push({ role: 'ai', content: data.ai_message })
    suggestions.value = data.suggestions || []
  } catch {
    messages.value.push({ role: 'ai', content: '你好，我会陪你把灵感整理成可以动笔的作品蓝图。先说说你想写什么故事？' })
  }
})

const applyResponse = (data: any) => {
  context.value = data.context || context.value
  currentStep.value = data.step || currentStep.value
  suggestions.value = data.suggestions || []
  if (data.card) editableCard.value = { ...data.card }
  if (data.ai_message) messages.value.push({ role: 'ai', content: data.ai_message })
}

const sendMessage = async (text?: string) => {
  const input = (text || userInput.value).trim()
  if (!input || loading.value || showFinalize.value) return
  messages.value.push({ role: 'user', content: input })
  userInput.value = ''
  suggestions.value = []
  loading.value = true
  await scrollToBottom()
  try {
    const { data } = await novelChatStep({ step: currentStep.value, user_input: input, context: context.value })
    applyResponse(data)
  } catch (err: any) {
    messages.value.push({ role: 'ai', content: `AI 暂时没有回应，请重试。\n\n${err?.response?.data?.detail || err.message || '未知错误'}` })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const selectScale = (option: (typeof scaleOptions)[number]) => {
  selectedScale.value = option.scale
  scaleConfig.value.target_chapters = option.target_chapters
  if (scaleConfig.value.target_chapters > targetChaptersInputMax(option.scale)) {
    scaleConfig.value.target_chapters = targetChaptersInputMax(option.scale)
  }
}

const finalize = async (action: 'create' | 'deep') => {
  if (!editableCard.value || loading.value) return
  loading.value = true
  try {
    const scale = scaleOptions.find((option) => option.scale === selectedScale.value) || scaleOptions[3]
    const { data } = await novelChatStep({
      step: 6,
      user_input: JSON.stringify({
        action,
        card: editableCard.value,
        target_chapters: scaleConfig.value.target_chapters,
        target_chars: scaleConfig.value.target_chars,
        scale: scale.scale,
        scale_label: scale.label,
        preset_composition: composition.value,
      }),
      context: context.value,
    })
    applyResponse(data)
    if (action === 'deep') {
      editableCard.value = null
      await scrollToBottom()
      return
    }
    const card = data.context?.summary_card || editableCard.value
    emit('complete', {
      name: data.context?.chosen_title || card?.title_suggestions?.[0] || '未命名小说',
      description: card?.logline || data.context?.theme || '',
      genre: data.context?.genre || card?.genre_positioning || '',
      context: data.context || context.value,
    })
  } catch (err: any) {
    messages.value.push({ role: 'ai', content: `确认失败，请重试。\n\n${err?.response?.data?.detail || err.message || '未知错误'}` })
  } finally {
    loading.value = false
  }
}

const useSuggestion = (suggestion: string) => sendMessage(suggestion)
</script>

<template>
  <div class="ai-guide">
    <div v-if="modelLabel" class="model-status">
      <el-icon><MagicStick /></el-icon>
      <span>AI 创作引导将调用：{{ modelLabel }}</span>
    </div>

    <div class="phase-head">
      <strong>{{ isDeepPlanning ? '深度规划 · 总纲草案' : '基础建档 · 快速蓝图' }}</strong>
      <span v-if="context.deep_complete" class="done-badge">深度规划已完成</span>
    </div>

    <div class="step-progress">
      <div
        v-for="(label, idx) in labels"
        :key="label"
        class="step-dot"
        :class="{ active: visibleStepIndex === idx, done: visibleStepIndex > idx }"
      >
        <div class="dot-circle">
          <el-icon v-if="visibleStepIndex > idx"><Check /></el-icon>
          <span v-else>{{ idx + 1 }}</span>
        </div>
        <span class="dot-label">{{ label }}</span>
      </div>
      <div class="progress-line"><div class="progress-fill" :style="{ width: progressWidth }" /></div>
    </div>

    <div class="chat-area" ref="chatContainer">
      <div v-for="(message, idx) in messages" :key="idx" class="message" :class="message.role">
        <div class="msg-avatar">
          <el-icon v-if="message.role === 'ai'"><MagicStick /></el-icon>
          <el-icon v-else><Edit /></el-icon>
        </div>
        <div class="msg-bubble" v-html="formatMessage(message.content)" />
      </div>
      <div v-if="loading" class="message ai">
        <div class="msg-avatar"><el-icon><MagicStick /></el-icon></div>
        <div class="msg-bubble">正在整理蓝图...</div>
      </div>
    </div>

    <div v-if="showFinalize" class="draft-panel">
      <div class="panel-head">
        <div>
          <h3>定稿建档</h3>
          <p>调整作品包装、体量和模板。默认可继续深度规划；若仅需锁定主题与体量，可勾选下方「精简建档」。</p>
        </div>
        <span v-if="context.deep_complete" class="done-badge">总纲已补强</span>
      </div>

      <el-checkbox v-model="skipDeepPlanning" class="compact-toggle">
        精简建档（跳过深度规划 7–10 步，保留主题与体量确认后直接创建）
      </el-checkbox>

      <div class="draft-layout">
        <div class="card-fields">
          <div class="card-field">
            <label>书名候选</label>
            <el-input v-for="(_title, idx) in editableCard!.title_suggestions" :key="idx" v-model="editableCard!.title_suggestions[idx]" size="small" />
          </div>
          <div class="card-field">
            <label>一句话卖点</label>
            <el-input v-model="editableCard!.logline" type="textarea" :rows="2" />
          </div>
          <div class="card-row">
            <div class="card-field">
              <label>类型定位</label>
              <el-input v-model="editableCard!.genre_positioning" size="small" />
            </div>
            <div class="card-field">
              <label>目标读者</label>
              <el-input v-model="editableCard!.target_reader" size="small" />
            </div>
          </div>
          <div class="card-field">
            <label>整体基调</label>
            <el-input v-model="editableCard!.tone" size="small" />
          </div>
        </div>

        <div class="finalize-right">
          <label>故事体量</label>
          <div class="scale-options">
            <button v-for="option in scaleOptions" :key="option.scale" type="button" class="scale-option" :class="{ active: selectedScale === option.scale }" @click="selectScale(option)">
              <strong>{{ option.aiLabel || option.label }}</strong>
              <small>{{ option.hint }}</small>
            </button>
          </div>
          <p v-if="scaleHint" class="scale-long-hint">{{ scaleHint }}</p>
          <div class="number-row">
            <label>目标章节数 <el-input-number v-model="scaleConfig.target_chapters" :min="1" :max="chaptersMax" :step="50" size="small" /></label>
            <label>每章字数 <el-input-number v-model="scaleConfig.target_chars[0]" :min="200" :max="5000" :step="100" size="small" /> ~ <el-input-number v-model="scaleConfig.target_chars[1]" :min="200" :max="5000" :step="100" size="small" /></label>
          </div>
          <div class="preset-wrap">
            <label>预设模板（可选）</label>
            <PresetSelector v-model="composition" compact />
          </div>
        </div>
      </div>

      <div class="draft-actions">
        <el-button
          v-if="!context.deep_complete && !skipDeepPlanning"
          size="large"
          @click="finalize('deep')"
          :loading="loading"
        >
          继续完善总纲
        </el-button>
        <el-button type="primary" size="large" @click="finalize('create')" :loading="loading">
          {{ skipDeepPlanning ? '精简建档并创建' : '创建作品' }}
        </el-button>
      </div>
    </div>

    <div v-if="suggestions.length && !showFinalize" class="suggestions">
      <span>试试这些方向：</span>
      <button v-for="suggestion in suggestions" :key="suggestion" type="button" @click="useSuggestion(suggestion)">{{ suggestion }}</button>
    </div>

    <div v-if="!showFinalize" class="input-bar">
      <el-input v-model="userInput" placeholder="描述你的想法，也可以直接选择上方建议..." :disabled="loading" @keyup.enter="sendMessage()">
        <template #append><el-button :icon="ChatDotRound" :loading="loading" @click="sendMessage()" /></template>
      </el-input>
    </div>
  </div>
</template>

<script lang="ts">
function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

function formatMessage(text: string): string {
  return escapeHtml(text).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
}
</script>

<style scoped>
.ai-guide { display: grid; gap: 14px; }
.compact-toggle { margin: 0 0 8px; color: var(--color-text-muted); }
.scale-long-hint {
  margin: 8px 0 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff8f4;
  border: 1px solid #f0d5c8;
  color: #9a5033;
  font-size: 12px;
  line-height: 1.45;
}
.model-status, .phase-head, .panel-head, .draft-actions { display: flex; align-items: center; gap: 8px; }
.model-status { width: fit-content; padding: 7px 10px; border: 1px solid var(--color-primary-muted); border-radius: 8px; background: var(--color-primary-soft); color: var(--color-primary-hover); font-size: 12px; font-weight: 600; }
.phase-head { justify-content: space-between; color: #374151; font-size: 14px; }
.done-badge { padding: 3px 8px; border-radius: 999px; background: #dcfce7; color: #166534; font-size: 12px; }
.step-progress { position: relative; display: flex; justify-content: space-between; padding: 0 24px 18px; }
.step-dot { position: relative; z-index: 1; display: grid; justify-items: center; gap: 5px; }
.dot-circle { display: grid; width: 30px; height: 30px; place-items: center; border: 2px solid #d1d5db; border-radius: 50%; background: var(--color-bg-surface); color: #9ca3af; font-size: 12px; }
.step-dot.active .dot-circle { border-color: #c66f4f; background: #c66f4f; color: var(--color-bg-surface); }
.step-dot.done .dot-circle { border-color: var(--color-success); background: var(--color-success); color: var(--color-bg-surface); }
.dot-label { color: #9ca3af; font-size: 11px; }
.step-dot.active .dot-label { color: #c66f4f; font-weight: 600; }
.progress-line { position: absolute; top: 14px; right: 42px; left: 42px; height: 3px; border-radius: 2px; background: #e5e7eb; }
.progress-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, var(--color-success), #c66f4f); transition: width .3s; }
.chat-area { display: grid; max-height: 320px; gap: 12px; overflow-y: auto; padding: 4px 8px; }
.message { display: flex; max-width: 86%; gap: 9px; }
.message.user { justify-self: end; flex-direction: row-reverse; }
.msg-avatar { display: grid; width: 32px; height: 32px; flex-shrink: 0; place-items: center; border-radius: 50%; background: #c66f4f; color: var(--color-bg-surface); }
.message.user .msg-avatar { background: #e5e7eb; color: #6b7280; }
.msg-bubble { padding: 10px 14px; border-radius: 12px; background: #f3f4f6; color: #1f2937; font-size: 14px; line-height: 1.6; }
.message.user .msg-bubble { background: #c66f4f; color: var(--color-bg-surface); }
.draft-panel { padding: 18px; border: 1px solid #e5e7eb; border-radius: 12px; background: var(--color-bg-surface); box-shadow: 0 8px 24px rgba(0,0,0,.06); }
.panel-head { justify-content: space-between; margin-bottom: 14px; }
.panel-head h3, .panel-head p { margin: 0; }
.panel-head p { margin-top: 3px; color: #9ca3af; font-size: 12px; }
.draft-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 380px); gap: 18px; }
.card-fields, .finalize-right, .preset-wrap { display: grid; align-content: start; gap: 10px; }
.card-field label, .finalize-right > label, .preset-wrap > label { display: block; margin-bottom: 4px; color: #4b5563; font-size: 12px; font-weight: 600; }
.card-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.scale-options { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.scale-option { display: grid; gap: 2px; padding: 7px 8px; border: 1px solid #e5e7eb; border-radius: 7px; background: var(--color-bg-surface); color: #374151; text-align: left; cursor: pointer; }
.scale-option.active { border-color: #c66f4f; background: #fff8f4; }
.scale-option small { color: #9ca3af; font-size: 10px; }
.number-row { display: grid; gap: 8px; color: #4b5563; font-size: 12px; }
.number-row label { display: flex; align-items: center; gap: 6px; }
.draft-actions { justify-content: center; margin-top: 16px; padding-top: 14px; border-top: 1px solid #f3f4f6; }
.suggestions { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; padding: 4px 8px; color: #9ca3af; font-size: 12px; }
.suggestions button { padding: 5px 11px; border: 1px solid #e5e7eb; border-radius: 14px; background: var(--color-bg-surface); color: #4b5563; cursor: pointer; }
.suggestions button:hover { border-color: #c66f4f; color: #c66f4f; }
.input-bar { padding-top: 8px; border-top: 1px solid #f3f4f6; }
@media (max-width: 860px) { .draft-layout { grid-template-columns: 1fr; } .dot-label { display: none; } }
</style>
