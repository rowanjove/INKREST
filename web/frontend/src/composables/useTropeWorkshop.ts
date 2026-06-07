import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listComponents, composePreset } from '../api'
import { useProjectStore } from '../stores/project'

export type TropeTab = 'channels' | 'themes' | 'mechanisms' | 'cool_points'
export type TropeSlotType = TropeTab

export interface TropeComponent {
  id: string
  name: string
  description: string
}

const SLOT_LABELS: Record<TropeSlotType, string> = {
  channels: '主角频道',
  themes: '主题题材',
  mechanisms: '情节机制',
  cool_points: '爽点节奏',
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function parseGuideMarkdown(markdown: string) {
  const lines = markdown.split('\n')
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
}

export function useTropeWorkshop() {
  const router = useRouter()
  const projectStore = useProjectStore()

  const channels = ref<TropeComponent[]>([])
  const themes = ref<TropeComponent[]>([])
  const mechanisms = ref<TropeComponent[]>([])
  const coolPoints = ref<TropeComponent[]>([])

  const loading = ref(false)
  const activeTab = ref<TropeTab>('channels')

  const selectedChannel = ref<TropeComponent | null>(null)
  const selectedTheme = ref<TropeComponent | null>(null)
  const selectedMechanisms = ref<TropeComponent[]>([])
  const selectedCoolPoints = ref<TropeComponent[]>([])

  const generatedGuide = ref('')
  const guideLoading = ref(false)

  const currentProjectId = computed(() => projectStore.currentProject?.id)

  const isValidBlueprint = computed(() => Boolean(selectedChannel.value && selectedTheme.value))

  const parsedGuideHtml = computed(() => {
    if (!generatedGuide.value) return ''
    return parseGuideMarkdown(generatedGuide.value)
  })

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

  const autoGeneratePreview = async () => {
    if (!isValidBlueprint.value || !selectedChannel.value || !selectedTheme.value) {
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

  const addToBlueprint = (item: TropeComponent, type: TropeSlotType) => {
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
    void autoGeneratePreview()
  }

  const removeFromBlueprint = (id: string, type: TropeSlotType) => {
    if (type === 'channels') {
      selectedChannel.value = null
    } else if (type === 'themes') {
      selectedTheme.value = null
    } else if (type === 'mechanisms') {
      selectedMechanisms.value = selectedMechanisms.value.filter((x) => x.id !== id)
    } else if (type === 'cool_points') {
      selectedCoolPoints.value = selectedCoolPoints.value.filter((x) => x.id !== id)
    }
    void autoGeneratePreview()
  }

  const handleApplyToActiveProject = async () => {
    if (!projectStore.currentProject?.id) {
      ElMessage.warning('当前没有激活的作品，请选择“创建新作品”！')
      return
    }
    if (!selectedChannel.value || !selectedTheme.value) return

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

  const openCreateDialog = () => {
    if (!isValidBlueprint.value || !selectedChannel.value || !selectedTheme.value) return
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

  const handleDragStart = (event: DragEvent, item: TropeComponent, type: TropeSlotType) => {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/json', JSON.stringify({ item, type }))
      event.dataTransfer.effectAllowed = 'copy'
    }
  }

  const handleDrop = (event: DragEvent, targetType: TropeSlotType) => {
    event.preventDefault()
    if (!event.dataTransfer) return
    try {
      const dataStr = event.dataTransfer.getData('application/json')
      if (!dataStr) return
      const { item, type } = JSON.parse(dataStr) as { item: TropeComponent; type: TropeSlotType }
      if (type !== targetType) {
        ElMessage.warning(`请将该类型元件拖入相对应的「${SLOT_LABELS[targetType]}」插槽内`)
        return
      }
      addToBlueprint(item, type)
    } catch {
      // Silent
    }
  }

  return {
    channels,
    themes,
    mechanisms,
    coolPoints,
    loading,
    activeTab,
    selectedChannel,
    selectedTheme,
    selectedMechanisms,
    selectedCoolPoints,
    generatedGuide,
    guideLoading,
    currentProjectId,
    isValidBlueprint,
    parsedGuideHtml,
    loadAllComponents,
    addToBlueprint,
    removeFromBlueprint,
    handleApplyToActiveProject,
    openCreateDialog,
    handleDragStart,
    handleDrop,
  }
}