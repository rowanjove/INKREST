<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  apiErrorMessage,
  listChapters, getChapter, updateChapter, extractSyncAssets, inlineExpand,
  createChapter, listSnapshots, createSnapshot, rollbackSnapshot,
  listVersions, createVersion, updateVersion, deleteVersion, activateVersion, compareVersions, getScrapbook,
  getCurrentProject, listPlatforms, getProjectPlatform, updateProjectPlatform, saveReaderFeedback, listReaderFeedback, getGoldenCheck,
  runChapter, getTask, deleteChapter, suggestChapterGoal
} from '../api'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Fold, Expand, Document, Plus, Delete, Check } from '@element-plus/icons-vue'
import AssetSidebar from '../components/AssetSidebar.vue'
import AiBubbleMenu from '../components/AiBubbleMenu.vue'
import { useTasksStore } from '../stores/tasks'
import { useWritingVisualSettings } from '../composables/useWritingVisualSettings'

const tasksStore = useTasksStore()


const route = useRoute()

// Chapter state
const chaptersList = ref<any[]>([])
const activeChapterId = ref('')
const currentChapter = ref<any>(null)
const editorText = ref('')
const loadingEditor = ref(false)
const saving = ref(false)
const sidebarCollapsed = ref(false)
const rightSidebarCollapsed = ref(false)

// Versions / Scrapbook states
const versionsList = ref<any[]>([])
const activeVersionId = ref('')
const activeVersion = computed(() => versionsList.value.find(v => v.id === activeVersionId.value))

const rightTab = ref<'assets' | 'scrapbook' | 'feedback' | 'golden'>('assets')
const scrapbookList = ref<any[]>([])
const scrapbookQuery = ref('')
const loadingScrapbook = ref(false)

// Platform & Feedback states
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
  active_readers: 5000
})

const goldenCheckResult = ref<any>(null)

const compareDialogOpen = ref(false)
const diffChunks = ref<any[]>([])
const loadingDiff = ref(false)
const compareVersionId = ref('')

// Adjacent panel / Sidebar reference
const assetSidebarRef = ref<any>(null)

// Selection & AI Bubble Menu state
const showBubble = ref(false)
const bubbleX = ref(0)
const bubbleY = ref(0)
const selectedText = ref('')
const editorRef = ref<HTMLTextAreaElement | null>(null)

// AI Expansion State
const expanding = ref(false)
const expandResult = ref('')
const showExpandDialog = ref(false)

// Load all chapters
const fetchChapters = async () => {
  try {
    const { data } = await listChapters({ offset: 0, limit: 500, sync: true })
    const chapterRows = data.items ?? data
    // Filter out missing chapters or handle them
    chaptersList.value = chapterRows || []
    
    if (chaptersList.value.length > 0 && !activeChapterId.value) {
      // Load first chapter by default
      await loadChapter(chaptersList.value[0].chapter_id)
    }
  } catch (e: any) {
    ElMessage.error('获取章节列表失败: ' + apiErrorMessage(e, '获取章节列表失败'))
  }
}

// Load a specific chapter's final text
const loadChapter = async (cid: string) => {
  loadingEditor.value = true
  activeChapterId.value = cid
  showBubble.value = false
  expandResult.value = ''
  showExpandDialog.value = false
  
  try {
    const { data } = await getChapter(cid)
    currentChapter.value = data
    
    // 获取版本列表并默认加载 active 版本
    const { data: vData } = await listVersions(cid)
    versionsList.value = vData || []
    
    const activeV = versionsList.value.find((v: any) => v.is_active === 1)
    if (activeV) {
      activeVersionId.value = activeV.id
      editorText.value = activeV.content || ''
    } else if (versionsList.value.length > 0) {
      activeVersionId.value = versionsList.value[0].id
      editorText.value = versionsList.value[0].content || ''
    } else {
      activeVersionId.value = ''
      editorText.value = data.final_text || ''
    }
    
    if (rightTab.value === 'scrapbook') {
      await fetchScrapbook()
    }
    
    nextTick(adjustTextareaHeight)
  } catch (e: any) {
    ElMessage.error('加载章节内容失败: ' + apiErrorMessage(e, '加载章节内容失败'))
    editorText.value = ''
    currentChapter.value = null
  } finally {
    loadingEditor.value = false
  }
}

// Save chapter and trigger asset extraction
const handleSave = async (silent = false) => {
  if (!activeChapterId.value || saving.value) return
  saving.value = true
  
  try {
    const curVer = activeVersion.value
    if (curVer && curVer.is_active === 0) {
      // 如果当前是分支草稿，仅保存分支内容
      await updateVersion(activeVersionId.value, {
        content: editorText.value
      })
      if (!silent) {
        ElMessage.success('分支剧情草稿已保存！')
      }
    } else {
      // 否则，正常保存为正文稿件
      await updateChapter(activeChapterId.value, {
        title: currentChapter.value?.title || '',
        final_text: editorText.value
      })
      if (!silent) {
        ElMessage.success('章节内容已保存！')
      }
    }
    
    await fetchChapters()
    const { data: vData } = await listVersions(activeChapterId.value)
    versionsList.value = vData || []
    
    // 2. Trigger entity extraction and asset sync only when manually saved
    if (!silent) {
      const { data } = await extractSyncAssets({ chapter_text: editorText.value })
      if (data.success && data.synced && data.synced.length > 0) {
        // Show notification on what assets were updated/created
        const created = data.synced.filter((s: any) => s.status === 'created').map((s: any) => s.label)
        const updated = data.synced.filter((s: any) => s.status === 'updated').map((s: any) => s.label)
        
        let message = ''
        if (created.length) message += `✨ <strong>新增设定</strong>: ${created.join('，')}<br />`
        if (updated.length) message += `🔄 <strong>更新设定</strong>: ${updated.join('，')}<br />`
        
        ElNotification({
          title: '资产库自动同步成功',
          message: message,
          type: 'success',
          duration: 5000,
          dangerouslyUseHTMLString: true
        })
        
        // Refresh sidebar assets list
        if (assetSidebarRef.value) {
          assetSidebarRef.value.refreshAssets()
        }
      }
    }
  } catch (e: any) {
    if (!silent) {
      ElMessage.error('保存失败: ' + apiErrorMessage(e, '保存失败'))
    }
  } finally {
    saving.value = false
  }
}

// ---- Versions & Scrapbook Operations ----
const handleVersionChange = (vid: string) => {
  const ver = versionsList.value.find(v => v.id === vid)
  if (ver) {
    activeVersionId.value = vid
    editorText.value = ver.content || ''
    nextTick(adjustTextareaHeight)
  }
}

const handleCreateVersion = () => {
  ElMessageBox.prompt('请输入分支版本名称（如：版本 B）', '新建分支试写', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: `版本 ${String.fromCharCode(65 + versionsList.value.length)}`,
    inputPattern: /.+/,
    inputErrorMessage: '名称不能为空'
  }).then(({ value: name }) => {
    ElMessageBox.prompt('请输入该分支的剧情走向备注说明（选填）', '分支走向备注', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: '',
    }).then(async ({ value: note }) => {
      try {
        await createVersion(activeChapterId.value, {
          version_name: name.trim(),
          note: note ? note.trim() : '',
          copy_from_active: true
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
    }).catch(() => {})
  }).catch(() => {})
}

const handleActivateVersion = async () => {
  if (!activeChapterId.value || !activeVersionId.value) return
  const curVer = activeVersion.value
  if (!curVer || curVer.is_active === 1) return
  
  ElMessageBox.confirm(
    `确定要将 [${curVer.version_name}] 设为正史活跃版本吗？这会用当前内容覆写正文 final 稿件并自动产生备份。`,
    '设为正史确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await activateVersion(activeChapterId.value, activeVersionId.value)
      ElMessage.success(`[${curVer.version_name}] 已设为本章正史！`)
      await loadChapter(activeChapterId.value)
      await fetchChapters()
    } catch (e: any) {
      ElMessage.error('激活版本失败: ' + apiErrorMessage(e, '激活版本失败'))
    }
  }).catch(() => {})
}

const handleDeleteVersion = async (vid: string) => {
  const ver = versionsList.value.find(v => v.id === vid)
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
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteVersion(vid)
      ElMessage.success('剧情分支删除成功！')
      
      const { data: vData } = await listVersions(activeChapterId.value)
      versionsList.value = vData || []
      
      if (activeVersionId.value === vid) {
        const activeV = versionsList.value.find((v: any) => v.is_active === 1)
        if (activeV) handleVersionChange(activeV.id)
      }
      
      await fetchScrapbook()
    } catch (e: any) {
      ElMessage.error('删除分支失败: ' + apiErrorMessage(e, '删除分支失败'))
    }
  }).catch(() => {})
}

const handleOpenCompare = async (targetVid: string) => {
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
      version_id_b: targetVid
    })
    diffChunks.value = data || []
  } catch (e: any) {
    ElMessage.error('计算剧情分支差异失败: ' + apiErrorMessage(e, '计算剧情分支差异失败'))
    diffChunks.value = []
  } finally {
    loadingDiff.value = false
  }
}

const fetchScrapbook = async () => {
  loadingScrapbook.value = true
  try {
    const { data } = await getScrapbook({
      query: scrapbookQuery.value,
      chapter_id: activeChapterId.value
    })
    scrapbookList.value = data || []
  } catch (e: any) {
    ElMessage.error('获取废稿段落失败: ' + apiErrorMessage(e, '获取废稿段落失败'))
  } finally {
    loadingScrapbook.value = false
  }
}

const copyScrapbookText = (text: string) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制废稿段落到剪贴板')
}

const insertScrapbookText = (text: string) => {
  if (!editorRef.value) return
  const start = editorRef.value.selectionStart
  const originVal = editorText.value
  editorText.value = originVal.substring(0, start) + text + originVal.substring(start)
  nextTick(() => {
    if (editorRef.value) {
      editorRef.value.focus()
      editorRef.value.setSelectionRange(start + text.length, start + text.length)
      adjustTextareaHeight()
    }
  })
  ElMessage.success('废稿段落已成功插入编辑器！')
}

watch(rightTab, (val) => {
  if (val === 'scrapbook') {
    fetchScrapbook()
  }
})

const handleOpenCreateChapter = () => {
  let nextIdNum = 1
  if (chaptersList.value && chaptersList.value.length > 0) {
    const ids = chaptersList.value
      .map(ch => parseInt(ch.chapter_id, 10))
      .filter(num => !isNaN(num))
    if (ids.length > 0) {
      nextIdNum = Math.max(...ids) + 1
    }
  }
  const nextIdStr = nextIdNum.toString().padStart(3, '0')
  
  ElMessageBox.prompt('请输入新建章节的标题', '新建章节', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: `第 ${nextIdNum} 章`,
    inputPattern: /.+/,
    inputErrorMessage: '标题不能为空'
  }).then(async ({ value }) => {
    try {
      await createChapter({
        chapter_id: nextIdStr,
        title: value.trim()
      })
      ElMessage.success('章节创建成功！')
      await fetchChapters()
      await loadChapter(nextIdStr)
    } catch (e: any) {
      ElMessage.error('创建章节失败: ' + apiErrorMessage(e, '创建章节失败'))
    }
  }).catch(() => {})
}

const handleDeleteChapter = async (chapterId: string) => {
  try {
    await ElMessageBox.confirm(
      `确定删除章节 ${chapterId}？正文、计划、报告、历史版本，以及状态库中该章同步的事件/人物/伏笔等数据都会一并移除。`,
      '删除章节',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteChapter(chapterId)
    if (activeChapterId.value === chapterId) {
      activeChapterId.value = ''
      currentChapter.value = null
      editorText.value = ''
      versionsList.value = []
      activeVersionId.value = ''
    }
    await fetchChapters()
    ElMessage.success(`章节 ${chapterId} 已删除`)
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除章节失败: ' + apiErrorMessage(error, '删除章节失败'))
    }
  }
}

// Handle Editor Keyboard Shortcuts (Ctrl + S / Tab autocomplete)
const handleKeyDown = (event: KeyboardEvent) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 's') {
    event.preventDefault()
    handleSave()
  }
}

// Handle Text Selection for AI Bubble Menu
const handleTextSelection = (event: any) => {
  if (!editorRef.value) return
  
  const selectionStart = editorRef.value.selectionStart
  const selectionEnd = editorRef.value.selectionEnd
  
  if (selectionStart !== selectionEnd) {
    const rawText = editorText.value.substring(selectionStart, selectionEnd)
    if (rawText.trim().length > 0) {
      selectedText.value = rawText
      // Position the bubble at mouse click coordinates safely
      bubbleX.value = event.clientX || bubbleX.value || 300
      bubbleY.value = event.clientY || bubbleY.value || 200
      showBubble.value = true
      return
    }
  }
  showBubble.value = false
}

// Accept rewritten text replacement
const handleAcceptRewrite = (newText: string) => {
  if (!editorRef.value) return
  const start = editorRef.value.selectionStart
  const end = editorRef.value.selectionEnd
  
  const originVal = editorText.value
  editorText.value = originVal.substring(0, start) + newText + originVal.substring(end)
  
  // Auto-focus back to editor and select the new block
  nextTick(() => {
    if (editorRef.value) {
      editorRef.value.focus()
      editorRef.value.setSelectionRange(start, start + newText.length)
    }
  })
  
  ElMessage.success('已替换原段落！')
  showBubble.value = false
}

// Trigger AI inline expansion (continue writing)
const handleTriggerExpand = async () => {
  if (!editorRef.value || expanding.value) return
  expanding.value = true
  expandResult.value = ''
  
  const cursorPosition = editorRef.value.selectionStart
  const beforeText = editorText.value.substring(0, cursorPosition)
  
  try {
    const { data } = await inlineExpand({
      before_text: beforeText,
      chapter_id: activeChapterId.value,
      goal: currentChapter.value?.plan?.chapter_goal || ''
    })
    expandResult.value = data.expanded_text
    showExpandDialog.value = true
  } catch (e: any) {
    ElMessage.error('续写失败: ' + apiErrorMessage(e, '续写失败'))
  } finally {
    expanding.value = false
  }
}

// Accept AI expansion
const handleAcceptExpand = () => {
  if (!editorRef.value || !expandResult.value) return
  const cursorPosition = editorRef.value.selectionStart
  const originVal = editorText.value
  
  // Insert at cursor
  editorText.value = originVal.substring(0, cursorPosition) + expandResult.value + originVal.substring(cursorPosition)
  
  // Close dialog and focus back
  showExpandDialog.value = false
  const insertedLen = expandResult.value.length
  expandResult.value = ''
  
  nextTick(() => {
    if (editorRef.value) {
      editorRef.value.focus()
      editorRef.value.setSelectionRange(cursorPosition + insertedLen, cursorPosition + insertedLen)
    }
  })
  ElMessage.success('续写内容已插入！')
}

const {
  writeTheme,
  writeFontSize,
  writeLineHeight,
  writeIndent,
  writeTitleCenter,
  adjustTextareaHeight,
  loadVisualSettings,
} = useWritingVisualSettings({ editorRef, editorText })

// ---- AI Writing & Automatic Formatting ----
const writing = ref(false)
const writeDialogOpen = ref(false)
const chapterGoalForWrite = ref('')
let aiWritePollTimer: number | null = null

const stopAiWritePolling = () => {
  if (aiWritePollTimer) {
    window.clearInterval(aiWritePollTimer)
    aiWritePollTimer = null
  }
}

const pollAiWriteResult = (taskId: string, chapterId: string) => {
  stopAiWritePolling()
  aiWritePollTimer = window.setInterval(async () => {
    try {
      const { data } = await getTask(taskId)
      if (data.status === 'completed') {
        stopAiWritePolling()
        await loadChapter(chapterId)
        await fetchChapters()
        ElMessage.success('AI 写作已完成，正文已自动载入写作页。')
      } else if (data.status === 'failed') {
        stopAiWritePolling()
        ElMessage.error(data.error || 'AI 写作任务失败')
      }
    } catch {
      stopAiWritePolling()
    }
  }, 2000)
}

const handleTriggerWrite = async () => {
  if (!activeChapterId.value) return
  
  if (editorText.value.trim().length > 0) {
    try {
      await ElMessageBox.confirm(
        '该章节目前已有正文内容。触发 [AI 写作] 将重新生成整章并覆盖当前编辑内容（覆盖前系统会自动备份快照）。是否继续？',
        'AI 写作警告',
        {
          confirmButtonText: '继续',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      await createSnapshot(activeChapterId.value, { title: `AI写作前自动备份（原正文）` })
    } catch {
      return
    }
  }

  loadingEditor.value = true
  try {
    const { data } = await suggestChapterGoal(activeChapterId.value)
    chapterGoalForWrite.value = data.goal || ''
    writeDialogOpen.value = true
  } catch (e: any) {
    ElMessage.error('获取章节大纲目标失败: ' + apiErrorMessage(e, '获取章节大纲目标失败'))
  } finally {
    loadingEditor.value = false
  }
}

const handleStartAiWrite = async () => {
  if (!chapterGoalForWrite.value.trim()) {
    ElMessage.warning('章节写作目标不能为空')
    return
  }
  writing.value = true
  try {
    const { data } = await runChapter({
      chapter_id: activeChapterId.value,
      goal: chapterGoalForWrite.value,
      dry_run: false
    })
    pollAiWriteResult(data.id, activeChapterId.value)
    ElMessage.success('AI 写作任务已提交，完成后正文会自动载入当前写作页。')
    writeDialogOpen.value = false
  } catch (e: any) {
    ElMessage.error('启动 AI 写作失败: ' + apiErrorMessage(e, '启动 AI 写作失败'))
  } finally {
    writing.value = false
  }
}

const handleAutoFormat = () => {
  writeTitleCenter.value = true
  writeIndent.value = true

  if (editorText.value) {
    const lines = editorText.value.split('\n')
    const formattedLines = lines.map(line => {
      let trimmed = line.trim()
      trimmed = trimmed.replace(/^[ 　]+/g, '')
      return trimmed
    })
    
    let resultText = formattedLines.join('\n')
    resultText = resultText.replace(/\n{3,}/g, '\n\n')
    
    editorText.value = resultText
    nextTick(() => {
      adjustTextareaHeight()
    })
  }
  ElMessage.success('一键排版完成！已自动将标题居中并启用首行缩进。')
}

// ---- Snapshots / Time Machine State & Operations ----
const timeMachineOpen = ref(false)
const snapshotsList = ref<any[]>([])
const loadingSnapshots = ref(false)
const previewingSnapshot = ref<any>(null)
const showPreviewDialog = ref(false)

const handleOpenTimeMachine = async () => {
  if (!activeChapterId.value) return
  timeMachineOpen.value = true
  await fetchSnapshots()
}

const fetchSnapshots = async () => {
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

const handleManualSnapshot = () => {
  if (!activeChapterId.value) return
  ElMessageBox.prompt('请输入本次备份的描述备注', '保存手动快照', {
    confirmButtonText: '备份',
    cancelButtonText: '取消',
    inputValue: `手动备份于 ${new Date().toLocaleTimeString()}`,
    inputPattern: /.+/,
    inputErrorMessage: '备注不能为空'
  }).then(async ({ value }) => {
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
  }).catch(() => {})
}

const handlePreviewSnapshot = (snap: any) => {
  previewingSnapshot.value = snap
  showPreviewDialog.value = true
}

const handleRollback = (snap: any) => {
  ElMessageBox.confirm(
    `确认将当前章节内容回滚到 [${snap.title || snap.datetime}] 版本吗？这会覆盖编辑器当前的正文内容（回滚前系统会自动备份当前版本）。`,
    '版本回滚二次确认',
    {
      confirmButtonText: '确认回滚',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const currentTitle = currentChapter.value?.title || `第 ${activeChapterId.value} 章`
      await createSnapshot(activeChapterId.value, { title: `系统自动备份（回滚前：${currentTitle}）` })
      
      await rollbackSnapshot(activeChapterId.value, snap.timestamp)
      ElMessage.success('成功回滚到历史版本！')
      
      await loadChapter(activeChapterId.value)
      await fetchChapters()
      timeMachineOpen.value = false
      showPreviewDialog.value = false
    } catch (e: any) {
      ElMessage.error('回滚失败: ' + e.message)
    }
  }).catch(() => {})
}

const initProjectPlatformAndFeedback = async () => {
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
      
      fetchFeedback()
    }
  } catch (e: any) {
    console.error('Failed to init project platform/feedback:', e)
  }
}

const fetchFeedback = async () => {
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

const handlePlatformChange = async (platformName: string) => {
  if (!activeProjectId.value) return
  try {
    const { data } = await updateProjectPlatform(activeProjectId.value, platformName)
    activePlatform.value = data.platform
    const found = platformsList.value.find(p => p.name === platformName)
    if (found) {
      activePlatformLabel.value = found.label
    }
    ElMessage.success(`目标平台成功切换为 [${activePlatformLabel.value}]，大纲与生成约束已同步重载！`)
  } catch (e: any) {
    ElMessage.error('切换平台失败: ' + e.message)
  }
}

const submitFeedback = async () => {
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
      active_readers: feedbackForm.value.active_readers
    })
    ElMessage.success('读者反馈模拟数据录入成功！')
    fetchFeedback()
  } catch (e: any) {
    ElMessage.error('录入失败: ' + e.message)
  }
}

const runGoldenCheck = async () => {
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

const handleForceRefresh = async () => {
  if (!activeChapterId.value) return
  try {
    await loadChapter(activeChapterId.value)
    ElMessage.success('当前章节内容已重新载入！')
  } catch (error: any) {
    ElMessage.error('刷新失败：' + error.message)
  }
}

const handleGoldenRewrite = async () => {
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
        type: 'warning'
      }
    )
  } catch {
    return
  }

  loadingEditor.value = true
  try {
    // 1. 创建备份快照
    const snapshotTitle = `【黄金三章重写前备份】推荐分：${goldenCheckResult.value.overall_score}`
    await createSnapshot(activeChapterId.value, { title: snapshotTitle })
    
    // 2. 拼接目标建议
    const suggestionsStr = goldenCheckResult.value.suggestions.join('；')
    const rewriteGoal = `【黄金三章整改优化】：${suggestionsStr}`
    
    // 3. 提交重写任务
    await runChapter({
      chapter_id: activeChapterId.value,
      goal: rewriteGoal,
      dry_run: false
    })
    
    ElNotification({
      title: '任务提交成功',
      message: `第 ${activeChapterId.value} 章的黄金三章整改重写任务已提交！请前往日志中心查看任务流水。`,
      type: 'success',
      duration: 5000
    })
  } catch (error: any) {
    ElMessage.error('优化重写失败: ' + error.message)
  } finally {
    loadingEditor.value = false
  }
}

// Auto-save timer
let autoSaveTimer: number | null = null
const openChapterFromQuery = async (raw: unknown) => {
  if (typeof raw !== 'string' || !raw.trim()) return
  const cid = raw.trim()
  if (chaptersList.value.some((ch) => ch.chapter_id === cid)) {
    await loadChapter(cid)
  }
}

watch(
  () => route.query.chapter,
  (chapter) => {
    void openChapterFromQuery(chapter)
  },
)

onMounted(async () => {
  loadVisualSettings()
  await fetchChapters()
  await openChapterFromQuery(route.query.chapter)
  initProjectPlatformAndFeedback()
  autoSaveTimer = window.setInterval(() => {
    handleSave(true)
  }, 60000) // Auto save every 60s
})

onBeforeUnmount(() => {
  stopAiWritePolling()
  if (autoSaveTimer) {
    window.clearInterval(autoSaveTimer)
  }
})
</script>

<template>
  <div class="workspace-page-container writing-page-shell">
    <!-- 左侧章节目录侧边栏 (可隐藏) -->
    <div class="chapter-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <span class="sidebar-title">📖 章节目录</span>
        <div style="display: flex; align-items: center; gap: 6px;">
          <el-button
            type="primary"
            size="small"
            circle
            :icon="Plus"
            :disabled="tasksStore.isRunning"
            @click="handleOpenCreateChapter"
            title="新建章节"
          />
          <el-button
            type="text"
            :icon="Fold"
            class="collapse-btn"
            @click="sidebarCollapsed = true"
            title="收起目录"
            style="margin: 0; padding: 4px;"
          />
        </div>
      </div>
      <div class="chapter-list-scroll">
        <div
          v-for="ch in chaptersList"
          :key="ch.chapter_id"
          class="chapter-item"
          :class="{ active: activeChapterId === ch.chapter_id }"
          @click="loadChapter(ch.chapter_id)"
        >
          <div class="chapter-item-header">
            <el-icon class="chapter-icon"><Document /></el-icon>
            <span class="chapter-item-title">{{ ch.chapter_id }}. {{ ch.title || '未命名章节' }}</span>
            <el-button
              class="chapter-delete-btn"
              type="danger"
              link
              :icon="Delete"
              title="删除章节"
              :disabled="tasksStore.isRunning"
              @click.stop="handleDeleteChapter(ch.chapter_id)"
            />
          </div>
          <span v-if="ch.word_count" class="chapter-item-wc">{{ ch.word_count }}字</span>
        </div>
      </div>
    </div>

    <!-- 左侧编辑器工作台 (弹性占位) -->
    <div class="editor-workspace">
      <!-- 中间主编辑器区域 -->
      <div class="editor-main-container" v-loading="loadingEditor">

        <div class="editor-header-actions glass-panel">
          <div class="left-chapter-meta" style="display: flex; align-items: center; gap: 10px; flex-shrink: 0; min-width: 200px;">
            <!-- 展开按钮 (折叠时显示) -->
            <el-button
              v-if="sidebarCollapsed"
              type="text"
              :icon="Expand"
              class="expand-sidebar-btn"
              @click="sidebarCollapsed = false"
              title="展开目录"
              style="font-size: 18px; padding: 0; margin-right: 4px; color: var(--color-text-muted);"
            />
            <div class="chapter-info">
              <span v-if="editorText" class="wc-label">共 <strong>{{ editorText.length }}</strong> 字符</span>
            </div>

            <!-- 目标写作平台选择 -->
            <div v-if="platformsList.length > 0" class="platform-selector-container" style="display: flex; align-items: center; gap: 6px; margin-left: 16px;">
              <el-dropdown trigger="click" @command="handlePlatformChange">
                <el-button size="small" type="success" plain class="premium-btn">
                  🎯 平台: {{ activePlatformLabel }}
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="p in platformsList"
                      :key="p.name"
                      :command="p.name"
                      :disabled="activePlatform === p.name"
                    >
                      <div style="width: 240px; display: flex; flex-direction: column; white-space: normal; padding: 6px 0; align-items: flex-start; text-align: left;">
                        <span style="font-weight: 600; font-size: 13px; color: var(--color-text-strong); display: flex; align-items: center; gap: 4px;">
                          🎯 {{ p.label }}
                        </span>
                        <div style="font-size: 11px; color: var(--color-text-muted); margin-top: 4px; line-height: 1.4; word-break: break-all;">
                          {{ p.style_prompt }}
                        </div>
                      </div>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <!-- 分支剧情选择下拉框 -->
            <div v-if="versionsList.length > 0" class="version-selector-container" style="display: flex; align-items: center; gap: 6px; margin-left: 12px;">
              <el-dropdown trigger="click" @command="handleVersionChange">
                <el-button size="small" type="warning" plain class="premium-btn">
                  🌿 分支: {{ activeVersion?.version_name || '未命名' }}
                  <span v-if="activeVersion?.is_active" style="margin-left:4px;font-size:10px;color:#67c23a;">(正史)</span>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="v in versionsList"
                      :key="v.id"
                      :command="v.id"
                    >
                      <div class="ver-item-drop" style="display:flex; align-items:center; justify-content:space-between; width:220px; gap:8px;">
                        <div style="flex:1; overflow:hidden;">
                          <div style="font-weight:600; font-size:13px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
                            {{ v.version_name }}
                            <span v-if="v.is_active" style="margin-left:4px; color:#67c23a; font-size:10px;">[正史]</span>
                          </div>
                          <div style="font-size:11px; color:#909399; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" v-if="v.note">{{ v.note }}</div>
                        </div>
                        <div style="display:flex; gap:2px; flex-shrink:0;">
                          <el-button size="small" type="primary" link :icon="Check" v-if="!v.is_active" @click.stop="handleOpenCompare(v.id)" title="比对正史" style="padding:0 2px;" />
                          <el-button size="small" type="danger" link :icon="Delete" v-if="!v.is_active" @click.stop="handleDeleteVersion(v.id)" title="删除分支" style="padding:0 2px;" />
                        </div>
                      </div>
                    </el-dropdown-item>
                    <el-dropdown-item divided :command="null" @click="handleCreateVersion" style="color:var(--el-color-primary);">
                      ✨ 新建分支试写...
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button
                v-if="activeVersion && activeVersion.is_active === 0"
                size="small"
                type="success"
                @click="handleActivateVersion"
                title="采纳为本章的正史版本"
              >
                采纳为正史
              </el-button>
            </div>
          </div>
          <div class="action-buttons">
            <!-- 视效排版 Popover -->
            <el-popover placement="bottom" title="排版与视觉设置" :width="240" trigger="click">
              <template #reference>
                <el-button size="default" class="premium-btn">⚙️ 排版</el-button>
              </template>
              <div class="typography-settings">
                <div class="setting-item">
                  <span class="setting-label">护眼主题</span>
                  <div class="theme-options">
                    <button class="theme-opt white" :class="{ active: writeTheme === 'white' }" @click="writeTheme = 'white'">白</button>
                    <button class="theme-opt parchment" :class="{ active: writeTheme === 'parchment' }" @click="writeTheme = 'parchment'">黄</button>
                    <button class="theme-opt green" :class="{ active: writeTheme === 'green' }" @click="writeTheme = 'green'">绿</button>
                    <button class="theme-opt dark" :class="{ active: writeTheme === 'dark' }" @click="writeTheme = 'dark'">黑</button>
                  </div>
                </div>
                <div class="setting-item">
                  <span class="setting-label">字体大小 ({{ writeFontSize }}px)</span>
                  <el-slider v-model="writeFontSize" :min="14" :max="26" :step="1" />
                </div>
                <div class="setting-item">
                  <span class="setting-label">行高比例 ({{ writeLineHeight }})</span>
                  <el-slider v-model="writeLineHeight" :min="1.6" :max="2.6" :step="0.1" />
                </div>
                <div class="setting-item flex-between">
                  <span class="setting-label">首行缩进 (两字符)</span>
                  <el-switch v-model="writeIndent" />
                </div>
                <el-button type="primary" size="small" style="width: 100%; margin-top: 10px;" :disabled="tasksStore.isRunning" @click="handleAutoFormat">一键排版</el-button>
              </div>
            </el-popover>

            <!-- 备份当前快照按钮 -->
            <el-button
              type="info"
              size="default"
              class="premium-btn"
              :disabled="tasksStore.isRunning"
              @click="handleManualSnapshot"
              title="保存手动快照"
            >
              💾 手动快照
            </el-button>

            <el-button
              size="default"
              class="premium-btn btn-save"
              :loading="saving"
              :disabled="tasksStore.isRunning"
              @click="handleSave()"
            >
              💾 保存章节
            </el-button>

            <!-- 强制刷新当前章节按钮 -->
            <el-button
              type="info"
              size="default"
              class="premium-btn"
              @click="handleForceRefresh"
              title="重新加载当前章节内容"
            >
              🔄 刷新
            </el-button>

            <!-- 历史快照时光机 -->
            <el-button
              type="warning"
              size="default"
              class="premium-btn"
              @click="handleOpenTimeMachine"
              title="版本时光机"
            >
              ⏳ 历史
            </el-button>
            <el-button
              type="primary"
              size="default"
              class="premium-btn btn-ai"
              :loading="loadingEditor"
              :disabled="tasksStore.isRunning"
              @click="handleTriggerWrite"
            >
              <span class="ai-sparkle">🤖</span> AI 写作
            </el-button>
          </div>
        </div>

        <!-- 文本书写滚动容器与稿纸信纸 -->
        <div class="textarea-scroll-container" :class="`theme-${writeTheme}`">
          <div class="zen-paper-sheet">
            <input
              v-if="currentChapter"
              v-model="currentChapter.title"
              class="chapter-title-input"
              :class="{ 'text-center': writeTitleCenter }"
              placeholder="请输入章节名称..."
            />
            <textarea
              ref="editorRef"
              v-model="editorText"
              class="zen-textarea"
              :class="{ 'indent-active': writeIndent }"
              :style="{ fontSize: `${writeFontSize}px`, lineHeight: writeLineHeight }"
              placeholder="在此开始你的小说创作吧... 支持拖动或选中文字使用 AI 智能润色修改。"
              @keydown="handleKeyDown"
              @mouseup="handleTextSelection"
              @keyup="handleTextSelection"
              @input="adjustTextareaHeight"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧辅助看板 -->
    <el-button
      v-if="rightSidebarCollapsed"
      class="right-sidebar-expand"
      :icon="Expand"
      circle
      title="展开辅助栏"
      @click="rightSidebarCollapsed = false"
    />
    <div class="sidebar-workspace" :class="{ collapsed: rightSidebarCollapsed }">
      <div class="right-sidebar-tabs">
        <button class="tab-btn" :class="{ active: rightTab === 'assets' }" @click="rightTab = 'assets'">🏰 设定</button>
        <button class="tab-btn" :class="{ active: rightTab === 'scrapbook' }" @click="rightTab = 'scrapbook'">🗑️ 废稿</button>
        <button class="tab-btn" :class="{ active: rightTab === 'feedback' }" @click="rightTab = 'feedback'">📊 反馈</button>
        <button class="tab-btn" :class="{ active: rightTab === 'golden' }" @click="rightTab = 'golden'">✨ 黄金</button>
        <el-button class="right-sidebar-collapse" :icon="Fold" link title="隐藏辅助栏" @click="rightSidebarCollapsed = true" />
      </div>
      
      <div class="right-sidebar-content" v-show="rightTab === 'assets'">
        <AssetSidebar
          ref="assetSidebarRef"
          :chapter-id="activeChapterId"
          :chapter-goal="currentChapter?.plan?.chapter_goal || ''"
        />
      </div>
      
      <div class="right-sidebar-content scrapbook-panel" v-show="rightTab === 'scrapbook'">
        <div class="scrapbook-header">
          <el-input
            v-model="scrapbookQuery"
            placeholder="搜索废稿段落..."
            prefix-icon="Search"
            clearable
            @input="fetchScrapbook"
            size="small"
          />
        </div>
        <div class="scrapbook-list" v-loading="loadingScrapbook">
          <el-empty v-if="scrapbookList.length === 0" description="废稿库暂无此类检索内容" :image-size="60" />
          <div v-else class="scrapbook-card" v-for="(item, idx) in scrapbookList" :key="idx">
            <div class="scrapbook-card-header">
              <span class="sc-ch">CH {{ item.chapter_id }}</span>
              <span class="sc-ver">{{ item.version_name }}</span>
            </div>
            <div class="sc-note" v-if="item.note">走向: {{ item.note }}</div>
            <p class="sc-text">{{ item.text }}</p>
            <div class="sc-actions">
              <el-button size="small" type="primary" link @click="copyScrapbookText(item.text)">复制段落</el-button>
              <el-button size="small" type="success" link @click="insertScrapbookText(item.text)">插入编辑器</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 读者反馈 Tab 面板 -->
      <div class="right-sidebar-content feedback-panel" v-show="rightTab === 'feedback'" style="padding: 16px; display: flex; flex-direction: column; height: calc(100% - 40px); overflow-y: auto; box-sizing: border-box;">
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
          📊 追读与跳出率监控
        </div>
        
        <div v-loading="loadingFeedback" style="flex: 1; min-height: 200px;">
          <el-empty v-if="feedbackList.length === 0" description="暂无章节读者反馈数据" :image-size="60" />
          <div v-else style="display: flex; flex-direction: column; gap: 10px;">
            <div 
              v-for="item in feedbackList" 
              :key="item.id" 
              class="feedback-metric-card"
              style="border: 1px solid var(--color-border); border-radius: 8px; padding: 10px; background: var(--color-bg-surface);"
            >
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 600; font-size: 13px;">第 {{ item.chapter_id }} 章</span>
                <span 
                  :style="{
                    color: item.bounce_rate > 0.35 ? 'var(--color-danger)' : (item.bounce_rate > 0.25 ? 'var(--color-warning)' : 'var(--color-success)'),
                    fontWeight: 600,
                    fontSize: '11px'
                  }"
                >
                  {{ item.bounce_rate > 0.35 ? '🚨 重度危机' : (item.bounce_rate > 0.25 ? '⚠️ 中度警戒' : '✅ 节奏健康') }}
                </span>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; font-size: 11px; color: var(--color-text-muted);">
                <div>跳出率: <strong :style="{ color: item.bounce_rate > 0.25 ? 'var(--color-danger)' : 'var(--color-text-strong)' }">{{ (item.bounce_rate * 100).toFixed(1) }}%</strong></div>
                <div>追读率: <strong>{{ (item.retention_rate * 100).toFixed(1) }}%</strong></div>
                <div>读者数: <strong>{{ item.active_readers }}</strong></div>
              </div>
              <div v-if="item.bounce_rate > 0.25" style="margin-top:6px; font-size:10px; color:var(--color-danger); background:#fef2f2; padding:4px 6px; border-radius:4px;">
                💡 Agent 在本章后已自动调大剧情冲突密度与爆点权重！
              </div>
            </div>
          </div>
        </div>

        <!-- 模拟器反馈表单 -->
        <div style="border-top: 1px dashed var(--color-border); margin-top: 16px; padding-top: 16px;">
          <div style="font-weight: 600; font-size: 13px; margin-bottom: 12px; color: var(--color-text-muted);">
            🧪 读者数据模拟录入
          </div>
          <el-form label-width="70px" size="small">
            <el-form-item label="对应章节">
              <el-select v-model="feedbackForm.chapter_id" placeholder="选择章节" style="width:100%;">
                <el-option 
                  v-for="ch in chaptersList" 
                  :key="ch.chapter_id" 
                  :label="ch.title || `第 ${ch.chapter_id} 章`" 
                  :value="ch.chapter_id" 
                />
              </el-select>
            </el-form-item>
            <el-form-item label="跳出率">
              <el-slider v-model="feedbackForm.bounce_rate" :min="0" :max="1" :step="0.01" show-input :input-size="'small'" />
            </el-form-item>
            <el-form-item label="追读率">
              <el-slider v-model="feedbackForm.retention_rate" :min="0" :max="1" :step="0.01" show-input :input-size="'small'" />
            </el-form-item>
            <el-form-item label="活跃读者">
              <el-input-number v-model="feedbackForm.active_readers" :min="100" :max="1000000" style="width:100%;" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" style="width:100%;" @click="submitFeedback">提交模拟数据</el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 黄金三章质检 Tab 面板 -->
      <div class="right-sidebar-content golden-panel" v-show="rightTab === 'golden'" style="padding: 16px; display: flex; flex-direction: column; height: calc(100% - 40px); overflow-y: auto; box-sizing: border-box;">
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
          ✨ 黄金三章签约级诊断向导
        </div>
        
        <div style="margin-bottom: 16px;">
          <el-button 
            type="warning" 
            style="width: 100%; font-weight: 600;" 
            :loading="loadingGolden" 
            @click="runGoldenCheck"
          >
            🚀 开始黄金三章质检评估
          </el-button>
        </div>

        <div v-if="goldenCheckResult" style="display: flex; flex-direction: column; gap: 14px;">
          <div v-if="goldenCheckResult.status === 'pending'" style="font-size: 12px; color: #909399; text-align: center;">
            {{ goldenCheckResult.message }}
          </div>
          <div v-else-if="goldenCheckResult.status === 'success'">
            <!-- 总得分 -->
            <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 12px; background: #fffdf5; border: 1px solid #fef08a; border-radius: 8px; padding: 12px;">
              <span style="font-size: 11px; color: #854d0e;">前三章综合推荐分</span>
              <span style="font-size: 32px; font-weight: 800; color: var(--color-warning); margin: 4px 0;">{{ goldenCheckResult.overall_score }}</span>
              <span style="font-size: 12px; font-weight: 600; color: #3f3f46; text-align: center;">"{{ goldenCheckResult.summary }}"</span>
            </div>

            <!-- 检测项目 -->
            <div style="font-weight: 600; font-size: 12px; color: #4b5563; margin-bottom: 8px;">诊断拆解：</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div 
                v-for="(check, idx) in goldenCheckResult.checks" 
                :key="idx"
                style="border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px; background: #fefefe;"
              >
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-weight: 600; font-size: 12px; color: #1f2937;">{{ check.indicator }}</span>
                  <el-tag 
                    size="small" 
                    :type="check.status === 'pass' ? 'success' : (check.status === 'warning' ? 'warning' : 'danger')"
                  >
                    {{ check.score }}分
                  </el-tag>
                </div>
                <div style="font-size: 11px; color: #6b7280; line-height: 1.4;">{{ check.reason }}</div>
              </div>
            </div>

            <!-- 修改建议 -->
            <div style="font-weight: 600; font-size: 12px; color: #4b5563; margin-top: 14px; margin-bottom: 8px;">编辑部整改建议：</div>
            <ul style="margin: 0; padding-left: 18px; font-size: 11px; color: #4b5563; line-height: 1.5; display: flex; flex-direction: column; gap: 6px;">
              <li v-for="(sug, idx) in goldenCheckResult.suggestions" :key="idx">{{ sug }}</li>
            </ul>

            <!-- 一键重写按钮 -->
            <div v-if="['001', '002', '003', '1', '2', '3'].includes(activeChapterId)" style="margin-top: 20px; border-top: 1px solid var(--color-border); padding-top: 14px;">
              <el-button 
                type="danger" 
                style="width: 100%; font-weight: 600;" 
                @click="handleGoldenRewrite"
              >
                🔄 针对本章建议一键优化重写
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 选中文字悬浮 AI 气泡菜单 -->
    <AiBubbleMenu
      :visible="showBubble"
      :x="bubbleX"
      :y="bubbleY"
      :selected-text="selectedText"
      :chapter-id="activeChapterId"
      :chapter-goal="currentChapter?.plan?.chapter_goal || ''"
      @accept="handleAcceptRewrite"
      @close="showBubble = false"
      @expand="handleTriggerExpand"
    />

    <!-- AI 续写结果预览对话框 -->
    <el-dialog
      v-model="showExpandDialog"
      title="🚀 AI 续写段落预览"
      width="450px"
      :close-on-click-modal="false"
    >
      <div class="expand-dialog-body">
        <div class="expand-result-box">
          {{ expandResult }}
        </div>
        <p class="dialog-tips">您可以选择采纳并直接插入到当前光标所在位置，或点击放弃。</p>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showExpandDialog = false; expandResult = ''">放弃</el-button>
          <el-button type="primary" @click="handleAcceptExpand">采纳并插入</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 历史快照抽屉 -->
    <el-drawer
      v-model="timeMachineOpen"
      title="⏳ 版本时光机"
      direction="rtl"
      size="380px"
      :append-to-body="true"
    >
      <div class="time-machine-drawer" v-loading="loadingSnapshots">
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 12px; color: var(--color-text-muted);">本地保留最近 30 次自动与手动备份</span>
          <el-button type="primary" size="small" :icon="Plus" @click="handleManualSnapshot">新建快照</el-button>
        </div>
        
        <el-empty v-if="snapshotsList.length === 0" description="暂无历史版本备份" :image-size="60" />
        <div v-else class="snapshots-list">
          <div
            v-for="snap in snapshotsList"
            :key="snap.timestamp"
            class="snapshot-card"
            :class="{ manual: snap.is_manual }"
          >
            <div class="snapshot-card-header">
              <span class="snapshot-title">{{ snap.title }}</span>
              <el-tag size="small" :type="snap.is_manual ? 'primary' : 'info'">
                {{ snap.is_manual ? '手动' : '自动' }}
              </el-tag>
            </div>
            <div class="snapshot-meta">
              <span>📅 {{ snap.datetime }}</span>
              <span>🔤 {{ snap.word_count }} 字</span>
            </div>
            <div class="snapshot-actions">
              <el-button size="small" link type="primary" @click="handlePreviewSnapshot(snap)">预览正文</el-button>
              <el-button size="small" link type="warning" @click="handleRollback(snap)">回滚到此版本</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 快照正文预览 Dialog -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="`预览备份: ${previewingSnapshot?.title || ''}`"
      width="600px"
      :append-to-body="true"
    >
      <div class="snapshot-preview-dialog-body" v-if="previewingSnapshot">
        <div class="preview-meta-bar">
          <span>备份时间：{{ previewingSnapshot.datetime }}</span>
          <span>字数统计：{{ previewingSnapshot.word_count }} 字</span>
        </div>
        <div class="preview-text-box">
          {{ previewingSnapshot.final_text || '（空正文）' }}
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showPreviewDialog = false">关闭预览</el-button>
          <el-button type="warning" @click="handleRollback(previewingSnapshot)">回滚到此版本</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 分支剧情差异 Diff 比对 Dialog -->
    <el-dialog
      v-model="compareDialogOpen"
      :title="`剧情分支比对: 正史版本 vs ${versionsList.find(v => v.id === compareVersionId)?.version_name || ''}`"
      width="750px"
      align-center
    >
      <div v-loading="loadingDiff" class="diff-dialog-body" style="max-height: 480px; overflow-y: auto; padding: 12px;">
        <div class="diff-legend" style="margin-bottom: 12px; display: flex; gap: 14px; font-size: 12px;">
          <span>标注说明:</span>
          <span style="color:var(--color-success); background-color:#d1fae5; padding:2px 6px; border-radius:4px; font-weight:600;">绿色表示分支新增字句</span>
          <span style="color:var(--color-danger); background-color:#fee2e2; padding:2px 6px; border-radius:4px; text-decoration:line-through;">红色表示分支删除/改写字句</span>
        </div>
        <div class="diff-container" style="white-space: pre-wrap; line-height: 1.8; font-size: 14px; background: #fafaf9; padding: 16px; border-radius: 8px; border: 1px solid var(--color-border);">
          <template v-for="(chunk, idx) in diffChunks" :key="idx">
            <span v-if="chunk.type === 'equal'" class="diff-text equal">{{ chunk.text }}</span>
            <del v-else-if="chunk.type === 'delete'" class="diff-text delete">{{ chunk.text }}</del>
            <ins v-else-if="chunk.type === 'insert'" class="diff-text insert">{{ chunk.text }}</ins>
          </template>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="compareDialogOpen = false">关闭比对</el-button>
          <el-button type="success" @click="compareDialogOpen = false; handleActivateVersion()">采纳该分支为正史</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- AI 写作输入对话框 -->
    <el-dialog
      v-model="writeDialogOpen"
      title="🤖 AI 快速写作"
      width="500px"
      :close-on-click-modal="false"
    >
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <p style="margin: 0; font-size: 13px; color: var(--color-text-muted); line-height: 1.6;">
          本功能将根据您设定的章节大纲目标，由 AI 快速撰写并填满当前章节。您可以对预设目标进行修改调整。
        </p>
        <el-input
          v-model="chapterGoalForWrite"
          type="textarea"
          :rows="6"
          placeholder="请输入本章详细的大纲与写作目标，例如：交代主角在坊市购买符笔的经过，并遇到竞争对手刁难..."
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="writeDialogOpen = false">取消</el-button>
          <el-button type="primary" :loading="writing" @click="handleStartAiWrite">开始写作</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workspace-page-container {
  display: flex;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
  background: var(--color-bg-hover); /* Slate background */
  font-family: "PingFang SC", "Lantinghei SC", "Microsoft YaHei", -apple-system, sans-serif;
}

/* Custom Scrollbars */
.chapter-list-scroll::-webkit-scrollbar,
.textarea-scroll-container::-webkit-scrollbar,
.expand-result-box::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.chapter-list-scroll::-webkit-scrollbar-thumb,
.textarea-scroll-container::-webkit-scrollbar-thumb,
.expand-result-box::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 99px;
}
.chapter-list-scroll::-webkit-scrollbar-thumb:hover,
.textarea-scroll-container::-webkit-scrollbar-thumb:hover,
.expand-result-box::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

/* 章节目录侧边栏 */
.chapter-sidebar {
  width: 240px;
  height: 100%;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
}
.chapter-sidebar.collapsed {
  width: 0;
  min-width: 0;
  border-right: none;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface-muted);
  flex-shrink: 0;
}
.sidebar-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: 0.05em;
}
.collapse-btn {
  color: var(--color-text-muted);
  padding: 4px;
  border-radius: 6px;
  transition: all 0.2s;
}
.collapse-btn:hover {
  background: var(--color-border);
  color: var(--color-text-strong);
}

.chapter-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  position: relative;
}
.chapter-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 3px;
  background: transparent;
  border-radius: 0 4px 4px 0;
  transition: all 0.2s;
}
.chapter-item:hover {
  background: var(--color-bg-hover);
}
.chapter-item.active {
  background: var(--color-bg-surface);
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
}
.chapter-item.active::before {
  background: var(--primary, #c66f4f);
}

.chapter-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.chapter-icon {
  font-size: 13px;
  color: var(--color-text-subtle);
  transition: color 0.2s;
}
.chapter-item.active .chapter-icon {
  color: var(--primary, #c66f4f);
}

.chapter-item-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s;
}
.chapter-delete-btn {
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.chapter-item:hover .chapter-delete-btn,
.chapter-item.active .chapter-delete-btn {
  opacity: 1;
}
.chapter-item.active .chapter-item-title {
  color: var(--color-text-strong);
}

.chapter-item-wc {
  align-self: flex-start;
  font-size: 10.5px;
  background: var(--color-border);
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  margin-left: 21px; /* Align with text under icon */
}

/* 左侧编辑器区域 */
.editor-workspace {
  flex: 3;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-bg-hover); /* Match outer page */
}

.editor-main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 悬浮毛玻璃工具控制条 */
.editor-header-actions.glass-panel {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 24px;
  margin: 16px 24px 0;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
  z-index: 10;
  flex-shrink: 0;
}

.left-chapter-meta {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  min-width: 200px;
  width: 100%;
  flex-wrap: wrap;
}
.chapter-info h2 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text-strong);
  font-weight: 800;
}
.wc-label {
  font-size: 11.5px;
  color: var(--color-text-muted);
  margin-top: 2px;
  display: block;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));
  gap: 10px;
  align-items: center;
  width: 100%;
  padding-top: 10px;
  border-top: 1px solid rgba(226, 232, 240, 0.85);
}
.action-buttons .premium-btn {
  width: 100%;
  margin: 0;
}
.premium-btn {
  border-radius: 8px !important;
  font-weight: 700 !important;
  transition: all 0.2s ease !important;
}
.premium-btn:hover {
  transform: translateY(-1px);
}
.btn-ai {
  background: var(--gradient-ai) !important;
  border: 0 !important;
  color: var(--color-bg-surface) !important;
  box-shadow: 0 4px 12px var(--color-primary-muted);
}
.btn-save {
  background: var(--gradient-save) !important;
  border: 0 !important;
  color: var(--color-bg-surface) !important;
  box-shadow: 0 4px 12px var(--color-success-soft);
}
.btn-save:hover {
  box-shadow: 0 6px 16px var(--color-success-soft);
}
.btn-ai {
  order: -1;
}
.btn-ai:hover {
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
}
.ai-sparkle {
  margin-right: 4px;
}

/* 文本书写滚动容器与稿纸信纸 */
.textarea-scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 40px;
  display: flex;
  justify-content: center; /* Center horizontally */
  align-items: flex-start; /* Ensure children height can grow dynamically based on content */
}

.zen-paper-sheet {
  width: 100%;
  max-width: 820px;
  min-height: 100%;
  height: auto;
  background: var(--color-bg-surface);
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
  border: 1px solid rgba(226, 232, 240, 0.8);
  padding: 40px 50px 200px;
  box-sizing: border-box;
}

.chapter-title-input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-strong);
  padding: 0 0 16px 0;
  margin-bottom: 20px;
  border-bottom: 2px dashed var(--color-border);
  background: transparent;
  font-family: inherit;
}
.chapter-title-input::placeholder {
  color: var(--color-text-subtle);
  font-weight: normal;
}

.zen-textarea {
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: 0;
  resize: none;
  background: transparent;
  outline: none;
  font-family: "PingFang SC", "Lantinghei SC", "Microsoft YaHei", -apple-system, sans-serif;
  font-size: 16px;
  line-height: 2.0; /* Modern line-height for Chinese reading */
  letter-spacing: 0.03em;
  color: var(--color-text);
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
}

/* 右侧侧边栏区域 */
.sidebar-workspace {
  width: 320px; /* Locked width for visual consistency */
  height: 100%;
  overflow: hidden;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  transition: width 0.25s ease, border-left-width 0.25s ease;
}
.sidebar-workspace.collapsed {
  width: 0;
  border-left-width: 0;
}
.right-sidebar-expand {
  align-self: center;
  margin: 0 8px;
  flex-shrink: 0;
}
.right-sidebar-collapse {
  flex: none;
  margin-left: 2px;
}

/* Dialog and other styling refinements */
.expand-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.expand-result-box {
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 18px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
  max-height: 280px;
  overflow-y: auto;
}
.dialog-tips {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
}

/* Themes */
.textarea-scroll-container.theme-white {
  background: var(--color-bg-hover);
}
.textarea-scroll-container.theme-white .zen-paper-sheet {
  background: var(--color-bg-surface);
  border-color: rgba(226, 232, 240, 0.8);
}
.textarea-scroll-container.theme-white .zen-textarea,
.textarea-scroll-container.theme-white .chapter-title-input {
  color: var(--color-text);
}

.textarea-scroll-container.theme-parchment {
  background: #f1ebd9;
}
.textarea-scroll-container.theme-parchment .zen-paper-sheet {
  background: #fdfaf2;
  border-color: #e5d8b7;
  box-shadow: 0 10px 30px rgba(78, 52, 46, 0.05);
}
.textarea-scroll-container.theme-parchment .zen-textarea,
.textarea-scroll-container.theme-parchment .chapter-title-input {
  color: #4e342e;
}
.textarea-scroll-container.theme-parchment .chapter-title-input {
  border-bottom-color: #e5d8b7;
}

.textarea-scroll-container.theme-green {
  background: #d5ebd7;
}
.textarea-scroll-container.theme-green .zen-paper-sheet {
  background: #f1fcf3;
  border-color: #c0dfc5;
  box-shadow: 0 10px 30px rgba(27, 94, 32, 0.05);
}
.textarea-scroll-container.theme-green .zen-textarea,
.textarea-scroll-container.theme-green .chapter-title-input {
  color: #1b5e20;
}
.textarea-scroll-container.theme-green .chapter-title-input {
  border-bottom-color: #c0dfc5;
}

.textarea-scroll-container.theme-dark {
  background: var(--color-text-strong);
}
.textarea-scroll-container.theme-dark .zen-paper-sheet {
  background: var(--color-text-strong);
  border-color: var(--color-text);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
.textarea-scroll-container.theme-dark .zen-textarea,
.textarea-scroll-container.theme-dark .chapter-title-input {
  color: var(--color-border);
}
.textarea-scroll-container.theme-dark .chapter-title-input {
  border-bottom-color: var(--color-text);
}

/* Typography settings */
.typography-settings {
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.setting-item.flex-between {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}
.setting-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
}
.theme-options {
  display: flex;
  gap: 6px;
}
.theme-opt {
  flex: 1;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  outline: none;
  font-weight: 600;
  transition: all 0.2s;
}
.theme-opt.white { background: var(--color-bg-surface); color: var(--color-text); }
.theme-opt.parchment { background: #fdfaf2; color: #4e342e; border-color: #e5d8b7; }
.theme-opt.green { background: #f1fcf3; color: #1b5e20; border-color: #c0dfc5; }
.theme-opt.dark { background: var(--color-text-strong); color: var(--color-border); border-color: var(--color-text-muted); }
.theme-opt.active {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 2px var(--color-primary-muted);
}

/* Time machine drawer and snapshots */
.time-machine-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.snapshots-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
  padding-bottom: 20px;
}
.snapshot-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
}
.snapshot-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}
.snapshot-card.manual {
  border-left: 3px solid var(--color-primary);
}
/* 稿纸主题色块保持独立，不随全局暗色切换 */
.snapshot-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.snapshot-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}
.snapshot-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--color-text-muted);
}
.snapshot-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--color-bg-hover);
  padding-top: 8px;
  margin-top: 4px;
}

/* Preview snapshot */
.snapshot-preview-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.preview-meta-bar {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-muted);
  background: var(--color-bg-surface-muted);
  padding: 8px 12px;
  border-radius: 6px;
}
.preview-text-box {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

.indent-active {
  text-indent: 2em;
}

/* Multi-version and Scrapbook styles */
.right-sidebar-tabs {
  display: flex;
  background: var(--color-bg-surface-muted);
  border-bottom: 1px solid var(--color-border);
  padding: 4px;
}
.tab-btn {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}
.tab-btn:hover {
  background: var(--color-border-subtle);
  color: var(--color-text-strong);
}
.tab-btn.active {
  background: var(--color-bg-surface);
  color: var(--primary, #c66f4f);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.right-sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: calc(100% - 37px);
}
.scrapbook-panel {
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
}
.scrapbook-header {
  padding: 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
}
.scrapbook-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.scrapbook-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.scrapbook-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sc-ch {
  font-size: 11px;
  font-weight: 700;
  background: var(--color-border);
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
}
.sc-ver {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary, #c66f4f);
}
.sc-note {
  font-size: 11px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 4px 8px;
  border-radius: 4px;
}
.sc-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
}
.sc-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--color-bg-hover);
  padding-top: 8px;
}
.diff-container .diff-text.equal {
  color: var(--color-text);
}
.diff-container .diff-text.delete {
  color: var(--color-danger);
  background-color: #fee2e2;
  text-decoration: line-through;
  padding: 2px 0;
  border-radius: 2px;
  display: inline;
}
.diff-container .diff-text.insert {
  color: var(--color-success);
  background-color: #d1fae5;
  text-decoration: none;
  font-weight: 600;
  padding: 2px 0;
  border-radius: 2px;
  display: inline;
}

.chapter-title-input.text-center {
  text-align: center;
}
</style>
