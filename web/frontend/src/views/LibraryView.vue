<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Document, Plus, Reading, Download, Upload } from '@element-plus/icons-vue'
import EmptyStatePanel from '../components/EmptyStatePanel.vue'
import { useProjectStore } from '../stores/project'
import {
  exportNovel,
  exportProjectZip,
  importProjectZip,
  getProjectCoverUrl,
  suggestCoverPrompt,
  generateCover,
  saveCover,
  rewriteDescription,
  updateDescription,
  listModels,
  getOutline,
  pinProject,
  apiErrorMessage,
} from '../api'
import type { Project } from '../stores/project'

const MAX_PINNED = 10
const searchQuery = ref('')
const pinningId = ref<string | null>(null)

const router = useRouter()
const projectStore = useProjectStore()

const detailsVisible = ref(false)
const selectedProject = ref<any>(null)
const exportingZip = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  await projectStore.fetchProjects()
})

const channelLabel = (id?: string) => {
  if (!id) return ''
  const map: Record<string, string> = { general: '通用', male: '男频', female: '女频', custom: '自定' }
  return map[id] || ''
}

const pinnedCount = computed(
  () => projectStore.projects.filter((p) => p.pinned).length,
)

const displayedProjects = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let list = projectStore.projects
  if (q) {
    list = list.filter((p) => {
      const hay = [
        p.name,
        p.description,
        p.genre,
        channelLabel(p.channel),
        p.id,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return hay.includes(q)
    })
  }
  return list
})

const togglePin = async (project: Project, event: Event) => {
  event.stopPropagation()
  if (!project.pinned && pinnedCount.value >= MAX_PINNED) {
    ElMessage.warning(`最多置顶 ${MAX_PINNED} 本书，请先取消其它置顶`)
    return
  }
  pinningId.value = project.id
  try {
    await pinProject(project.id, !project.pinned)
    await projectStore.fetchProjects()
    ElMessage.success(project.pinned ? '已取消置顶' : '已置顶')
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '操作失败'))
  } finally {
    pinningId.value = null
  }
}

const openPendingMaintenance = async (project: Project, event: Event) => {
  event.stopPropagation()
  try {
    await projectStore.switchProject(project.id)
    await router.push('/chapters/maintenance?expand=alerts')
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '打开修章维护失败'))
  }
}

const openProject = async (id: string) => {
  await projectStore.switchProject(id)
  try {
    const { data } = await getOutline()
    const outline = data && typeof data === 'object' ? data : {}
    const hasTitle = Boolean(outline.chosen_title)
    const hasMacro = Array.isArray(outline.macro_outline) && outline.macro_outline.length > 0
    if (!hasTitle || !hasMacro) {
      router.push('/outline')
      return
    }
  } catch {
    router.push('/outline')
    return
  }
  router.push('/workspace')
}

const openDetails = (project: any) => {
  selectedProject.value = project
  detailsVisible.value = true
}

const goCreate = async () => {
  await router.push('/create')
}

const handleDelete = async (id: string, name: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${name}」吗？所有章节和数据都会被删除。`,
      '删除小说',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'error' },
    )
    await projectStore.deleteProject(id)
    ElMessage.success('已删除')
    if (selectedProject.value?.id === id) {
      detailsVisible.value = false
    }
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(apiErrorMessage(error, '删除失败'))
  }
}

const handleRead = async (id: string) => {
  try {
    await projectStore.switchProject(id)
    router.push('/reader')
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '打开阅读失败'))
  }
}

const handleExportFormat = async (format: string, project: any) => {
  try {
    ElMessage.info(`正在准备导出为 ${format} 格式，请稍候...`)
    const res = await exportNovel({
      format,
      title: project.name,
      project_id: project.id
    })
    const blob = new Blob([res.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const ext = format === 'markdown' ? 'md' : format
    link.setAttribute('download', `${project.name}.${ext}`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error: any) {
    ElMessage.error('导出失败: ' + apiErrorMessage(error, '导出失败'))
  }
}

const handleExportZip = async (pid: string) => {
  try {
    exportingZip.value = true
    const res = await exportProjectZip(pid)
    const blob = new Blob([res.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    const proj = projectStore.projects.find(p => p.id === pid)
    const filename = `${proj?.name || pid}.zip`
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出项目包成功')
  } catch (error: any) {
    ElMessage.error('导出项目包失败: ' + apiErrorMessage(error, '导出项目包失败'))
  } finally {
    exportingZip.value = false
  }
}

const triggerUpload = () => {
  fileInput.value?.click()
}

const handleImportZip = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    ElMessage.info('正在导入项目包，请稍候...')
    await importProjectZip(formData)
    ElMessage.success('导入成功！')
    await projectStore.fetchProjects()
  } catch (error: any) {
    ElMessage.error('导入失败: ' + apiErrorMessage(error, '导入失败'))
  } finally {
    if (fileInput.value) fileInput.value.value = ''
  }
}

const formatDate = (iso?: string) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

/** 书库封面：带年份的更新日期 */
const formatCardDate = (iso?: string) => {
  if (!iso) return '暂无'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '暂无'
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

/** 书库封面左下角：时:分 */
const formatCardTime = (iso?: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${min}`
}

const lastEditIso = (project: Project) => project.activity_at || project.updated_at

const lastEditLabel = (project: Project) => formatCardDate(lastEditIso(project))

const lastEditTime = (project: Project) => formatCardTime(lastEditIso(project))

const lastEditTitle = (project: Project) => {
  const date = lastEditLabel(project)
  const time = lastEditTime(project)
  if (date === '暂无') return '更新时间未知'
  return time ? `更新 ${date} ${time}` : `更新 ${date}`
}

const getCoverClass = (channel?: string) => {
  if (channel === 'male') return 'cover-male'
  if (channel === 'female') return 'cover-female'
  if (channel === 'custom') return 'cover-custom'
  return 'cover-general'
}

const formatWords = (words?: number) => {
  if (!words) return '0字'
  if (words >= 10000) {
    return (words / 10000).toFixed(1) + '万字'
  }
  return words + '字'
}

const coverTimestamps = ref<Record<string, number>>({})

const getCoverUrl = (pid: string) => {
  const t = coverTimestamps.value[pid] || ''
  return `${getProjectCoverUrl(pid)}?t=${t}`
}

const getCoverStyle = (project: any) => {
  if (project.has_cover) {
    return {
      background: `linear-gradient(to bottom, rgba(0, 0, 0, 0.28), rgba(0, 0, 0, 0.1) 40%, rgba(0, 0, 0, 0.58)), url(${getCoverUrl(project.id)}) center/cover no-repeat`
    }
  }
  return {}
}

// AI 简介重写
const rewriteVisible = ref(false)
const rewriteStyle = ref('爽文吸睛')
const userPreference = ref('')
const rewriteLoading = ref(false)
const rewrittenDesc = ref('')

const openDescriptionRewriter = () => {
  if (!selectedProject.value) return
  rewrittenDesc.value = ''
  userPreference.value = ''
  rewriteStyle.value = '爽文吸睛'
  rewriteVisible.value = true
}

const handleRewrite = async () => {
  if (!selectedProject.value) return
  rewriteLoading.value = true
  try {
    const { data } = await rewriteDescription(selectedProject.value.id, {
      old_description: selectedProject.value.description || '',
      style: rewriteStyle.value,
      user_preference: userPreference.value
    })
    rewrittenDesc.value = data.description
    ElMessage.success('简介已重写！')
  } catch (error: any) {
    ElMessage.error('重写失败: ' + apiErrorMessage(error, '重写失败'))
  } finally {
    rewriteLoading.value = false
  }
}

const copyDescription = async (text?: string) => {
  const desc = text || selectedProject.value?.description || ''
  if (!desc) {
    ElMessage.warning('没有简介可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(desc)
    ElMessage.success('简介已成功复制到剪贴板！')
  } catch (error) {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

const applyDescription = async () => {
  if (!selectedProject.value || !rewrittenDesc.value) return
  try {
    await updateDescription(selectedProject.value.id, rewrittenDesc.value)
    selectedProject.value.description = rewrittenDesc.value
    await projectStore.fetchProjects()
    ElMessage.success('简介应用成功！已更新作品库。')
    rewriteVisible.value = false
  } catch (error: any) {
    ElMessage.error('应用简介失败: ' + apiErrorMessage(error, '应用简介失败'))
  }
}

// 封面管理
const coverManagerVisible = ref(false)
const imageModels = ref<any[]>([])
const selectedImageModel = ref('')
const coverPrompt = ref('')
const generatingPrompt = ref(false)
const coverGenerating = ref(false)
const generatedRawImage = ref('')

// 裁剪器
const cropImageSrc = ref('')
const cropperImg = ref<HTMLImageElement | null>(null)
const scale = ref(1.0)
const minScale = ref(0.1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStart = { x: 0, y: 0 }
const savingCover = ref(false)
const fileInputCover = ref<HTMLInputElement | null>(null)

const openCoverManager = async () => {
  if (!selectedProject.value) return
  generatedRawImage.value = ''
  cropImageSrc.value = ''
  coverPrompt.value = ''
  selectedImageModel.value = ''
  
  try {
    const { data } = await listModels()
    imageModels.value = data.filter((m: any) => m.type === 'image')
    if (imageModels.value.length > 0) {
      selectedImageModel.value = imageModels.value[0].id
    }
  } catch (error) {
    console.error('拉取模型库失败', error)
  }
  
  coverManagerVisible.value = true
}

const handleSuggestCoverPrompt = async () => {
  if (!selectedProject.value) return
  generatingPrompt.value = true
  try {
    const { data } = await suggestCoverPrompt(selectedProject.value.id)
    coverPrompt.value = data.prompt
    ElMessage.success('画图提示词生成成功！')
  } catch (error: any) {
    ElMessage.error('提示词生成失败: ' + apiErrorMessage(error, '提示词生成失败'))
  } finally {
    generatingPrompt.value = false
  }
}

const handleGenerateCover = async () => {
  if (!selectedProject.value) return
  if (!selectedImageModel.value) {
    ElMessage.warning('请选择图像模型。若没有模型，请先去模型库配置。')
    return
  }
  if (!coverPrompt.value.trim()) {
    ElMessage.warning('画图提示词不能为空')
    return
  }
  coverGenerating.value = true
  try {
    const { data } = await generateCover(selectedProject.value.id, {
      model_id: selectedImageModel.value,
      prompt: coverPrompt.value
    })
    generatedRawImage.value = data.image
    cropImageSrc.value = data.image
    ElMessage.success('封面图片生成成功！现在可以进行裁剪。')
  } catch (error: any) {
    ElMessage.error('封面生成失败: ' + apiErrorMessage(error, '封面生成失败'))
  } finally {
    coverGenerating.value = false
  }
}

const triggerCoverUpload = () => {
  fileInputCover.value?.click()
}

const handleCoverFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (event) => {
    if (event.target?.result) {
      cropImageSrc.value = event.target.result as string
      generatedRawImage.value = ''
      ElMessage.success('本地图片加载成功！请在裁剪框中调整。')
    }
  }
  reader.readAsDataURL(file)
}

const initCropper = () => {
  if (!cropperImg.value) return
  const img = cropperImg.value
  const wRatio = 300 / img.naturalWidth
  const hRatio = 400 / img.naturalHeight
  const initialScale = Math.max(wRatio, hRatio)
  scale.value = initialScale
  minScale.value = initialScale * 0.4
  translateX.value = 0
  translateY.value = 0
}

const handleMouseDown = (e: MouseEvent) => {
  isDragging.value = true
  dragStart.x = e.clientX - translateX.value
  dragStart.y = e.clientY - translateY.value
}

const handleMouseMove = (e: MouseEvent) => {
  if (!isDragging.value) return
  translateX.value = e.clientX - dragStart.x
  translateY.value = e.clientY - dragStart.y
}

const handleMouseUp = () => {
  isDragging.value = false
}

const handleTouchStart = (e: TouchEvent) => {
  if (e.touches.length !== 1) return
  isDragging.value = true
  dragStart.x = e.touches[0].clientX - translateX.value
  dragStart.y = e.touches[0].clientY - translateY.value
}

const handleTouchMove = (e: TouchEvent) => {
  if (!isDragging.value || e.touches.length !== 1) return
  translateX.value = e.touches[0].clientX - dragStart.x
  translateY.value = e.touches[0].clientY - dragStart.y
}

const handleSaveCover = async () => {
  if (!selectedProject.value) return
  if (!cropImageSrc.value) {
    ElMessage.warning('没有可裁剪的图片')
    return
  }
  
  savingCover.value = true
  try {
    const croppedBase64 = await new Promise<string>((resolve, reject) => {
      if (!cropperImg.value) return reject('No image')
      const img = cropperImg.value
      const canvas = document.createElement('canvas')
      canvas.width = 600
      canvas.height = 800
      const ctx = canvas.getContext('2d')
      if (!ctx) return reject('No canvas context')
      
      ctx.fillStyle = 'var(--color-bg-surface)'
      ctx.fillRect(0, 0, 600, 800)
      
      const factor = 600 / 300
      ctx.save()
      ctx.translate(300 + translateX.value * factor, 400 + translateY.value * factor)
      ctx.scale(scale.value * factor, scale.value * factor)
      ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2)
      ctx.restore()
      
      resolve(canvas.toDataURL('image/jpeg', 0.9))
    })
    
    await saveCover(selectedProject.value.id, croppedBase64)
    coverTimestamps.value[selectedProject.value.id] = Date.now()
    selectedProject.value.has_cover = true
    await projectStore.fetchProjects()
    ElMessage.success('封面图片已成功裁剪并保存！')
    coverManagerVisible.value = false
  } catch (error: any) {
    ElMessage.error('保存封面失败: ' + apiErrorMessage(error, '保存封面失败'))
  } finally {
    savingCover.value = false
  }
}
</script>

<template>
  <section class="library-page">
    <header class="page-head">
      <div class="page-title-area">
        <h1>我的书库</h1>
        <p>选择项目继续创作，或用预设创建一本新小说。</p>
      </div>
      <div class="header-actions">
        <el-input
          v-if="projectStore.projects.length > 0"
          v-model="searchQuery"
          class="library-search"
          placeholder="搜索书名、题材、简介…"
          clearable
        />
        <el-button type="warning" plain :icon="Upload" @click="triggerUpload">导入项目包</el-button>
        <el-button type="primary" :icon="Plus" @click="goCreate">新建小说</el-button>
        <input
          type="file"
          ref="fileInput"
          accept=".zip"
          style="display: none"
          @change="handleImportZip"
        />
      </div>
    </header>

    <EmptyStatePanel
      v-if="projectStore.projects.length === 0"
      class="empty-library"
      :icon="Document"
      title="还没有小说项目"
      description="创建项目后即可进入多 Agent 工作台。"
      :actions="[
        { label: '导入项目包', type: 'warning', plain: true, icon: Upload, onClick: triggerUpload },
        { label: '新建小说', type: 'primary', icon: Plus, onClick: goCreate },
      ]"
    />

    <p
      v-if="projectStore.projects.length > 0 && searchQuery.trim()"
      class="search-hint"
    >
      共 {{ projectStore.projects.length }} 本，筛选 {{ displayedProjects.length }} 本
      <span v-if="pinnedCount > 0"> · 已置顶 {{ pinnedCount }}/{{ MAX_PINNED }}</span>
    </p>

    <div v-if="projectStore.projects.length > 0 && displayedProjects.length === 0" class="search-empty">
      <p>没有匹配「{{ searchQuery }}」的作品</p>
      <el-button text type="primary" @click="searchQuery = ''">清空搜索</el-button>
    </div>

    <div v-else-if="projectStore.projects.length > 0" class="project-grid">
      <article
        v-for="project in displayedProjects"
        :key="project.id"
        class="project-card"
        :class="{ 'is-pinned': project.pinned }"
        @click="openProject(project.id)"
      >
        <div class="book-spine" aria-hidden="true" />
        <div class="book-spine-shadow" aria-hidden="true" />
        <!-- 书本封面 -->
        <div class="book-cover" :class="[getCoverClass(project.channel), { 'has-cover': project.has_cover }]" :style="getCoverStyle(project)">
          <button
            type="button"
            class="pin-btn"
            :class="{ active: project.pinned }"
            :title="project.pinned ? '取消置顶' : '置顶（最多 10 本）'"
            :disabled="pinningId === project.id"
            @click="togglePin(project, $event)"
          >
            <span class="pin-glyph" aria-hidden="true" />
          </button>
          <!-- 封面内容设计 -->
          <div class="cover-design">
            <span class="genre-badge" v-if="project.genre">{{ project.genre }}</span>
            <button
              v-if="(project.pending_alert_count || 0) > 0"
              type="button"
              class="pending-badge"
              :title="`有 ${project.pending_alert_count} 章待处理，点击直达修章维护`"
              @click="openPendingMaintenance(project, $event)"
            >
              待处理 {{ project.pending_alert_count }} 章
            </button>
            <h2 class="book-title" @click.stop="openDetails(project)">{{ project.name }}</h2>
          </div>
          
          <!-- 封面底部元数据 & 操作 -->
          <div class="cover-footer">
            <div class="book-meta">
              <p class="meta-inline-stats">
                <span class="meta-inline-item">{{ project.chapter_count || 0 }} 章</span>
                <span class="meta-sep" aria-hidden="true">·</span>
                <span class="meta-inline-item">{{ formatWords(project.total_words) }}</span>
              </p>
              <p class="meta-updated" :title="lastEditTitle(project)">
                更新 {{ lastEditLabel(project) }}
              </p>
            </div>

            <div class="cover-footer-bottom" @click.stop>
              <span v-if="lastEditTime(project)" class="meta-time">{{ lastEditTime(project) }}</span>
              <span v-else class="meta-time meta-time--empty">--:--</span>
              <div class="book-actions">
                <el-button
                  class="action-btn read-btn"
                  text
                  size="small"
                  :icon="Reading"
                  @click="handleRead(project.id)"
                />
                <el-dropdown
                  trigger="click"
                  @command="(fmt: string) => handleExportFormat(fmt, project)"
                >
                  <el-button
                    class="action-btn export-btn"
                    text
                    size="small"
                    :icon="Download"
                  />
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="markdown">导出为 Markdown (.md)</el-dropdown-item>
                      <el-dropdown-item command="docx">导出为 Word (.docx)</el-dropdown-item>
                      <el-dropdown-item command="txt">导出为 文本 (.txt)</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button
                  class="action-btn delete-btn"
                  text
                  size="small"
                  :icon="Delete"
                  @click="handleDelete(project.id, project.name)"
                />
              </div>
            </div>
          </div>
        </div>
      </article>
    </div>

    <!-- 书籍详细介绍对话框 -->
    <el-dialog
      v-model="detailsVisible"
      :title="selectedProject?.name || '书籍详情'"
      width="560px"
      destroy-on-close
      align-center
    >
      <div v-if="selectedProject" class="book-details-content">
        <div 
          class="details-cover-preview" 
          :class="getCoverClass(selectedProject.channel)"
          :style="selectedProject.has_cover ? { background: 'linear-gradient(to bottom, rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.45)), url(' + getCoverUrl(selectedProject.id) + ') center/cover no-repeat' } : {}"
        >
          <div class="preview-design">
            <span class="preview-genre" v-if="selectedProject.genre">{{ selectedProject.genre }}</span>
            <h3 class="preview-title">{{ selectedProject.name }}</h3>
          </div>
          <el-button 
            type="warning" 
            size="small" 
            :icon="Plus" 
            @click="openCoverManager"
            style="position: absolute; right: 16px; bottom: 16px; z-index: 10;"
          >
            更换封面
          </el-button>
        </div>
        
        <div class="details-info-grid">
          <div class="info-item full-width">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span class="info-label">作品简介</span>
              <div style="display: flex; gap: 8px;">
                <el-button size="small" type="primary" link @click="copyDescription()">复制简介</el-button>
                <el-button size="small" type="warning" link @click="openDescriptionRewriter">AI 重写</el-button>
              </div>
            </div>
            <p class="info-value desc-text">{{ selectedProject.description || '暂无简介' }}</p>
          </div>
          <div class="info-item">
            <span class="info-label">作品题材</span>
            <span class="info-value">{{ selectedProject.genre || '未设置' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">频道/受众</span>
            <span class="info-value">{{ channelLabel(selectedProject.channel) || '通用' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">已生成章节</span>
            <span class="info-value">{{ selectedProject.chapter_count || 0 }} 章 / 目标 {{ selectedProject.target_chapters || '-' }} 章</span>
          </div>
          <div class="info-item">
            <span class="info-label">总字数</span>
            <span class="info-value">{{ formatWords(selectedProject.total_words) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatDate(selectedProject.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">上次更新</span>
            <span class="info-value">{{ formatDate(selectedProject.updated_at) }}</span>
          </div>
        </div>
        
        <div class="details-actions">
          <el-button
            type="primary"
            :icon="Download"
            :loading="exportingZip"
            @click="handleExportZip(selectedProject.id)"
          >
            导出完整项目包 (.zip)
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- AI 简介重写对话框 -->
    <el-dialog
      v-model="rewriteVisible"
      title="AI 重写小说简介"
      width="600px"
      append-to-body
      align-center
    >
      <div v-if="selectedProject" style="display: flex; flex-direction: column; gap: 16px;">
        <div>
          <span style="font-weight: 600; font-size: 13.5px; color: var(--color-text-muted); display: block; margin-bottom: 8px;">原简介</span>
          <el-input
            type="textarea"
            v-model="selectedProject.description"
            rows="3"
            placeholder="当前简介内容"
            disabled
          />
        </div>
        
        <div style="display: flex; gap: 20px; align-items: center;">
          <span style="font-weight: 600; font-size: 13.5px; color: var(--color-text-muted); width: 70px;">重写风格:</span>
          <el-radio-group v-model="rewriteStyle">
            <el-radio value="爽文吸睛">爽文吸睛</el-radio>
            <el-radio value="悬疑勾人">悬疑勾人</el-radio>
            <el-radio value="宏大叙事">宏大叙事</el-radio>
            <el-radio value="轻松搞笑">轻松搞笑</el-radio>
          </el-radio-group>
        </div>
        
        <div>
          <span style="font-weight: 600; font-size: 13.5px; color: var(--color-text-muted); display: block; margin-bottom: 8px;">修改偏好 (例如：带有一点吐槽元素、强调男主心路历程)</span>
          <el-input
            v-model="userPreference"
            placeholder="可选，请输入微调指令"
          />
        </div>
        
        <div style="text-align: right;">
          <el-button type="warning" :loading="rewriteLoading" @click="handleRewrite">
            AI 一键重写
          </el-button>
        </div>
        
        <div v-if="rewrittenDesc">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong);">AI 重写结果 (番茄平台常规字数长度)</span>
            <div style="display: flex; gap: 8px;">
              <el-button size="small" type="primary" plain @click="copyDescription(rewrittenDesc)">复制</el-button>
              <el-button size="small" type="success" @click="applyDescription">保存并应用</el-button>
            </div>
          </div>
          <el-input
            type="textarea"
            v-model="rewrittenDesc"
            rows="6"
            placeholder="重写后的内容将在此展示"
          />
        </div>
      </div>
    </el-dialog>

    <!-- 封面管理与裁剪对话框 -->
    <el-dialog
      v-model="coverManagerVisible"
      title="封面管理与裁剪"
      width="680px"
      append-to-body
      align-center
    >
      <div v-if="selectedProject" style="display: grid; grid-template-columns: 320px 1fr; gap: 24px;">
        <!-- 左侧：3:4 交互裁剪器区域 -->
        <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
          <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong);">3:4 封面裁剪预览</span>
          
          <div 
            v-if="cropImageSrc"
            class="crop-viewport" 
            style="width: 270px; height: 360px; overflow: hidden; position: relative; border: 2px solid var(--color-border); border-radius: 8px; background: var(--color-text-strong); cursor: move; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
            @touchstart="handleTouchStart"
            @touchmove="handleTouchMove"
            @touchend="handleMouseUp"
          >
            <img 
              :src="cropImageSrc" 
              ref="cropperImg" 
              @load="initCropper"
              :style="{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: 'auto',
                height: 'auto',
                maxWidth: 'none',
                transform: 'translate(-50%, -50%) translate(' + translateX + 'px, ' + translateY + 'px) scale(' + scale + ')',
                pointerEvents: 'none'
              }"
            />
          </div>
          <div v-else style="width: 270px; height: 360px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--color-bg-surface-muted); border: 2px dashed var(--color-border); border-radius: 8px; color: var(--color-text-subtle); text-align: center; padding: 16px;">
            <el-icon :size="40"><Document /></el-icon>
            <span style="margin-top: 12px; font-size: 13px;">请选择本地图片或使用图像大模型生成，随后在此裁剪。</span>
          </div>
          
          <!-- 缩放滑动条 -->
          <div v-if="cropImageSrc" style="width: 270px; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 12px; color: var(--color-text-muted);">缩放</span>
            <el-slider v-model="scale" :min="minScale" :max="scale * 4" :step="0.01" :show-tooltip="false" style="flex: 1;" />
          </div>
          
          <el-button v-if="cropImageSrc" type="primary" :loading="savingCover" @click="handleSaveCover" style="width: 270px; margin-top: 8px;">
            确认并保存封面
          </el-button>
        </div>
        
        <!-- 右侧：AI 生成与上传方式 -->
        <div style="display: flex; flex-direction: column; gap: 16px; border-left: 1px solid var(--color-border); padding-left: 20px;">
          <div>
            <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong); display: block; margin-bottom: 12px;">方式一：AI 图像大模型生成</span>
            
            <div style="margin-bottom: 12px;">
              <span style="font-size: 13px; color: var(--color-text-muted); display: block; margin-bottom: 6px;">选择已配置的图像模型</span>
              <el-select v-model="selectedImageModel" placeholder="选择已配置的图像模型" style="width: 100%;">
                <el-option
                  v-for="model in imageModels"
                  :key="model.id"
                  :label="model.name || model.id"
                  :value="model.id"
                />
              </el-select>
              <small v-if="imageModels.length === 0" style="color: var(--color-danger); display: block; margin-top: 4px;">
                模型库内未检测到图像模型，请先去“模型库”中添加配置。
              </small>
            </div>
            
            <div style="margin-bottom: 12px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 13px; color: var(--color-text-muted);">画图提示词 (Prompt)</span>
                <el-button size="small" type="warning" plain :loading="generatingPrompt" @click="handleSuggestCoverPrompt">
                  自动推荐提示词
                </el-button>
              </div>
              <el-input
                type="textarea"
                v-model="coverPrompt"
                rows="4"
                placeholder="例如：中国水墨画风格，气势磅礴，一位白衣剑仙立于云巅之上..."
              />
            </div>
            
            <el-button 
              type="warning" 
              :loading="coverGenerating" 
              :disabled="imageModels.length === 0 || !coverPrompt.trim()"
              @click="handleGenerateCover"
              style="width: 100%;"
            >
              生成封面原图
            </el-button>
          </div>
          
          <div style="border-top: 1px dashed var(--color-border); padding-top: 16px; margin-top: 8px;">
            <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong); display: block; margin-bottom: 12px;">方式二：本地文件上传</span>
            <el-button type="info" plain :icon="Upload" @click="triggerCoverUpload" style="width: 100%;">
              上传本地图片
            </el-button>
            <input
              type="file"
              ref="fileInputCover"
              accept="image/*"
              style="display: none"
              @change="handleCoverFileChange"
            />
          </div>
        </div>
      </div>
    </el-dialog>
  </section>
</template>

<style scoped>
.library-page {
  display: grid;
  grid-template-rows: auto 1fr;
  align-content: start;
  gap: 16px;
  min-height: calc(100vh - 120px);
  padding: 40px 42px 46px;
  margin-top: 15px;
  background:
    repeating-linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.34) 0 1px,
      rgba(186, 151, 102, 0.06) 1px 8px,
      rgba(255, 255, 255, 0.12) 8px 14px
    ),
    linear-gradient(135deg, #fbfaf6 0%, #f2eee6 100%);
  border-radius: 12px;
  border: 1px solid #e0d2bf;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.58),
    inset 0 26px 42px rgba(255, 255, 255, 0.5),
    0 16px 34px rgba(82, 58, 34, 0.1);
  position: relative;
}

.library-search {
  width: 220px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.search-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.search-empty {
  text-align: center;
  padding: 48px 20px;
  color: var(--color-text-muted);
  border: 1px dashed #cfd7e3;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.search-empty p {
  margin: 0 0 12px;
}

.project-card.is-pinned {
  outline: 2px solid rgba(198, 111, 79, 0.45);
  outline-offset: 2px;
}

.pin-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 4;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.42);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.15s;
  backdrop-filter: blur(4px);
}

.pin-btn:hover {
  background: rgba(15, 23, 42, 0.62);
  transform: scale(1.05);
}

.pin-btn.active {
  background: rgba(198, 111, 79, 0.92);
  border-color: rgba(255, 255, 255, 0.7);
}

.pin-glyph {
  display: block;
  width: 11px;
  height: 11px;
  background: var(--color-bg-surface);
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.12);
}

.pin-btn.active .pin-glyph {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.35);
}



.empty-actions {
  display: flex;
  gap: 12px;
  margin-top: 10px;
}



.empty-library {
  min-height: 360px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  border: 1px dashed #cfd7e3;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #7b8494;
  z-index: 10;
}

.empty-library h2 {
  color: #1f2937;
  font-size: 18px;
}

/* 拟物现代壁挂书架网格 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 210px);
  grid-auto-rows: 288px;
  justify-content: start;
  gap: 0 30px;
  min-height: 360px;
  position: relative;
  z-index: 10;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 220px,
    rgba(201, 159, 104, 0.22) 220px 223px,
    #ead6b5 223px 232px,
    #d3ad78 232px 243px,
    #b9864d 243px 248px,
    rgba(118, 81, 43, 0.16) 248px 260px,
    transparent 260px 288px
  );
}

/* 3D 书本卡片 */
.project-card {
  position: relative;
  width: 190px;
  height: 224px;
  justify-self: center;
  background: transparent;
  border: none;
  cursor: pointer;
  perspective: 1000px;
  transform-style: preserve-3d;
  transition: transform 0.4s ease;
  user-select: none;
}

/* 书脊立体线条 */
.book-spine {
  position: absolute;
  top: 0;
  left: 0;
  width: 14px;
  height: 100%;
  background: linear-gradient(
    to right,
    rgba(0, 0, 0, 0.18) 0%,
    rgba(0, 0, 0, 0.04) 28%,
    rgba(255, 255, 255, 0.14) 44%,
    rgba(255, 255, 255, 0) 50%,
    rgba(0, 0, 0, 0.1) 100%
  );
  border-radius: 4px 0 0 4px;
  z-index: 10;
  pointer-events: none;
}

.book-spine-shadow {
  position: absolute;
  top: 0;
  left: 14px;
  width: 6px;
  height: 100%;
  background: linear-gradient(to right, rgba(0, 0, 0, 0.12), rgba(0, 0, 0, 0));
  z-index: 6;
  pointer-events: none;
}

/* 书本封面 */
.book-cover {
  position: absolute;
  top: 0;
  left: 0;
  width: calc(100% - 14px);
  height: 100%;
  border: 1px solid rgba(255, 255, 255, 0.46);
  border-radius: 6px 2px 2px 6px;
  background:
    linear-gradient(to bottom, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0) 36%),
    radial-gradient(circle at 78% 18%, rgba(255, 255, 255, 0.22), transparent 18%),
    linear-gradient(135deg, var(--cover-start), var(--cover-mid) 52%, var(--cover-end));
  box-shadow:
    2px 6px 12px rgba(60, 42, 24, 0.2),
    inset 14px 0 18px rgba(0, 0, 0, 0.12),
    inset -1px 0 0 rgba(255, 255, 255, 0.28);
  transform-origin: left center;
  transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.4s ease;
  z-index: 5;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 14px;
  color: var(--color-bg-surface);
  overflow: hidden;
}

/* 经典墨绿-青翠渐变封面 */
.cover-general {
  --cover-start: #3f7f75;
  --cover-mid: #73a88b;
  --cover-end: #d7be84;
}

/* 坚毅深蓝-科技靛蓝渐变封面 */
.cover-male {
  --cover-start: #425f83;
  --cover-mid: #6f89ad;
  --cover-end: #d5c095;
}

/* 柔美暖金-樱粉渐变封面 */
.cover-female {
  --cover-start: #b86978;
  --cover-mid: #d89483;
  --cover-end: #ead19a;
}

/* 自定义项目：独立的酒红-紫灰封面，避免和通用类型混色 */
.cover-custom {
  --cover-start: #76648d;
  --cover-mid: #9f8dae;
  --cover-end: #dcc28d;
}

/* Hover 时书本浮空拔起，而下方木托板保持原处，实现逼真的拿书交互 */
.project-card:hover .book-cover {
  transform: rotateY(-14deg) translateZ(7px) translateY(-10px);
  box-shadow: 12px 18px 24px rgba(15, 23, 42, 0.3);
}

/* 封面设计排版 */
.cover-design {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 9px;
  width: 100%;
}

.pending-badge {
  max-width: 100%;
  font-size: 10px;
  font-weight: 800;
  color: #fff8f0;
  background: rgba(220, 38, 38, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 3px;
  padding: 3px 6px;
  backdrop-filter: blur(4px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  font-family: inherit;
}

.genre-badge {
  max-width: 100%;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.96);
  background: rgba(37, 37, 37, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 3px;
  padding: 3px 6px;
  backdrop-filter: blur(4px);
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-title {
  margin: 6px 0 0 0 !important;
  font-size: 17px !important;
  font-weight: 800;
  line-height: 1.35;
  color: var(--color-bg-surface) !important;
  text-shadow: 0 2px 5px rgba(72, 50, 30, 0.28);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
  white-space: normal !important;
  cursor: pointer;
  transition: color 0.15s ease;
}

.book-title:hover {
  text-decoration: underline;
  color: #ffe1d1 !important;
}

.book-desc {
  font-size: 11px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.85);
  margin: 4px 0 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-shadow: 0 1px 2px rgba(72, 50, 30, 0.2);
}

.cover-footer {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.book-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.meta-inline-stats {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.94);
}

.meta-inline-item {
  white-space: nowrap;
}

.meta-sep {
  font-weight: 400;
  opacity: 0.45;
  user-select: none;
}

.meta-updated {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.78);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.cover-footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  padding-top: 8px;
  width: 100%;
}

.meta-time {
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.82);
  text-shadow: 0 1px 3px rgba(40, 28, 18, 0.35);
  flex-shrink: 0;
}

.meta-time--empty {
  opacity: 0.45;
  font-weight: 600;
}

.book-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-btn {
  color: rgba(255, 255, 255, 0.75) !important;
  padding: 0 !important;
  height: 24px !important;
  width: 24px !important;
  margin: 0 !important;
  font-size: 14px !important;
  transition: all 0.2s ease;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  border-radius: 4px !important;
}

.action-btn:hover {
  color: var(--color-bg-surface) !important;
  background: rgba(255, 255, 255, 0.18) !important;
}

.action-btn.delete-btn:hover {
  color: #ff5e62 !important;
}

.book-details-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.details-cover-preview {
  height: 120px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.15);
  background:
    linear-gradient(to bottom, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0) 36%),
    radial-gradient(circle at 78% 18%, rgba(255, 255, 255, 0.22), transparent 18%),
    linear-gradient(135deg, var(--cover-start), var(--cover-mid) 52%, var(--cover-end));
}

.preview-design {
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--color-bg-surface);
}

.preview-genre {
  align-self: flex-start;
  font-size: 10px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 3px;
  padding: 2px 5px;
  font-weight: 700;
}

.preview-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

.details-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px 20px;
  background: var(--color-bg-surface-muted);
  padding: 18px;
  border-radius: 8px;
  border: 1px solid #eef2f6;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item.full-width {
  grid-column: span 2;
  border-bottom: 1px solid #eef2f6;
  padding-bottom: 12px;
}

.info-label {
  font-size: 12.5px;
  color: var(--color-text-muted);
  font-weight: 600;
}

.info-value {
  font-size: 14px;
  color: #1f2937;
  font-weight: 600;
}

.info-value.desc-text {
  font-size: 13.5px;
  color: #4b5563;
  line-height: 1.5;
  font-weight: 400;
  margin: 0;
}

.details-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>
