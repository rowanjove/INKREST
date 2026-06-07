import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProjectStore } from '../stores/project'
import {
  exportNovel,
  exportProjectZip,
  importProjectZip,
  getProjectCoverUrl,
  getOutline,
  pinProject,
  apiErrorMessage,
} from '../api'
import type { Project } from '../stores/project'
import { channelLabel } from '../utils/libraryFormatters'

export const MAX_PINNED = 10

export function useLibraryProjects() {
  const searchQuery = ref('')
  const pinningId = ref<string | null>(null)

  const router = useRouter()
  const projectStore = useProjectStore()

  const detailsVisible = ref(false)
  const selectedProject = ref<Project | null>(null)
  const exportingZip = ref(false)
  const fileInput = ref<HTMLInputElement | null>(null)

  const coverTimestamps = ref<Record<string, number>>({})

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

  const getCoverUrl = (pid: string) => {
    const t = coverTimestamps.value[pid] || ''
    return `${getProjectCoverUrl(pid)}?t=${t}`
  }

  const getCoverStyle = (project: Project) => {
    if (project.has_cover) {
      return {
        background: `linear-gradient(to bottom, rgba(0, 0, 0, 0.28), rgba(0, 0, 0, 0.1) 40%, rgba(0, 0, 0, 0.58)), url(${getCoverUrl(project.id)}) center/cover no-repeat`,
      }
    }
    return {}
  }

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

  const openDetails = (project: Project) => {
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

  const handleExportFormat = async (format: string, project: Project) => {
    try {
      ElMessage.info(`正在准备导出为 ${format} 格式，请稍候...`)
      const res = await exportNovel({
        format,
        title: project.name,
        project_id: project.id,
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

      const proj = projectStore.projects.find((p) => p.id === pid)
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

  return {
    searchQuery,
    pinningId,
    detailsVisible,
    selectedProject,
    exportingZip,
    fileInput,
    coverTimestamps,
    pinnedCount,
    displayedProjects,
    getCoverUrl,
    getCoverStyle,
    togglePin,
    openPendingMaintenance,
    openProject,
    openDetails,
    goCreate,
    handleDelete,
    handleRead,
    handleExportFormat,
    handleExportZip,
    triggerUpload,
    handleImportZip,
  }
}