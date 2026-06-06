<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Refresh, Tickets, Warning, Brush, Edit } from '@element-plus/icons-vue'
import {
  generateOutline,
  getOutline,
  getCurrentProject,
  updateOutline,
  getArcQueueStale,
  markArcQueueSynced,
  apiErrorMessage,
  ensureNovelQueue,
} from '../api'
import OutlineQueueStatus from '../components/workbench/OutlineQueueStatus.vue'
import NovelProgressHelp from '../components/NovelProgressHelp.vue'
import { useTasksStore } from '../stores/tasks'

const tasksStore = useTasksStore()
const loading = ref(false)
const submitting = ref(false)
const outline = ref<Record<string, any> | null>(null)
const project = ref<any>(null)
const dialogVisible = ref(false)
const editDialogVisible = ref(false)

const viewMode = ref<'mindmap' | 'classic'>('classic')

const form = ref({
  theme: '',
  genre: '',
  target_chapters: 20,
  special_requirements: '',
  overwrite: false,
})
const editForm = ref({
  title: '',
  logline: '',
  genre: '',
  core_theme: '',
  conflict: '',
  protagonist_name: '',
  protagonist_desire: '',
  protagonist_flaw: '',
  protagonist_edge: '',
  protagonist_limit: '',
})

const editGenesVisible = ref(false)
const editGenesForm = ref({
  pleasure_mechanism: '',
  protagonist_arc: '',
  romance_weight: '',
  pacing_baseline: '',
  drift_guards: [] as string[],
})
const newGuard = ref('')
const arcQueueStale = ref<{ stale?: boolean; message?: string } | null>(null)
const arcSyncLoading = ref(false)

const loadArcStale = async () => {
  try {
    const { data } = await getArcQueueStale()
    arcQueueStale.value = data
  } catch {
    arcQueueStale.value = null
  }
}

const syncArcQueue = async () => {
  arcSyncLoading.value = true
  try {
    await ensureNovelQueue()
    await markArcQueueSynced()
    await loadArcStale()
    ElMessage.success('卷队列已按当前大纲同步')
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '同步卷队列失败'))
  } finally {
    arcSyncLoading.value = false
  }
}

const genreGenes = computed(() => outline.value?.genre_genes || {})

// DOM element references for dynamic connections
const nodeRefs = ref<Record<string, HTMLElement>>({})
const connections = ref<Array<{ d: string }>>([])

const title = computed(() => {
  if (outline.value?.chosen_title) {
    return outline.value.chosen_title
  }
  return outline.value ? '【未确定最终小说名，请在上方选择】' : (project.value?.name || '未命名作品')
})
const logline = computed(() => outline.value?.logline || '还没有一句话梗概')
const genre = computed(() => outline.value?.genre_positioning || project.value?.genre || '未设定')
const protagonist = computed(() => outline.value?.protagonist || {})
const arcs = computed(() => outline.value?.macro_outline || outline.value?.volume_arcs || outline.value?.arcs || [])
const promises = computed(() => outline.value?.reader_promise || [])
const targetChapters = computed(() => project.value?.target_chapters || form.value.target_chapters || 20)
const displayIndex = (index: string | number) => Number(index) + 1

const load = async () => {
  loading.value = true
  try {
    const [{ data: outlineData }, { data: projectData }] = await Promise.all([
      getOutline().catch(() => ({ data: {} })),
      getCurrentProject().catch(() => ({ data: null })),
    ])
    project.value = projectData
    outline.value = outlineData && Object.keys(outlineData).length ? outlineData : null
    form.value.theme = outline.value?.core_theme || projectData?.name || ''
    form.value.genre = outline.value?.genre_positioning || projectData?.genre || ''
    form.value.target_chapters = projectData?.target_chapters || 20
    
    // Draw mindmap connections
    if (viewMode.value === 'mindmap' && outline.value) {
      nextTick(() => {
        setTimeout(updateConnections, 300)
      })
    }
    await loadArcStale()
  } finally {
    loading.value = false
  }
}

const updateConnections = () => {
  connections.value = []
  if (viewMode.value !== 'mindmap' || !outline.value) return

  const container = document.querySelector('.mindmap-canvas')
  if (!container) return
  const containerRect = container.getBoundingClientRect()

  const links: Array<[string, string]> = [
    ['center-node', 'branch-arcs'],
  ]

  arcs.value.forEach((_: any, idx: number) => {
    links.push(['branch-arcs', `arc-node-${idx}`])
  })

  links.forEach(([parentId, childId]) => {
    const parentEl = nodeRefs.value[parentId]
    const childEl = nodeRefs.value[childId]

    if (parentEl && childEl) {
      const parentRect = parentEl.getBoundingClientRect()
      const childRect = childEl.getBoundingClientRect()

      const x1 = parentRect.left + parentRect.width - containerRect.left
      const y1 = parentRect.top + parentRect.height / 2 - containerRect.top

      const x2 = childRect.left - containerRect.left
      const y2 = childRect.top + childRect.height / 2 - containerRect.top

      const dx = Math.abs(x2 - x1) * 0.45
      const pathStr = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`
      connections.value.push({ d: pathStr })
    }
  })
}

// Watchers
watch(viewMode, (mode) => {
  if (mode === 'mindmap' && outline.value) {
    nextTick(() => {
      setTimeout(updateConnections, 200)
    })
  }
})

// Listeners for window resize to redrawing
const onResize = () => {
  updateConnections()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})

const submitOutline = async () => {
  if (!form.value.theme.trim()) {
    ElMessage.warning('先填写主题或核心卖点')
    return
  }
  submitting.value = true
  try {
    const { data } = await generateOutline(form.value)
    outline.value = data
    dialogVisible.value = false
    const staged = data.planning_staged ? '（长篇已分段生成卷纲）' : ''
    ElMessage.success(`大纲已生成并保存${staged}`)
    if (data.arc_queue_stale?.stale) {
      ElMessage.warning(data.arc_queue_stale.message || '请同步卷队列后再续跑')
    }
    if ((data.validation_warnings || []).length) {
      ElMessage.warning(data.validation_warnings.join('；'))
    }
    await loadArcStale()
    nextTick(() => {
      setTimeout(updateConnections, 300)
    })
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '大纲生成失败')
  } finally {
    submitting.value = false
  }
}

const openEditDialog = () => {
  const current = outline.value || {}
  const p = current.protagonist || {}
  const titles = current.title_options || []
  editForm.value = {
    title: current.chosen_title || (Array.isArray(titles) ? titles[0] || '' : String(titles || '')),
    logline: current.logline || '',
    genre: current.genre_positioning || project.value?.genre || '',
    core_theme: current.core_theme || '',
    conflict: current.conflict || '',
    protagonist_name: p.name || '',
    protagonist_desire: p.desire || '',
    protagonist_flaw: p.flaw || '',
    protagonist_edge: p.edge || '',
    protagonist_limit: p.limit || '',
  }
  editDialogVisible.value = true
}

const customTitle = ref('')

const selectChosenTitle = async (selectedTitle: string) => {
  if (!selectedTitle || !selectedTitle.trim()) {
    ElMessage.warning('请输入或选择有效的书名')
    return
  }
  if (!outline.value) return
  
  loading.value = true
  try {
    const next = { ...outline.value }
    next.chosen_title = selectedTitle.trim()
    
    const { data } = await updateOutline(next)
    outline.value = data
    ElMessage.success(`书名已确定为「${selectedTitle}」`)
    window.location.reload()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '确定书名失败')
  } finally {
    loading.value = false
  }
}

const saveOutlineBasics = async () => {
  const next = { ...(outline.value || {}) }
  next.title_options = editForm.value.title ? [editForm.value.title] : []
  next.chosen_title = editForm.value.title || ''
  next.logline = editForm.value.logline
  next.genre_positioning = editForm.value.genre
  next.core_theme = editForm.value.core_theme
  next.conflict = editForm.value.conflict
  next.protagonist = {
    ...(next.protagonist || {}),
    name: editForm.value.protagonist_name,
    desire: editForm.value.protagonist_desire,
    flaw: editForm.value.protagonist_flaw,
    edge: editForm.value.protagonist_edge,
    limit: editForm.value.protagonist_limit,
  }
  try {
    const { data } = await updateOutline(next)
    outline.value = data
    editDialogVisible.value = false
    ElMessage.success('基础设定已保存')
    if (data.arc_queue_stale?.stale) {
      ElMessage.warning(data.arc_queue_stale.message || '卷纲已变更，请点「同步卷队列」')
    }
    await loadArcStale()
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
  }
}

const openEditGenes = () => {
  if (!outline.value) {
    ElMessage.warning('暂无小说大纲')
    return
  }
  const genes = genreGenes.value
  editGenesForm.value = {
    pleasure_mechanism: genes.pleasure_mechanism || '',
    protagonist_arc: genes.protagonist_arc || '',
    romance_weight: genes.romance_weight || '',
    pacing_baseline: genes.pacing_baseline || '',
    drift_guards: [...(genes.drift_guards || [])],
  }
  editGenesVisible.value = true
}

const addGuard = () => {
  if (newGuard.value.trim() && !editGenesForm.value.drift_guards.includes(newGuard.value.trim())) {
    editGenesForm.value.drift_guards.push(newGuard.value.trim())
    newGuard.value = ''
  }
}

const removeGuard = (tag: string) => {
  editGenesForm.value.drift_guards = editGenesForm.value.drift_guards.filter(g => g !== tag)
}

const handleSaveGenes = async () => {
  loading.value = true
  try {
    const updatedOutline = {
      ...outline.value,
      genre_genes: {
        pleasure_mechanism: editGenesForm.value.pleasure_mechanism,
        protagonist_arc: editGenesForm.value.protagonist_arc,
        romance_weight: editGenesForm.value.romance_weight,
        pacing_baseline: editGenesForm.value.pacing_baseline,
        drift_guards: editGenesForm.value.drift_guards,
      }
    }
    await updateOutline(updatedOutline)
    ElMessage.success('类型基因修改成功')
    editGenesVisible.value = false
    await load()
  } catch (error: any) {
    ElMessage.error(error.message || '类型基因修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="outline-page" v-loading="loading">
    <header class="page-head">
      <div class="page-title-area">
        <h1>作品大纲</h1>
        <p>设定小说大纲、题材定位、爽点机制与篇章规划。</p>
      </div>
      <div class="head-actions">
        <el-segmented
          v-model="viewMode"
          :options="[
            { label: '思维导图', value: 'mindmap' },
            { label: '传统视图', value: 'classic' }
          ]"
          class="mode-switcher"
          size="small"
        />
        <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
        <el-button size="small" :disabled="!outline || tasksStore.isRunning" @click="openEditDialog">编辑设定</el-button>
        <el-button size="small" type="primary" :icon="DocumentAdd" :disabled="tasksStore.isRunning" @click="dialogVisible = true">{{ outline ? '更新大纲' : '生成大纲' }}</el-button>
      </div>
    </header>

    <NovelProgressHelp />

    <OutlineQueueStatus v-if="outline" />

    <el-alert
      v-if="arcQueueStale?.stale"
      type="warning"
      :closable="false"
      show-icon
      class="arc-stale-alert"
      :title="arcQueueStale?.message || '宏观卷纲与卷队列可能不一致'"
    >
      <template #default>
        <el-button size="small" type="primary" :loading="arcSyncLoading" :disabled="tasksStore.isRunning || arcSyncLoading" @click="syncArcQueue">
          同步卷队列
        </el-button>
      </template>
    </el-alert>

    <div v-if="outline && !outline.chosen_title" class="title-pick-bar">
      <span class="pick-label"><el-icon><Warning /></el-icon> 请确定小说最终名称（确定后开始生成）：</span>
      <div class="pick-options">
        <button
          v-for="opt in (outline.title_options || [])"
          :key="opt"
          class="pick-pill"
          @click="selectChosenTitle(opt)"
        >
          {{ opt }}
        </button>
        <el-input
          v-model="customTitle"
          placeholder="输入自定义名称..."
          size="small"
          style="width: 210px;"
          @keyup.enter="selectChosenTitle(customTitle)"
        >
          <template #append>
            <el-button size="small" @click="selectChosenTitle(customTitle)">确定</el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div v-if="outline" class="outline-body">
      <div class="config-strip config-strip-single">
        <section class="config-card genes-panel">
          <div class="config-card-head">
            <div class="config-card-title">
              <el-icon class="panel-icon genes-color"><Brush /></el-icon>
              <h2>类型基因</h2>
            </div>
            <el-button text type="primary" :icon="Edit" size="small" @click="openEditGenes">编辑</el-button>
          </div>
          <dl class="config-kv">
            <div>
              <dt>爽点机制</dt>
              <dd class="ellipsis">{{ genreGenes?.pleasure_mechanism || '未设定' }}</dd>
            </div>
            <div>
              <dt>主角弧线</dt>
              <dd class="ellipsis">{{ genreGenes?.protagonist_arc || '未设定' }}</dd>
            </div>
            <div>
              <dt>感情线</dt>
              <dd class="ellipsis">{{ genreGenes?.romance_weight || '未设定' }}</dd>
            </div>
            <div>
              <dt>节奏基调</dt>
              <dd class="ellipsis">{{ genreGenes?.pacing_baseline || '未设定' }}</dd>
            </div>
          </dl>
          <div v-if="genreGenes?.drift_guards?.length" class="guard-inline">
            <span class="guard-label">防跑偏</span>
            <el-tag v-for="guard in genreGenes.drift_guards" :key="guard" size="small" type="info">{{ guard }}</el-tag>
          </div>
        </section>
      </div>

      <div class="outline-viewport">
        <!-- 1. Mindmap Interactive Canvas -->
        <div v-if="viewMode === 'mindmap'" class="mindmap-wrapper panel">
          <div class="mindmap-canvas">
            <svg class="canvas-svg">
              <path
                v-for="(link, i) in connections"
                :key="i"
                :d="link.d"
                fill="none"
                stroke="#ffcfbc"
                stroke-width="2.5"
              />
            </svg>

            <div class="mindmap-tree">
              <div class="tree-column center-col">
                <div
                  :ref="el => { if (el) nodeRefs['center-node'] = el as HTMLElement }"
                  class="mm-node root-node"
                >
                  <span class="node-tag">作品中心</span>
                  <h3>{{ title }}</h3>
                  <small>{{ genre }} · {{ targetChapters }} 章</small>
                </div>
              </div>

              <div class="tree-column branches-col">
                <div class="branch-group">
                  <div
                    :ref="el => { if (el) nodeRefs['branch-arcs'] = el as HTMLElement }"
                    class="mm-node branch-node arcs-branch"
                  >
                    <el-icon><Tickets /></el-icon>
                    <strong>推进篇章 (Arcs)</strong>
                  </div>
                  <div class="leaf-nodes">
                    <div
                      v-for="(arc, idx) in arcs"
                      :key="`arc-${idx}`"
                      :ref="el => { if (el) nodeRefs[`arc-node-${idx}`] = el as HTMLElement }"
                      class="mm-node leaf-node arc-node-item"
                    >
                      <span class="arc-badge">Phase {{ displayIndex(idx) }}</span>
                      <strong>{{ arc.title || arc.name || `阶段 ${displayIndex(idx)}` }}</strong>
                      <p>{{ arc.summary || arc.description || arc.goal || arc }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. Classic Card Grid View -->
        <div v-else class="classic-layout">
          <section class="main-panel">
            <div class="title-block">
              <span>{{ outline?.chosen_title ? '最终书名' : '候选书名' }}</span>
              <h2>{{ title }}</h2>
              <p class="logline-clamp">{{ logline }}</p>
            </div>

            <div class="info-grid">
              <article>
                <span>题材</span>
                <strong>{{ genre }}</strong>
              </article>
              <article>
                <span>篇幅</span>
                <strong>{{ targetChapters }} 章</strong>
              </article>
              <article>
                <span>主角</span>
                <strong>{{ protagonist.name || '未设定' }}</strong>
              </article>
              <article>
                <span>冲突</span>
                <strong>{{ outline.conflict || '未设定' }}</strong>
              </article>
            </div>

            <div class="text-pair">
              <section class="text-section">
                <h3>核心主题</h3>
                <p class="text-clamp">{{ outline.core_theme || '暂无' }}</p>
              </section>
              <section class="text-section">
                <h3>主角弧光</h3>
                <p class="text-clamp">{{ protagonist.arc || protagonist.description || '暂无' }}</p>
              </section>
            </div>
          </section>

          <aside class="side-panel">
            <h3>读者承诺</h3>
            <div v-if="promises.length" class="promise-list">
              <span v-for="item in promises" :key="item">{{ item }}</span>
            </div>
            <el-empty v-else description="暂无" :image-size="48" />
          </aside>

          <section class="arc-panel">
            <div class="section-head">
              <h3>卷纲 / 阶段</h3>
              <span>{{ arcs.length }} 阶段</span>
            </div>
            <div v-if="arcs.length" class="arc-scroll">
              <div class="arc-list">
                <article v-for="(arc, index) in arcs" :key="index" class="arc-card">
                  <span>Phase {{ displayIndex(index) }}</span>
                  <strong>{{ arc.title || arc.name || `阶段 ${displayIndex(index)}` }}</strong>
                  <p>{{ arc.summary || arc.description || arc.goal || arc }}</p>
                </article>
              </div>
            </div>
            <el-empty v-else description="暂无阶段" :image-size="48" />
          </section>
        </div>
      </div>
    </div>

    <section v-else-if="!loading" class="empty-outline">
        <el-icon><Tickets /></el-icon>
        <h2>还没有作品大纲</h2>
        <p>生成大纲后，这里会展示书名、卖点、主角脑图和卷纲，工作台只负责运行章节。</p>
        <el-button type="primary" :icon="DocumentAdd" @click="dialogVisible = true">生成大纲</el-button>
    </section>

    <!-- Dialog Forms -->
    <el-dialog v-model="dialogVisible" title="生成作品大纲" width="640px" top="8vh">
      <el-form label-width="110px">
        <el-form-item label="主题/卖点" required>
          <el-input v-model="form.theme" placeholder="例如：现代都市中，女主通过电竞重建自我" />
        </el-form-item>
        <el-form-item label="题材">
          <el-input v-model="form.genre" placeholder="都市 / 玄幻 / 科幻 / 历史..." />
        </el-form-item>
        <el-form-item label="目标章数">
          <el-input-number v-model="form.target_chapters" :min="1" :max="3000" />
        </el-form-item>
        <el-form-item label="额外要求">
          <el-input v-model="form.special_requirements" type="textarea" :rows="5" resize="none" />
        </el-form-item>
        <el-form-item v-if="outline" label="更新方式">
          <el-radio-group v-model="form.overwrite">
            <el-radio :value="false">基于当前大纲补全（保留书名和主角）</el-radio>
            <el-radio :value="true">覆盖重生成</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="tasksStore.isRunning || submitting" @click="submitOutline">生成并保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑基础设定" width="720px" top="6vh">
      <el-form label-width="110px">
        <el-form-item label="作品名">
          <el-input v-model="editForm.title" placeholder="例如：《她与枪火》" />
        </el-form-item>
        <el-form-item label="一句话梗概">
          <el-input v-model="editForm.logline" />
        </el-form-item>
        <el-form-item label="题材定位">
          <el-input v-model="editForm.genre" />
        </el-form-item>
        <el-form-item label="核心主题">
          <el-input v-model="editForm.core_theme" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="核心冲突">
          <el-input v-model="editForm.conflict" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="主角名">
          <el-input v-model="editForm.protagonist_name" />
        </el-form-item>
        <el-form-item label="主角目标">
          <el-input v-model="editForm.protagonist_desire" />
        </el-form-item>
        <el-form-item label="主角缺陷">
          <el-input v-model="editForm.protagonist_flaw" />
        </el-form-item>
        <el-form-item label="主角优势">
          <el-input v-model="editForm.protagonist_edge" />
        </el-form-item>
        <el-form-item label="主角限制">
          <el-input v-model="editForm.protagonist_limit" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveOutlineBasics">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑基因 Dialog -->
    <el-dialog v-model="editGenesVisible" title="编辑类型基因" width="600px" top="10vh">
      <el-form label-width="110px">
        <el-form-item label="爽点机制">
          <el-input v-model="editGenesForm.pleasure_mechanism" placeholder="如：金手指升级、打脸爽感" />
        </el-form-item>
        <el-form-item label="主角弧线">
          <el-input v-model="editGenesForm.protagonist_arc" placeholder="如：平民崛起、复仇救赎" />
        </el-form-item>
        <el-form-item label="感情线权重">
          <el-input v-model="editGenesForm.romance_weight" placeholder="如：单女主、轻感情重事业" />
        </el-form-item>
        <el-form-item label="节奏基调">
          <el-input v-model="editGenesForm.pacing_baseline" placeholder="如：快节奏爽文、慢热升级" />
        </el-form-item>
        <el-form-item label="防跑偏守护线">
          <div style="display: flex; gap: 10px; margin-bottom: 10px;">
            <el-input v-model="newGuard" placeholder="新增规则，如：绝不虐主、智商在线" @keyup.enter="addGuard" />
            <el-button type="primary" @click="addGuard">添加</el-button>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <el-tag
              v-for="guard in editGenesForm.drift_guards"
              :key="guard"
              closable
              @close="removeGuard(guard)"
            >
              {{ guard }}
            </el-tag>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editGenesVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveGenes">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.outline-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 72px);
  overflow: hidden;
}

.main-panel,
.side-panel,
.arc-panel,
.empty-outline,
.mindmap-wrapper,
.config-card {
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}



.hero-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.mode-switcher {
  margin-right: 2px;
}

.outline-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.config-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  flex-shrink: 0;
}

.config-strip-single {
  grid-template-columns: minmax(0, 1fr);
}

.config-card {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.config-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.config-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.config-card-title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: #111827;
}

.panel-icon.scale-color { color: #409eff; font-size: 16px; }
.panel-icon.genes-color { color: #67c23a; font-size: 16px; }

.config-hint {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.config-kv {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px 10px;
  margin: 0;
}

.config-kv dt {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-subtle);
  font-weight: 600;
}

.config-kv dd {
  margin: 2px 0 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.config-kv .kv-span-2 {
  grid-column: span 2;
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.config-warn {
  margin: 0;
  font-size: 11px;
  color: var(--color-warning);
}

.guard-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.guard-label {
  font-size: 11px;
  color: var(--color-text-subtle);
  flex-shrink: 0;
}

.outline-viewport {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* MINDMAP — 限制在视口内，仅画布区滚动 */
.mindmap-wrapper {
  flex: 1;
  min-height: 0;
  padding: 12px;
  overflow: auto;
  background: var(--color-bg-surface-muted);
}

.mindmap-canvas {
  position: relative;
  min-width: 1100px;
  min-height: 520px;
  padding: 8px;
}

.canvas-svg {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.mindmap-tree {
  position: relative;
  display: flex;
  gap: 120px;
  z-index: 5;
  min-height: 480px;
}

.tree-column {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.center-col {
  width: 260px;
  flex-shrink: 0;
}

.branches-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 60px;
  justify-content: space-around;
}

.branch-group {
  display: flex;
  align-items: center;
  gap: 120px;
}

/* Nodes Base Style */
.mm-node {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px 18px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 0.2s ease;
}

.mm-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(198, 111, 79, 0.08);
  border-color: #ffbba1;
}

/* Node Variants */
.root-node {
  border: 2px solid var(--primary);
  box-shadow: 0 10px 28px rgba(198, 111, 79, 0.1);
  padding: 20px;
}

.root-node h3 {
  margin: 4px 0;
  font-size: 20px;
  color: var(--color-text-strong);
}

.root-node small {
  color: var(--text-muted);
}

.node-tag {
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 800;
  color: var(--primary);
  letter-spacing: 1px;
}

.branch-node {
  width: 180px;
  flex-direction: row !important;
  align-items: center;
  gap: 8px !important;
  font-size: 15px;
  color: var(--color-text-strong);
  border-left: 4px solid var(--color-text-subtle);
  flex-shrink: 0;
}

.arcs-branch { border-left-color: #8b5cf6; }

.leaf-nodes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 320px;
}

.leaf-node {
  border-radius: 6px;
  padding: 10px 14px;
}

.leaf-node p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.leaf-node strong {
  font-size: 14px;
  color: var(--color-text-strong);
}

.arc-node-item {
  border-left: 3px solid #f3e8ff;
  background: #faf5ff;
  max-width: 440px;
}

.arc-node-item strong {
  color: #6b21a8;
  font-size: 14.5px;
  margin: 4px 0;
}

.arc-node-item p {
  color: #582787;
}

.arc-badge {
  font-size: 10px;
  font-weight: 800;
  color: #a855f7;
  text-transform: uppercase;
}

/* CLASSIC — 三行网格，卷纲区内部滚动 */
.classic-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px;
}

.main-panel,
.side-panel,
.arc-panel {
  padding: 12px 14px;
  min-height: 0;
}

.main-panel {
  grid-row: 1;
  grid-column: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.side-panel {
  grid-row: 1;
  grid-column: 2;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.arc-panel {
  grid-column: 1 / -1;
  grid-row: 2;
  max-height: 168px;
  display: flex;
  flex-direction: column;
}

.title-block span,
.info-grid span,
.arc-card span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.title-block h2 {
  margin: 2px 0 0;
  color: #111827;
  font-size: 18px;
  line-height: 1.25;
}

.logline-clamp,
.text-clamp,
.arc-card p {
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 0;
  font-size: 13.5px;
}

.logline-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.info-grid article {
  padding: 8px 10px;
  border: 1px solid #e5eaf2;
  border-radius: 6px;
  background: var(--color-bg-surface-muted);
}

.info-grid strong {
  display: block;
  margin-top: 4px;
  color: #111827;
  font-size: 13.5px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.text-section {
  padding: 8px 10px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 6px;
  background: var(--color-bg-surface-muted);
  min-height: 0;
  overflow: hidden;
}

.text-section h3,
.side-panel h3,
.section-head h3 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 13px;
}

.text-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.promise-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  overflow: auto;
  flex: 1;
  min-height: 0;
  align-content: flex-start;
}

.promise-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff4ee;
  color: #a55236;
  font-size: 12.5px;
  font-weight: 650;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 12px;
  flex-shrink: 0;
  margin-bottom: 6px;
}

.arc-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.arc-list {
  display: flex;
  gap: 10px;
  padding-bottom: 4px;
}

.arc-card {
  flex: 0 0 220px;
  padding: 10px;
  border: 1px solid #e5eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.arc-card strong {
  display: block;
  margin: 4px 0;
  color: #111827;
  font-size: 13px;
}

.arc-card p {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-outline {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 48px 24px;
  text-align: center;
  flex: 1;
}

@media (max-width: 1280px) {
  .config-kv {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .classic-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }

  .side-panel {
    grid-column: 1;
    grid-row: 2;
    max-height: 100px;
  }

  .arc-panel {
    grid-row: 3;
  }

  .info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.empty-outline .el-icon {
  color: #c66f4f;
  font-size: 42px;
}

.empty-outline h2 {
  margin: 0;
  color: #111827;
}

.empty-outline p {
  max-width: 560px;
  margin: 0;
  color: var(--color-text-muted);
}

/* 拟物确定书名条 */
.title-pick-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #fdfaf2;
  border: 1px solid #f2e3d0;
  border-radius: 8px;
  padding: 8px 12px;
  flex-shrink: 0;
}

.pick-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #a55236;
  font-weight: 700;
  font-size: 14px;
}

.pick-options {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pick-pill {
  border: 1px solid #f0c9b7;
  background: var(--color-bg-surface);
  color: #9a5033;
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pick-pill:hover {
  background: #fff4ee;
  color: #c66f4f;
  border-color: #c66f4f;
  transform: translateY(-1px);
}
</style>
