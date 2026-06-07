import { nextTick, ref, type ComputedRef, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  activateVersion,
  apiErrorMessage,
  compareVersions,
  createVersion,
  deleteVersion,
  listVersions,
} from '../api'

export function useWritingVersions(options: {
  activeChapterId: Ref<string>
  editorText: Ref<string>
  versionsList: Ref<any[]>
  activeVersionId: Ref<string>
  activeVersion: ComputedRef<any | undefined>
  adjustTextareaHeight: () => void
  loadChapter: (cid: string) => Promise<void>
  fetchChapters: () => Promise<void>
  fetchScrapbook?: () => Promise<void>
}) {
  const {
    activeChapterId,
    editorText,
    versionsList,
    activeVersionId,
    activeVersion,
    adjustTextareaHeight,
    loadChapter,
    fetchChapters,
    fetchScrapbook,
  } = options

  const compareDialogOpen = ref(false)
  const diffChunks = ref<any[]>([])
  const loadingDiff = ref(false)
  const compareVersionId = ref('')

  function handleVersionChange(vid: string) {
    const ver = versionsList.value.find((v) => v.id === vid)
    if (ver) {
      activeVersionId.value = vid
      editorText.value = ver.content || ''
      void nextTick(adjustTextareaHeight)
    }
  }

  function handleCreateVersion() {
    ElMessageBox.prompt('请输入分支版本名称（如：版本 B）', '新建分支试写', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: `版本 ${String.fromCharCode(65 + versionsList.value.length)}`,
      inputPattern: /.+/,
      inputErrorMessage: '名称不能为空',
    })
      .then(({ value: name }) => {
        ElMessageBox.prompt('请输入该分支的剧情走向备注说明（选填）', '分支走向备注', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          inputValue: '',
        })
          .then(async ({ value: note }) => {
            try {
              await createVersion(activeChapterId.value, {
                version_name: name.trim(),
                note: note ? note.trim() : '',
                copy_from_active: true,
              })
              ElMessage.success('新建剧情分支成功！')
              const { data: vData } = await listVersions(activeChapterId.value)
              versionsList.value = vData || []
              if (versionsList.value.length > 0) {
                const newV = versionsList.value[versionsList.value.length - 1]
                handleVersionChange(newV.id)
              }
            } catch (e: any) {
              ElMessage.error('新建分支失败: ' + apiErrorMessage(e, '新建分支失败'))
            }
          })
          .catch(() => {})
      })
      .catch(() => {})
  }

  function handleActivateVersion() {
    if (!activeChapterId.value || !activeVersionId.value) return
    const curVer = activeVersion.value
    if (!curVer || curVer.is_active === 1) return

    ElMessageBox.confirm(
      `确定要将 [${curVer.version_name}] 设为正史活跃版本吗？这会用当前内容覆写正文 final 稿件并自动产生备份。`,
      '设为正史确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
      .then(async () => {
        try {
          await activateVersion(activeChapterId.value, activeVersionId.value)
          ElMessage.success(`[${curVer.version_name}] 已设为本章正史！`)
          await loadChapter(activeChapterId.value)
          await fetchChapters()
        } catch (e: any) {
          ElMessage.error('激活版本失败: ' + apiErrorMessage(e, '激活版本失败'))
        }
      })
      .catch(() => {})
  }

  function handleDeleteVersion(vid: string) {
    const ver = versionsList.value.find((v) => v.id === vid)
    if (!ver) return
    if (ver.is_active === 1) {
      ElMessage.warning('无法删除当前正史活跃版本分支')
      return
    }

    ElMessageBox.confirm(
      `确定要删除剧情分支 [${ver.version_name}] 吗？删除后此分支内容将彻底丢失。`,
      '删除分支确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
      .then(async () => {
        try {
          await deleteVersion(vid)
          ElMessage.success('剧情分支删除成功！')

          const { data: vData } = await listVersions(activeChapterId.value)
          versionsList.value = vData || []

          if (activeVersionId.value === vid) {
            const activeV = versionsList.value.find((v: any) => v.is_active === 1)
            if (activeV) handleVersionChange(activeV.id)
          }

          if (fetchScrapbook) {
            await fetchScrapbook()
          }
        } catch (e: any) {
          ElMessage.error('删除分支失败: ' + apiErrorMessage(e, '删除分支失败'))
        }
      })
      .catch(() => {})
  }

  async function handleOpenCompare(targetVid: string) {
    const activeV = versionsList.value.find((v: any) => v.is_active === 1)
    if (!activeV) {
      ElMessage.warning('未找到正史活跃版本，无法进行 Diff 对比')
      return
    }
    compareVersionId.value = targetVid
    compareDialogOpen.value = true
    loadingDiff.value = true
    try {
      const { data } = await compareVersions(activeChapterId.value, {
        version_id_a: activeV.id,
        version_id_b: targetVid,
      })
      diffChunks.value = data || []
    } catch (e: any) {
      ElMessage.error('计算剧情分支差异失败: ' + apiErrorMessage(e, '计算剧情分支差异失败'))
      diffChunks.value = []
    } finally {
      loadingDiff.value = false
    }
  }

  return {
    compareDialogOpen,
    diffChunks,
    loadingDiff,
    compareVersionId,
    handleVersionChange,
    handleCreateVersion,
    handleActivateVersion,
    handleDeleteVersion,
    handleOpenCompare,
  }
}