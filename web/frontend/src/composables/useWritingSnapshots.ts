import { ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createSnapshot, listSnapshots, rollbackSnapshot } from '../api'

export function useWritingSnapshots(options: {
  activeChapterId: Ref<string>
  currentChapter: Ref<any>
  loadChapter: (cid: string) => Promise<void>
  fetchChapters: () => Promise<void>
  handleSave: (silent?: boolean) => Promise<void>
}) {
  const { activeChapterId, currentChapter, loadChapter, fetchChapters, handleSave } = options

  const timeMachineOpen = ref(false)
  const snapshotsList = ref<any[]>([])
  const loadingSnapshots = ref(false)
  const previewingSnapshot = ref<any>(null)
  const showPreviewDialog = ref(false)

  async function handleOpenTimeMachine() {
    if (!activeChapterId.value) return
    timeMachineOpen.value = true
    await fetchSnapshots()
  }

  async function fetchSnapshots() {
    if (!activeChapterId.value) return
    loadingSnapshots.value = true
    try {
      const { data } = await listSnapshots(activeChapterId.value)
      snapshotsList.value = data || []
    } catch (e: any) {
      ElMessage.error('获取备份列表失败: ' + e.message)
    } finally {
      loadingSnapshots.value = false
    }
  }

  function handleManualSnapshot() {
    if (!activeChapterId.value) return
    ElMessageBox.prompt('请输入本次备份的描述备注', '保存手动快照', {
      confirmButtonText: '备份',
      cancelButtonText: '取消',
      inputValue: `手动备份于 ${new Date().toLocaleTimeString()}`,
      inputPattern: /.+/,
      inputErrorMessage: '备注不能为空',
    })
      .then(async ({ value }) => {
        try {
          await handleSave(true)
          await createSnapshot(activeChapterId.value, { title: value.trim() })
          ElMessage.success('手动备份快照成功！')
          if (timeMachineOpen.value) {
            await fetchSnapshots()
          }
        } catch (e: any) {
          ElMessage.error('备份失败: ' + e.message)
        }
      })
      .catch(() => {})
  }

  function handlePreviewSnapshot(snap: any) {
    previewingSnapshot.value = snap
    showPreviewDialog.value = true
  }

  function handleRollback(snap: any) {
    ElMessageBox.confirm(
      `确认将当前章节内容回滚到 [${snap.title || snap.datetime}] 版本吗？这会覆盖编辑器当前的正文内容（回滚前系统会自动备份当前版本）。`,
      '版本回滚二次确认',
      {
        confirmButtonText: '确认回滚',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
      .then(async () => {
        try {
          const currentTitle = currentChapter.value?.title || `第 ${activeChapterId.value} 章`
          await createSnapshot(activeChapterId.value, {
            title: `系统自动备份（回滚前：${currentTitle}）`,
          })

          await rollbackSnapshot(activeChapterId.value, snap.timestamp)
          ElMessage.success('成功回滚到历史版本！')

          await loadChapter(activeChapterId.value)
          await fetchChapters()
          timeMachineOpen.value = false
          showPreviewDialog.value = false
        } catch (e: any) {
          ElMessage.error('回滚失败: ' + e.message)
        }
      })
      .catch(() => {})
  }

  return {
    timeMachineOpen,
    snapshotsList,
    loadingSnapshots,
    previewingSnapshot,
    showPreviewDialog,
    handleOpenTimeMachine,
    fetchSnapshots,
    handleManualSnapshot,
    handlePreviewSnapshot,
    handleRollback,
  }
}