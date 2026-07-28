import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { rewriteDescription, updateDescription, apiErrorMessage } from '../api'
import type { Project } from '../stores/project'

type UseLibraryDescriptionOptions = {
  selectedProject: Ref<Project | null>
  refreshProjects: () => Promise<void>
}

export function useLibraryDescription({ selectedProject, refreshProjects }: UseLibraryDescriptionOptions) {
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
        user_preference: userPreference.value,
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
    } catch {
      ElMessage.error('复制失败，请手动选择复制')
    }
  }

  const applyDescription = async () => {
    if (!selectedProject.value || !rewrittenDesc.value) return
    try {
      await updateDescription(selectedProject.value.id, rewrittenDesc.value)
      selectedProject.value.description = rewrittenDesc.value
      await refreshProjects()
      ElMessage.success('简介应用成功！已更新作品库。')
      rewriteVisible.value = false
    } catch (error: any) {
      ElMessage.error('应用简介失败: ' + apiErrorMessage(error, '应用简介失败'))
    }
  }

  return {
    rewriteVisible,
    rewriteStyle,
    userPreference,
    rewriteLoading,
    rewrittenDesc,
    openDescriptionRewriter,
    handleRewrite,
    copyDescription,
    applyDescription,
  }
}