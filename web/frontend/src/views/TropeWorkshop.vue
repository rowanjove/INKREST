<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Collection,
  Cpu,
  DataLine,
  Delete,
  Lightning,
  MagicStick,
  Plus,
  Refresh,
  User,
} from '@element-plus/icons-vue'
import { listComponents, composePreset } from '../api'
import { useProjectStore } from '../stores/project'

const router = useRouter()
const projectStore = useProjectStore()

// State lists for categories
const channels = ref<any[]>([])
const themes = ref<any[]>([])
const mechanisms = ref<any[]>([])
const coolPoints = ref<any[]>([])

const loading = ref(false)
const activeTab = ref<'channels' | 'themes' | 'mechanisms' | 'cool_points'>('channels')

// Selected assembly blueprint
const selectedChannel = ref<any>(null)
const selectedTheme = ref<any>(null)
const selectedMechanisms = ref<any[]>([])
const selectedCoolPoints = ref<any[]>([])

// Output guide MD representation
const generatedGuide = ref('')
const guideLoading = ref(false)



// Fetching components
const loadAllComponents = async () => {
  loading.value = true
  try {
    const [cRes, tRes, mRes, cpRes] = await Promise.all([
      listComponents('channels'),
      listComponents('themes'),
      listComponents('mechanisms'),
      listComponents('cool_points'),
    ])
    channels.value = cRes.data || []
    themes.value = tRes.data || []
    mechanisms.value = mRes.data || []
    coolPoints.value = cpRes.data || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载套路元件失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAllComponents()
})

// Add element to blueprint slots
const addToBlueprint = (item: any, type: string) => {
  if (type === 'channels') {
    selectedChannel.value = item
    ElMessage.success(`已设置主角频道为「${item.name}」`)
  } else if (type === 'themes') {
    selectedTheme.value = item
    ElMessage.success(`已设置核心题材为「${item.name}」`)
  } else if (type === 'mechanisms') {
    if (selectedMechanisms.value.some((x) => x.id === item.id)) {
      ElMessage.warning('该情节机制已在蓝图中')
      return
    }
    selectedMechanisms.value.push(item)
    ElMessage.success(`已添加机制「${item.name}」`)
  } else if (type === 'cool_points') {
    if (selectedCoolPoints.value.some((x) => x.id === item.id)) {
      ElMessage.warning('该爽点节奏已在蓝图中')
      return
    }
    selectedCoolPoints.value.push(item)
    ElMessage.success(`已添加爽点「${item.name}」`)
  }
  autoGeneratePreview()
}

// Remove from blueprint
const removeFromBlueprint = (id: string, type: string) => {
  if (type === 'channels') {
    selectedChannel.value = null
  } else if (type === 'themes') {
    selectedTheme.value = null
  } else if (type === 'mechanisms') {
    selectedMechanisms.value = selectedMechanisms.value.filter((x) => x.id !== id)
  } else if (type === 'cool_points') {
    selectedCoolPoints.value = selectedCoolPoints.value.filter((x) => x.id !== id)
  }
  autoGeneratePreview()
}

// Check validation before applying or composing
const isValidBlueprint = computed(() => {
  return selectedChannel.value && selectedTheme.value
})

// Auto compile text guide or request preview
const autoGeneratePreview = async () => {
  if (!isValidBlueprint.value) {
    generatedGuide.value = ''
    return
  }
  guideLoading.value = true
  try {
    const res = await composePreset({
      channel: selectedChannel.value.id,
      theme: selectedTheme.value.id,
      mechanisms: selectedMechanisms.value.map((x) => x.id),
      cool_points: selectedCoolPoints.value.map((x) => x.id),
    })
    generatedGuide.value = res.data?.guide || ''
  } catch (error: any) {
    ElMessage.error(error.message || '预览套路指南失败')
  } finally {
    guideLoading.value = false
  }
}

// Simple marked parser helper (replaces standard markdown lines with basic tags)
const escapeHtml = (value: string) => value
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const parsedGuideHtml = computed(() => {
  if (!generatedGuide.value) return ''
  const lines = generatedGuide.value.split('\n')
  let html = ''
  let inList = false

  for (let line of lines) {
    line = escapeHtml(line.trim())
    if (!line) {
      if (inList) {
        html += '</ul>'
        inList = false
      }
      continue
    }

    if (line.startsWith('### ')) {
      if (inList) {
        html += '</ul>'
        inList = false
      }
      html += `<h3>${line.substring(4)}</h3>`
    } else if (line.startsWith('## ')) {
      if (inList) {
        html += '</ul>'
        inList = false
      }
      html += `<h2>${line.substring(3)}</h2>`
    } else if (line.startsWith('# ')) {
      if (inList) {
        html += '</ul>'
        inList = false
      }
      html += `<h1>${line.substring(2)}</h1>`
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!inList) {
        html += '<ul>'
        inList = true
      }
      html += `<li>${line.substring(2)}</li>`
    } else if (line === '---') {
      if (inList) {
        html += '</ul>'
        inList = false
      }
      html += '<hr />'
    } else {
      if (inList) {
        html += '</ul>'
        inList = false
      }
      html += `<p>${line}</p>`
    }
  }

  if (inList) {
    html += '</ul>'
  }

  return html
})

// Apply preset composition to active project
const handleApplyToActiveProject = async () => {
  if (!projectStore.currentProject?.id) {
    ElMessage.warning('当前没有激活的作品，请选择“创建新作品”！')
    return
  }
  loading.value = true
  try {
    await composePreset({
      channel: selectedChannel.value.id,
      theme: selectedTheme.value.id,
      mechanisms: selectedMechanisms.value.map((x) => x.id),
      cool_points: selectedCoolPoints.value.map((x) => x.id),
      project_id: projectStore.currentProject.id,
    })
    ElMessage.success('套路规范已保存并覆盖当前作品的 assets/writing_guide.md')
  } catch (error: any) {
    ElMessage.error(error.message || '应用到当前作品失败')
  } finally {
    loading.value = false
  }
}

/** 统一走 /create 快速创建，预填套路与最小大纲 */
const openCreateDialog = () => {
  if (!isValidBlueprint.value) return
  router.push({
    path: '/create',
    query: {
      from: 'trope',
      mode: 'quick',
      name: `${selectedTheme.value.name}故事`,
      description: `围绕「${selectedTheme.value.name}」展开，融合频道【${selectedChannel.value.name}】要素。`,
      genre: selectedTheme.value.name,
      channel: selectedChannel.value.id,
      theme: selectedTheme.value.id,
      mechanisms: selectedMechanisms.value.map((x) => x.id).join(','),
      cool_points: selectedCoolPoints.value.map((x) => x.id).join(','),
      target_chapters: '80',
      scale: 'medium',
    },
  })
}

// HTML5 Drag and Drop Handlers
const handleDragStart = (event: DragEvent, item: any, type: string) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/json', JSON.stringify({ item, type }))
    event.dataTransfer.effectAllowed = 'copy'
  }
}

const handleDrop = (event: DragEvent, targetType: string) => {
  event.preventDefault()
  if (!event.dataTransfer) return
  try {
    const dataStr = event.dataTransfer.getData('application/json')
    if (!dataStr) return
    const { item, type } = JSON.parse(dataStr)
    if (type !== targetType) {
      ElMessage.warning(`请将该类型元件拖入相对应的「${getSlotLabel(targetType)}」插槽内`)
      return
    }
    addToBlueprint(item, type)
  } catch (e) {
    // Silent
  }
}

const getSlotLabel = (type: string) => {
  const map: Record<string, string> = {
    channels: '主角频道',
    themes: '主题题材',
    mechanisms: '情节机制',
    cool_points: '爽点节奏',
  }
  return map[type] || ''
}
</script>

<template>
  <section class="trope-workshop">
    <header class="page-head">
      <div class="page-title-area">
        <h1>网文套路设计工坊</h1>
        <p>通过拖拽或选择题材主题、主角设定、情节机制与节奏爽点卡，自由组装定制专属的小说写作蓝图，一键输出项目级指南规则书。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="Refresh" @click="loadAllComponents">刷新元件</el-button>
      </div>
    </header>

    <div class="workshop-layout">
      <!-- Left side: Candidates Library -->
      <aside class="component-library">
        <div class="library-header">
          <h3>套路预设元件库</h3>
          <p>选中或向右侧拖拽卡片来进行拼装</p>
        </div>

        <el-tabs v-model="activeTab" class="library-tabs">
          <!-- Channels -->
          <el-tab-pane name="channels" label="主角角色">
            <div class="component-grid" v-loading="loading">
              <div
                v-for="item in channels"
                :key="item.id"
                class="component-card card-channel"
                draggable="true"
                @dragstart="(e) => handleDragStart(e, item, 'channels')"
                @click="addToBlueprint(item, 'channels')"
              >
                <div class="card-head">
                  <span class="card-tag">主角</span>
                  <el-icon class="card-icon"><User /></el-icon>
                </div>
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div class="card-footer">
                  <span class="card-id">#{{ item.id }}</span>
                  <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                    <el-icon><Plus /></el-icon>
                  </span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Themes -->
          <el-tab-pane name="themes" label="题材主题">
            <div class="component-grid" v-loading="loading">
              <div
                v-for="item in themes"
                :key="item.id"
                class="component-card card-theme"
                draggable="true"
                @dragstart="(e) => handleDragStart(e, item, 'themes')"
                @click="addToBlueprint(item, 'themes')"
              >
                <div class="card-head">
                  <span class="card-tag">主题</span>
                  <el-icon class="card-icon"><Collection /></el-icon>
                </div>
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div class="card-footer">
                  <span class="card-id">#{{ item.id }}</span>
                  <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                    <el-icon><Plus /></el-icon>
                  </span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Mechanisms -->
          <el-tab-pane name="mechanisms" label="剧情机制">
            <div class="component-grid" v-loading="loading">
              <div
                v-for="item in mechanisms"
                :key="item.id"
                class="component-card card-mechanism"
                draggable="true"
                @dragstart="(e) => handleDragStart(e, item, 'mechanisms')"
                @click="addToBlueprint(item, 'mechanisms')"
              >
                <div class="card-head">
                  <span class="card-tag">机制</span>
                  <el-icon class="card-icon"><Cpu /></el-icon>
                </div>
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div class="card-footer">
                  <span class="card-id">#{{ item.id }}</span>
                  <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                    <el-icon><Plus /></el-icon>
                  </span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Cool Points -->
          <el-tab-pane name="cool_points" label="爽点节奏">
            <div class="component-grid" v-loading="loading">
              <div
                v-for="item in coolPoints"
                :key="item.id"
                class="component-card card-cool"
                draggable="true"
                @dragstart="(e) => handleDragStart(e, item, 'cool_points')"
                @click="addToBlueprint(item, 'cool_points')"
              >
                <div class="card-head">
                  <span class="card-tag">爽点</span>
                  <el-icon class="card-icon"><Lightning /></el-icon>
                </div>
                <h4>{{ item.name }}</h4>
                <p>{{ item.description }}</p>
                <div class="card-footer">
                  <span class="card-id">#{{ item.id }}</span>
                  <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                    <el-icon><Plus /></el-icon>
                  </span>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </aside>

      <!-- Right side: Blueprint Slots & Preview -->
      <main class="blueprint-workbench">
        <div class="workbench-header">
          <h3>套路组装工作台</h3>
          <div class="workbench-actions">
            <el-button
              type="success"
              :disabled="!isValidBlueprint"
              @click="openCreateDialog"
              :icon="MagicStick"
            >
              以此新建作品
            </el-button>
            <el-button
              type="primary"
              :disabled="!isValidBlueprint || !projectStore.currentProject?.id"
              @click="handleApplyToActiveProject"
              :icon="DataLine"
            >
              应用到当前作品
            </el-button>
          </div>
        </div>

        <div class="blueprint-slots">
          <!-- Slot 1: Channel (Single) -->
          <div
            class="slot-wrapper"
            @dragover.prevent
            @drop="(e) => handleDrop(e, 'channels')"
          >
            <label>主角定位 (Channel) <span class="req">*</span></label>
            <div v-if="selectedChannel" class="assembled-card chan-bg">
              <div class="assembled-info">
                <strong>{{ selectedChannel.name }}</strong>
                <span>{{ selectedChannel.description }}</span>
              </div>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeFromBlueprint('', 'channels')"
              />
            </div>
            <div v-else class="empty-slot">
              拖拽或点击主角角色卡片到此处 (必选)
            </div>
          </div>

          <!-- Slot 2: Theme (Single) -->
          <div
            class="slot-wrapper"
            @dragover.prevent
            @drop="(e) => handleDrop(e, 'themes')"
          >
            <label>题材主题 (Theme) <span class="req">*</span></label>
            <div v-if="selectedTheme" class="assembled-card theme-bg">
              <div class="assembled-info">
                <strong>{{ selectedTheme.name }}</strong>
                <span>{{ selectedTheme.description }}</span>
              </div>
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeFromBlueprint('', 'themes')"
              />
            </div>
            <div v-else class="empty-slot">
              拖拽或点击题材主题卡片到此处 (必选)
            </div>
          </div>

          <!-- Slot 3: Mechanisms (Multiple) -->
          <div
            class="slot-wrapper"
            @dragover.prevent
            @drop="(e) => handleDrop(e, 'mechanisms')"
          >
            <label>核心机制 (Mechanisms)</label>
            <div class="tags-container">
              <div
                v-for="item in selectedMechanisms"
                :key="item.id"
                class="assembled-card-small mech-bg"
              >
                <strong>{{ item.name }}</strong>
                <el-button
                  type="danger"
                  link
                  :icon="Delete"
                  @click="removeFromBlueprint(item.id, 'mechanisms')"
                />
              </div>
              <div v-if="selectedMechanisms.length === 0" class="empty-slot-thin">
                暂无核心机制。支持放入多个机制
              </div>
            </div>
          </div>

          <!-- Slot 4: Cool Points (Multiple) -->
          <div
            class="slot-wrapper"
            @dragover.prevent
            @drop="(e) => handleDrop(e, 'cool_points')"
          >
            <label>爽点节奏 (Cool Points)</label>
            <div class="tags-container">
              <div
                v-for="item in selectedCoolPoints"
                :key="item.id"
                class="assembled-card-small cool-bg"
              >
                <strong>{{ item.name }}</strong>
                <el-button
                  type="danger"
                  link
                  :icon="Delete"
                  @click="removeFromBlueprint(item.id, 'cool_points')"
                />
              </div>
              <div v-if="selectedCoolPoints.length === 0" class="empty-slot-thin">
                暂无爽点节奏。支持放入多个爽点
              </div>
            </div>
          </div>
        </div>

        <!-- Blueprint Guide Preview -->
        <div class="preview-section" v-loading="guideLoading">
          <div class="preview-header">
            <h4>套路写作指南预览 (MD格式)</h4>
            <span v-if="!isValidBlueprint" class="validation-tip">配置完主角和题材题材后，系统将自动拼接生成</span>
          </div>

          <div class="preview-content">
            <div v-if="generatedGuide" class="markdown-preview" v-html="parsedGuideHtml" />
            <el-empty v-else description="组装基本参数后，这里会展现系统为你拼接的设定指南" />
          </div>
        </div>
      </main>
    </div>

  </section>
</template>

<style scoped>
.trope-workshop {
  display: grid;
  gap: 20px;
}



.workshop-layout {
  display: grid;
  grid-template-columns: 460px minmax(0, 1fr);
  gap: 20px;
  min-height: calc(100vh - 190px);
}

.component-library,
.blueprint-workbench {
  background: var(--color-bg-surface);
  border: 1px solid #e1e7ef;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.component-library {
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: hidden;
}

.library-header {
  margin-bottom: 12px;
}

.library-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
  color: #1a202c;
}

.library-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #718096;
}

.library-tabs {
  flex: 1;
  overflow: auto;
}

.component-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  max-height: calc(100vh - 350px);
  overflow-y: auto;
  padding-right: 4px;
}

.component-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--color-bg-surface-muted);
  cursor: grab;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 140px;
}

.component-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: var(--primary);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-tag {
  font-size: 10px;
  font-weight: 750;
  padding: 2px 6px;
  border-radius: 4px;
}

.card-channel .card-tag { background: #e0f2fe; color: #0284c7; }
.card-theme .card-tag { background: #dcfce7; color: var(--color-success); }
.card-mechanism .card-tag { background: #fef3c7; color: var(--color-warning); }
.card-cool .card-tag { background: #f3e8ff; color: #9333ea; }

.card-icon {
  font-size: 14px;
  color: #a0aec0;
}

.component-card h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 700;
  color: #2d3748;
}

.component-card p {
  margin: 0;
  font-size: 11.5px;
  color: #718096;
  line-height: 1.4;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-id {
  font-size: 10px;
  font-family: monospace;
  color: #a0aec0;
}

.card-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(198, 111, 79, 0.38);
  border: 1.5px solid rgba(255, 255, 255, 0.55);
  transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.card-add-btn .el-icon {
  font-size: 15px;
  font-weight: 700;
}

.component-card:hover .card-add-btn {
  background: var(--color-primary-hover);
  transform: scale(1.08);
  box-shadow: 0 3px 10px rgba(198, 111, 79, 0.45);
}

/* Workbench side */
.blueprint-workbench {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
}

.workbench-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 12px;
}

.workbench-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
  color: #1a202c;
}

.workbench-actions {
  display: flex;
  gap: 10px;
}

.blueprint-slots {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 20px;
}

.slot-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slot-wrapper label {
  font-size: 13.5px;
  font-weight: 700;
  color: #4a5568;
}

.slot-wrapper label .req {
  color: var(--color-danger);
}

.assembled-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--color-bg-surface-muted);
}

.assembled-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.assembled-info strong {
  font-size: 14px;
  color: var(--color-text-strong);
}

.assembled-info span {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chan-bg { border-left: 4px solid #0284c7; background: #f0f9ff; }
.theme-bg { border-left: 4px solid var(--color-success); background: #f0fdf4; }

.empty-slot {
  height: 60px;
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-subtle);
  background: var(--color-bg-surface-muted);
  text-align: center;
  padding: 0 10px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px;
  min-height: 60px;
  background: var(--color-bg-surface-muted);
  align-content: flex-start;
}

.assembled-card-small {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12.5px;
}

.mech-bg { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
.cool-bg { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }

.empty-slot-thin {
  font-size: 12px;
  color: var(--color-text-subtle);
  align-self: center;
  width: 100%;
  text-align: center;
}

.preview-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #2d3748;
}

.validation-tip {
  font-size: 11px;
  color: #e53e3e;
  background: #fff5f5;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #fed7d7;
}

.preview-content {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: #fafafa;
  min-height: 250px;
  padding: 16px;
  overflow-y: auto;
}

.markdown-preview {
  font-size: 14.5px;
  line-height: 1.6;
  color: #2d3748;
}

.markdown-preview h1 { font-size: 20px; border-bottom: 1px solid var(--color-border-subtle); padding-bottom: 8px; margin-top: 0; }
.markdown-preview h2 { font-size: 17px; margin-top: 18px; color: #1a202c; }
.markdown-preview h3 { font-size: 15px; margin-top: 14px; }
.markdown-preview p { margin: 8px 0; }
.markdown-preview ul { padding-left: 20px; margin: 8px 0; }
.markdown-preview li { margin: 4px 0; }
.markdown-preview hr { border: 0; border-top: 1px solid var(--color-border-subtle); margin: 16px 0; }

.char-limit-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.char-limit-row .range-sep {
  color: #718096;
}

.char-limit-row .unit {
  color: #718096;
  font-size: 13.5px;
}
</style>
