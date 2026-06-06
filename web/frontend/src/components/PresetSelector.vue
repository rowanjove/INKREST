<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Reading } from '@element-plus/icons-vue'
import { listComponents, getComponent } from '../api'
import type { Composition } from '../types/preset'

const emit = defineEmits<{
  (e: 'update:modelValue', value: Composition | null): void
}>()

const props = defineProps<{
  modelValue: Composition | null
  compact?: boolean
}>()

interface ComponentMeta {
  id: string
  name: string
  channels?: string[]
  tags: string[]
  description: string
}

const channel = ref<string>('general')
const theme = ref<string>('')
const mechanisms = ref<string[]>([])
const coolPoints = ref<string[]>([])

const channels = ref<ComponentMeta[]>([])
const allThemes = ref<ComponentMeta[]>([])
const mechanismList = ref<ComponentMeta[]>([])
const coolPointList = ref<ComponentMeta[]>([])

const loading = ref(false)
const error = ref('')
const guidePreview = ref('')
const previewVisible = ref(false)
const previewTitle = ref('')

watch(() => props.modelValue, (val) => {
  if (val) {
    channel.value = val.channel || 'general'
    theme.value = val.theme || ''
    mechanisms.value = [...(val.mechanisms || [])]
    coolPoints.value = [...(val.cool_points || [])]
  }
}, { immediate: true })

const filteredThemes = computed(() => {
  const themes = allThemes.value || []
  if (!channel.value) return themes
  return themes.filter(
    (t) => t && (!t.channels || t.channels.includes(channel.value))
  )
})

const emitComposition = () => {
  if (!theme.value) {
    emit('update:modelValue', null)
    return
  }
  emit('update:modelValue', {
    channel: channel.value,
    theme: theme.value,
    mechanisms: mechanisms.value,
    cool_points: coolPoints.value,
  })
}

const selectChannel = (id: string) => {
  channel.value = id
  // Clear theme if incompatible with new channel
  const availableThemes = allThemes.value.filter(
    (t) => t && (!t.channels || t.channels.includes(id))
  )
  if (theme.value && !availableThemes.some((t) => t && t.id === theme.value)) {
    theme.value = ''
  }
  // Clear mechanisms incompatible with new channel
  mechanisms.value = mechanisms.value.filter((mId) => {
    const mech = mechanismList.value.find((m) => m && m.id === mId)
    return !mech?.channels || mech.channels.includes(id)
  })
  // Clear cool_points incompatible with new channel
  coolPoints.value = coolPoints.value.filter((cpId) => {
    const cp = coolPointList.value.find((c) => c && c.id === cpId)
    return !cp?.channels || cp.channels.includes(id)
  })
  emitComposition()
}

const selectTheme = (id: string) => {
  theme.value = theme.value === id ? '' : id
  emitComposition()
}

const toggleMechanism = (id: string) => {
  if (mechanisms.value.includes(id)) {
    mechanisms.value = mechanisms.value.filter((m) => m !== id)
  } else if (mechanisms.value.length < 2) {
    mechanisms.value = [...mechanisms.value, id]
  }
  emitComposition()
}

const toggleCoolPoint = (id: string) => {
  if (coolPoints.value.includes(id)) {
    coolPoints.value = coolPoints.value.filter((c) => c !== id)
  } else if (coolPoints.value.length < 3) {
    coolPoints.value = [...coolPoints.value, id]
  }
  emitComposition()
}

const resetAll = () => {
  channel.value = 'general'
  theme.value = ''
  mechanisms.value = []
  coolPoints.value = []
  emit('update:modelValue', null)
}

/** Escape HTML to prevent XSS in guide previews. */
const sanitizeHtml = (raw: string): string =>
  raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>')

const showGuide = async (type: string, id: string, name: string) => {
  try {
    const { data } = await getComponent(type, id)
    guidePreview.value = data.guide || '暂无指南'
  } catch {
    guidePreview.value = '加载失败'
  }
  previewTitle.value = name
  previewVisible.value = true
}

const channelLabel = (id: string) => {
  const map: Record<string, string> = { general: '通用', male: '男频', female: '女频', custom: '自定' }
  return map[id] || id
}

type TagType = '' | 'success' | 'info' | 'warning' | 'danger'

const channelTagType = (id: string): TagType => {
  const map: Record<string, TagType> = { general: 'info', male: '', female: 'danger', custom: 'warning' }
  return map[id] || 'info'
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const [chRes, thRes, mechRes, cpRes] = await Promise.all([
      listComponents('channels'),
      listComponents('themes'),
      listComponents('mechanisms'),
      listComponents('cool_points'),
    ])
    channels.value = chRes.data || []
    allThemes.value = thRes.data || []
    mechanismList.value = mechRes.data || []
    coolPointList.value = cpRes.data || []
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '加载模板组件失败，请检查后端服务是否运行'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="composable-selector" :class="{ compact: props.compact }" v-loading="loading">
    <!-- Error state -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    />

    <template v-if="!error && !loading">
      <!-- Channel: horizontal buttons -->
      <div class="section">
        <div class="section-label">频道</div>
        <div class="channel-row">
          <button
            v-for="ch in channels"
            :key="ch.id"
            class="channel-btn"
            :class="{ active: channel === ch.id }"
            @click="selectChannel(ch.id)"
          >
            {{ ch.name }}
          </button>
        </div>
      </div>

      <!-- Theme: 2-column grid -->
      <div class="section">
        <div class="section-label">题材壳 <small>（{{ filteredThemes.length }} 个可选）</small></div>
        <div class="theme-grid">
          <button
            v-for="th in filteredThemes"
            :key="th.id"
            class="theme-card"
            :class="{ active: theme === th.id }"
            @click="selectTheme(th.id)"
          >
            <div class="tc-head">
              <strong>{{ th.name }}</strong>
              <el-button text size="small" :icon="Reading" @click.stop="showGuide('themes', th.id, th.name)" />
            </div>
            <small>{{ th.description }}</small>
            <div class="tc-tags">
              <el-tag v-for="tag in (th.tags || []).slice(0, 3)" :key="tag" size="small" type="info" effect="plain">
                {{ tag }}
              </el-tag>
            </div>
          </button>
        </div>
      </div>

      <!-- Mechanisms: tag selection -->
      <div class="section">
        <div class="section-label">机制 <small>（可选 0-2）</small></div>
        <div class="tag-row">
          <button
            v-for="mech in mechanismList"
            :key="mech.id"
            class="tag-pick"
            :class="{ active: mechanisms.includes(mech.id) }"
            @click="toggleMechanism(mech.id)"
          >
            {{ mech.name }}
            <span class="tag-desc">{{ mech.description }}</span>
          </button>
        </div>
      </div>

      <!-- Cool points: tag selection -->
      <div class="section">
        <div class="section-label">爽点 <small>（可选 0-3）</small></div>
        <div class="tag-row">
          <button
            v-for="cp in coolPointList"
            :key="cp.id"
            class="tag-pick"
            :class="{ active: coolPoints.includes(cp.id) }"
            @click="toggleCoolPoint(cp.id)"
          >
            {{ cp.name }}
            <span class="tag-desc">{{ cp.description }}</span>
          </button>
        </div>
      </div>

      <!-- Summary bar -->
      <div class="selection-summary" v-if="theme || channel !== 'general'">
        <el-tag :type="channelTagType(channel)" effect="plain" size="small">{{ channelLabel(channel) }}</el-tag>
        <el-tag v-if="theme" effect="plain" size="small">{{ allThemes.find(t => t && t.id === theme)?.name || theme }}</el-tag>
        <el-tag v-for="m in mechanisms" :key="m" size="small" type="success" effect="plain">
          {{ mechanismList.find(mm => mm && mm.id === m)?.name || m }}
        </el-tag>
        <el-tag v-for="c in coolPoints" :key="c" size="small" type="warning" effect="plain">
          {{ coolPointList.find(cc => cc && cc.id === c)?.name || c }}
        </el-tag>
        <button class="reset-btn" @click="resetAll">重置</button>
      </div>
    </template>

    <!-- Guide preview dialog -->
    <el-dialog v-model="previewVisible" :title="`${previewTitle} · 写作指南`" width="720px" top="6vh">
      <article class="guide-content" v-html="sanitizeHtml(guidePreview)"></article>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.composable-selector {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.section {
  display: grid;
  gap: 8px;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.section-label small {
  font-weight: 400;
  color: #9ca3af;
}

/* Channel row */
.channel-row {
  display: flex;
  gap: 8px;
}

.channel-btn {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #4b5563;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.channel-btn:hover {
  border-color: #c66f4f;
}

.channel-btn.active {
  border-color: #c66f4f;
  background: #fff8f4;
  color: #c66f4f;
}

/* Theme grid */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  max-height: 300px;
  overflow: auto;
  padding: 2px;
}

.theme-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #374151;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s;
}

.theme-card:hover {
  border-color: #c66f4f;
}

.theme-card.active {
  border-color: #c66f4f;
  background: #fff8f4;
  box-shadow: 0 2px 8px rgba(198, 111, 79, 0.1);
}

.tc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.theme-card strong {
  font-size: 14px;
  color: #111827;
}

.theme-card small {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.tc-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 2px;
}

/* Tag-style selection for mechanisms & cool points */
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-pick {
  padding: 6px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: var(--color-bg-surface);
  color: #4b5563;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.tag-pick:hover {
  border-color: #c66f4f;
  color: #c66f4f;
}

.tag-pick.active {
  border-color: var(--color-success);
  background: #f0fdf4;
  color: var(--color-success);
  font-weight: 600;
}

.tag-desc {
  font-size: 11px;
  color: #9ca3af;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-pick.active .tag-desc {
  color: #6ee7b7;
}

/* Summary bar */
.selection-summary {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 0;
  border-top: 1px solid #f3f4f6;
}

.reset-btn {
  margin-left: auto;
  padding: 4px 12px;
  border: none;
  background: transparent;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
}

.reset-btn:hover {
  color: var(--color-danger);
}

.guide-content {
  max-height: 62vh;
  overflow: auto;
  color: #303848;
  font-size: 14px;
  line-height: 1.8;
}

/* Compact layout for narrow side panels in the AI creation draft. */
.composable-selector.compact {
  gap: 12px;
}

.compact .channel-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.compact .channel-btn {
  padding: 8px 10px;
  min-width: 0;
}

.compact .theme-grid {
  grid-template-columns: 1fr;
  max-height: 260px;
}

.compact .theme-card {
  gap: 6px;
  padding: 10px;
}

.compact .tc-head strong,
.compact .theme-card small,
.compact .tag-desc {
  min-width: 0;
}

.compact .tc-tags {
  display: none;
}

.compact .tag-row {
  display: grid;
  grid-template-columns: 1fr;
  max-height: 180px;
  overflow: auto;
  padding-right: 4px;
}

.compact .tag-pick {
  width: 100%;
  justify-content: flex-start;
  border-radius: 8px;
}

.compact .tag-desc {
  flex: 1;
  max-width: none;
}
</style>
