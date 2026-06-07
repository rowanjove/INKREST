import { ref, type Ref } from 'vue'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import {
  createSnapshot,
  getCurrentProject,
  getGoldenCheck,
  getProjectPlatform,
  listPlatforms,
  listReaderFeedback,
  runChapter,
  saveReaderFeedback,
  updateProjectPlatform,
} from '../api'

export function useWritingPlatformFeedback(options: {
  activeChapterId: Ref<string>
  loadingEditor: Ref<boolean>
}) {
  const { activeChapterId, loadingEditor } = options

  const activeProjectId = ref('')
  const activePlatform = ref('qidian')
  const activePlatformLabel = ref('起点中文网')
  const platformsList = ref<any[]>([])
  const feedbackList = ref<any[]>([])
  const loadingFeedback = ref(false)
  const loadingGolden = ref(false)
  const feedbackForm = ref({
    chapter_id: '',
    bounce_rate: 0.15,
    retention_rate: 0.85,
    active_readers: 5000,
  })
  const goldenCheckResult = ref<any>(null)

  async function initProjectPlatformAndFeedback() {
    try {
      const { data: proj } = await getCurrentProject()
      if (proj && proj.id) {
        activeProjectId.value = proj.id

        const { data: plist } = await listPlatforms()
        platformsList.value = plist || []

        const { data: p } = await getProjectPlatform(proj.id)
        if (p) {
          activePlatform.value = p.platform || 'qidian'
          activePlatformLabel.value = p.label || '起点中文网'
        }

        void fetchFeedback()
      }
    } catch (e: any) {
      console.error('Failed to init project platform/feedback:', e)
    }
  }

  async function fetchFeedback() {
    if (!activeProjectId.value) return
    loadingFeedback.value = true
    try {
      const { data } = await listReaderFeedback(activeProjectId.value)
      feedbackList.value = data || []
    } catch (e: any) {
      console.error('Failed to fetch feedback:', e)
    } finally {
      loadingFeedback.value = false
    }
  }

  async function handlePlatformChange(platformName: string) {
    if (!activeProjectId.value) return
    try {
      const { data } = await updateProjectPlatform(activeProjectId.value, platformName)
      activePlatform.value = data.platform
      const found = platformsList.value.find((p) => p.name === platformName)
      if (found) {
        activePlatformLabel.value = found.label
      }
      ElMessage.success(
        `目标平台成功切换为 [${activePlatformLabel.value}]，大纲与生成约束已同步重载！`,
      )
    } catch (e: any) {
      ElMessage.error('切换平台失败: ' + e.message)
    }
  }

  async function submitFeedback() {
    if (!activeProjectId.value) return
    if (!feedbackForm.value.chapter_id) {
      ElMessage.warning('请选择要模拟录入反馈的章节')
      return
    }
    try {
      await saveReaderFeedback(activeProjectId.value, {
        chapter_id: feedbackForm.value.chapter_id,
        bounce_rate: feedbackForm.value.bounce_rate,
        retention_rate: feedbackForm.value.retention_rate,
        active_readers: feedbackForm.value.active_readers,
      })
      ElMessage.success('读者反馈模拟数据录入成功！')
      void fetchFeedback()
    } catch (e: any) {
      ElMessage.error('录入失败: ' + e.message)
    }
  }

  async function runGoldenCheck() {
    if (!activeProjectId.value) return
    loadingGolden.value = true
    goldenCheckResult.value = null
    try {
      const { data } = await getGoldenCheck(activeProjectId.value)
      goldenCheckResult.value = data
      if (data.status === 'pending') {
        ElMessage.warning(data.message)
      } else if (data.status === 'success') {
        ElMessage.success('黄金三章签约质检评估完成！')
      } else {
        ElMessage.error(data.message || '诊断失败')
      }
    } catch (e: any) {
      ElMessage.error('签约质检失败: ' + e.message)
    } finally {
      loadingGolden.value = false
    }
  }

  async function handleGoldenRewrite() {
    if (!activeChapterId.value) return
    if (!goldenCheckResult.value?.suggestions || goldenCheckResult.value.suggestions.length === 0) {
      ElMessage.warning('没有诊断整改建议，无法优化重写')
      return
    }

    try {
      await ElMessageBox.confirm(
        '确定要根据黄金三章诊断建议一键优化重写吗？这将自动为当前章节创建快照备份并提交重写任务。',
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
    } catch {
      return
    }

    loadingEditor.value = true
    try {
      const snapshotTitle = `【黄金三章重写前备份】推荐分：${goldenCheckResult.value.overall_score}`
      await createSnapshot(activeChapterId.value, { title: snapshotTitle })

      const suggestionsStr = goldenCheckResult.value.suggestions.join('；')
      const rewriteGoal = `【黄金三章整改优化】：${suggestionsStr}`

      await runChapter({
        chapter_id: activeChapterId.value,
        goal: rewriteGoal,
        dry_run: false,
      })

      ElNotification({
        title: '任务提交成功',
        message: `第 ${activeChapterId.value} 章的黄金三章整改重写任务已提交！请前往日志中心查看任务流水。`,
        type: 'success',
        duration: 5000,
      })
    } catch (error: any) {
      ElMessage.error('优化重写失败: ' + error.message)
    } finally {
      loadingEditor.value = false
    }
  }

  return {
    activeProjectId,
    activePlatform,
    activePlatformLabel,
    platformsList,
    feedbackList,
    loadingFeedback,
    loadingGolden,
    feedbackForm,
    goldenCheckResult,
    initProjectPlatformAndFeedback,
    fetchFeedback,
    handlePlatformChange,
    submitFeedback,
    runGoldenCheck,
    handleGoldenRewrite,
  }
}